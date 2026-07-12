<!--
Independent multi-agent audit of latent-sre/sde-agents
Generated 2026-07-12 by a 12-reviewer workflow (5 deep + 3 devil's-advocate + 4 AI-best-practice),
each finding adversarially re-verified against the actual files.
Reviewers: 12 | Raw findings: 64 | Verified: 58 | Survived: 52 | Refuted: 6
Caveat: the ai:agent-design lens degraded to a placeholder stub and contributed no substantive findings.
-->

# Independent Audit Report — `latent-sre/sde-agents`

*Synthesized from 12 blind reviewers (5 deep, 3 devil's-advocate, 4 AI-best-practice). Every finding below was adversarially re-verified; the verdict column reflects that second pass. Severities are post-verification (several reviewer-assigned "high" ratings were corrected down during verification and are reported at their verified level).*

> **Erratum (2026-07-12, post-publication) — finding #22 / D1 is RETRACTED.** The report asserted that Claude Code's subagent tool is `Task` and that `Agent` does not exist. That is false. Claude Code renamed `Task` to `Agent` in **v2.1.63**; `Agent` is canonical and `Task(...)` survives only as a deprecated compatibility alias ([sub-agents docs](https://code.claude.com/docs/en/sub-agents), [tools reference](https://code.claude.com/docs/en/tools-reference)). The reviewers' model predated the rename. **Do not apply the `Agent`→`Task` rename this report recommends** — it was briefly applied and then reverted in `3409d83`. `agents/prompt-engineer.md` is correct as written.

---

## Executive Summary

The repository is in **fundamentally sound health**: it is a small, disciplined agent/skill fleet with a real single-source-of-truth philosophy, a working validator, a CI pipeline, and — unusually — a self-aware security posture that honestly documents its own limits. No high-severity or exploitable defect survived verification; every issue is either a correctness/coverage gap or an architectural consistency risk. **The single most important cluster is the `readonly-guard.py` denylist**, which simultaneously *over-denies* routine read-only commands the reviewer agent depends on (`git log -p src/app.py | grep -e def` is blocked) and *under-denies* several real state-changers (`bash < deploy.sh`, `patch -p1 < changes.diff`, `git tag v1.0`, `tar x`), so the guard is inaccurate in both directions on common, non-adversarial input. The repo's genuine strengths are its explicit anti-drift design intent, its honest "this is a speed-bump, not a sandbox; OS least-privilege is load-bearing" framing, and a validator that already enforces meaningful invariants (models, inventory drift, evidence phrasing, packet headings). The recurring theme is that the validator and CI don't yet *enforce* the single-source-of-truth discipline the project preaches: tool names, routing references, read-only wiring, and the validator's own exit contract are all trusted rather than checked.

---

## Top Findings

| # | Severity | Verdict | Area | File | Finding (one line) |
|---|----------|---------|------|------|--------------------|
| 1 | Medium | CONFIRMED | Correctness | `scripts/readonly-guard.py:183` | Interpreter eval rules falsely DENY read-only commands: unbounded `.*` crosses pipes and `\bpy\b`/`\bsh\b` collide with `.py`/`.sh` filenames |
| 2 | Medium | CONFIRMED | Security | `scripts/readonly-guard.py:199` | `interpreter < script` (stdin redirection) bypasses every script-execution and pipe-to-shell guard |
| 3 | Medium | CONFIRMED | Security | `scripts/readonly-guard.py:106` | Ref-mutating / file-writing git subcommands absent from write verb list (`tag <name>`, `branch <name>`, `fetch`, `format-patch -o`, `bundle`, `archive`) |
| 4 | Medium | CONFIRMED | Security | `scripts/readonly-guard.py:117` | Common file-writing tools `patch`, `tar x`, `unzip` are not on the denylist |
| 5 | Medium | CONFIRMED | Architecture | `scripts/readonly-guard.py:5` | Read-only-agent set + guard wiring is a hardcoded second source, uncoupled from the validator |
| 6 | Medium | CONFIRMED | Architecture | `scripts/validate_fleet.py:121` | `tools:` authority list is never validated against a known vocabulary; any string (typo) passes |
| 7 | Medium | CONFIRMED | Testing | `scripts/validate_fleet.py:281` | `main()` exit-code contract (1 on fail / 0 on pass) — which all CI enforcement depends on — is untested |
| 8 | Medium | CONFIRMED | Testing | `tests/test_validate_fleet.py:12` | ~12 validator guardrail branches (name/filename match, model enum, dup names…) have no fixture |
| 9 | Medium | CONFIRMED | Testing | `scripts/validate_fleet.py:220` | Documented `--write-inventory` regeneration path has zero test coverage |
| 10 | Medium | CONFIRMED | CI | `.github/workflows/validate.yml:14` | CI is ubuntu-only despite heavy Windows-specific guard/hook code the tests blame for past failures |
| 11 | Low | CONFIRMED | Correctness | `scripts/readonly-guard.py:108` | `git tag <name>` / `git branch <name>` ref creation is allowed; only delete/rename denied |
| 12 | Low | CONFIRMED | Correctness | `scripts/readonly-guard.py:107` | Read-only `git stash list` / `git worktree list` are over-blocked |
| 13 | Low | CONFIRMED | Testing | `tests/test_readonly_guard.py:41` | Guard tests never exercise piped/compound commands, hiding the whole false-positive class |
| 14 | Low | CONFIRMED | Correctness | `scripts/validate_fleet.py:135` | Evidence-triad "cannot drift" invariant is opt-in and bypassable (2/7 agents exempt) |
| 15 | Low | CONFIRMED | Architecture | `agents/code-reviewer.md:3` | Inter-agent/skill routing graph in descriptions is an unvalidated second source (~20 refs) |
| 16 | Low | CONFIRMED | Architecture | `skills/eng-ladder/references/builder.md:6` | `references/*.md` are self-admitted duplicate copies of agent definitions |
| 17 | Low | CONFIRMED | Architecture | `skills/eng-ladder/SKILL.md:9` | Ladder rung↔agent mapping duplicated across incompatible naming schemes (`builder` vs `sde-fullstack`) |
| 18 | Low | CONFIRMED | Docs | `README.md:37` | README's own description of the validator has already drifted from the validator |
| 19 | Low | CONFIRMED | Testing | `tests/test_hook_wiring.py:98` | Installed-guard `$HOME` fallback branch is always skipped in CI |
| 20 | Low | CONFIRMED | Testing | `tests/test_validate_fleet.py:45` | Frontmatter parser: literal-block (`\|`, `\|-`) and quoted/malformed inputs untested |
| 21 | Low | CONFIRMED | Docs | `README.md:32` | Setup blocks fenced `powershell` and use `python`, contradicting CI's bash/`python3` reality |
| 22 | ~~Low~~ | **RETRACTED** | Consistency | `agents/prompt-engineer.md:4` | ~~Grants a tool named `Agent`; the real Claude Code subagent tool is `Task`~~ — **false; `Agent` is canonical since v2.1.63. See erratum above and D1.** |
| 23 | Low | CONFIRMED | Consistency | `skills/eng-ladder/SKILL.md:29` | eng-ladder references agents by bare `agents/*.md` paths that don't resolve in the deployed layout |
| 24 | Low | PLAUSIBLE | Devil's-advocate | `scripts/readonly-guard.py:14` | The 293-line regex guard reinvents a boundary the platform provides — and its own docstring says the real control is elsewhere |

---

## Security

The guard (`scripts/readonly-guard.py`) is wired into `code-reviewer` via a `PreToolUse` hook to claw back write capability from an agent that was granted `Bash`. It is explicitly self-described (docstring lines 12–20) as a *speed-bump*, "NOT a sandbox," with OS-level least privilege as the load-bearing control. That framing correctly caps the severity of everything below to **medium** — none of these crosses a real security boundary — but each is a plain, idiomatic command form a *cooperative* agent could emit, in categories the guard already tries to cover, so all are worth fixing and locking in with tests.

### S1 — stdin input redirection bypasses script-execution and pipe-to-shell guards (#2, Medium, CONFIRMED)

**What it is.** The denylist blocks an interpreter invoked with a script-file *argument* (`bash deploy.sh`, `python3 mutate.py`) and a script *piped* into a shell (`… | bash`), but has no rule for stdin redirection (`<`). The output-redirection rule at line 141 only matches `>`/`>>`.

**Evidence (reproduced as a subprocess).** `bash < deploy.sh`, `python3 < mutate.py`, `node < build.js`, `sh -s < script.sh`, `ruby < x.rb`, `command bash < deploy.sh`, and `sudo bash < deploy.sh` all return **ALLOW**, while the argument forms `bash deploy.sh` and `cat deploy.sh | bash` correctly **DENY**. The trailing-redirect trick even neutralizes the pipe-to-shell sink: `curl -s https://x/install.sh | bash` DENIES, but `curl -s … | bash < /dev/null` **ALLOWS**, because the `< /dev/null` displaces the separator the sink anchor (line 224) requires. Root cause: the script-file rules (lines 199–206) anchor the filename to the interpreter via a charset that excludes `<` and cannot span the whitespace `<` introduces. This directly contradicts `agents/code-reviewer.md:52` ("It also blocks running local script files") and is *not* one of the documented accepted residuals.

**Fix.** Add a command-position rule denying an interpreter whose argument is a stdin redirect from a real file, e.g. `\b(bash|sh|zsh|python3?|py|perl|ruby|node)\b[^|;&]*<(?!<)\s*(?!/dev/null)\S`, and make the pipe-to-shell sink tolerant of a trailing redirect. Lock it in with DENIED test fixtures.

**Verdict: CONFIRMED.** Every input reproduced exactly. Severity corrected high→medium on the guard's own non-boundary framing.

### S2 — ref-mutating and file-writing git subcommands missing from the write verb list (#3, Medium, CONFIRMED)

**What it is.** The git write rule (lines 106–109) enumerates `add/mv/rm/push/commit/reset/rebase/merge/… branch -[dDmM]/tag -d` but omits subcommands that still mutate refs or write files: `git tag <name>` / `git branch <name>` (create refs — only their `-d`/`-D` delete forms are caught), `git notes add`, `git replace`, `git fetch` (present: `pull`; absent: `fetch`), and the filesystem-writers `git format-patch -o`, `git bundle create`, `git archive -o`.

**Evidence.** Reproduced ALLOW for all of: `git tag v1.0`, `git branch newbranch`, `git format-patch -o /tmp HEAD~1`, `git bundle create /tmp/x.bundle HEAD`, `git archive -o /tmp/x.tar HEAD`, `git notes add -m hi HEAD`, `git replace HEAD~1 HEAD~2`, `git fetch origin`; contrast DENY for `git commit -m x`, `git branch -D old`, `git tag -d v1.0`. The docstring (lines 103–105) claims coverage of "history, remote, index, or worktree mutations," yet the `archive`/`bundle`/`format-patch` file-writers defeat exactly the filesystem-write protection the guard advertises. The delete-caught / create-uncaught asymmetry also underlies the lower-severity #11 below.

**Fix.** Extend the verb alternation to include bare `tag`/`branch` creation (deny when a name argument follows so `git tag -l` / `git branch --list` still pass), plus `notes`, `replace`, `fetch`, `format-patch`, `bundle`, `archive`, `send-email`.

**Verdict: CONFIRMED.** The file-writers are the substantive part; local ref creation is lower-impact.

### S3 — file-writing extraction/patch tools not on the denylist (#4, Medium, CONFIRMED)

**What it is.** The filesystem-mutation rule (line 117) lists `rm/mv/cp/dd/truncate/mkdir/touch/…` but omits `patch`, `tar`, `unzip`, `gunzip`. `patch -p1 < changes.diff` — the single most natural way an over-eager but cooperative reviewer would mutate the tree — also rides the unhandled `<` from S1.

**Evidence.** ALLOW reproduced for `patch -p1 < changes.diff`, `tar xzf archive.tar.gz`, `unzip pkg.zip`, `gunzip -k f.gz`. A whole-file scan confirms none of these verbs appear anywhere in the denylist.

**Fix.** Add command-position rules: `patch` (deny unless `--dry-run`), `tar` in extract mode (`x`/`--extract`), `unzip`, `gunzip -k`. Add DENIED fixtures.

**Verdict: CONFIRMED.** Directly comparable to already-denied writers (`cp`, `mv`, `sed -i`).

---

## Correctness

### C1 — interpreter eval rules falsely DENY routine read-only commands (#1, Medium, CONFIRMED)

**What it is.** The nested-shell/interpreter deny rules (lines 180, 183) match an interpreter token, then an **unbounded `.*`**, then an eval flag. Two defects compound: (1) `.*` is not bounded to one command segment, so a flag on the far side of a `|` satisfies it; (2) the interpreter alternation includes the two-letter tokens `py` and `sh`, and because `.` is a non-word char, `\bpy\b`/`\bsh\b` match the *extension* of an ordinary filename.

**Evidence.** DENY (should ALLOW): `cat notes.py | grep -e todo` (vs ALLOW for `notes.txt`), `wc -l scripts/validate_fleet.py | grep -e 1`, `git log -p src/app.py | grep -e def`, `python3 --version | grep -e 3`, `node --version | grep -e 20`, `cat deploy.sh | grep -c foo` (vs ALLOW for `deploy.rb`). These are exactly the inspection commands the module docstring promises pass through "untouched," and the harm lands squarely on `code-reviewer` inspecting a Python-heavy repo. It fails *safe* (over-restrictive), so it is a correctness/usability defect, not a hole.

**Fix.** Replace `.*` with a single-segment `[^|;&]*`; anchor the interpreter in command position (reuse the `_CMD`/`_CMD_SUB` anchors) so a `.py`/`.sh` filename in argument position can't supply the token; drop bare `py`/`sh` or require them to be command-position words.

**Verdict: CONFIRMED**, both compounding causes reproduced.

### C2 — read-only git subcommands over-blocked (#12, Low, CONFIRMED)

`stash` and `worktree` are listed as bare stems terminated by `\b` (line 107), so `git stash list`, `git stash show`, and `git worktree list` — pure reads — are DENIED. Fail-safe, but it degrades the reviewer workflow the docstring promises to preserve. **Fix:** scope to mutating sub-forms, e.g. `stash(?!\s+(list|show))`, `worktree(?!\s+list)` (which still catches `stash create`/`store`).

### C3 — git ref creation allowed (#11, Low, CONFIRMED)

`git tag <name>` and `git branch <name>` create refs but pass; only `-d`/`-D`/`-m`/`-M` forms are denied — a false-negative (the dangerous direction), though trivially reversible and local. Subsumed by the fix for S2. Untested (see T-cluster).

### C4 — evidence-triad "cannot drift" invariant is opt-in and bypassable (#14, Low, CONFIRMED)

The comment at `validate_fleet.py:28` asserts the evidence triad "cannot drift file by file," but the stem check (lines 136–141) runs only `if EVIDENCE_LABEL_RE.search(content)` — i.e. only for files that already contain the exact `**[verified]**`-style token. An agent that omits the labels or paraphrases them is exempt; `code-reviewer.md` (a prose `## Evidence gate`, line 25) and `prompt-engineer.md` contain zero tokens, so 2 of 7 agents sit outside the "fleet-wide" guarantee. **Fix:** require the stems in every finding-producing agent, or soften the comment to say enforcement is opt-in.

---

## Architecture — single source of truth vs. hand-maintained second sources

The README (lines 4–5) makes canonical/derived single-source the project's core claim. The recurring architectural finding is that the validator does not actually *enforce* that claim across several parallel, hand-maintained facts. None is currently broken (all references resolve today), so these are latent drift risks — but they are exactly the drift the design says it prevents.

### A1 — read-only-agent set + guard wiring is an uncoupled second source (#5, Medium, CONFIRMED)

Three facts must stay consistent and nothing links them: an agent's tools list (`Bash` but no `Write`/`Edit`), whether it wires the `PreToolUse` guard, and the guard's invocation contract. The read-only set is asserted in prose (`readonly-guard.py:4–5`, "today: `code-reviewer`"); the ~600-char hook command is inlined verbatim in `code-reviewer.md:12`; `test_hook_wiring.py` hardcodes `AGENT = … code-reviewer.md`. `validate_fleet.py` has *zero* references to hooks/`PreToolUse`/`Write`/`Edit`. The invariant holds today only because N=1 (an enumeration confirms `code-reviewer` is the sole Bash-without-Write agent). A future read-only agent that omits the hook runs Bash **unguarded**, silently. **Fix:** have the validator flag any agent with `Bash` but not `Write`/`Edit` and assert it carries the guard hook; factor the hook command into one canonical string.

### A2 — `tools:` authority has no canonical vocabulary (#6, Medium, CONFIRMED)

The security-relevant `tools:` field is only split and deduped (`validate_fleet.py:124–127`); there is no membership check — in contrast to the model field, which *is* validated against `ALLOWED_MODELS` (line 26, enforced 129–133). A typo (`Wrte`, `Bsh`) or stale name would silently grant/drop authority and pass. The vocabulary is also inconsistent: `prompt-engineer.md` lists `… Agent` while `sde-fullstack.md` lists `… Skill`. **Fix:** define an `ALLOWED_TOOLS` set mirroring `ALLOWED_MODELS`, validate every entry, and reconcile `Agent` vs `Skill` (see #22). This is the enforcement gap that lets #22 through.

### A3 — inter-agent/skill routing graph is an unvalidated second source (#15, Low, CONFIRMED)

Every description embeds a hand-written routing graph referencing siblings by bare name (~20 cross-references: `code-reviewer`→`lab-audit`; `homelab-platform`→`service-onboard`/`sde-fullstack`/`code-reviewer`; etc.). `validate_fleet.py` never scans description bodies for sibling names, so renaming/removing any member drifts every prose reference silently while validation stays green. *Counter-evidence (keeps this at low):* a rename also changes the filename and thus the README fleet inventory, which **is** validated (`validate_inventory`, 231–243) — so a rename produces at least one loud failure even though the reference itself is unchecked. **Fix:** extract the canonical name set once and assert every `use <name>`/backticked sibling reference resolves.

### A4 — `eng-ladder/references/*.md` are self-admitted duplicate sources (#16, Low, CONFIRMED)

`builder.md:6–8`, `principal.md:6–8`, `distinguished.md:7–9` each restate a rung's method that also lives in the agent file, and encode a *manual* precedence rule ("if this file disagrees … the agent file is right: fix this file"); `SKILL.md:21` confirms it. The validator's only reference check (`validate_bundle_references`, 154–162) verifies a path *exists*, never that content agrees. Mitigated by being explicit paraphrases with a declared winner — hence low. **Fix:** generate reference bodies from a delimited agent section, or narrow references to inline-only material that deliberately doesn't restate the bar.

### A5 — ladder rung↔agent mapping uses incompatible naming schemes (#17, Low, CONFIRMED)

The mapping lives in three places with two vocabularies and no join key: the SKILL table header uses agent names (`sde-fullstack | principal-engineer | distinguished-architect`, `SKILL.md:9`), while the prose and reference filenames use rung names (`builder`/`principal`/`distinguished`). `builder` and `sde-fullstack` are the same rung; only column order links them. `SKILL.md:23` calls the table "the source of truth for routing," yet nothing checks its columns are real agent names. **Fix:** pick one canonical rung key and derive the rest, or assert the table's agent columns equal the ladder agent set.

### A6 — README's description of the validator has drifted (#18, Low, CONFIRMED)

`README.md:37–39` lists what the validator checks but omits two invariants the code enforces: the evidence-label triad phrasing and the mandatory `## … packet`/`## Output format` heading (`validate_fleet.py:136–145`). A contributor could fail validation for a reason the README never mentions — ironic in the very README that warns against a second source of truth. **Fix:** add the two checks to the list; ideally derive the README bullet and the validator help text from one string.

---

## Testing & CI

The suite tests the validator's *pure* functions directly and skips the glue and failure paths the pipeline actually depends on. Nothing here documents a present bug; all are latent-risk coverage holes on load-bearing signals.

### T1 — `main()` exit-code contract is untested (#7, Medium, CONFIRMED)

All six unit tests call `validate_repo()` and inspect the returned `issues` list; none invokes `main()` or asserts its return code / `SystemExit`. But CI (`validate.yml:20`) trusts the script's exit status, and `main()` returns 1 only via the branch at `validate_fleet.py:281–285`. If `main()` regressed to always return 0 (swallowed list, mis-ordered `--write-inventory` branch, early return), all unit tests stay green **and** the CI step stays green because it only ever runs against the currently-valid real repo (which returns 0). The failure signal the whole pipeline rests on is exercised by nothing. **Fix:** `assert main(['--root', FIXTURES/'missing-tools']) == 1` and `… 'valid') == 0`, plus the `__main__` `SystemExit` path.

### T2 — ~12 validator guardrail branches have no fixture (#8, Medium, CONFIRMED)

Fixtures cover only `valid, missing-tools, missing-reference, evidence-drift, missing-packet, inventory-drift, folded` (7 dirs; every agent fixture is `name: builder`, `model: inherit`). Untested branches include the checks that most directly enforce the single-source claim: invalid name regex (line 87), agent name≠filename (117) and skill name≠directory (186), duplicate agent/skill names (149/195), duplicate tool (126), missing/malformed frontmatter (111/179), missing `SKILL.md` (174), missing agents/skills dir (105/169), empty/over-length description (94–97), missing/unsupported model (131/132). Disabling name-vs-filename or model validation would pass the entire suite. **Fix:** add cheap negative fixtures for each.

### T3 — `--write-inventory` regeneration path has zero coverage (#9, Medium, CONFIRMED)

`write_inventory()` (220–228) and `main()`'s write branch (272–276) are the exact operation the whole single-source design depends on (`README.md:17`), yet no test calls them or asserts the resulting README bytes. Only the *pure* substitution (`replace_inventory`) is tested. `main()` re-validates only the marker block afterward (line 279), so corruption *outside* the markers would ship green. **Fix:** run `main(['--write-inventory','--root',tmp])` against a copied fixture and assert README content + exit 0; add a negative test for a markers-missing README raising `ValueError`.

### T4 — guard tests never exercise piped/compound commands (#13, Low, CONFIRMED)

`test_readonly_guard.py` ALLOWED (41–83) contains no pipeline whose read side carries a `-c/-e/-p` flag and no `.py`/`.sh` file before a pipe; DENIED (85–163) has `git checkout -b feature` but no bare `git branch`/`git tag`. So the entire false-positive class (C1) and the false-negatives (C3) are unexercised and the suite passes despite the guard mis-deciding them. *Correction from verification:* the finding's headline example `grep -e def src/app.py` is actually ALLOWED (no interpreter token precedes `-e`); the broader class and the git omissions hold. **Fix:** add ALLOWED cases (`wc -l …py | grep -e 1`, `python3 --version | grep -e 3`, `git stash list`) and DENIED cases (`git branch feature`, `git tag v1.0.0`) — they fail today and pin the fixes for C1–C3.

### T5 — installed-guard `$HOME` fallback branch always skipped in CI (#19, Low, CONFIRMED)

`test_falls_back_to_installed_guard_outside_the_repo` `skipTest()`s unless `~/.claude/scripts/readonly-guard.py` exists, which it never does on a clean runner (local run reports `OK (skipped=1)`), and CI has no install step. So CI verifies in-repo resolution and total-failure deny but never the fallback governing real cross-repo use. *Mitigation:* the security-critical fail-**open** direction is still covered by the missing-everywhere test, so a regression here most likely fails closed (over-deny). **Fix:** seed `HOME` at a tmp dir containing the guard, or symlink it in CI.

### T6 — frontmatter parser: literal-block and quoted/malformed inputs untested (#20, Low, CONFIRMED)

`parse_frontmatter` treats `>`, `>-`, `|`, `|-` identically (line 66), joining continuation lines with spaces — but YAML literal blocks (`|`, `|-`) should preserve newlines. Only `>-` is tested. The `|`/`|-` conflation (a latent correctness issue), the quoted-value strip (line 75), and the two malformed-frontmatter→`None` paths (48, 53) have no fixture. Benign today given the current files. **Fix:** add cases for `|`/`|-`, quoted values, no-opening-`---`, and unterminated blocks.

### T7 — CI is ubuntu-only despite substantial Windows-specific code (#10, Medium, CONFIRMED)

The guard invests heavily in Windows: a PowerShell mutation-verb block (`Remove-Item`/`Set-Content`/`Stop-Service`, lines 129–132) and an interpreter-probe hook (`for PY in python3 python py; do … "$PY" -c "" … exec …`, `code-reviewer.md:12`) that exists *specifically* because — per `test_hook_wiring.py:6–11` — "on Windows the Microsoft Store stub … wins `command -v` and exits 49 without running anything," one of the repo's two real past guard failures. Yet `validate.yml:14` is `runs-on: ubuntu-latest` with no matrix, so on ubuntu `python3` always works and the fallback branch, the stub path, and native path/env handling are never taken. *Verification also found* the PowerShell denylist has **zero** test coverage on any platform (no `Remove-Item`/`Stop-Service` case in `test_readonly_guard.py`) — a broader gap that strengthens the finding. **Fix:** add a `windows-latest` (and ideally `macos-latest`) matrix leg, and add PowerShell-verb DENIED fixtures.

---

## AI / Agent / Skill / Prompt Design

### D1 — ~~`prompt-engineer` grants a nonexistent tool~~ (#22) — **RETRACTED, the finding was wrong**

**Original claim (do not act on it):** that `prompt-engineer.md:4`'s `Agent` grant names a tool that doesn't exist, because Claude Code's subagent tool is `Task`, and that the fix is to rename the grant and the body reference to `Task`.

**Why it's wrong.** Claude Code renamed `Task` to `Agent` in **v2.1.63**. `Agent` is the canonical, documented name; `Task(...)` still resolves as a deprecated alias, so *both* work but only `Agent` is current ([sub-agents](https://code.claude.com/docs/en/sub-agents), [tools reference](https://code.claude.com/docs/en/tools-reference)). All twelve reviewers shared a pre-2.1.63 knowledge cutoff, and the adversarial verification pass inherited the same stale prior, so a unanimous-but-wrong claim was stamped CONFIRMED — a reminder that agreement across reviewers is not independent evidence when they share a training corpus. `agents/prompt-engineer.md` was correct as originally written; the recommended rename was applied and then reverted in `3409d83`.

**What survives.** Only the *generalization*: at the time, the validator had no tool vocabulary, so any string in `tools:` passed. That is the real defect, and it is tracked on its own as **A2 (#6)** — now fixed by `ALLOWED_TOOLS` in `scripts/validate_fleet.py`, which is deliberately canonical-only (an `Agent` grant passes; a legacy `Task` grant fails and must be rewritten).

### D2 — eng-ladder references agents by bare repo-relative paths (#23, Low, CONFIRMED)

`eng-ladder/SKILL.md:29` (Mode 2) and each reference file tell the reader to read `agents/sde-fullstack.md` etc. — bare `agents/*.md` paths that only resolve from the fleet repo. In the deployed layout agents live at `~/.claude/agents/*.md`. The rest of the fleet handles this move with explicit resolution ceremony (`sde-fullstack.md:42`, `homelab-platform.md:35`: "the target repo's own … else `~/.claude/…`"); a repo-wide grep confirms these four eng-ladder lines are the *only* bare-path agent references. *Nuance:* the reference-file instances say "don't load it for inline work," so they're citations, not broken loads; the load-bearing case is line 29. **Fix:** give eng-ladder the same `~/.claude/agents/` fallback language (note: agents have no per-repo override, so the skills-override pattern over-applies — just add the deployed form).

### D3 — README setup blocks mislabeled and use `python` (#21, Low, CONFIRMED)

`README.md:16,32` fence the Validation/Refresh blocks as ` ```powershell ` but contain shell-agnostic `python scripts/validate_fleet.py` / `python -m unittest …`. Two mismatches: the `powershell` label is misleading for a tool the README itself (lines 38–39) calls "intentionally runtime-neutral," and the commands use `python` while the authoritative runner (`validate.yml:20,23`) uses `python3` on ubuntu, where bare `python` is frequently absent — so a copy-paste can yield `command not found`. **Fix:** fence as `bash` (or none) and use `python3`.

---

## Devil's-Advocate Challenge

### DA1 — Does the guard justify its own existence? (#24, Low, PLAUSIBLE)

The strongest whole-premise challenge: `readonly-guard.py` is a 293-line case-insensitive regex denylist plus a ~210-line test file, wired via a dense multi-interpreter shell one-liner, to claw back write capability from an agent that was granted `Bash` in the first place. Claude Code already expresses read-only natively (grant only `Glob/Grep/Read`, or use platform permission deny-rules), and the guard's own docstring concedes it is subordinate: "this is NOT a sandbox … It cannot stop a determined adversary … The LOAD-BEARING control is OS-level least privilege" (14–20), with a "Known residuals (ACCEPTED BY DESIGN)" list of permanent bypasses (22–30). The complexity has already produced its own bug class: git history shows it shipped as a fail-**open** no-op (`c01b3bb` "make it fail closed") and shipped with allowlist bypasses (`bd5809e`) — defects that exist *only because the guard exists*.

**Assessment (PLAUSIBLE, not confirmed).** The citations are accurate and the argument is legitimate, but it is a design-judgment critique rather than a defect: the guard is deliberately positioned as defense-in-depth, and every finding above (S1–S3, C1–C3) is evidence the layer is imperfect — which cuts both ways (it argues for either hardening or retiring it, not unambiguously one). Worth a deliberate decision. **Recommendation:** if `Bash` is only for `git diff/log/show/blame` + running tests, prefer platform deny-rules or hand the reviewer pre-computed diff/test output so `Bash` isn't needed; otherwise commit to the guard and close S1–S3 with tests. Do not grow the denylist indefinitely without this decision.

---

## Refuted / Non-issues

The full separate refuted-findings list was truncated from the data provided to this synthesizer; the six items below are sub-claims that the adversarial verification pass explicitly **checked and dismissed** (grounded in the verification evidence, not invented):

1. **`grep -e def src/app.py` is NOT denied.** The finding-#13 headline example is actually ALLOWED — no interpreter token precedes `-e`; the `py` is inside `app.py` after the flag. (The broader false-positive class still holds.)
2. **Renames are not silently invisible fleet-wide.** For the routing-graph drift (#15), `validate_inventory` (`validate_fleet.py:231–243`) *does* validate the README name inventory, so a rename yields at least one loud failure even though the individual prose reference is unchecked.
3. **The `Agent`/`Task` bug does not break `sre-tool` spawn orchestration.** A spawnee agent needs no subagent-tool grant to be spawned; the secondary breakage claim in #22 was refuted. *(Post-publication: the #22 headline claim was refuted too — `Agent` is canonical. See the erratum and D1.)*
4. **eng-ladder reference-file path citations are not broken load instructions.** They say "don't load it for inline work," so #23's real impact is confined to the Mode 2 line 29 case, not the reference files.
5. **The PowerShell denylist regexes are not OS-conditional in matching.** For #10, the patterns compile and match identically on ubuntu; the actual gap is that they have *no test on any platform*, not that ubuntu can't run them.
6. **The guard's fail-open no-op is already fixed.** The devil's-advocate history (#24) cites `c01b3bb`/`bd5809e` as *past* fixes; the guard currently fails closed, so the fail-open behavior is not a live issue.

---

## Prioritized Action Plan

**Quick wins (hours; mostly one file or a few fixtures):**

1. **Fix the guard's false-denials (C1):** bound `.*`→`[^|;&]*` and remove/anchor the bare `py`/`sh` tokens at `readonly-guard.py:180,183`. Highest daily-friction item for the reviewer agent.
2. **Add stdin-redirect and file-writer deny rules (S1, S3):** cover `interpreter < file`, `patch`/`tar x`/`unzip`, and the trailing-redirect pipe-to-shell bypass.
3. **Extend the git write verb list (S2, C3):** `tag`/`branch` creation, `notes`, `replace`, `fetch`, `format-patch -o`, `bundle`, `archive`; scope `stash`/`worktree` to mutating sub-forms (C2).
4. **Pin all of the above with tests (T4):** add the piped/compound ALLOWED and git-create DENIED fixtures — they fail today.
5. **Add an `ALLOWED_TOOLS` set (A2)** mirroring `ALLOWED_MODELS`, and validate every `tools:` entry. ~~and fix `Agent`→`Task` (D1)~~ — **struck: D1 is retracted, `Agent` is the canonical name. Do not perform this rename.**
6. **Doc fixes:** update the README validator list (A6), re-fence + `python3` the setup blocks (D3), add eng-ladder's deployed-path fallback (D2).

**Medium effort (a day; test/CI hardening):**

7. **Test the enforcement signal (T1):** assert `main()` returns 1 on a bad fixture and 0 on a good one, plus the `SystemExit` path.
8. **Fill the validator branch fixtures (T2)** and the `--write-inventory` round-trip + negative test (T3).
9. **Add a Windows (and macOS) CI matrix leg (T7)** and PowerShell-verb DENIED fixtures; deseed the `$HOME`-fallback skip (T5) and add parser edge cases (T6).

**Larger / structural work (design decisions):**

10. **Close the single-source enforcement gaps (A1, A3, A5):** have the validator (a) flag any `Bash`-without-`Write`/`Edit` agent that lacks the guard hook and factor the hook into one canonical string; (b) assert every `use <name>` routing reference resolves; (c) assert the eng-ladder table columns are real agent names.
11. **Resolve the eng-ladder duplication (A4):** generate reference bodies from a delimited agent section, or narrow them to non-restating inline material.
12. **Make the guard decision explicitly (DA1):** decide whether to harden `readonly-guard.py` as committed defense-in-depth (having closed S1–S3) or replace it with platform permission deny-rules / pre-computed diff+test output so `code-reviewer` doesn't need raw `Bash`. Either way, stop growing the denylist without this decision.

*No research-citation URLs were present in the verified data supplied to this synthesizer; none are fabricated here.*
