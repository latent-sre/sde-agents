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
REVIEW_SCHEMA_VERSION = 2
SCHEMA_VERSION = 3
SUPPORTED_SCHEMA_VERSIONS = {LEGACY_SCHEMA_VERSION, REVIEW_SCHEMA_VERSION, SCHEMA_VERSION}
PROVENANCE = {"verified", "sourced", "unverified"}
DISPOSITIONS = {"skip", "add", "merge", "supersede", "drop"}
PROMOTION_STATES = {
    "quarantined",
    "proposed",
    "approved",
    "promoted",
    "released",
    "inconclusive",
    "rejected",
    "retired",
}
PENDING_STATES = {"quarantined", "proposed", "approved", "inconclusive"}
# `promoted` is deliberately absent from PENDING_STATES: the candidate's decision queue really is
# done. What it still owes is a measurement, which the awaiting-retest view answers instead, so
# the drift report keeps meaning "someone must decide" rather than "someone must measure".
LIST_VIEWS = {"pending", "stale", "awaiting-retest", "all"}
ADVERSE_STATES = {"inconclusive", "rejected", "retired"}
FRESH_PROMOTION_STATES = {"proposed", "approved", "promoted", "released"}
TRANSITIONS = {
    "quarantined": {"proposed", "inconclusive", "rejected"},
    "proposed": {"approved", "inconclusive", "rejected", "retired"},
    "approved": {"promoted", "inconclusive", "rejected", "retired"},
    # `promoted` means the canonical change merged. It is deliberately NOT terminal: a candidate
    # can pass every source-level gate and still fail in the installed plugin, another host
    # adapter, or the workflow that reported it. `released` is the only state that records the
    # exact shipped version retested against the originating scenario.
    "promoted": {"released", "rejected", "retired"},
    "released": {"rejected", "retired"},
    "inconclusive": {"proposed", "rejected", "retired"},
    "rejected": {"proposed", "inconclusive"},
    "retired": {"proposed", "inconclusive"},
}
STATE_DISPOSITIONS = {
    "proposed": {"add", "merge", "supersede"},
    "approved": {"add", "merge", "supersede"},
    "promoted": {"add", "merge", "supersede"},
    "released": {"add", "merge", "supersede"},
    "inconclusive": {"skip"},
    "rejected": {"skip", "drop"},
    "retired": {"skip", "drop", "merge", "supersede"},
}
# A released-artifact retest is evidence about the bytes users received, so its result class is
# distinct from a source-level PASS. `waived` is the owner-approved escape hatch the closure rule
# names -- retest impossible or no longer applicable -- and it is recorded, never implied.
RETEST_RESULTS = {"pass", "fail", "waived"}
RETEST_CLOSING_RESULTS = {"pass", "waived"}
# The point of the gate is an EXACT released version. A loose token ("latest", "main", "current")
# would satisfy a non-empty-string check while naming nothing retestable, so the shape is pinned.
RELEASED_VERSION_RE = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z][0-9A-Za-z.-]*)?$")

CANDIDATE_ID_RE = re.compile(r"^lc_[0-9a-f]{32}$")
SOURCE_KIND_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_CANDIDATES = 1_000
MAX_FILE_BYTES = 64 * 1024
MAX_SOURCE_REFS = 64
MAX_TRANSITIONS = 32
MAX_REVIEWS = 32
# One release retest per shipped version, with room for a failed retest and its repair. A
# candidate needing more than this is not awaiting a retest; it is a different candidate.
MAX_RETESTS = 16
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
    "released_version": 64,
    "retest_environment": 256,
    "retest_evidence": 500,
    "rollback_trigger": 500,
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
RELEASE_TOP_LEVEL_FIELDS = TOP_LEVEL_FIELDS | {"retest_history"}
# Field sets are version-keyed rather than "legacy or current" so a record written before a
# shape extension stays readable exactly as written. A silent in-place migration of tracked
# records would be indistinguishable from a hand edit in the Git diff that is this store's only
# trust anchor.
SCHEMA_FIELDS = {
    LEGACY_SCHEMA_VERSION: LEGACY_TOP_LEVEL_FIELDS,
    REVIEW_SCHEMA_VERSION: TOP_LEVEL_FIELDS,
    SCHEMA_VERSION: RELEASE_TOP_LEVEL_FIELDS,
}
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
# A retest entry is evidence about ONE released artifact. Version, environment, result, and
# rollback trigger travel together because a result without the version it was measured on is
# exactly the source-PASS-reported-as-released-PASS confusion this record exists to prevent.
RETEST_FIELDS = {
    "at",
    "released_version",
    "environment",
    "result",
    "evidence",
    "rollback_trigger",
    "owner",
    "reason",
    "sensitivity_reviewed",
}

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


def _retest_closes_loop(retest: Mapping[str, object]) -> bool:
    """A retest that can carry a candidate to ``released``: it passed, or it was waived."""
    return retest.get("result") in RETEST_CLOSING_RESULTS


