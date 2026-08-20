#!/usr/bin/env python3
"""Maintain a local, quarantined ledger of cross-task learning candidates."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterator, Mapping, Sequence


LEGACY_SCHEMA_VERSION = 1
SCHEMA_VERSION = 2
SUPPORTED_SCHEMA_VERSIONS = {LEGACY_SCHEMA_VERSION, SCHEMA_VERSION}
PROVENANCE = {"verified", "sourced", "unverified"}
DISPOSITIONS = {"skip", "add", "merge", "supersede", "drop"}
PROMOTION_STATES = {
    "quarantined",
    "proposed",
    "approved",
    "promoted",
    "inconclusive",
    "rejected",
    "retired",
}
PENDING_STATES = {"quarantined", "proposed", "approved", "inconclusive"}
ADVERSE_STATES = {"inconclusive", "rejected", "retired"}
LIST_VIEWS = {"pending", "stale", "all", "awaiting-retest", "regressed", "awaiting-release"}
FRESH_PROMOTION_STATES = {"proposed", "approved", "promoted"}
TRANSITIONS = {
    "quarantined": {"proposed", "inconclusive", "rejected"},
    "proposed": {"approved", "inconclusive", "rejected", "retired"},
    "approved": {"promoted", "inconclusive", "rejected", "retired"},
    "promoted": {"rejected", "retired"},
    "inconclusive": {"proposed", "rejected", "retired"},
    "rejected": {"proposed", "inconclusive"},
    "retired": {"proposed", "inconclusive"},
}
STATE_DISPOSITIONS = {
    "proposed": {"add", "merge", "supersede"},
    "approved": {"add", "merge", "supersede"},
    "promoted": {"add", "merge", "supersede"},
    "inconclusive": {"skip"},
    "rejected": {"skip", "drop"},
    "retired": {"skip", "drop", "merge", "supersede"},
}

CANDIDATE_ID_RE = re.compile(r"^lc_[0-9a-f]{32}$")
SOURCE_KIND_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_CANDIDATES = 1_000
MAX_FILE_BYTES = 64 * 1024
MAX_SOURCE_REFS = 64
MAX_TRANSITIONS = 32
MAX_REVIEWS = 32
MAX_OBSERVATION_LENGTH = 1_000
FIELD_LIMITS = {
    "observation": MAX_OBSERVATION_LENGTH,
    "expected_behavior": 1_000,
    "scope": 500,
    "applicability": 500,
    "source_kind": 64,
    "source_reference": 500,
    "revision": 128,
    "environment": 256,
    "destination": 256,
    "owner": 128,
    "reason": 1_000,
    "version": 128,
    "reference": 500,
}
RETENTION_POLICY = "review-or-expire"
SENSITIVITY_STATEMENT = (
    "Operator attested that the candidate contains no raw transcripts, secrets, credentials, "
    "or executable instructions."
)

LEGACY_TOP_LEVEL_FIELDS = {
    "schema_version",
    "candidate_id",
    "created_at",
    "updated_at",
    "observation",
    "expected_behavior",
    "scope",
    "fingerprint",
    "evidence",
    "recurrence",
    "sensitivity_review",
    "promotion_state",
    "disposition",
    "destination",
    "owner",
    "reason",
    "transition_history",
    "applicability",
    "freshness",
    "retention",
}
TOP_LEVEL_FIELDS = LEGACY_TOP_LEVEL_FIELDS | {"review_history"}
SOURCE_FIELDS = {
    "provenance",
    "source_kind",
    "source_reference",
    "revision",
    "environment",
}
OBSERVED_SOURCE_FIELDS = SOURCE_FIELDS | {"observed_at"}
TRANSITION_FIELDS = {
    "at",
    "from",
    "to",
    "disposition",
    "destination",
    "owner",
    "reason",
}
REVIEW_FIELDS = {
    "at",
    "previous_review_at",
    "review_at",
    "owner",
    "reason",
}
# LOOP-001: merged != released. These blocks are additive and OPTIONAL on every schema version --
# an old record without them stays valid with no migration, because "was this promoted candidate
# ever released, and did the release hold up" is a fact layered on top of the existing promotion
# lifecycle, not a new promotion_state that would ripple through STATE_DISPOSITIONS and its two
# declared mirrors for no added power. `release_history` holds completed cycles: a candidate can
# legally reject and re-promote (the state machine already allows it), and a new promotion after
# the current release is a genuinely new cycle, not a correction of the old one -- so the old
# {release, retest} pair is archived verbatim rather than discarded or refused a second slot.
OPTIONAL_TOP_LEVEL_FIELDS = {"release", "retest", "release_history"}
RELEASE_FIELDS = {"version", "reference", "recorded_at"}
RETEST_FIELDS = {"result", "environment", "reference", "recorded_at"}
RETEST_RESULTS = {"pass", "fail", "inconclusive"}
RELEASE_HISTORY_ENTRY_FIELDS = {"release", "retest"}
MAX_RELEASE_HISTORY = 32

SECRET_PATTERNS = (
    re.compile(
        r"(?i)\b(?:api[_-]?(?:key|token)|authorization|credential|password|passwd|secret|token)"
        r"\s*[:=]\s*\S+"
    ),
    re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+\S+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s/:]+:[^\s/@]+@"),
)
EXECUTABLE_PATTERNS = (
    re.compile(r"(?i)(?:^|\s)(?:bash|sh|zsh|cmd(?:\.exe)?|powershell|pwsh)\s+(?:-c|/c|-command)\b"),
    re.compile(r"(?i)\bcurl\b[^\r\n]*(?:\||&&|;|--output|\s-o\s)"),
    re.compile(r"(?i)\bwget\b[^\r\n]*(?:\||&&|;|--output-document|\s-O\s)"),
    re.compile(r"(?:&&|\|\||`|\$\()"),
    re.compile(r"(?:^|\s)(?:\$|PS>)\s+\S+"),
    re.compile(
        r"(?i)^(?:python(?:3(?:\.\d+)?)?|node|npm|npx|git|make|docker|kubectl|terraform)"
        r"\s+(?:-|\S+\.(?:py|js|sh|ps1)\b|(?:run|exec|apply|destroy|push)\b)"
    ),
)


class LedgerError(ValueError):
    """The ledger or a requested operation violates its fail-closed contract."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise LedgerError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise LedgerError(f"{field} must be an ISO UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise LedgerError(f"{field} is not a valid timestamp") from exc
    return parsed.astimezone(timezone.utc)


def _is_link_or_reparse(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(metadata.st_mode):
        return True
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)


def _require_plain_directory(path: Path, field: str) -> None:
    if _is_link_or_reparse(path):
        raise LedgerError(f"{field} must not be a symlink or reparse point: {path}")
    if not path.exists() or not path.is_dir():
        raise LedgerError(f"{field} must be an existing directory: {path}")


def _require_mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise LedgerError(f"{field} must be an object")
    return value


def _exact_fields(value: Mapping[str, object], expected: set[str], field: str) -> None:
    unknown = set(value) - expected
    missing = expected - set(value)
    if unknown:
        raise LedgerError(f"unknown {field} fields: {sorted(unknown)}")
    if missing:
        raise LedgerError(f"missing {field} fields: {sorted(missing)}")


