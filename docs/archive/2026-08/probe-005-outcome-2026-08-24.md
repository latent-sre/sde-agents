# PROBE-005 outcome — 2026-08-24

**Status: historical outcome record.** This records only the live `--agent` scoping evidence
required by PROBE-005. It is not a claim that the full plugin probe passed.

## Source and conditions

- `python3 -u scripts/probe_plugin.py` ran from
  `9fd40d8318debee3e7647bfaf2312a5f1a6febfb`. Its probe-relevant files —
  `scripts/probe_plugin.py`, `scripts/readonly-guard.py`, `hooks/hooks.json`, and
  `agents/code-reviewer.md` — are byte-identical to `origin/main` at
  `fcc8886592e23d2990c508f2959777fdf3e1969f`.
- The run used an isolated local install of `@anthropic-ai/claude-code@2.1.219`, the exact CLI
  version pinned by `.github/workflows/validate.yml`. `claude --version` reported
  `2.1.219 (Claude Code)` before the probe. The host's global CLI remained `2.1.241`.
- This was a real model/API run using the host's ambient Claude authentication. The lane does not
  pin or report a model, so this record makes no model-specific claim. Raw session JSONL was not
  retained.

## Required result

**Observed: PASS.** The probe launched a main session with
`--agent sde-agents:code-reviewer`, observed its denylisted Bash call, correlated the call with its
own `tool_result`, and found the read-only guard's denial voice. The probe printed:

```text
[PASS] the guard DENIED a --agent main session's denylisted command
```

This establishes the narrow PROBE-005 property on CLI 2.1.219: a main session launched as the
guarded agent carries the active-agent identity needed for the Claude `PreToolUse` hook to scope
and deny the command.

## Limits and disposition

The broader probe did not complete. Its initial composite session reproduced PROBE-002's known
asynchronous correlation gap, and the later conditional-reference session remained active for
several minutes after the required `--agent` result. The run was manually interrupted before the
script's 900-second subprocess timeout and before its workflow tail, so there is no full-probe
exit-zero result to report.

The interruption does not open a new timeout item. Inspection confirmed that
`scripts/probe_plugin.py` already bounds each subprocess at 900 seconds; the earlier hypothesis
that it had no timeout was false and is dropped. PROBE-002 remains the owner of the asynchronous
correlation evidence.

Reopen PROBE-005 when the pinned Claude CLI changes, the guard's active-agent scoping changes, or a
fresh `--agent` run does not reproduce the denial.
