# HANDOFF-001 Codex Terra paired evidence — 2026-08-11

This directory preserves the first paid paired capture for HANDOFF-001. It is evidence, not an
acceptance record: the candidate proves the producer improvement, while the other five cases need
better diagnostic evidence and oracle repair before their failures can be assigned to prompt text.

## Conditions

Both sides used the candidate evaluator and the same six case definitions. Only the selected
generated agent profiles changed between the two plugin revisions.

| Condition | Value |
|---|---|
| Runtime | Codex CLI 0.147.0 through ChatGPT subscription authentication |
| Requested model | `gpt-5.6-terra` |
| Requested reasoning effort | `medium` |
| Repetitions | 3 per case, 6 cases, 18 sessions per side |
| Execution | `concurrency=1`, 600-second timeout, read-only sandbox |
| Measurement | Subscription-backed same-runtime approximation |
| Baseline plugin | `4777df9cc97b5a855c2c7ba693ce990e4d6ee1c2` |
| Candidate plugin | `47fdaa6c50e168a67db0cc0b42bfc7f92c21da35` |

The artifacts record the requested model because Codex 0.147.0 JSONL does not independently
report the served model. The runner also cannot prove that no code-mode `exec`/`wait` call was
attempted, so this evidence is not Claude empty-tool parity. Both sides used the same controlled
machine and account, an empty MCP inventory before and after, and the same explicit provider,
authentication, sandbox, feature, and isolation settings.

## Artifacts and result

| Side | Tracked SHA-256 | Strict cases | Passing runs | Tokens | Duration sum |
|---|---|---:|---:|---:|---:|
| Baseline | `A42C9072F6A110687A95892476885303192D8DECA506FC2BE2E16FB109FF16DF` | 0/6 | 0/18 | 178,727 | 233,813 ms |
| Candidate | `8FB69B3908BED543173943D698EC3A27D6ADD465CC7BB8FF701B1D0E623AF593` | 1/6 | 4/18 | 185,175 | 216,687 ms |

Git normalizes tracked JSON to LF. The untouched Windows capture files used CRLF and had SHA-256
`1DBD3846BB44EF4FAA1D046F00FC1E96A56F219A2327302F703B551C7BA92D85` (baseline) and
`D35D3262DFF3F6C78749FBDB29EE94836F39109E24B75898CE73CEC4CA15F639` (candidate); only line
endings differ from the tracked artifacts.

| Case | Baseline | Candidate | Disposition |
|---|---:|---:|---|
| `handoff-producer-preserves-discovered-constraints` | 0/3 | 3/3 | Measured improvement; retain the producer change. |
| `handoff-discovery-is-evidence-and-capture-safe` | 0/3 | 0/3 | Fewer failed assertions, but aggregate output cannot distinguish text from grammar. |
| `handoff-first-artifact-keeps-open-work` | 0/3 | 1/3 | Mixed; the forbidden-completion oracle is negation-blind. |
| `handoff-simple-build-stays-short` | 0/3 | 0/3 | Shorter output, but the behavioral contract remains red. |
| `handoff-builder-echo-rejects-regression` | 0/3 | 0/3 | Unresolved; the co-occurrence oracle is negation-blind. |
| `handoff-reviewer-rejects-regression-test` | 0/3 | 0/3 | Unresolved; it shares the negation-blind co-occurrence oracle and lacks per-run responses. |

Candidate token use increased by 6,448 tokens (3.61%). The aggregate duration sum decreased by
17,126 ms (7.32%), but the per-run ranges overlap, so the plan does not permit a general faster
claim. Exact first-artifact and first-token latency remain unmeasured.

## Why this is not acceptance evidence yet

The benchmark artifact retains each case's union of failed assertions, not the final response or
the assertion result for each individual run. That is enough for a score, but not enough to decide
whether a remaining red is a prompt defect or a grader defect. Two unique forbidden-pattern
shapes, used by three case assertions, reject correct negated statements in offline controls:

- `Backups are not complete.` hits the forbidden completed-lane pattern.
- `String co-occurrence is not sufficient evidence.` hits the forbidden sufficient-evidence
  pattern.

The next change should repair those existing oracles and add opt-in diagnostic retention of the
final response plus per-run assertion results. It should not add another packet schema, validator,
or global gate. After the offline controls pass and the operator separately approves the spend,
run one retained Terra/medium diagnostic for each of the five unresolved cases: five paid sessions
for diagnosis, not acceptance. Use those exact responses to identify real text failures, edit only
the responsible prompt sentences, freeze the new hashes, and obtain separate authorization before
another paid paired capture.