def _safe_text(value: object, field: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise LedgerError(f"{field} must be a non-empty string")
    limit = FIELD_LIMITS[field]
    if len(value) > limit:
        raise LedgerError(f"{field} exceeds the {limit}-character limit")
    if "\n" in value or "\r" in value:
        raise LedgerError(f"{field} must be a single line; raw transcripts are not ledger data")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise LedgerError(f"{field} contains control characters")
    for pattern in SECRET_PATTERNS:
        if pattern.search(value):
            raise LedgerError(f"{field} contains secret-like data and was rejected")
    for pattern in EXECUTABLE_PATTERNS:
        if pattern.search(value):
            raise LedgerError(f"{field} looks like executable instructions and was rejected")
    return value.strip()


def _validate_source(value: object, field: str = "evidence") -> dict[str, str | None]:
    source = _require_mapping(value, field)
    _exact_fields(source, SOURCE_FIELDS, field)
    provenance = source["provenance"]
    if provenance not in PROVENANCE:
        raise LedgerError(f"{field}.provenance must be one of {sorted(PROVENANCE)}")
    source_kind = _safe_text(source["source_kind"], "source_kind")
    if not SOURCE_KIND_RE.fullmatch(source_kind or ""):
        raise LedgerError(f"{field}.source_kind has an invalid identifier")
    return {
        "provenance": str(provenance),
        "source_kind": source_kind,
        "source_reference": _safe_text(source["source_reference"], "source_reference"),
        "revision": _safe_text(source["revision"], "revision", optional=True),
        "environment": _safe_text(source["environment"], "environment", optional=True),
    }


def _source_record(
    *,
    provenance: str,
    source_kind: str,
    source_reference: str,
    revision: str | None,
    environment: str | None,
) -> dict[str, str | None]:
    return _validate_source(
        {
            "provenance": provenance,
            "source_kind": source_kind,
            "source_reference": source_reference,
            "revision": revision,
            "environment": environment,
        }
    )


def _normalize_for_fingerprint(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.split())


def _fingerprint(material: Mapping[str, str]) -> str:
    encoded = json.dumps(
        {key: _normalize_for_fingerprint(value) for key, value in material.items()},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _legacy_candidate_fingerprint(
    observation: str,
    expected_behavior: str,
    scope: str,
) -> str:
    """Version-1 identity retained only so existing tracked records remain readable."""
    return _fingerprint(
        {
            "expected_behavior": expected_behavior,
            "observation": observation,
            "scope": scope,
        }
    )


def candidate_fingerprint(
    observation: str,
    expected_behavior: str,
    scope: str,
    applicability: str,
) -> str:
    """Stable recurrence identity, including where the claimed behavior applies."""
    return _fingerprint(
        {
            "applicability": applicability,
            "expected_behavior": expected_behavior,
            "observation": observation,
            "scope": scope,
        }
    )


def _source_identity(source: Mapping[str, object]) -> tuple[object, ...]:
    """Underlying evidence identity; changing its trust label is not a new occurrence."""
    return tuple(
        source[name]
        for name in ("source_kind", "source_reference", "revision", "environment")
    )


def _has_distinct_observation_after(
    observations: Sequence[tuple[datetime, tuple[object, ...]]],
    adverse_at: datetime,
) -> bool:
    identities_at_adverse = {
        identity for observed_at, identity in observations if observed_at <= adverse_at
    }
    return any(
        observed_at > adverse_at and identity not in identities_at_adverse
        for observed_at, identity in observations
    )


def _review_deadline_at(
    at: datetime,
    current_review_at: datetime,
    review_schedule: Sequence[tuple[datetime, datetime, datetime]],
) -> datetime:
    """Return the review deadline in force at ``at`` from an audited renewal chain."""
    deadline = review_schedule[0][1] if review_schedule else current_review_at
    for reviewed_at, _previous_deadline, renewed_deadline in review_schedule:
        if reviewed_at > at:
            break
        deadline = renewed_deadline
    return deadline


def _validate_candidate_id(value: object) -> str:
    if not isinstance(value, str) or not CANDIDATE_ID_RE.fullmatch(value):
        raise LedgerError("invalid candidate ID; expected lc_<32 lowercase hex characters>")
    return value


def _safe_positive_days(value: object, field: str, *, allow_zero: bool) -> int:
    lower = 0 if allow_zero else 1
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < lower
        or value > 3_650
    ):
        qualifier = "non-negative" if allow_zero else "positive"
        raise LedgerError(f"{field} must be a {qualifier} integer no greater than 3650")
    return value


def _validate_release_block(
    release: object,
    *,
    created: datetime,
    updated: datetime,
    history: Sequence[Mapping[str, object]],
    prefix: str,
) -> datetime:
    """Validate one release block's shape and its trace to a landed promotion; return its time.

    Shared by the current `release` block and every `release_history` entry so both obey the
    identical rule: released bytes must trace to a candidate that actually landed.
    """
    release = _require_mapping(release, prefix)
    _exact_fields(release, RELEASE_FIELDS, prefix)
    _safe_text(release["version"], "version")
    _safe_text(release["reference"], "reference")
    release_at = _parse_timestamp(release["recorded_at"], f"{prefix}.recorded_at")
    if release_at < created or release_at > updated:
        raise LedgerError(
            f"{prefix}.recorded_at must fall between candidate creation and the latest update"
        )
    if not any(
        item["to"] == "promoted"
        and _parse_timestamp(item["at"], "transition_history.at") <= release_at
        for item in history
    ):
        raise LedgerError(
            f"{prefix} requires a prior transition to promoted at or before it; released bytes "
            "must trace to a candidate that actually landed"
        )
    return release_at


def _validate_retest_block(
    retest: object,
    *,
    release_at: datetime,
    updated: datetime,
    prefix: str,
) -> None:
    """Validate one retest block's shape and its ordering against its own release."""
    retest = _require_mapping(retest, prefix)
    _exact_fields(retest, RETEST_FIELDS, prefix)
    # isinstance guard first, same as the promotion_state check below: an unhashable stored value
    # (a hand-edited list or dict) makes plain `in` on the RETEST_RESULTS set raise TypeError,
    # degrading `check`'s clean LedgerError into an unhandled traceback -- still fail-closed, but
    # with the wrong message.
    if not isinstance(retest["result"], str) or retest["result"] not in RETEST_RESULTS:
        raise LedgerError(f"{prefix}.result must be one of {sorted(RETEST_RESULTS)}")
    _safe_text(retest["environment"], "environment")
    _safe_text(retest["reference"], "reference")
    retest_at = _parse_timestamp(retest["recorded_at"], f"{prefix}.recorded_at")
    if retest_at < release_at or retest_at > updated:
        raise LedgerError(
            f"{prefix}.recorded_at must fall between its release record and the latest update"
        )


def validate_candidate(record: Mapping[str, object]) -> None:
    missing_core = LEGACY_TOP_LEVEL_FIELDS - set(record)
    if missing_core:
        raise LedgerError(f"missing candidate fields: {sorted(missing_core)}")
    schema_version = record.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version not in SUPPORTED_SCHEMA_VERSIONS
    ):
        raise LedgerError(f"unsupported schema_version: {schema_version!r}")
    expected_fields = (
        LEGACY_TOP_LEVEL_FIELDS if schema_version == LEGACY_SCHEMA_VERSION else TOP_LEVEL_FIELDS
    )
    # release/retest are the only fields allowed to be ABSENT here without loosening the exact
    # check for everything else: unlike _exact_fields's normal all-or-nothing contract, a candidate
    # written before LOOP-001 must keep validating with neither key present.
    unknown_fields = set(record) - expected_fields - OPTIONAL_TOP_LEVEL_FIELDS
    missing_fields = expected_fields - set(record)
    if unknown_fields:
        raise LedgerError(f"unknown candidate fields: {sorted(unknown_fields)}")
    if missing_fields:
        raise LedgerError(f"missing candidate fields: {sorted(missing_fields)}")
    candidate_id = _validate_candidate_id(record["candidate_id"])
    created = _parse_timestamp(record["created_at"], "created_at")
    updated = _parse_timestamp(record["updated_at"], "updated_at")
    if updated < created:
        raise LedgerError("updated_at cannot precede created_at")

    observation = _safe_text(record["observation"], "observation")
    expected = _safe_text(record["expected_behavior"], "expected_behavior")
    scope = _safe_text(record["scope"], "scope")
    applicability = _safe_text(record["applicability"], "applicability")
    fingerprint = record["fingerprint"]
    if not isinstance(fingerprint, str) or not SHA256_RE.fullmatch(fingerprint):
        raise LedgerError("fingerprint must be a lowercase SHA-256 digest")
    expected_fingerprint = (
        _legacy_candidate_fingerprint(observation or "", expected or "", scope or "")
        if schema_version == LEGACY_SCHEMA_VERSION
        else candidate_fingerprint(
            observation or "", expected or "", scope or "", applicability or ""
        )
    )
    if fingerprint != expected_fingerprint:
        raise LedgerError(f"candidate {candidate_id} fingerprint does not match its bounded claim")

    evidence = _validate_source(record["evidence"])
    recurrence = _require_mapping(record["recurrence"], "recurrence")
    _exact_fields(recurrence, {"count", "sources"}, "recurrence")
    sources = recurrence["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= MAX_SOURCE_REFS:
        raise LedgerError(f"recurrence.sources must contain 1 to {MAX_SOURCE_REFS} entries")
    if (
        not isinstance(recurrence["count"], int)
        or isinstance(recurrence["count"], bool)
        or recurrence["count"] != len(sources)
    ):
        raise LedgerError("recurrence.count must equal the number of compact source references")
    normalized_sources: list[dict[str, str | None]] = []
    source_keys: set[tuple[object, ...]] = set()
    source_observations: list[tuple[datetime, tuple[object, ...]]] = []
    last_observed = created
    for index, item in enumerate(sources):
        observed = _require_mapping(item, f"recurrence.sources[{index}]")
        _exact_fields(observed, OBSERVED_SOURCE_FIELDS, f"recurrence.sources[{index}]")
        observed_at = _parse_timestamp(
            observed["observed_at"], f"recurrence.sources[{index}].observed_at"
        )
        if observed_at < created or (index and observed_at < last_observed):
            raise LedgerError("recurrence source timestamps must be chronological")
        last_observed = observed_at
        normalized = _validate_source(
            {key: observed[key] for key in SOURCE_FIELDS},
            f"recurrence.sources[{index}]",
        )
        key = _source_identity(normalized)
        if key in source_keys:
            raise LedgerError(
                "recurrence contains the same underlying source more than once; changing only "
                "provenance does not establish recurrence"
            )
        source_keys.add(key)
        source_observations.append((observed_at, key))
        normalized_sources.append(normalized)
    if normalized_sources[0] != evidence or sources[0]["observed_at"] != record["created_at"]:
        raise LedgerError("evidence must match the first recurrence source")
    if last_observed > updated:
        raise LedgerError("updated_at cannot precede the latest recurrence source")

    review = _require_mapping(record["sensitivity_review"], "sensitivity_review")
    _exact_fields(
        review,
        {"attested", "attestation_count", "last_attested_at", "statement"},
        "sensitivity_review",
    )
    if review["attested"] is not True:
        raise LedgerError("sensitivity_review.attested must be true")
    if (
        not isinstance(review["attestation_count"], int)
        or isinstance(review["attestation_count"], bool)
        or review["attestation_count"] != len(sources)
    ):
        raise LedgerError("sensitivity review must cover every recurrence source")
    if review["statement"] != SENSITIVITY_STATEMENT:
        raise LedgerError("sensitivity_review.statement does not match the ledger contract")
    _parse_timestamp(review["last_attested_at"], "sensitivity_review.last_attested_at")
    if review["last_attested_at"] != sources[-1]["observed_at"]:
        raise LedgerError("the latest sensitivity attestation must match the latest source")

    state = record["promotion_state"]
    if not isinstance(state, str) or state not in PROMOTION_STATES:
        raise LedgerError(f"unknown promotion_state: {state!r}")
    history = record["transition_history"]
    if not isinstance(history, list) or len(history) > MAX_TRANSITIONS:
        raise LedgerError(f"transition_history must contain at most {MAX_TRANSITIONS} entries")
    if state == "quarantined":
        if history:
            raise LedgerError("a quarantined candidate cannot have transition history")
        if any(
            record[field] is not None
            for field in ("disposition", "destination", "owner", "reason")
        ):
            raise LedgerError("quarantined intake must have null triage fields")
    else:
        if not isinstance(record["disposition"], str) or record["disposition"] not in DISPOSITIONS:
            raise LedgerError("a triaged candidate must carry one allowed disposition")
        if record["disposition"] not in STATE_DISPOSITIONS[state]:
            raise LedgerError(
                f"disposition {record['disposition']!r} is not valid for promotion_state {state!r}"
            )
        for field in ("destination", "owner", "reason"):
            _safe_text(record[field], field)
        if not history:
            raise LedgerError("a triaged candidate must carry transition history")

    previous_state = "quarantined"
    previous_time = created
    for index, item in enumerate(history):
        transition = _require_mapping(item, f"transition_history[{index}]")
        _exact_fields(transition, TRANSITION_FIELDS, f"transition_history[{index}]")
        at = _parse_timestamp(transition["at"], f"transition_history[{index}].at")
        if at < previous_time:
            raise LedgerError("transition timestamps must be chronological")
        if transition["from"] != previous_state:
            raise LedgerError("transition history has a discontinuous promotion state")
        target = transition["to"]
        if not isinstance(target, str) or target not in TRANSITIONS[previous_state]:
            raise LedgerError(f"invalid promotion transition: {previous_state} -> {target}")
        if (
            previous_state in ADVERSE_STATES
            and target == "proposed"
            and not _has_distinct_observation_after(source_observations, previous_time)
        ):
            raise LedgerError(
                f"reopening {previous_state} to proposed requires a distinct fresh observation "
                "newer than the adverse transition"
            )
        if (
            not isinstance(transition["disposition"], str)
            or transition["disposition"] not in DISPOSITIONS
        ):
            raise LedgerError("each transition must carry exactly one allowed disposition")
        if transition["disposition"] not in STATE_DISPOSITIONS[target]:
            raise LedgerError(
                f"disposition {transition['disposition']!r} is not valid for "
                f"promotion_state {target!r}"
            )
        for field in ("destination", "owner", "reason"):
            _safe_text(transition[field], field)
        previous_state = str(target)
        previous_time = at
    if previous_time > updated:
        raise LedgerError("updated_at cannot precede the latest transition")
    if history:
        latest = history[-1]
        if state != latest["to"]:
            raise LedgerError("promotion_state must match the latest transition")
        for field in ("disposition", "destination", "owner", "reason"):
            if record[field] != latest[field]:
                raise LedgerError(f"{field} must match the latest transition")

    freshness = _require_mapping(record["freshness"], "freshness")
    _exact_fields(freshness, {"as_of", "review_at"}, "freshness")
    as_of = _parse_timestamp(freshness["as_of"], "freshness.as_of")
    review_at = _parse_timestamp(freshness["review_at"], "freshness.review_at")
    if as_of < created:
        raise LedgerError("freshness.as_of cannot precede candidate creation")
    if as_of > updated:
        raise LedgerError("freshness.as_of cannot follow updated_at")
    retention = _require_mapping(record["retention"], "retention")
    _exact_fields(retention, {"policy", "expires_at"}, "retention")
    if retention["policy"] != RETENTION_POLICY:
        raise LedgerError(f"retention.policy must be {RETENTION_POLICY!r}")
    expires_at = _parse_timestamp(retention["expires_at"], "retention.expires_at")
    if review_at < created or expires_at <= created or review_at > expires_at:
        raise LedgerError("retention must outlive creation and the scheduled review")

    review_history = [] if schema_version == LEGACY_SCHEMA_VERSION else record["review_history"]
    if not isinstance(review_history, list) or len(review_history) > MAX_REVIEWS:
        raise LedgerError(f"review_history must contain at most {MAX_REVIEWS} entries")
    review_schedule: list[tuple[datetime, datetime, datetime]] = []
    previous_review_at: datetime | None = None
    previous_review_time = created
    for index, item in enumerate(review_history):
        review = _require_mapping(item, f"review_history[{index}]")
        _exact_fields(review, REVIEW_FIELDS, f"review_history[{index}]")
        at = _parse_timestamp(review["at"], f"review_history[{index}].at")
        prior = _parse_timestamp(
            review["previous_review_at"], f"review_history[{index}].previous_review_at"
        )
        renewed = _parse_timestamp(review["review_at"], f"review_history[{index}].review_at")
        if at < previous_review_time or at > updated:
            raise LedgerError(
                "review history timestamps must be chronological and not in the future"
            )
        if previous_review_at is not None and prior != previous_review_at:
            raise LedgerError("review history has a discontinuous review_at chain")
        if prior < created or renewed <= prior or renewed <= at:
            raise LedgerError("each review must move review_at forward beyond the review time")
        if renewed > expires_at:
            raise LedgerError("a review cannot renew review_at beyond retention expiry")
        for field in ("owner", "reason"):
            _safe_text(review[field], field)
        review_schedule.append((at, prior, renewed))
        previous_review_at = renewed
        previous_review_time = at
    if review_history and review_at != previous_review_at:
        raise LedgerError("freshness.review_at must match the latest explicit review")

    # Staleness is a review trigger and a promotion gate. This consistency check rejects a
    # transition that contradicts the deadline recorded in the same file. The ledger is not an
    # authenticated store: a coherent edit to both deadline and history needs Git review/history,
    # not a stronger claim from self-consistent JSON. Adverse/subtractive transitions remain
    # available so obsolete data can be rejected or retired.
    for index, item in enumerate(history):
        target = item["to"]
        if target not in FRESH_PROMOTION_STATES:
            continue
        at = _parse_timestamp(item["at"], f"transition_history[{index}].at")
        deadline = _review_deadline_at(at, review_at, review_schedule)
        if at >= expires_at:
            raise LedgerError(
                f"transition to {target} occurred after retention expiry"
            )
        if at >= deadline:
            raise LedgerError(
                f"transition to {target} occurred while the candidate was stale; "
                "record an explicit review first"
            )

    # LOOP-001 acceptance: a released-version retest is required before a field-feedback item
    # closes as successful, and source-eval PASS is never reportable as released-artifact PASS.
    # Validating the ordering here -- not just the shape -- is what makes a hand-edited record
    # (a retest with no release, or a release stamped before the candidate ever landed) fail
    # `check` instead of silently certifying a lineage that could not have happened through the
    # CLI.
    release = record.get("release")
    release_at: datetime | None = None
    if release is not None:
        release_at = _validate_release_block(
            release, created=created, updated=updated, history=history, prefix="release"
        )

    retest = record.get("retest")
    if retest is not None:
        if release_at is None:
            raise LedgerError("a retest record requires an existing release record")
        _validate_retest_block(retest, release_at=release_at, updated=updated, prefix="retest")

    # A candidate can legally reject and re-promote (the state machine already allows it), and a
    # release recorded after that fresh promotion is a new cycle, not a correction of the old
    # one. `record_release` archives the completed {release, retest} pair here rather than
    # refusing a second release outright or silently overwriting the first; validating each
    # archived entry with the SAME rules as the current release/retest (same helpers) is what
    # stops a hand-edited history from smuggling in a release that never actually landed.
    release_history = record.get("release_history")
    if release_history is not None:
        if release_at is None:
            # The writer only ever archives while writing a new current release, so a stranded
            # history is proof of a hand edit -- and learning/README.md's rollback enumeration
            # promises readers this shape cannot validate. Without this check that promise was
            # writer-only prose reading as a reader guarantee (executed verification finding).
            raise LedgerError(
                "release_history requires a current release record; a history with no release "
                "can only come from a hand edit and would silently break the rollback "
                "enumeration the docs promise"
            )
        if not isinstance(release_history, list) or len(release_history) > MAX_RELEASE_HISTORY:
            raise LedgerError(
                f"release_history must contain at most {MAX_RELEASE_HISTORY} entries"
            )
        previous_entry_release_at: datetime | None = None
        for index, entry in enumerate(release_history):
            entry = _require_mapping(entry, f"release_history[{index}]")
            _exact_fields(
                entry, RELEASE_HISTORY_ENTRY_FIELDS, f"release_history[{index}]"
            )
            entry_release_at = _validate_release_block(
                entry["release"],
                created=created,
                updated=updated,
                history=history,
                prefix=f"release_history[{index}].release",
            )
            entry_retest = entry["retest"]
            if entry_retest is not None:
                _validate_retest_block(
                    entry_retest,
                    release_at=entry_release_at,
                    updated=updated,
                    prefix=f"release_history[{index}].retest",
                )
            if (
                previous_entry_release_at is not None
                and entry_release_at <= previous_entry_release_at
            ):
                raise LedgerError("release_history entries must be chronological")
            previous_entry_release_at = entry_release_at
        if (
            release_at is not None
            and previous_entry_release_at is not None
            and previous_entry_release_at >= release_at
        ):
            raise LedgerError("release_history entries must all predate the current release")


class LearningLedger:
    """One-writer store for learning candidates beneath a repository root."""

    def __init__(
        self,
        root: Path,
        *,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.root = Path(os.path.abspath(os.fspath(root)))
        self.now = now
        _require_plain_directory(self.root, "repository root")
        self.learning_dir = self._contained(self.root / "learning")
        self.candidates_dir = self._contained(self.learning_dir / "candidates")

    def _contained(self, path: Path) -> Path:
        absolute = Path(os.path.abspath(os.fspath(path)))
        try:
            common = Path(os.path.commonpath((self.root, absolute)))
        except ValueError as exc:
            raise LedgerError(f"ledger path escapes repository root: {path}") from exc
        if common != self.root:
            raise LedgerError(f"ledger path escapes repository root: {path}")
        return absolute

    def _prepare(self, *, create: bool) -> bool:
        _require_plain_directory(self.root, "repository root")
        for path, field in (
            (self.learning_dir, "learning directory"),
            (self.candidates_dir, "candidate directory"),
        ):
            if path.exists() or _is_link_or_reparse(path):
                _require_plain_directory(path, field)
            elif create:
                path.mkdir()
                _require_plain_directory(path, field)
            else:
                return False
        return True

    def _candidate_path(self, candidate_id: object) -> Path:
        validated = _validate_candidate_id(candidate_id)
        path = self._contained(self.candidates_dir / f"{validated}.json")
        if _is_link_or_reparse(path):
            raise LedgerError(f"candidate file must not be a symlink or reparse point: {path}")
        return path

    @contextmanager
    def _writer(self) -> Iterator[None]:
        self._prepare(create=True)
        lock_path = self._contained(self.candidates_dir / ".learning-ledger.lock")
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except FileExistsError as exc:
            raise LedgerError(
                "another ledger writer is active, or a crashed writer left the lock; "
                "do not mutate the ledger concurrently"
            ) from exc
        try:
            with os.fdopen(descriptor, "w", encoding="ascii") as handle:
                handle.write(f"pid={os.getpid()}\n")
                handle.flush()
                os.fsync(handle.fileno())
            yield
        finally:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    def _load_file(self, path: Path) -> dict[str, object]:
        if _is_link_or_reparse(path):
            raise LedgerError(f"candidate file must not be a symlink or reparse point: {path}")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
            with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
                metadata = os.fstat(handle.fileno())
                if not stat.S_ISREG(metadata.st_mode):
                    raise LedgerError(f"candidate path is not a regular file: {path}")
                if metadata.st_size > MAX_FILE_BYTES:
                    raise LedgerError(
                        f"candidate file exceeds the {MAX_FILE_BYTES}-byte limit: {path}"
                    )
                record = json.load(handle)
        except FileNotFoundError as exc:
            raise LedgerError(f"candidate does not exist: {path.stem}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise LedgerError(f"malformed JSON candidate: {path.name}") from exc
        if not isinstance(record, dict):
            raise LedgerError(f"candidate must be a JSON object: {path.name}")
        validate_candidate(record)
        if path.name != f"{record['candidate_id']}.json":
            raise LedgerError(f"candidate filename does not match its ID: {path.name}")
        return record

    def _load_all(self) -> list[dict[str, object]]:
        if not self._prepare(create=False):
            # Read paths used to treat a missing store as zero records, so a mispointed
            # --root was indistinguishable from a clean empty ledger and the fleet
            # validator's ledger gate would pass against the wrong tree. Intake still
            # creates the store (`_writer` uses create=True). An existing empty
            # candidates directory remains a real empty ledger.
            raise LedgerError(
                f"candidate store does not exist: {self.candidates_dir}. "
                "A missing store is not an empty ledger; a mispointed --root would "
                "otherwise report zero candidates."
            )
        records: list[dict[str, object]] = []
        for path in sorted(self.candidates_dir.iterdir(), key=lambda item: item.name):
            if path.name in {".gitkeep", ".learning-ledger.lock"}:
                if _is_link_or_reparse(path):
                    raise LedgerError(
                        f"learning/candidates/{path.name} must not be a symlink or reparse point"
                    )
                continue
            if not path.name.endswith(".json"):
                raise LedgerError(f"unexpected file in candidate ledger: {path.name}")
            records.append(self._load_file(path))
            if len(records) > MAX_CANDIDATES:
                raise LedgerError(f"candidate ledger exceeds the {MAX_CANDIDATES}-record limit")
        identities: dict[str, str] = {}
        for record in records:
            identity = candidate_fingerprint(
                str(record["observation"]),
                str(record["expected_behavior"]),
                str(record["scope"]),
                str(record["applicability"]),
            )
            previous = identities.get(identity)
            if previous is not None:
                raise LedgerError(
                    "duplicate recurrence identity in candidates "
                    f"{previous} and {record['candidate_id']}"
                )
            identities[identity] = str(record["candidate_id"])
        return records

    def _atomic_write(
        self,
        path: Path,
        record: Mapping[str, object],
        *,
        overwrite: bool,
    ) -> None:
        validate_candidate(record)
        payload = (
            json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        if len(payload) > MAX_FILE_BYTES:
            raise LedgerError(f"candidate exceeds the {MAX_FILE_BYTES}-byte file limit")
        if overwrite:
            if not path.exists() or _is_link_or_reparse(path):
                raise LedgerError(f"candidate cannot be atomically updated: {path.stem}")
        elif path.exists() or _is_link_or_reparse(path):
            raise LedgerError(f"candidate already exists; refusing to overwrite: {path.stem}")

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.stem}.",
            suffix=".tmp",
            dir=self.candidates_dir,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if overwrite:
                os.replace(temporary, path)
            else:
                try:
                    os.link(temporary, path)
                except FileExistsError as exc:
                    raise LedgerError(
                        f"candidate already exists; refusing to overwrite: {path.stem}"
                    ) from exc
                temporary.unlink()
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def add(
        self,
        *,
        provenance: str,
        source_kind: str,
        source_reference: str,
        observation: str,
        expected_behavior: str,
        scope: str,
        applicability: str,
        sensitivity_reviewed: bool,
        revision: str | None = None,
        environment: str | None = None,
        review_days: int = 30,
        retention_days: int = 365,
    ) -> dict[str, object]:
        if sensitivity_reviewed is not True:
            raise LedgerError("--sensitivity-reviewed is required before candidate intake")
        review_days = _safe_positive_days(review_days, "review_days", allow_zero=True)
        retention_days = _safe_positive_days(
            retention_days, "retention_days", allow_zero=False
        )
        if review_days >= retention_days:
            raise LedgerError("review_days must be less than retention_days")
        source = _source_record(
            provenance=provenance,
            source_kind=source_kind,
            source_reference=source_reference,
            revision=revision,
            environment=environment,
        )
        observation = _safe_text(observation, "observation") or ""
        expected_behavior = _safe_text(expected_behavior, "expected_behavior") or ""
        scope = _safe_text(scope, "scope") or ""
        applicability = _safe_text(applicability, "applicability") or ""
        fingerprint = candidate_fingerprint(
            observation, expected_behavior, scope, applicability
        )
        with self._writer():
            existing = self._load_all()
            if len(existing) >= MAX_CANDIDATES:
                raise LedgerError(f"candidate ledger reached its {MAX_CANDIDATES}-record limit")
            for record in existing:
                existing_identity = candidate_fingerprint(
                    str(record["observation"]),
                    str(record["expected_behavior"]),
                    str(record["scope"]),
                    str(record["applicability"]),
                )
                if existing_identity == fingerprint:
                    raise LedgerError(
                        "duplicate learning candidate; use observe with candidate ID "
                        f"{record['candidate_id']}"
                    )
            now = self.now()
            created_at = _timestamp(now)
            candidate_id = f"lc_{uuid.uuid4().hex}"
            record: dict[str, object] = {
                "schema_version": SCHEMA_VERSION,
                "candidate_id": candidate_id,
                "created_at": created_at,
                "updated_at": created_at,
                "observation": observation,
                "expected_behavior": expected_behavior,
                "scope": scope,
                "fingerprint": fingerprint,
                "evidence": source,
                "recurrence": {
                    "count": 1,
                    "sources": [{"observed_at": created_at, **source}],
                },
                "sensitivity_review": {
                    "attested": True,
                    "attestation_count": 1,
                    "last_attested_at": created_at,
                    "statement": SENSITIVITY_STATEMENT,
                },
                "promotion_state": "quarantined",
                "disposition": None,
                "destination": None,
                "owner": None,
                "reason": None,
                "transition_history": [],
                "review_history": [],
                "applicability": applicability,
                "freshness": {
                    "as_of": created_at,
                    "review_at": _timestamp(now + timedelta(days=review_days)),
                },
                "retention": {
                    "policy": RETENTION_POLICY,
                    "expires_at": _timestamp(now + timedelta(days=retention_days)),
                },
            }
            self._atomic_write(self._candidate_path(candidate_id), record, overwrite=False)
        return record

    def observe(
        self,
        candidate_id: str,
        *,
        provenance: str,
        source_kind: str,
        source_reference: str,
        sensitivity_reviewed: bool,
        revision: str | None = None,
        environment: str | None = None,
    ) -> dict[str, object]:
        candidate_id = _validate_candidate_id(candidate_id)
        if sensitivity_reviewed is not True:
            raise LedgerError("--sensitivity-reviewed is required before recording an observation")
        source = _source_record(
            provenance=provenance,
            source_kind=source_kind,
            source_reference=source_reference,
            revision=revision,
            environment=environment,
        )
        with self._writer():
            path = self._candidate_path(candidate_id)
            matches = [
                record
                for record in self._load_all()
                if record["candidate_id"] == candidate_id
            ]
            if not matches:
                raise LedgerError(f"candidate does not exist: {candidate_id}")
            record = copy.deepcopy(matches[0])
            recurrence = record["recurrence"]
            sources = recurrence["sources"]
            if len(sources) >= MAX_SOURCE_REFS:
                raise LedgerError(f"candidate reached its {MAX_SOURCE_REFS}-source limit")
            source_key = _source_identity(source)
            for prior in sources:
                prior_key = _source_identity(prior)
                if prior_key == source_key:
                    raise LedgerError(
                        "this underlying source observation is already recorded; changing only "
                        "provenance does not establish recurrence"
                    )
            now = self.now()
            if now < _parse_timestamp(record["updated_at"], "updated_at"):
                raise LedgerError("new observation time cannot precede the current record")
            observed_at = _timestamp(now)
            sources.append({"observed_at": observed_at, **source})
            recurrence["count"] = len(sources)
            review = record["sensitivity_review"]
            review["attestation_count"] = len(sources)
            review["last_attested_at"] = observed_at
            record["freshness"]["as_of"] = observed_at
            record["updated_at"] = observed_at
            self._atomic_write(path, record, overwrite=True)
        return record

    def transition(
        self,
        candidate_id: str,
        *,
        promotion_state: str,
        disposition: str,
        destination: str,
        owner: str,
        reason: str,
    ) -> dict[str, object]:
        candidate_id = _validate_candidate_id(candidate_id)
        if (
            not isinstance(promotion_state, str)
            or promotion_state not in PROMOTION_STATES - {"quarantined"}
        ):
            raise LedgerError(f"unknown transition target: {promotion_state!r}")
        if not isinstance(disposition, str) or disposition not in DISPOSITIONS:
            raise LedgerError(f"unknown disposition: {disposition!r}")
        if disposition not in STATE_DISPOSITIONS[promotion_state]:
            raise LedgerError(
                f"disposition {disposition!r} is not valid for "
                f"promotion_state {promotion_state!r}"
            )
        destination = _safe_text(destination, "destination") or ""
        owner = _safe_text(owner, "owner") or ""
        reason = _safe_text(reason, "reason") or ""
        with self._writer():
            path = self._candidate_path(candidate_id)
            matches = [
                record
                for record in self._load_all()
                if record["candidate_id"] == candidate_id
            ]
            if not matches:
                raise LedgerError(f"candidate does not exist: {candidate_id}")
            record = copy.deepcopy(matches[0])
            current = str(record["promotion_state"])
            if promotion_state not in TRANSITIONS[current]:
                raise LedgerError(f"invalid promotion transition: {current} -> {promotion_state}")
            now = self.now()
            if now < _parse_timestamp(record["updated_at"], "updated_at"):
                raise LedgerError("transition time cannot precede the current record")
            if promotion_state in FRESH_PROMOTION_STATES:
                review_at = _parse_timestamp(
                    record["freshness"]["review_at"], "freshness.review_at"
                )
                expires_at = _parse_timestamp(
                    record["retention"]["expires_at"], "retention.expires_at"
                )
                if now >= expires_at:
                    raise LedgerError(
                        f"cannot transition to {promotion_state}: candidate retention expired"
                    )
                if now >= review_at:
                    raise LedgerError(
                        f"cannot transition to {promotion_state}: candidate is stale; "
                        "record an explicit review first"
                    )
            history = record["transition_history"]
            if current in ADVERSE_STATES and promotion_state == "proposed":
                adverse_at = _parse_timestamp(history[-1]["at"], "latest adverse transition")
                observations = [
                    (
                        _parse_timestamp(source["observed_at"], "recurrence source observed_at"),
                        _source_identity(source),
                    )
                    for source in record["recurrence"]["sources"]
                ]
                if not _has_distinct_observation_after(observations, adverse_at):
                    raise LedgerError(
                        f"reopening {current} to proposed requires a distinct fresh observation "
                        "newer than the adverse transition"
                    )
            if len(history) >= MAX_TRANSITIONS:
                raise LedgerError(f"candidate reached its {MAX_TRANSITIONS}-transition limit")
            transitioned_at = _timestamp(now)
            entry = {
                "at": transitioned_at,
                "from": current,
                "to": promotion_state,
                "disposition": disposition,
                "destination": destination,
                "owner": owner,
                "reason": reason,
            }
            history.append(entry)
            record.update(
                {
                    "updated_at": transitioned_at,
                    "promotion_state": promotion_state,
                    "disposition": disposition,
                    "destination": destination,
                    "owner": owner,
                    "reason": reason,
                }
            )
            self._atomic_write(path, record, overwrite=True)
        return record

    def review(
        self,
        candidate_id: str,
        *,
        review_days: int,
        owner: str,
        reason: str,
    ) -> dict[str, object]:
        """Record an explicit review and renew review_at without inventing recurrence."""
        candidate_id = _validate_candidate_id(candidate_id)
        review_days = _safe_positive_days(review_days, "review_days", allow_zero=False)
        owner = _safe_text(owner, "owner") or ""
        reason = _safe_text(reason, "reason") or ""
        with self._writer():
            path = self._candidate_path(candidate_id)
            matches = [
                record
                for record in self._load_all()
                if record["candidate_id"] == candidate_id
            ]
            if not matches:
                raise LedgerError(f"candidate does not exist: {candidate_id}")
            record = copy.deepcopy(matches[0])
            now = self.now()
            updated_at = _parse_timestamp(record["updated_at"], "updated_at")
            if now < updated_at:
                raise LedgerError("review time cannot precede the current record")
            current_review_at = _parse_timestamp(
                record["freshness"]["review_at"], "freshness.review_at"
            )
            expires_at = _parse_timestamp(
                record["retention"]["expires_at"], "retention.expires_at"
            )
            if now >= expires_at:
                raise LedgerError("an expired candidate cannot renew review_at")
            renewed_at = now + timedelta(days=review_days)
            if renewed_at <= current_review_at:
                raise LedgerError("an explicit review must move review_at forward")
            if renewed_at > expires_at:
                raise LedgerError("a review cannot renew review_at beyond retention expiry")

            if record["schema_version"] == LEGACY_SCHEMA_VERSION:
                record["schema_version"] = SCHEMA_VERSION
                record["fingerprint"] = candidate_fingerprint(
                    str(record["observation"]),
                    str(record["expected_behavior"]),
                    str(record["scope"]),
                    str(record["applicability"]),
                )
                record["review_history"] = []
            review_history = record["review_history"]
            if len(review_history) >= MAX_REVIEWS:
                raise LedgerError(f"candidate reached its {MAX_REVIEWS}-review limit")
            reviewed_at = _timestamp(now)
            next_review_at = _timestamp(renewed_at)
            review_history.append(
                {
                    "at": reviewed_at,
                    "previous_review_at": record["freshness"]["review_at"],
                    "review_at": next_review_at,
                    "owner": owner,
                    "reason": reason,
                }
            )
            record["freshness"]["review_at"] = next_review_at
            record["updated_at"] = reviewed_at
            self._atomic_write(path, record, overwrite=True)
        return record

    def record_release(
        self,
        candidate_id: str,
        *,
        version: str,
        reference: str,
    ) -> dict[str, object]:
        """Stamp the released version a promoted candidate shipped in.

        Legal only on a currently-promoted candidate: an unlanded change has no released bytes to
        record. Within one promotion cycle a candidate carries at most one release -- a second
        call before any fresh promotion is refused, not a silent overwrite. But the state machine
        already allows a promoted candidate to reject and re-promote (fresh evidence required),
        and a release recorded after that later promotion is a genuinely new cycle: this archives
        the completed {release, retest} pair into `release_history` and starts a fresh current
        pair, so a second cycle's release is never simply unrecordable.

        Deliberately does not check `retention.expires_at`/`freshness.review_at`, unlike
        `transition()`'s FRESH_PROMOTION_STATES gate: this records a fact about what already
        shipped, not a new promotion judgment about the candidate's continued validity, so a
        stale or expired review window has nothing to say about whether a release may still be
        recorded.
        """
        candidate_id = _validate_candidate_id(candidate_id)
        version = _safe_text(version, "version") or ""
        reference = _safe_text(reference, "reference") or ""
        with self._writer():
            path = self._candidate_path(candidate_id)
            matches = [
                record
                for record in self._load_all()
                if record["candidate_id"] == candidate_id
            ]
            if not matches:
                raise LedgerError(f"candidate does not exist: {candidate_id}")
            record = copy.deepcopy(matches[0])
            if record["promotion_state"] != "promoted":
                raise LedgerError(
                    f"cannot record a release for {candidate_id}: promotion_state is "
                    f"{record['promotion_state']!r}, not 'promoted' -- an unlanded candidate has "
                    "no released bytes to record"
                )
            now = self.now()
            if now < _parse_timestamp(record["updated_at"], "updated_at"):
                raise LedgerError("release time cannot precede the current record")
            existing_release = record.get("release")
            if existing_release is not None:
                existing_release_at = _parse_timestamp(
                    existing_release["recorded_at"], "release.recorded_at"
                )
                latest_promoted_at = max(
                    (
                        _parse_timestamp(item["at"], "transition_history.at")
                        for item in record["transition_history"]
                        if item["to"] == "promoted"
                    ),
                    default=None,
                )
                if latest_promoted_at is None or latest_promoted_at <= existing_release_at:
                    raise LedgerError(
                        f"candidate {candidate_id} already carries a release record for this "
                        "promotion; a later release requires a fresh promotion first, not a "
                        "silent overwrite of this one"
                    )
                record.setdefault("release_history", []).append(
                    {"release": existing_release, "retest": record.pop("retest", None)}
                )
            recorded_at = _timestamp(now)
            record["release"] = {
                "version": version,
                "reference": reference,
                "recorded_at": recorded_at,
            }
            record["updated_at"] = recorded_at
            self._atomic_write(path, record, overwrite=True)
        return record

    def record_retest(
        self,
        candidate_id: str,
        *,
        result: str,
        environment: str,
        reference: str,
    ) -> dict[str, object]:
        """Stamp the downstream retest of a released candidate against its originating scenario.

        Legal only once a release is recorded -- source-eval PASS is never reportable as
        released-artifact PASS, so there is nothing to retest against before a release exists.
        `pass` and `fail` are settled and single-shot, same as release: a later retest belongs to
        a new candidate record (or, after a fresh promotion, a new `release_history` cycle --
        see `record_release`). `inconclusive` is not settled and may be re-recorded in place --
        it means the retest could not be run to a verdict (environment unavailable, scenario not
        yet reproducible), and without this exception the candidate would be stuck carrying an
        unsettled result forever, retriable nowhere and invisible to `awaiting-retest`.

        On a `fail` result the returned record carries an extra transient `regression` key (never
        written to disk -- attached after the persisted write) so a PROGRAMMATIC caller gets the
        same signal the CLI prints to stderr, instead of having to notice `retest.result == "fail"`
        on its own. `main()` prints from this key rather than re-deriving the message.

        Deliberately does not check `retention.expires_at`/`freshness.review_at`, same reasoning
        as `record_release`: a retest records what actually happened downstream, not a new
        promotion judgment, so it is not gated on the review/expiry clock that gates promotion.
        """
        candidate_id = _validate_candidate_id(candidate_id)
        if result not in RETEST_RESULTS:
            raise LedgerError(f"retest result must be one of {sorted(RETEST_RESULTS)}")
        environment = _safe_text(environment, "environment") or ""
        reference = _safe_text(reference, "reference") or ""
        with self._writer():
            path = self._candidate_path(candidate_id)
            matches = [
                record
                for record in self._load_all()
                if record["candidate_id"] == candidate_id
            ]
            if not matches:
                raise LedgerError(f"candidate does not exist: {candidate_id}")
            record = copy.deepcopy(matches[0])
            release = record.get("release")
            if release is None:
                raise LedgerError(
                    f"cannot record a retest for {candidate_id}: no release is recorded yet -- "
                    "source-eval PASS is never reportable as released-artifact PASS"
                )
            existing_retest = record.get("retest")
            if existing_retest is not None and existing_retest["result"] != "inconclusive":
                raise LedgerError(
                    f"candidate {candidate_id} already carries a settled retest record "
                    f"({existing_retest['result']!r}); a later retest is a new record's "
                    "business, not a silent overwrite of this one"
                )
            now = self.now()
            if now < _parse_timestamp(record["updated_at"], "updated_at"):
                raise LedgerError("retest time cannot precede the current record")
            release_at = _parse_timestamp(release["recorded_at"], "release.recorded_at")
            if now < release_at:
                raise LedgerError("retest time cannot precede its recorded release")
            recorded_at = _timestamp(now)
            record["retest"] = {
                "result": result,
                "environment": environment,
                "reference": reference,
                "recorded_at": recorded_at,
            }
            record["updated_at"] = recorded_at
            self._atomic_write(path, record, overwrite=True)
            # Attached AFTER the write: this key is never persisted, only returned. A fail here
            # is worse news than a source-eval fail because it slipped past every earlier gate on
            # a destination that already shipped -- a caller that only inspects retest.result
            # would have to know to check for "fail" specifically, so the signal is surfaced
            # explicitly instead of staying implicit in an enum value.
            if result == "fail":
                record["regression"] = {
                    "destination": record["destination"],
                    "environment": environment,
                    "reference": reference,
                    "message": (
                        f"REGRESSION: candidate {candidate_id}'s destination "
                        f"{record['destination']!r} regressed in the field "
                        f"(environment={environment!r}, reference={reference!r})"
                    ),
                }
        return record

    def check(self) -> list[dict[str, object]]:
        lock_path = self._contained(self.candidates_dir / ".learning-ledger.lock")
        if lock_path.exists() or _is_link_or_reparse(lock_path):
            raise LedgerError(
                "learning ledger writer lock is present; validation cannot certify a store while "
                "a writer may be active or a crashed writer may have left state behind"
            )
        return self._load_all()

    def list_records(self, view: str = "pending") -> list[dict[str, object]]:
        if view not in LIST_VIEWS:
            raise LedgerError(f"list view must be one of {sorted(LIST_VIEWS)}")
        now = self.now()
        summaries: list[dict[str, object]] = []
        for record in self._load_all():
            stale = _parse_timestamp(record["freshness"]["review_at"], "freshness.review_at") <= now
            if view == "pending" and record["promotion_state"] not in PENDING_STATES:
                continue
            if view == "stale" and not stale:
                continue
            # LOOP-001 spec item 5: retest discovery is pull-based, not scheduled. A release or
            # upgrade retro reads this view to find what it still owes a downstream retest --
            # nothing here starts a background process. An `inconclusive` retest is not settled
            # (the retest could not reach a verdict, not that it passed or failed), so it stays
            # in this backlog exactly like no retest at all -- otherwise recording the honest
            # "could not tell yet" result would be the one way to make an item unretriable.
            retest = record.get("retest")
            if view == "awaiting-retest" and not (
                record["promotion_state"] == "promoted"
                and record.get("release") is not None
                and (retest is None or retest["result"] == "inconclusive")
            ):
                continue
            # A `fail` retest is a live regression on a candidate whose destination already
            # shipped -- it stays discoverable here until an owner acts (rejects or retires the
            # candidate), which is the same "pull, don't schedule" discipline as awaiting-retest.
            if view == "regressed" and not (
                record["promotion_state"] == "promoted"
                and retest is not None
                and retest["result"] == "fail"
            ):
                continue
            # The merged-not-released backlog: a promoted candidate with no destination pattern
            # this module could reliably parse, so "promoted with no release block yet" is the
            # literal, unambiguous surface instead of guessing at the destination's shape.
            if view == "awaiting-release" and not (
                record["promotion_state"] == "promoted" and record.get("release") is None
            ):
                continue
            summaries.append(
                {
                    "candidate_id": record["candidate_id"],
                    "promotion_state": record["promotion_state"],
                    "disposition": record["disposition"],
                    "destination": record["destination"],
                    "owner": record["owner"],
                    "recurrence_count": record["recurrence"]["count"],
                    "review_at": record["freshness"]["review_at"],
                    "stale": stale,
                    "scope": record["scope"],
                    "observation": record["observation"],
                    "release": record.get("release"),
                    "retest": retest,
                }
            )
        return summaries


def _add_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provenance", choices=sorted(PROVENANCE), required=True)
    parser.add_argument("--source-kind", required=True)
    parser.add_argument("--source-reference", required=True)
    parser.add_argument("--revision")
    parser.add_argument("--environment")
    parser.add_argument(
        "--sensitivity-reviewed",
        action="store_true",
        required=True,
        help="attest that the submitted fields contain no sensitive or executable material",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="repository root")
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="quarantine a new learning candidate")
    _add_source_arguments(add)
    add.add_argument("--observation", required=True)
    add.add_argument("--expected-behavior", required=True)
    add.add_argument("--scope", required=True)
    add.add_argument("--applicability", required=True)
    add.add_argument("--review-days", type=int, default=30)
    add.add_argument("--retention-days", type=int, default=365)

    observe = commands.add_parser("observe", help="record another source for a candidate")
    observe.add_argument("candidate_id")
    _add_source_arguments(observe)

    transition = commands.add_parser("transition", help="triage or promote one candidate")
    transition.add_argument("candidate_id")
    transition.add_argument(
        "--promotion-state",
        choices=sorted(PROMOTION_STATES - {"quarantined"}),
        required=True,
    )
    transition.add_argument("--disposition", choices=sorted(DISPOSITIONS), required=True)
    transition.add_argument("--destination", required=True)
    transition.add_argument("--owner", required=True)
    transition.add_argument("--reason", required=True)

    review = commands.add_parser(
        "review",
        help="record an explicit review and renew review_at within retention",
    )
    review.add_argument("candidate_id")
    review.add_argument("--review-days", type=int, default=30)
    review.add_argument("--owner", required=True)
    review.add_argument("--reason", required=True)

    record_release = commands.add_parser(
        "record-release",
        help="stamp the plugin version a promoted candidate shipped in",
    )
    record_release.add_argument("candidate_id")
    record_release.add_argument("--version", required=True)
    record_release.add_argument("--reference", required=True)

    record_retest = commands.add_parser(
        "record-retest",
        help="stamp the downstream retest of a released candidate",
    )
    record_retest.add_argument("candidate_id")
    record_retest.add_argument("--result", choices=sorted(RETEST_RESULTS), required=True)
    record_retest.add_argument("--environment", required=True)
    record_retest.add_argument("--reference", required=True)

    listing = commands.add_parser(
        "list",
        help=(
            "surface pending, stale, all, awaiting-retest, regressed, or awaiting-release "
            "candidates"
        ),
    )
    listing.add_argument("--view", choices=sorted(LIST_VIEWS), default="pending")
    commands.add_parser("check", help="validate every candidate and fingerprint")
    return parser


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        ledger = LearningLedger(args.root)
        if args.command == "add":
            result = ledger.add(
                provenance=args.provenance,
                source_kind=args.source_kind,
                source_reference=args.source_reference,
                revision=args.revision,
                environment=args.environment,
                observation=args.observation,
                expected_behavior=args.expected_behavior,
                scope=args.scope,
                applicability=args.applicability,
                sensitivity_reviewed=args.sensitivity_reviewed,
                review_days=args.review_days,
                retention_days=args.retention_days,
            )
            _print_json(result)
        elif args.command == "observe":
            result = ledger.observe(
                args.candidate_id,
                provenance=args.provenance,
                source_kind=args.source_kind,
                source_reference=args.source_reference,
                revision=args.revision,
                environment=args.environment,
                sensitivity_reviewed=args.sensitivity_reviewed,
            )
            _print_json(result)
        elif args.command == "transition":
            result = ledger.transition(
                args.candidate_id,
                promotion_state=args.promotion_state,
                disposition=args.disposition,
                destination=args.destination,
                owner=args.owner,
                reason=args.reason,
            )
            _print_json(result)
        elif args.command == "review":
            result = ledger.review(
                args.candidate_id,
                review_days=args.review_days,
                owner=args.owner,
                reason=args.reason,
            )
            _print_json(result)
        elif args.command == "record-release":
            result = ledger.record_release(
                args.candidate_id,
                version=args.version,
                reference=args.reference,
            )
            _print_json(result)
        elif args.command == "record-retest":
            result = ledger.record_retest(
                args.candidate_id,
                result=args.result,
                environment=args.environment,
                reference=args.reference,
            )
            _print_json(result)
            # The method itself is the source of this signal (see its docstring), not main() --
            # a programmatic LearningLedger.record_retest caller gets the same "regression" key
            # this CLI prints from, instead of only a stderr line no library caller ever sees.
            regression = result.get("regression")
            if regression:
                print(regression["message"], file=sys.stderr)
        elif args.command == "list":
            _print_json(ledger.list_records(args.view))
        else:
            records = ledger.check()
            suffix = "" if len(records) == 1 else "s"
            print(f"OK: {len(records)} learning candidate{suffix} validated")
    except (LedgerError, OSError) as exc:
        print(f"learning-ledger error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
