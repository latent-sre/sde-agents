# Targeted review — `affaan-m/ECC` skills & agents — July 2026

**Question:** the operator pointed at four components of `affaan-m/ECC` ("Everything Claude Code",
~280 skills / 67 agents, MIT) — `skills/frontend-a11y`, `skills/frontend-design-direction`,
`skills/agent-self-evaluation` (full directory), `agents/homelab-architect` — and asked what they
teach us about improving this fleet's own skills and agents.

**Method:** shallow clone of ECC @ `a3130f9ebfae` (2026-07-23), full read of the four targets and
every supporting file (`references/`, `scripts/`, `templates/`, `examples/`), spot reads of
adjacent ECC components to test whether target-level patterns are local or systemic
(`accessibility`, `a11y-architect`, agent frontmatter across all 67). Comparative read of this
fleet's seven agents, ten skills, and the three standing docs, so verdicts land against what
exists and what is already planned rather than re-deriving either. Load-bearing claims cite
file:line in both repos. Licensing: ECC is MIT; imports are legal with provenance noted in commit
messages (same convention as `docs/sre-agents-adaptation-backlog.md`).

**Headline (three findings, in order of consequence):**

1. **The comparison validates this fleet's architecture more than it challenges it.** Every
   structural mechanism this repo enforces is absent in ECC, and the four targets show the
   resulting failure modes live: 66 of 67 ECC agents open with an identical six-bullet "Prompt
   Defense Baseline" (unconditioned boilerplate where this fleet ships one tailored sentence plus
   an enforcing hook); `homelab-architect` instructs "use these focused skills" for four skills it
   has no mechanism to load (no `skills:` key, no `Skill` tool, `tools: ["Read", "Grep"]` with no
   path to read them by — the exact silent-failure class `validate_fleet.py`'s resolution and
   namespacing rules exist to catch); and ECC ships two overlapping accessibility skills
   (`accessibility`, `frontend-a11y`) plus an `a11y-architect` agent with no negative routing
   between them and nothing measuring the overlap.
2. **One genuine capability gap on our side: accessibility wiring.** `frontend-craft` compresses
   accessibility to one strong paragraph (`SKILL.md:63`); ECC's `frontend-a11y` carries the
   interaction-level patterns that paragraph doesn't reach — programmatic label/error association,
   `aria-live` announcement of async state, focus management for overlays, keyboard grammar for
   custom widgets. Our own Resilience UX doctrine (toasts, inline errors, designed states) is
   currently invisible to a screen reader by our own rules. This is the one Tier-1 import.
3. **The other two targets yield surgical residue, not components.** `agent-self-evaluation`'s
   numeric self-scorecard contradicts fleet doctrine three ways (adjudicated below) but its
   deterministic output-smell scanning is worth adopting *inverted*; `homelab-architect` is a
   planning-only advisor our tiered operator supersedes, carrying two network-safety invariants
   worth four lines.

---

## 1. `frontend-a11y` → `frontend-craft` — adopt the content, not the form (Tier 1) — **done**

**What it is:** 446 lines, 16 TSX blocks — form labeling (`SKILL.md:29-75`), semantic-element
rules, ARIA usage (`aria-label`/`labelledby`/`describedby`, `aria-live` at `:212-226`,
`expanded`/`controls`), keyboard navigation for a custom dropdown (`:254-315`), modal focus
save/restore with an honest "use a library for the full trap" note (`:319-351`), image/icon
labeling, `prefers-reduced-motion`, an anti-pattern list (`:406-427`), and a pre-review checklist
(`:429-440`).

**What we already have:** `frontend-craft/SKILL.md:63` (semantic HTML, labeled inputs, keyboard
reachability, visible focus, AA contrast, div-onClick→button, route-change focus move, ≥44px
targets, reflow), `SKILL.md:27` (compositor-only animation + reduced motion — universal),
`references/data-viz.md:12` (text/table alternative per chart). Verified against every
`frontend-craft` file: the following appear nowhere in this fleet.

**Verified gaps (ours):**

- **Form wiring** — `references/forms.md` covers validation timing, server truth, and dirty
  tracking but never label↔control association (`htmlFor`/`id`), error↔input linking
  (`aria-describedby` + `aria-invalid` + `role="alert"`), or required-field marking. ECC calls
  label/error disconnection the most commonly review-flagged a11y defect; our own file is silent.
- **Async state announcement** — nothing in the fleet mentions `aria-live`. `SKILL.md`'s
  Resilience UX mandates toasts, inline per-panel errors, and designed loading/empty states — all
  of it visual-only as specified. A skill that requires designed failure states should require
  they be *announced*.
