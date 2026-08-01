export const meta = {
  name: 'deep-review',
  description: 'Two parallel code-reviewer lanes (correctness + security threat model) over the working diff, schema-typed packets, deterministic merge record',
  phases: [
    { title: 'Scope', detail: 'guarded reviewer enumerates the diff' },
    { title: 'Review', detail: 'correctness and security lanes in parallel' },
  ],
}

// The packet contract mirrors agents/code-reviewer.md's canonical packet: P0-P3 severities, the
// [verified]/[sourced]/[unverified] evidence triad (validator-pinned), and the reviewer's own
// verdict forms -- including the mutable-tree PROVISIONAL form, which is why the scope packet
// records head_sha and tree_dirty: a merge record either binds to exact bytes or says it cannot.
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
  required: ['file', 'claim', 'severity', 'evidence', 'failure_scenario'],
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
const requestedRef = typeof args === 'string' && args.trim() ? args.trim() : null
let scope
try {
  scope = await agent(
    'Enumerate the review scope using read-only git inspection only. ' +
    (requestedRef
      ? `Diff the working tree against ${requestedRef}.`
      : 'Diff the working tree against the merge base with main (git merge-base HEAD main).') +
    ' Report the resolved base ref, the head commit (git rev-parse HEAD), whether the working ' +
    'tree is dirty (git status --porcelain), the changed file list, and a one-line-per-file ' +
    'summary of what changed. If the diff is empty, return an empty file list.',
    { agentType: 'sde-agents:code-reviewer', label: 'scope', schema: SCOPE_SCHEMA },
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
      { agentType: 'sde-agents:code-reviewer', label: 'review', schema: PACKET, phase: 'Review' },
    ),
    () => agent(
      'Second review lane, security-only threat model: source-to-sink reachability of untrusted ' +
      'input, authority and permission changes, injection surfaces, secret handling.\n' + context,
      { agentType: 'sde-agents:code-reviewer', label: 'security', schema: PACKET, phase: 'Review' },
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