def _qualifying_retest_at(
    retests: Sequence[tuple[datetime, Mapping[str, object]]],
    promoted_at: datetime | None,
    release_at: datetime,
) -> bool:
    """True when a closing retest was recorded for the merge that is being released.

    The retest must land after the promotion it certifies and before the release transition.
    Without the lower bound, a candidate rejected after release could reopen, re-merge, and
    inherit the previous version's PASS -- a released-artifact result for bytes nobody ran.
    """
    return any(
        _retest_closes_loop(retest)
        and at <= release_at
        and (promoted_at is None or at >= promoted_at)
        for at, retest in retests
    )


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


def _upgrade_schema(record: dict[str, object]) -> None:
    """Bring one record to the current shape, only in a write that needs the newer fields.

    A record nobody touches keeps the exact bytes it was reviewed with, so an upgrade is never
    an invisible sweep across the store: it appears in the same diff as the command that needed
    the field.
    """
    if record["schema_version"] == SCHEMA_VERSION:
        return
    if record["schema_version"] == LEGACY_SCHEMA_VERSION:
        record["fingerprint"] = candidate_fingerprint(
            str(record["observation"]),
            str(record["expected_behavior"]),
            str(record["scope"]),
            str(record["applicability"]),
        )
    record["schema_version"] = SCHEMA_VERSION
    record.setdefault("review_history", [])
    record.setdefault("retest_history", [])