- **Overlay focus management** — route-change focus is covered; modal/drawer open-and-close focus
  (save opener, move in, restore on close) is not.
- **Custom-widget keyboard grammar** — arrows/Enter/Space/Escape + `aria-expanded`/`controls` for
  menus, comboboxes, tabs: absent.
- **The anti-pattern set** — positive `tabIndex`, `aria-hidden` on a focusable element,
  placeholder-as-label (ux-writing has the voice half at `references/ux-writing.md:32-34`, not the
  a11y half), `role="button"` without keyboard handling: absent.

**Landing (respects the stack-neutrality fix, quality-review finding 1 — coordinate, don't
collide):**

- `references/forms.md` gains an accessibility block (~5 lines, house register): every control
  programmatically labeled; error text linked to its field via `aria-describedby` with
  `aria-invalid` and announced (`role="alert"`); required conveyed to AT, not by asterisk alone;
  `autocomplete` on identity/credential fields. Predicate already routes forms here — no
  description change.
- New `references/interaction-a11y.md` + one routing-table row in `SKILL.md` ("a modal, drawer,
  menu, tooltip, tabs, or any custom interactive widget — or announcing async status →"). Content:
  overlay focus save/restore (trap via the repo's library — never hand-rolled), keyboard grammar,
  `aria-expanded`/`aria-controls`/`aria-activedescendant`, `aria-live` (`polite` default,
  `assertive` only for urgent errors) wired to our toast/status conventions, icon-button and
  decorative-image labeling, and the anti-pattern list. Written framework-neutral with the default
  stack as the worked example — the reference must not reintroduce the React-universalism finding
  1 is removing from the core.
- `SKILL.md:63` gains one clause ("async status changes are announced, not just rendered") and the
  quality gate at `SKILL.md:75` gains "including a keyboard-only pass of the primary flow" — the
  cheapest verification that most of the above actually holds.

**Import the checklist, not the code.** Two reasons, both verified. (a) Form: 16 code blocks is
the shape our token-budget doctrine exists to avoid (`prompt-engineer.md:43`); the fleet's
one-compressed-example convention carries the same content in a fraction of the load. (b) Trust:
ECC's flagship dropdown example (`:254-315`) keeps focus on the combobox while arrow keys move a
highlight, but never sets `aria-activedescendant` (zero occurrences in the file) — a screen reader
announces nothing as the user arrows through options. The "GOOD" exemplar fails its own skill's
purpose. Large example libraries carry authority they haven't earned and rot silently; rules plus
one verified example is the sturdier form. (Their modal example is honest about its limits —
`:323` — which is the right pattern and matches our cooperative-control register.)

No description changes anywhere in this item → no routing-eval surface; validator + tests +
orphan/link checks cover it.

## 2. `frontend-design-direction` → `frontend-craft` — two surgical adds (Tier 2) — **done**

A 93-line direction-setting skill (salvaged from an upstream PR; ECC deliberately doesn't rebundle
Anthropic's `frontend-design` — honest provenance, noted). Most of it this fleet already owns in
stronger form: its "avoid purple gradients/blobs/stock atmosphere" list is our named stock-look
clusters with self-critique (`SKILL.md:29`); "don't describe the UI's features inside the UI" is
`ux-writing.md`'s words-are-navigation doctrine; "use existing components/tokens first" is the
design-system carve-out (`SKILL.md:15`). Two things survive comparison:

- **The register decision is implicit in ours.** ECC's direction step (`SKILL.md:32-45`) makes
  purpose/audience/tone an explicit pre-coding choice — "a SaaS operations tool should usually be
  dense, quiet, and scannable… do not force a landing-page composition onto a tool that needs
  repeated daily use." Our mini design plan (`references/design-language.md:17-23`) pins palette,
  type, and signature but never asks who repeats this workflow or whether the surface should be
  dense/calm or expressive — the ops-leaning default answers it silently, which is exactly the
  kind of undeclared default the fleet dislikes. **Fix:** add one slot to the plan comment
  (`audience/tone: <who repeats this workflow> · <dense-and-calm | expressive>`), plus one
  sentence tying tone to domain. Greenfield-only file, no routing surface.
- **Layout stability under state change is nowhere in the fleet.** ECC `SKILL.md:59-61, 64-65`:
  toolbars, tiles, grids, and controls keep stable dimensions — labels, hover states, and counters
  must not shift layout; long labels wrap or resize, verified at narrow widths. Our Layout section
  has hierarchy/spacing/type/theme; our motion rules make hover effects transform-only (no layout
  thrash) but never state the invariant for *content* changes. **Fix:** one bullet in
  `SKILL.md`'s Layout section — reserve space for the longest state (label, count, badge), never
  let interaction or data change move neighbors; verify text fit at narrow widths.

**Rejected:** "no cards inside cards" (a symptom; our "if every surface is elevated, nothing is"
names the cause); "first viewport communicates the product" (our genre is tools, and "every view
is a composition" plus build-the-usable-experience already binds); their dependency rule (covered
by the bundle-size line and the fleet's simplicity doctrine).

## 3. `agent-self-evaluation` — adopt the mechanism, reject the rubric (Tier 2/3)

The most instructive of the four: a post-task self-scoring skill (5 axes × 1–5, evidence per
score, report template, heuristic `scripts/evaluate.py`, opt-in reminder hooks). Full-directory
read; adjudicated against fleet doctrine.

**Why the rubric itself doesn't land here (three doctrine conflicts, one design flaw):**

- **Uncalibrated numbers.** A self-assigned "4.6/5" is precisely the claimed precision
  `code-reviewer.md:44` bans in favor of categorical confidence — an unmeasured number, now
  applied to one's own work.
- **Same-context self-grading.** The fleet's position is `self-improve-loop/SKILL.md:26`: a
  fresh-context evaluator catches more than self-critique in the same context. Our
  evaluator-optimizer split (builder → reviewer) is the load-bearing version of what this skill
  approximates in-context.
- **Averaging buries the gate.** Their own worked example scores wrong-library code 2.8/5 and
  proceeds to remediation planning; in this fleet a false or unverified claim isn't averaged
  against clarity points — it stops the "done" claim (`sde-fullstack.md:76`).
- **The scorer rewards confident silence.** `scripts/evaluate.py` starts each axis at 5 and
  *deducts* for hedge phrases ("I think", "untested", "should work"); an output with no
  verification signals at all keeps its 5 with the note "score assumes correctness"
  (`evaluate.py:85`). Honest, labeled uncertainty scores *worse* than saying nothing — the exact
  inversion our verification gate and `[unverified]` labels exist to prevent. Run over this
  fleet's packets it would penalize every compliant `[unverified]` line.

**What is worth taking:**

- **Deterministic packet linting, inverted (the real import).** Quality-review finding 7b already
  plans behavioral evals asserting packet compliance (all slots present). ECC demonstrates the
  assert can be a stdlib script, and its regex corpora (danger/vague-signal lists in
  `evaluate.py:66-71,219-223`) are a usable seed vocabulary. Build it to fleet doctrine: required
  slots present for the declared packet shape; hedge-smells flagged only when *unlabeled* (no
  adjacent `[verified]/[sourced]/[unverified]`); a "tests pass"-class claim without command+output
  cited is the finding — missing evidence fails, it never "assumes correctness." Land as an eval
  assert helper (`scripts/` + fixture tests) when finding 7's behavioral evals land — not before
  (no consumer), not as a hook (an output linter that fires on live sessions would train
  packet-shaped evasion, and quoting user text would false-positive). Note the convergence: their
  danger-phrase list is nearly our `sde-fullstack.md:82-86` red-flags — independently derived,
  placed upstream (before claiming) in ours, downstream (after output) in theirs. Keep ours
  upstream; add the mechanical check at eval time.
- **One rubric-hygiene clause for `eng-ladder` Mode 2** — **done**. Their anti-patterns include two
  assessor-failure rules with no equivalent in our assess-at-a-bar mode: score against what was
  asked (absence of unrequested work is not a gap), and a simple artifact done perfectly meets the
  bar — don't invent gaps to appear rigorous. `code-reviewer` has its version (the false-positive
  gate); `eng-ladder/SKILL.md:29`'s "gaps with cited evidence" implies but doesn't state it. One
  sentence in Mode 2.

**Rejected:** the skill as a component (no fleet slot — the reviewer and `self-improve-loop`
already partition evaluation, and its "after any non-trivial task" trigger is the fires-too-often
shape `prompt-craft` diagnoses); the Stop/PostToolUse echo-reminder hooks (unconditioned noise on
every session — their own reference concedes manual invocation is the reliable path,
`references/hook-integration.md:62-65`); the report template and numeric anchors (fall with the
rubric).

## 4. `agents/homelab-architect` → `homelab-platform` — two invariants (Tier 2) — **done**

A planning-only advisor (`tools: ["Read", "Grep"]`, `model: sonnet`): inventory → goals →
capability check → smallest-topology-first plan → staged phases with rollback. As a *product* it
is the safe half of what `homelab-platform` already is — its strongest rule ("planning and review
only; no copy-paste config unless platform, topology, backup path, console access, and rollback
are known", `homelab-architect.md:26-28`) is our Tier 2 approval evidence, which goes further
(per-apply, exact commands, blast radius, verified rollback). Its plan-shaped remit maps to the
ladder: capability-vs-goals and staged upgrade paths are `principal-engineer` options-and-trade-
offs; smallest-useful-topology-plus-optional-phases is `distinguished-architect`'s
every-phase-independently-valuable evolution rule. No roster or authority change.

**Adopt — two network-safety invariants this fleet nowhere states** (verified absent from
`homelab-platform`, `service-onboard`, `lab-audit`, `runbook`):

- **Resolver cutover** (`homelab-architect.md:58-59`): don't point DHCP's DNS at a local resolver
  until the resolver has a static address, a health check, and a stated fallback path. The
  classic self-inflicted household outage; our Tier 3 gates the *apply* but nothing supplies the
  readiness criteria.
- **Management-plane survival** (`:60-61`, `:49-51`): before a segmentation/VLAN step, confirm
  the operator still reaches gateway, switch, and AP afterward; a multi-step network change is
  sequenced so internet, DNS, and management access are recoverable at every step. This
  generalizes Prime directive 4 (`homelab-platform.md:18` — the *session's own* path) to the
  operator's access as such.

**Landing:** ~4 lines in `homelab-platform` — extend directive 4 with the management-plane
sentence; add the resolver-readiness rule beside it or under Standards. Body-only; no
description/routing surface. (If the fleet ever grows network-content skills, these lines are the
seed — but ECC's five `homelab-*` network skills are not the model to import: they hang off an
agent that cannot load them.)

**Rejected:** the "Prompt Defense Baseline" (66/67 agents carry it verbatim — unconditioned
boilerplate a reader learns to skim; several bullets are unenforceable prose where this fleet uses
tool scoping, the guard, and per-role adaptations of the canonical fetched-content sentence);
beginner/advanced register calibration (single-operator fleet, no observed failure, and a
conditional register is a nuance clause by another name); the plan-document template
(`principal-engineer`'s design-doc slots own that genre).

---

## What the comparison validates (keep, and cite when tempted otherwise)

- **Resolvable, namespaced cross-references + preload wiring.** ECC's aspirational skill mentions
  (an agent "using" skills it cannot reach) are the silent failure our validator's `skills:`
  resolution, namespacing, and unknown-key rules make loud. Also concretely: ECC's
  `metadata.origin` provenance key would fail `KNOWN_SKILL_FIELDS` here — by design; provenance
  belongs in commit messages (adaptation-backlog convention), not in frontmatter the runtime
  ignores.
- **Triggers live in descriptions.** ECC's body-level "When to Activate" sections sit below the
  routing decision — Claude Code never reads a body until the description already fired. Our
  description-carried triggers with negative routing are the working form; the crafts' in-body
  predicate tables are the legitimate body-level counterpart (they gate *which reference to load
  once running*, not whether to fire).
- **Measured overlap.** `accessibility` + `frontend-a11y` + `a11y-architect` ("use PROACTIVELY
  when designing UI components") is unmeasured triple overlap of the kind the routing evals exist
  to prevent — and a standing reason finding 7's remaining clusters outrank most polish work.
- **Enforcement over recitation.** One guarded reviewer with a fail-closed hook beats six
  security bullets pasted 66 times.

## Compliance checklist — for every import above

Same gates as `docs/sre-agents-adaptation-backlog.md`: skill-relative links for the new reference
(orphan check); namespaced cross-references in any description (none of these items should touch a
description — if one does, run the affected routing cluster before/after); canonical evidence-label
stems untouched; validator + unit tests + `claude plugin validate . --strict`; provenance
(`adapted from affaan-m/ECC`, MIT) in commit messages for the a11y reference and the invariant
lines; README inventory unchanged (no component adds — rerun `--write-inventory` only if that
changes).

## Sequencing

1. **Item 1** (frontend-craft a11y: forms block, `interaction-a11y.md` + table row, core clause,
   keyboard-pass gate) — **landed**. The new reference is written stack-neutral so quality-review
   finding 1's stack-neutrality edit composes with it rather than reworking it.
2. **Item 4** (homelab-platform network invariants) and **item 2** (design-plan tone slot, layout
   stability) — **landed**; small body edits, independent.
3. **Item 3a** (packet-lint assert) — **still open, deliberately**: it folds into quality-review
   finding 7's behavioral-eval work when that lands (no consumer exists yet); **3b** (eng-ladder
   Mode 2 clause) — **landed**.

Source snapshot: `affaan-m/ECC` @ `a3130f9ebfae` (2026-07-23 clone).
