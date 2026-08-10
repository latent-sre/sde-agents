export const meta = {
  name: 'deep-review',
  description: 'Two parallel code-reviewer lanes (correctness + security threat model) over the ambient working tree, schema-typed packets, deterministic merge record. Also the final static-review gate over a multi-commit branch, including one already reviewed per-task: it takes no brief, so it does not inherit the caller hypotheses a steered per-task loop carries — but its lanes are read-only reviewers that run nothing, so the verdict stacks on T1 and acceptance verification, never replaces them. args (optional) is a single git ref used as the diff base, resolved through merge-base with HEAD — never a target to check out, never a range, never prose/focus text; default base is the merge base with main. To review another branch, check it out first. The static-review signal is the returned verdict, gated on confirmed_criticals (P0/P1) and the lane verdicts — never an empty findings list, since P2/P3 nits do not block — and each lane names what it did not examine in not_checked, preserved in the record for the consumer to read.',
  phases: [
    { title: 'Scope', detail: 'guarded reviewer enumerates the diff', model: 'sonnet' },
    { title: 'Review', detail: 'correctness and security lanes in parallel', model: 'opus' },
  ],
}

// Lane model policy (operator ruling 2026-08-09). Review lanes are neither workers nor
// measurement pins, so the worker doctrine and the eval doctrine both leave them unpinned -- and
// unpinned meant silently inheriting the session model, which billed a Fable session ~152k
// tokens per round for no measured review-quality gain. The lanes pin to `opus`: its documented
// review profile (high precision AND recall, accurate at lower effort) is the fit for judgment
// work, at half Fable's rate. Scope is mechanical git enumeration, which fits the lower tier
// at `sonnet` (operator re-ruling 2026-08-10: workers default opus, lower when the task is
// genuinely mechanical -- this is the canonical mechanical case). Aliases only, never full
// model IDs: an alias
// follows the model line's upgrades, a pinned ID silently freezes review quality at last
// generation.
// To pin lower, edit the meta.phases `model` literals above -- deliberately NOT an args or
// config surface: the args contract stays ref-only (issue #63), and a runtime knob with no
// demonstrated consumer waits trigger-bound per the proportionality rule.
// The model names are REPEATED literals, not derived: the runtime extracts meta statically and
// evaluates the body with the export isolated, so `meta` is not in scope here at all --
// deriving (`meta.phases[0].model`) validated clean, installed everywhere, and then failed
// every invocation at load with "meta is not defined" (field-proven 2026-08-09, CLI 2.1.226,
// run wf_c1db8dfb-b9f, the 1.7.0 acceptance run). The validator now rejects any bare `meta`
// reference in the body, and a repo test holds these literals equal to the meta.phases models
// so the progress display cannot claim one model while the lanes run another.
const SCOPE_MODEL = 'sonnet'
const LANE_MODEL = 'opus'
const LANE_EFFORT = 'high'

// Severities and verdict forms mirror agents/code-reviewer.md's canonical packet -- including the
// mutable-tree PROVISIONAL form, which is why the scope packet records head_sha and tree_dirty: a
// merge record either binds to exact bytes or says it cannot. The evidence enum reuses the
// fleet's canonical [verified]/[sourced]/[unverified] triad (validator-pinned to
// EVIDENCE_LABEL_STEMS), which is fleet convention rather than code-reviewer's own packet
// vocabulary -- the prompt defines the labels inline for the reviewer.
// Schema constrains only the final packet; the agents reason in free prose first (format-tax
// evidence in the WF-001 spec). Validation retries at most 5 times, then the agent() call fails
// -- every await below is fail-closed and returns a structured inconclusive verdict instead of
// surfacing a bare runtime error.
const EVIDENCE = ['verified', 'sourced', 'unverified']
const FINDING = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    line: { type: 'integer' },
    claim: { type: 'string', description: 'one-sentence defect statement' },
    severity: { type: 'string', enum: ['P0', 'P1', 'P2', 'P3'] },
    evidence: { type: 'string', enum: EVIDENCE },
    failure_scenario: { type: 'string', description: 'concrete inputs/state -> wrong outcome' },
  },
  required: ['file', 'line', 'claim', 'severity', 'evidence', 'failure_scenario'],
}
const PACKET = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: FINDING },
    verdict: {
      type: 'string',
      enum: ['approve', 'approve-with-nits', 'request-changes', 'provisional-commit-and-re-review'],
      description: 'your canonical verdict; provisional whenever the tree was dirty',
    },
    not_checked: { type: 'string', description: 'what this pass could not or did not examine' },
  },
  required: ['findings', 'verdict', 'not_checked'],
}
const SCOPE_SCHEMA = {
  type: 'object',
  properties: {
    base_ref: { type: 'string' },
    head_sha: { type: 'string', description: 'git rev-parse HEAD -- the bytes any verdict binds to' },
    tree_dirty: { type: 'boolean', description: 'true if git status --porcelain printed anything' },
    changed_files: { type: 'array', items: { type: 'string' } },
    diff_summary: { type: 'string', description: 'per-file one-line change summary' },
  },
  required: ['base_ref', 'head_sha', 'tree_dirty', 'changed_files', 'diff_summary'],
}

