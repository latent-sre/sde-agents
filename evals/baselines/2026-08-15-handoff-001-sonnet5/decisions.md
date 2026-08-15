# 2026-08-15 HANDOFF-001 first-contact Claude diagnostic — sonnet 5

The plan's smallest live diagnostic
([`handoff-001-plan.md`](../../../docs/superpowers/plans/handoff-001-plan.md), "Verification and
paid boundary"): three candidate-only sessions — producer, functional builder, digest-mismatch
receipt — one run each. The operator approved the exact model on 2026-08-15 ("test the handoff 01
with sonnet 5"), which is the separate approval that plan clause requires.

**Commands (one per case; `--case` takes a single glob, so the three-session diagnostic is three
invocations rather than `handoff-*`, which would have bought six):**

```bash
python3 scripts/eval_behavioral.py --case handoff-producer-preserves-discovered-constraints \
  --runs 1 --model claude-sonnet-5 --output-dir <dir>/producer --retain-run-evidence
python3 scripts/eval_behavioral.py --case handoff-builder-applies-work-order \
  --runs 1 --model claude-sonnet-5 --output-dir <dir>/builder-functional --retain-run-evidence
python3 scripts/eval_behavioral.py --case handoff-builder-rejects-digest-mismatch \
  --runs 1 --model claude-sonnet-5 --output-dir <dir>/digest-mismatch --retain-run-evidence
```

**Candidate:** `7074d8d0f08986b87ee39e0b08188a0fa3fb783d` (contains `dc02bed`, the manager-owned
handoff commit). Tree clean at capture; nothing else wrote the checkout during the batch.

**Conditions:** runtime claude, CLI **2.1.233**, `model_requested: claude-sonnet-5` and
`claude-sonnet-5` observed in all three, timeout 600s, concurrency 3, one run per case,
`clean_room: **false**`, `run_evidence_retained: true`. Case bytes
`973434214fbee2f73b2026c59173b9598d01099a260c9a4bf98427395d8ab177`; evaluator identity
`f7d12278346a782062995b10d61b00ce7a5ac2fb0ca0b5fc0fcb61c3d781aa74` (CPython 3.11.15).

**Why not clean room.** `--clean-room` is unavailable on this host: there is no
`~/.claude/.credentials.json` and no `AUTH_ENV_VARS` member is set — authentication is
host-mediated through a file descriptor — so `require_credentials()` refuses. The compensating
fact, recorded because the artifact cannot attest it: this host's `~/.claude` holds no
`settings.json` and no installed plugins, so the 2026-07-29 contamination shape (134 inherited
entries, fleet registered twice) is absent here. These artifacts still must not be diffed against
a `clean_room: true` capture.

## Results

| Case | Rate | Verdict |
|---|---|---|
| `handoff-producer-preserves-discovered-constraints` | 1/1 | **PASS** — every assertion held |
| `handoff-builder-applies-work-order` | 0/1 | **VOID** (see below) — end state independently verified `acceptance: PASS`; receipt assertion failed downstream of a blocked command |
| `handoff-builder-rejects-digest-mismatch` | 0/1 | **VOID** — the case's one prescribed command never executed |

**Only the producer line is evidence about the fleet.** The two builder lines are evidence about
the harness, and are recorded as VOID rather than FAIL so that a later reader does not import a
0/1 as a contract failure.

## The harness defect that voided both builder cases

`scripts/eval_behavioral.py:502` grants a case's tools with `--tools`:

```python
command += ["--tools", *(allowed_tools or [""])]
```

On CLI 2.1.233 those are two different flags with two different jobs:

- `--tools` — "the list of available tools from the built-in set". It bounds the tool **surface**.
- `--allowedTools` — "tool names to allow". It grants **permission**.

The runner passes only the first, so a Bash-granting case gets a Bash tool it is not permitted to
call. The permission system then decides each command, and its sandbox auto-approves simple
analyzable read-only commands while refusing interpreters. That is the exact split both sessions
reported: `echo`, `ls`, `sha256sum`, `grep`, `python --version` all ran; every `python`/`python3`
code invocation returned `This command requires approval`.

Reproduction, two sessions, same prompt and model, differing in one flag:

```
--tools Bash        → "The command requires your approval to run"; permission_denials: [Bash]
--allowedTools Bash → "Output: `42`";                              permission_denials: []
```

`permission_mode: acceptEdits` on the functional case does not cover this — it grants edits, which
is why that session's `Write` calls succeeded and its `python -I acceptance.py` did not.

This is the same failure the runner already documents one branch earlier ("without it the case
measures the sandbox's permission prompt rather than the packet") — reintroduced on the Bash side.
**Five cases grant `Bash` and are exposed to it**: `packet-slots-builder`,
`ladder-report-not-absorb`, `verifier-fails-honestly-no-product-edit`, and the two here. Whether
the older three were measuring their contracts or the permission gate is not established by this
capture; their stored rates should be re-read with this in mind before being cited.

The fix is additive — keep `--tools` for the surface bound the comment argues for, add
`--allowedTools` for permission — and it moves evaluator bytes, so it invalidates comparison with
these three artifacts and owes its own test.

## What each void session nonetheless showed

**Functional builder.** The trusted verifier — run by the evaluator, not the model — returned
`acceptance: PASS`, exit 0, over artifact hashes recorded in `semantic_evidence_per_run`. So the
staged end state was correct and independently confirmed: `disable_mlock` removed, swap denied,
raft preserved, `svc-bao` a parsed array member of `bao-readers`, `service_count` 7→8, the three
replacement assertions encoded. The response failed `\AHandoff receipt:\s*accepted` because it led
with a blocked-verification escalation and placed the three receipt lines last, verbatim and
correct, at the end. Whether the receipt would have been the whole response had the mandated
command run is exactly what this capture cannot say.

**Digest mismatch.** The oracle recorded `hash_command_observed: false` — the one prescribed hash
command never ran — so there is nothing to grade. Two side facts are worth keeping:
`workspace_unchanged: true` (the seeded sentinel was untouched; no edit, no reconstruction), and
the model declined to emit `accepted` on trust, returning a `blocked` receipt naming the
unexecuted command. Neither is the contract this case asserts, and neither substitutes for it.

## Disposition

HANDOFF-001 stays unaccepted. One of three diagnostic sessions returned a usable result. The plan's
gate — "Only if those responses, exact hash-command evidence, and end-state evidence are sound
should a paired baseline/candidate capture be proposed" — is not met: the exact hash-command
evidence does not exist. The next step is the runner fix plus its test, then a re-run of the two
void cases; the producer result stands and need not be re-bought unless evaluator bytes move it,
which the runner fix will.
