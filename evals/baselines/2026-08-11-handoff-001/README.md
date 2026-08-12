# HANDOFF-001 Codex Terra paired evidence — 2026-08-11

This directory preserves the initial paid pair, retained diagnostics, prompt smoke, and final paid
pair for HANDOFF-001. It is evidence, not an acceptance record: the producer improvement is
repeatable, but the final strict suite did not accept the round.

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
| Baseline | `7EC0E6DE9C584792684799BF8A290E44F7D2BD6609E094011120ED6816DE61A6` | 0/6 | 0/18 | 178,727 | 233,813 ms |
| Candidate | `8FB69B3908BED543173943D698EC3A27D6ADD465CC7BB8FF701B1D0E623AF593` | 1/6 | 4/18 | 185,175 | 216,687 ms |

Git normalizes tracked JSON to LF. The candidate artifacts differ from the original Windows capture
only by line endings. The baseline artifacts were later redacted to replace an operator-local
`plugin_dir` path with `<external-plugin-dir>`, so their tracked hash now reflects both LF
normalization and that path redaction. The original Windows capture SHA-256 values were
`1DBD3846BB44EF4FAA1D046F00FC1E96A56F219A2327302F703B551C7BA92D85` (baseline) and
`D35D3262DFF3F6C78749FBDB29EE94836F39109E24B75898CE73CEC4CA15F639` (candidate).

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

That measurement repair landed in `7126c8d`: the two negation-blind pattern shapes were repaired,
and `--retain-run-evidence` now records ordered response/assertion evidence only when explicitly
enabled. The default artifact still omits raw model text. The five-session diagnostic then showed
that discovery and first-artifact were semantically correct but lexically missed, simple-build
passed, and builder/reviewer had real omissions. The narrow consumer fixes landed in `0ea72de`;
the exact two prompt-smoke responses became semantically correct and regraded clean after the last
observed-form oracle repair in final candidate `ff51f42`.

## Retained diagnostic artifacts

These files contain synthetic model responses and were privacy-scanned before commit. No API key,
bearer/JWT, private key, email/account identifier, or resolved secret value was found.

| Capture | Purpose | Capture SHA-256 | Tracked LF SHA-256 |
|---|---|---|---|
| `codex-terra-diagnostic-7126c8d/benchmark.json` | Five unresolved cases, one run each | `CD1C8265C60A1BE6F909B84E02AB2B4C423297A15801E43ED67F99E56405DD18` | `963B1F794437B1F2F15E073AFF8C598E5F3B764642AE77D8397855A816C00D81` |
| `codex-terra-prompt-smoke-0ea72de/benchmark.json` | Builder and reviewer after prompt repair | `970AC17175CB860880A1B0000A9D3675BD3C9AC6EDE087B97936E68E085A746F` | `809E08B21891FC9D7455BCAA0A88740B2DC8F75E6195067056763A071C3020BE` |

## Final paired capture

Both sides used the evaluator and cases from `ff51f42`, `--retain-run-evidence`, Codex CLI 0.147.0,
requested `gpt-5.6-terra` at medium effort, three runs per case, `concurrency=1`, a 600-second
timeout, and the same controlled subscription/auth/isolation conditions. Only the selected profile
identity differed: baseline `4777df9`, candidate `ff51f42`.

| Side | Capture SHA-256 | Tracked LF SHA-256 | Strict cases | Passing runs | Tokens | Duration sum |
|---|---|---|---:|---:|---:|---:|
| Baseline | `6308507C365253BA097CF25779BF1D6FF9EF7E825B0243AF80F971A8057E2B68` | `E84E18E61B995C2FFE200907A3CA3F79608DE9BAFB7C652EBC902FC31DE542CC` | 0/6 | 1/18 | 178,749 | 270,078 ms |
| Candidate | `C93201146E725E07E4C85FBD4FBFACC8FD3EDD85AE76154A74F603BB029708B7` | `D1BE71B84E04803DDEFD69E86FB8DDD4F43EF7BCF4A5E82D3E094680073BD793` | 1/6 | 6/18 | 175,768 | 259,781 ms |

| Case | Baseline | Candidate | Retained-evidence disposition |
|---|---:|---:|---|
| `handoff-producer-preserves-discovered-constraints` | 0/3 | 3/3 | Accepted by the deterministic oracle; repeatable improvement. |
| `handoff-discovery-is-evidence-and-capture-safe` | 0/3 | 0/3 | All candidate responses reject skipped-result evidence and resolved secrets; relation wording still misses. |
| `handoff-first-artifact-keeps-open-work` | 1/3 | 1/3 | All responses retain owned lanes; two miss the expected state words, and one invents removed `-verify-only` behavior. |
| `handoff-simple-build-stays-short` | 0/3 | 0/3 | All responses include health, an internal request/consumer check, and separately approved activation; literal relation words still miss. |
| `handoff-builder-echo-rejects-regression` | 0/3 | 1/3 | Both non-empty responses preserve the handoff; one run had no terminal success and one authority relation misses word order. |
| `handoff-reviewer-rejects-regression-test` | 0/3 | 1/3 | All responses reject both regressions; two use `independent string presence`, outside the lexical relation pattern. |

Candidate usage decreased by 2,981 tokens (1.67%) and summed runner wall-clock duration decreased
by 10,297 ms (3.81%). The overall evidence does not support a general faster claim. Only the
simple-build duration ranges do not overlap in the candidate's favor, and that case remained
strict-red, so speed is not an acceptance result.

## Decision

HANDOFF-001 remains active and is **not accepted**. Keep the producer and consumer prompt changes:
the producer is 3/3, and retained builder/reviewer responses show the intended behavior. Do not buy
another paired batch or keep extending regex windows. Before more model spend, add an offline
replay/regrade path for retained responses, simplify the five brittle relationship assertions using
their existing wrong-direction controls, and make the first-artifact case explicitly reject the
removed `-verify-only` behavior it surfaced. A later paid pair needs a fresh operator approval.