// Scope runs under the guarded reviewer identity, not a default workflow agent: the read-only
// boundary must be structural (the PreToolUse guard, probe-verified inside workflows), never the
// prompt phrase "read-only" -- a prompt-injected or mistaken default agent could write into the
// tree it is scoping. Everything scope needs is on the guard's git allowlist: diff, log, status,
// merge-base, rev-parse, ls-files (scripts/readonly-guard.py).
phase('Scope')
// Two arg shapes fail closed with an error that names the actual contract (issues #63/#64: the
// natural invocations -- a prose review brief, or a range like main..Y -- previously burned a
// full round-trip on a message that said neither what IS accepted nor that focus text is
// ignored). Prose can never become a silent no-op default, and a range can never produce the
// conflated working-tree-vs-range diff observed under concurrent worktrees.
const requestedRef = typeof args === 'string' && args.trim() ? args.trim() : null
if (requestedRef && (/^\-/.test(requestedRef) || /\s/.test(requestedRef))) {
  return {
    verdict: 'inconclusive',
    failed_lane: 'scope',
    error: 'args must be a single git ref to use as the diff base (e.g. "main", "HEAD~3"); ' +
      'review focus text is not accepted -- deep-review always reviews the ambient working ' +
      'tree, with no args defaulting the base to the merge base with main',
    review: null,
    security: null,
    scope: null,
  }
}
if (requestedRef && requestedRef.includes('..')) {
  return {
    verdict: 'inconclusive',
    failed_lane: 'scope',
    error: 'args must be a single base ref, not a range -- deep-review reviews the ambient ' +
      'working tree against the given base and cannot review a commit range; to review branch ' +
      'Y, check Y out and pass its base (or no args for the merge base with main)',
    review: null,
    security: null,
    scope: null,
  }
}
let scope
try {
  scope = await agent(
    'Enumerate the review scope using read-only git inspection only. ' +
    (requestedRef
      ? `Resolve the diff base as the merge base of HEAD and ${requestedRef} ` +
        `(git merge-base HEAD ${requestedRef}) and diff the working tree against that -- ` +
        'resolving through the merge base means a base on a diverged branch yields the fork ' +
        'point rather than a diff that conflates two unrelated change sets.'
      : 'Diff the working tree against the merge base with main (git merge-base HEAD main).') +
    ' Report the resolved base ref, the head commit (git rev-parse HEAD), whether the working ' +
    'tree is dirty (git status --porcelain), the changed file list, and a one-line-per-file ' +
    'summary of what changed. If the diff is empty, return an empty file list.',
    { agentType: 'sde-agents:code-reviewer', label: 'scope', schema: SCOPE_SCHEMA, model: SCOPE_MODEL },
  )
} catch (err) {
  return { verdict: 'inconclusive', failed_lane: 'scope', error: String(err), review: null, security: null, scope: null }
}
if (!scope) {
  return { verdict: 'inconclusive', failed_lane: 'scope', review: null, security: null, scope: null }
}
if (scope.changed_files.length === 0) {
  return { verdict: 'no-diff', confirmed_criticals: 0, review: null, security: null, scope }
}

phase('Review')
const context =
  `Base ref: ${scope.base_ref}\nHead: ${scope.head_sha} (tree_dirty: ${scope.tree_dirty})\n` +
  `Changed files:\n- ${scope.changed_files.join('\n- ')}\nSummary:\n${scope.diff_summary}\n` +
  'Work your normal checklist and reason in prose first; the schema constrains only your final ' +
  'packet. Label evidence honestly: verified only for what you ran or observed. If tree_dirty ' +
  'is true, your verdict must be provisional-commit-and-re-review.'
// The security lane is a second code-reviewer pass seeded with a security-only threat model --
// the fallback sre-tool documents when the auditor cannot run. application-security-auditor is
// deliberately NOT used: its own negative routing excludes branch diffs, and it holds no Bash.
let lanes
try {
  lanes = await parallel([
    () => agent(
      'Review this diff for correctness, safety, and convention adherence.\n' + context,
      { agentType: 'sde-agents:code-reviewer', label: 'review', schema: PACKET, phase: 'Review',
        model: LANE_MODEL, effort: LANE_EFFORT },
    ),
    () => agent(
      'Second review lane, security-only threat model: source-to-sink reachability of untrusted ' +
      'input, authority and permission changes, injection surfaces, secret handling.\n' + context,
      { agentType: 'sde-agents:code-reviewer', label: 'security', schema: PACKET, phase: 'Review',
        model: LANE_MODEL, effort: LANE_EFFORT },
    ),
  ])
} catch (err) {
  return { verdict: 'inconclusive', failed_lane: 'parallel', error: String(err), review: null, security: null, scope }
}
const [review, security] = lanes
// parallel() resolves a failed thunk to null (documented runtime contract) -- a null lane means
// schema retries exhausted or the agent died. Fail closed and name the lane; never guess.
if (!review || !security) {
  return {
    verdict: 'inconclusive',
    failed_lane: !review ? 'review' : 'security',
    confirmed_criticals: 0, review, security, scope,
  }
}
// The merge record, gated in code: criticals or a request-changes force do-not-merge; a dirty
// tree caps the record at the reviewer's own PROVISIONAL form; agent verdicts are preserved
// verbatim inside their packets -- this record interprets, never rewrites, them.
const criticals = [...review.findings, ...security.findings]
  .filter((f) => f.severity === 'P0' || f.severity === 'P1')
const verdicts = [review.verdict, security.verdict]
let merged
if (criticals.length > 0 || verdicts.includes('request-changes')) merged = 'do-not-merge'
else if (scope.tree_dirty || verdicts.includes('provisional-commit-and-re-review')) merged = 'provisional-commit-and-re-review'
else if (verdicts.includes('approve-with-nits')) merged = 'merge-with-nits'
else merged = 'merge'
return { verdict: merged, head_sha: scope.head_sha, confirmed_criticals: criticals.length, review, security, scope }