def _release_gate_state(
    record: Mapping[str, object],
) -> tuple[datetime | None, list[tuple[datetime, Mapping[str, object]]]]:
    """The two inputs the released gate reads: the merge being certified, and its retests.

    Both the gate in `transition` and the awaiting-retest view read this, so a candidate can
    never be listed as retested by one and blocked by the other.
    """
    promoted_at = next(
        (
            _parse_timestamp(item["at"], "transition_history[].at")
            for item in reversed(list(record["transition_history"]))
            if item["to"] == "promoted"
        ),
        None,
    )
    retests = [
        (_parse_timestamp(item["at"], "retest_history[].at"), item)
        for item in record.get("retest_history", [])
    ]
    return promoted_at, retests


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
    expected_fields = SCHEMA_FIELDS[schema_version]
    _exact_fields(record, expected_fields, "candidate")
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

    retest_history = record["retest_history"] if schema_version == SCHEMA_VERSION else []
    if not isinstance(retest_history, list) or len(retest_history) > MAX_RETESTS:
        raise LedgerError(f"retest_history must contain at most {MAX_RETESTS} entries")
    retests: list[tuple[datetime, Mapping[str, object]]] = []
    previous_retest_time = created
    for index, item in enumerate(retest_history):
        retest = _require_mapping(item, f"retest_history[{index}]")
        _exact_fields(retest, RETEST_FIELDS, f"retest_history[{index}]")
        at = _parse_timestamp(retest["at"], f"retest_history[{index}].at")
        if at < previous_retest_time or at > updated:
            raise LedgerError(
                "retest history timestamps must be chronological and not in the future"
            )
        released_version = _safe_text(retest["released_version"], "released_version")
        if not RELEASED_VERSION_RE.fullmatch(released_version or ""):
            raise LedgerError(
                f"retest_history[{index}].released_version must name one exact released version "
                "(for example 1.7.3); a moving label such as 'latest' records no retestable artifact"
            )
        if retest["result"] not in RETEST_RESULTS:
            raise LedgerError(
                f"retest_history[{index}].result must be one of {sorted(RETEST_RESULTS)}"
            )
        if retest["sensitivity_reviewed"] is not True:
            raise LedgerError(
                f"retest_history[{index}].sensitivity_reviewed must be true; a retest record is "
                "operator-attested evidence like every other ledger source"
            )
        _safe_text(retest["environment"], "retest_environment")
        _safe_text(retest["evidence"], "retest_evidence")
        _safe_text(retest["rollback_trigger"], "rollback_trigger")
        for field in ("owner", "reason"):
            _safe_text(retest[field], field)
        retests.append((at, retest))
        previous_retest_time = at

    # The closure rule, enforced on the record rather than only in the command that writes it:
    # `released` is reachable only with a released-artifact retest that passed or was explicitly
    # waived. Without this, a hand-edited record could claim the loop closed on a source-level
    # PASS -- the exact substitution the state exists to make impossible.
    promoted_at: datetime | None = None
    for index, item in enumerate(history):
        at = _parse_timestamp(item["at"], f"transition_history[{index}].at")
        if item["to"] == "promoted":
            promoted_at = at
        elif item["to"] == "released" and not _qualifying_retest_at(retests, promoted_at, at):
            raise LedgerError(
                "a released candidate must carry a passed or explicitly waived released-artifact "
                "retest recorded after the promotion it releases; source-level PASS is not a "
                "released-artifact PASS"
            )

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
            return []
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
                "retest_history": [],
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
            if promotion_state == "released":
                # Fail closed on the loop's last gate. A merge, green deterministic gates, and
                # adapter parity are all source-level evidence; none of them exercised the bytes
                # a user installs. The retest is recorded first, by `retest`, precisely so this
                # transition cannot be the place where a source PASS is relabelled.
                promoted_at, retests = _release_gate_state(record)
                if not _qualifying_retest_at(retests, promoted_at, now):
                    raise LedgerError(
                        "cannot transition to released: record a passed or explicitly waived "
                        "released-artifact retest of the exact shipped version first; a "
                        "source-level PASS is not a released-artifact PASS"
                    )
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

            if record["schema_version"] != SCHEMA_VERSION:
                _upgrade_schema(record)
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

    def retest(
        self,
        candidate_id: str,
        *,
        released_version: str,
        environment: str,
        result: str,
        evidence: str,
        rollback_trigger: str,
        owner: str,
        reason: str,
        sensitivity_reviewed: bool,
    ) -> dict[str, object]:
        """Attach one released-artifact retest: what shipped, where it ran, and what happened.

        This is an evidence command, like `observe`. It records a measurement and decides
        nothing: a failed retest does not demote the candidate and a passed one does not promote
        it. The lifecycle decision stays with `transition`, which is where an owner is named.
        """
        candidate_id = _validate_candidate_id(candidate_id)
        if sensitivity_reviewed is not True:
            raise LedgerError("--sensitivity-reviewed is required before recording a retest")
        if not isinstance(result, str) or result not in RETEST_RESULTS:
            raise LedgerError(f"retest result must be one of {sorted(RETEST_RESULTS)}")
        released_version = _safe_text(released_version, "released_version") or ""
        if not RELEASED_VERSION_RE.fullmatch(released_version):
            raise LedgerError(
                "released version must name one exact released version (for example 1.7.3); a "
                "moving label such as 'latest' records no retestable artifact"
            )
        environment = _safe_text(environment, "retest_environment") or ""
        evidence = _safe_text(evidence, "retest_evidence") or ""
        rollback_trigger = _safe_text(rollback_trigger, "rollback_trigger") or ""
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
            if current not in {"promoted", "released"}:
                raise LedgerError(
                    f"a {current} candidate has nothing released to retest; record the retest "
                    "after the change carrying it merges and ships"
                )
            now = self.now()
            if now < _parse_timestamp(record["updated_at"], "updated_at"):
                raise LedgerError("retest time cannot precede the current record")
            _upgrade_schema(record)
            retest_history = record["retest_history"]
            if len(retest_history) >= MAX_RETESTS:
                raise LedgerError(f"candidate reached its {MAX_RETESTS}-retest limit")
            retested_at = _timestamp(now)
            retest_history.append(
                {
                    "at": retested_at,
                    "released_version": released_version,
                    "environment": environment,
                    "result": result,
                    "evidence": evidence,
                    "rollback_trigger": rollback_trigger,
                    "owner": owner,
                    "reason": reason,
                    "sensitivity_reviewed": True,
                }
            )
            record["updated_at"] = retested_at
            self._atomic_write(path, record, overwrite=True)
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
            promoted_at, retests = _release_gate_state(record)
            # A merged candidate is the one state the loop used to lose: source gates are green,
            # the issue looks finished, and nothing names what is still owed. This view is the
            # query a release retro runs -- pulled, never scheduled. It holds a candidate until
            # the `released` transition, because a recorded retest that nobody acted on has not
            # closed anything either; `release_retested` says which of the two steps remains.
            merged_not_released = record["promotion_state"] == "promoted"
            release_retested = _qualifying_retest_at(retests, promoted_at, now)
            if view == "pending" and record["promotion_state"] not in PENDING_STATES:
                continue
            if view == "stale" and not stale:
                continue
            if view == "awaiting-retest" and not merged_not_released:
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
                    "release_retested": release_retested,
                    "scope": record["scope"],
                    "observation": record["observation"],
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

    retest = commands.add_parser(
        "retest",
        help="attach a released-artifact retest result to a promoted candidate",
    )
    retest.add_argument("candidate_id")
    retest.add_argument(
        "--released-version",
        required=True,
        help="the exact released version retested, for example 1.7.3",
    )
    retest.add_argument(
        "--environment",
        required=True,
        help="where the released artifact ran, for example 'installed plugin, codex host'",
    )
    retest.add_argument("--result", choices=sorted(RETEST_RESULTS), required=True)
    retest.add_argument("--evidence", required=True)
    retest.add_argument("--rollback-trigger", required=True)
    retest.add_argument("--owner", required=True)
    retest.add_argument("--reason", required=True)
    retest.add_argument(
        "--sensitivity-reviewed",
        action="store_true",
        required=True,
        help="attest that the submitted fields contain no sensitive or executable material",
    )

    listing = commands.add_parser(
        "list",
        help="surface pending, stale, awaiting-retest, or all candidates",
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
        elif args.command == "retest":
            result = ledger.retest(
                args.candidate_id,
                released_version=args.released_version,
                environment=args.environment,
                result=args.result,
                evidence=args.evidence,
                rollback_trigger=args.rollback_trigger,
                owner=args.owner,
                reason=args.reason,
                sensitivity_reviewed=args.sensitivity_reviewed,
            )
            _print_json(result)
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
