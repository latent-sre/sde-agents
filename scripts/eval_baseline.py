"""Resolve whether a stored routing benchmark still covers the 'before' side of a paired run.

The eval-first law says a description edit owes a before/after routing diff. The 'before' side
is evidence about bytes, not the calendar: if nothing a benchmark measured has changed — same
cluster definition, same selected cases, same evaluator and graders, same plugin bytes — and
the conditions the operator intends match the recorded ones, that benchmark IS the before run,
already paid for. This resolver answers exactly that question offline. It recomputes the same
provenance identities the runner records — imported from eval_routing, never reimplemented, so
the hash semantics cannot fork — and compares them against every stored benchmark.json. It
never launches a session and never touches the network: a REUSABLE verdict spends nothing, and
a STALE verdict names what diverged so the operator knows why a fresh capture is owed.

Match policy (TIER-001 spec, operator-approved 2026-08-08): provenance exact on schema,
eval_sources, selection, evaluator, and the plugin content hash; conditions exact on
model_requested, clean_room, threshold, timeout_s. cli_version is advisory — the probe, not
the eval suite, owns CLI drift — so a mismatch is printed but does not stale the verdict.

Exit codes: 0 a reusable benchmark exists (newest path printed), 1 none does (divergences
printed per same-cluster candidate), 2 usage or provenance error.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_routing  # noqa: E402  (sibling module; scripts/ is not a package)

REPO = Path(__file__).resolve().parents[1]
EXACT_CONDITIONS = ("model_requested", "clean_room", "threshold", "timeout_s")


def desired_provenance(root: Path, cluster_path: Path, expression: str, limit: int) -> dict:
    """The provenance a run started right now would record — the comparison target."""
    spec = json.loads(cluster_path.read_text(encoding="utf-8"))
    cases = [case for case in spec.get("cases", [])
             if isinstance(case, dict) and fnmatch.fnmatch(str(case.get("id", "")), expression)]
    if limit:
        cases = cases[:limit]
    if not cases:
        raise eval_routing.ProvenanceError("no cases matched the selection expression")
    return eval_routing.benchmark_provenance(
        [cluster_path], cases, expression, root, limit,
        evaluator_paths=eval_routing.routing_evaluator_paths(),
    )


def provenance_divergences(stored: dict, desired: dict) -> list[str]:
    if stored.get("schema") != desired["schema"]:
        # Older schemas lack identities the policy compares; nothing else is worth naming.
        return [f"schema ({stored.get('schema')!r}, current is {desired['schema']!r})"]
    diverged = [key for key in ("eval_sources", "selection", "evaluator")
                if stored.get(key) != desired[key]]
    stored_plugin = stored.get("plugin")
    if (
        not isinstance(stored_plugin, dict)
        or stored_plugin.get("sha256") != desired["plugin"]["sha256"]
    ):
        diverged.append("plugin")
    return diverged


def condition_divergences(stored: dict, desired: dict) -> list[str]:
    return [f"{key} (stored {stored.get(key)!r}, requested {desired[key]!r})"
            for key in EXACT_CONDITIONS if stored.get(key) != desired[key]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("cluster", nargs="?",
                        default=str(REPO / "evals" / "routing" / "prompt-tooling.json"))
    parser.add_argument("--root", type=Path, default=REPO, help="repository root")
    parser.add_argument("--baselines-dir", type=Path, default=None,
                        help="benchmark store (default <root>/evals/baselines)")
    # Selection and conditions mirror eval_routing's flags and defaults exactly: the resolver
    # asks "would THIS invocation's before-run be redundant", so it must speak the same request.
    parser.add_argument("--case", default="*", help="glob over case ids (default all)")
    parser.add_argument("--limit", type=int, default=0, help="cap number of cases (0 = all)")
    parser.add_argument("--model", required=True,
                        help="model the paired run will pin (required: an unpinned run is not "
                             "comparison-grade, so it has no baseline to resolve)")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--clean-room", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    cluster_path = Path(args.cluster).resolve()
    baselines = (args.baselines_dir or root / "evals" / "baselines").resolve()
    try:
        desired = desired_provenance(root, cluster_path, args.case, args.limit)
        cluster_name = json.loads(cluster_path.read_text(encoding="utf-8")).get("cluster")
    except (OSError, ValueError, eval_routing.ProvenanceError) as exc:
        print(f"resolver error: {exc}", file=sys.stderr)
        return 2
    desired_conditions = {"model_requested": args.model, "clean_room": args.clean_room,
                          "threshold": args.threshold, "timeout_s": args.timeout}

    matches: list[Path] = []
    near_misses: list[tuple[Path, list[str]]] = []
    # Lexicographic order: baseline directories are date-prefixed by convention, and file
    # mtimes do not survive a fresh clone, so path order is the only stable notion of "newest".
    for path in sorted(baselines.rglob("benchmark.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print(f"warning: unreadable benchmark skipped: {path}", file=sys.stderr)
            continue
        if not isinstance(document, dict) or document.get("cluster") != cluster_name:
            continue
        stored_provenance = document.get("provenance")
        stored_conditions = document.get("conditions")
        if not isinstance(stored_provenance, dict) or not isinstance(stored_conditions, dict):
            near_misses.append((path, ["no recorded provenance/conditions — not a baseline"]))
            continue
        diverged = provenance_divergences(stored_provenance, desired)
        diverged += condition_divergences(stored_conditions, desired_conditions)
        if diverged:
            near_misses.append((path, diverged))
        else:
            matches.append(path)
            cli = stored_conditions.get("cli_version")
            if cli is not None:
                print(f"note: cli_version {cli!r} recorded (advisory only; the probe owns "
                      f"CLI drift)")

    if matches:
        print(f"REUSABLE {matches[-1]}")
        for extra in matches[:-1]:
            print(f"  also matching: {extra}")
        return 0
    print(f"STALE: no stored benchmark for cluster {cluster_name!r} matches the current bytes "
          f"and requested conditions; a fresh 'before' capture is owed.")
    for path, diverged in near_misses[-3:]:
        print(f"  {path}: diverged on {', '.join(diverged)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
