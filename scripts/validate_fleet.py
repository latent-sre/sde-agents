#!/usr/bin/env python3
"""Validate this repository's canonical agent and skill definitions.

The validator intentionally uses only the Python standard library. It checks
the local ``agents/`` and ``skills/`` layout instead of assuming a particular
runtime's generated directories.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# The optional `./` is load-bearing. Without it the lookbehind rejected any link written
# `./references/foo.md`, so such a link matched nothing: the existence check never ran (a broken
# path shipped silently) and the orphan check counted the target as unlinked. The dot remains in
# the leading boundary: without it matching restarts inside `../references` or
# `foo.references`, incorrectly treating either as a local bundle path. Both consumers strip the
# allowed prefix before comparing, so the two valid spellings resolve to the same file.
BUNDLE_REF_RE = re.compile(
    r"(?<![\w./])(?:\./)?(?:references|assets|scripts)/[A-Za-z0-9._/-]*[A-Za-z0-9_-]"
)
TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")
# A YAML block-sequence item, e.g. `  - backend-craft`. TOP_LEVEL_KEY_RE is anchored at column zero
# and never matches an indented `- item` line, so a key like `skills:` whose value is a block
# sequence rather than an inline scalar needs its own reader or it silently parses to "".
LIST_ITEM_RE = re.compile(r"^\s*-\s+(\S.*?)\s*$")
INVENTORY_RE = re.compile(
    r"<!-- fleet-inventory:start -->.*?<!-- fleet-inventory:end -->",
    re.DOTALL,
)
# Two different questions, two different errors: keep runtime schema ("is this a real Claude Code
# value?") separate from fleet policy ("do we permit it?"). Claude Code accepts these aliases AND any
# full model ID that `--model` takes, e.g.
# `claude-opus-4-8` (per code.claude.com/docs/en/sub-agents). This fleet deliberately allows only the
# aliases: a pinned ID goes stale silently while an alias follows the model upgrade. So a full ID is
# a POLICY failure (valid runtime value, banned here) and anything else is a SCHEMA failure (not a
# model at all) — never report them as the same thing.
ALIAS_MODELS = {"inherit", "haiku", "sonnet", "opus", "fable"}
FULL_MODEL_ID_RE = re.compile(r"^claude-[a-z0-9]+(?:-[a-z0-9]+)+$")
# Every frontmatter key Claude Code defines for a subagent (code.claude.com/docs/en/sub-agents).
# This exists to close a silent-disarm hole, not for tidiness: the validator used to check only the
# VALUES of keys it knew and never the KEY NAMESPACE, so a misspelled key was dropped on the floor.
# That matters because `hooks:` on code-reviewer is what installs the read-only guard on an agent
# holding Bash — misspell it `hook:` and (before this check) the validator passed, the hook-wiring
# test passed, and the guard was gone. Whether the runtime errors or silently ignores an unknown key
# is UNDOCUMENTED, so we refuse to depend on the answer: an unknown key fails here.
KNOWN_AGENT_FIELDS = {
    "name",
    "description",
    "tools",
    "disallowedTools",
    "model",
    "permissionMode",
    "maxTurns",
    "skills",
    "mcpServers",
    "hooks",
    "memory",
    "background",
    "effort",
    "isolation",
    "color",
    "initialPrompt",
}
# Every documented SKILL.md frontmatter field (code.claude.com/docs/en/skills, frontmatter table).
# Same rationale as KNOWN_AGENT_FIELDS: an unrecognized key is not guaranteed to fail loudly, so a
# typo silently drops what it configured — a `disable-model-invocaton` or `user-invokable` slip would
# quietly turn a side-effect skill model-invocable, or expose a background skill, with no error. The
# agent path had this check; the skill path did not (external-review gap). Kept in sync with the docs
# by hand; `claude plugin validate --strict` is the backstop for anything added upstream since.
KNOWN_SKILL_FIELDS = {
    "name",
    "description",
    "when_to_use",
    "argument-hint",
    "arguments",
    "disable-model-invocation",
    "user-invocable",
    "allowed-tools",
    "disallowed-tools",
    "model",
    "effort",
    "context",
    "agent",
    "background",
    "hooks",
    "paths",
    "shell",
}
# Claude Code SILENTLY IGNORES these three on a PLUGIN-SHIPPED agent: "For security reasons,
# `hooks`, `mcpServers`, and `permissionMode` are not supported for plugin-shipped agents"
# (code.claude.com/docs/en/plugins-reference). Probed on CLI 2.1.200: a plugin agent's frontmatter
# hook never fired, while a byte-identical hook on a project-scope agent did.
#
# This fleet SHIPS AS A PLUGIN, so any of them here is configuration that does not exist. `hooks:`
# is the dangerous one — it is how the read-only guard used to be attached to `code-reviewer`, and
# leaving it would read as armor while providing none. An agent that LOOKS guarded and isn't is
# strictly worse than one that is honestly unguarded, because nobody goes looking. The guard now
# lives in hooks/hooks.json (session-wide) and scopes itself on the payload's `agent_type`.
#
# This replaces the old `bypassPermissions` value check: banning `permissionMode` outright covers
# it, and the old error ("it would nullify the read-only guard") is no longer even true for a
# plugin agent — the field is ignored, so it nullifies nothing. Wrong reasons rot into wrong fixes.
PLUGIN_INERT_AGENT_FIELDS = {"hooks", "mcpServers", "permissionMode"}
# Tools that make an agent a WRITER. An agent holding Bash but none of these is a read-only agent
# whose only route to mutation is the shell — exactly what the guard exists to close.
WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
# The `tools:` field IS the authority an agent is granted, so it gets the same runtime-schema vs
# fleet-policy split as `model`: RUNTIME_TOOLS answers "is this a real Claude Code tool?" and
# FLEET_TOOLS answers "do we grant it here?". A typo (`Wrte`) is a schema error; a real-but-unadopted
# tool (`PowerShell`) is a policy error you can lift deliberately. Collapsing the two would either
# let typos through or make the validator a mirror of the runtime with no opinion of its own.
#
# Canonical table: code.claude.com/docs/en/tools-reference. Note `BashOutput`, `KillShell`, and
# `SlashCommand` were previously allowed here and appear nowhere in it — they were accepted names
# that grant nothing.
RUNTIME_TOOLS = {
    # "Task" was renamed to "Agent" in 2.1.63 and survives only as a deprecated alias; we take the
    # canonical name so a legacy `Task` grant fails and gets rewritten. Do not "fix" Agent -> Task.
    "Agent", "Artifact", "AskUserQuestion", "Bash", "CronCreate", "CronDelete", "CronList", "Edit",
    "EnterPlanMode", "EnterWorktree", "ExitPlanMode", "ExitWorktree", "Glob", "Grep",
    "ListMcpResourcesTool", "LSP", "Monitor", "NotebookEdit", "PowerShell", "PushNotification",
    "Read", "ReadMcpResourceTool", "RemoteTrigger", "ReportFindings", "ScheduleWakeup", "SendMessage",
    "SendUserFile", "ShareOnboardingGuide", "Skill", "TaskCreate", "TaskGet", "TaskList", "TaskOutput",
    "TaskStop", "TaskUpdate", "TodoWrite", "ToolSearch", "WaitForMcpServers", "WebFetch", "WebSearch",
    "Workflow", "Write",
}
# What this fleet actually grants. Widen deliberately; every entry is authority.
FLEET_TOOLS = {
    "Agent", "Bash", "Edit", "Glob", "Grep", "NotebookEdit", "Read", "Skill", "TodoWrite",
    "ToolSearch", "WebFetch", "WebSearch", "Write",
}
# MCP tools share the `tools:` availability allowlist with built-ins, but their namespace is
# runtime-configured rather than a closed Claude Code table. Keep a separate exact allowlist so
# every external capability is an explicit fleet decision. Server-level grants (`mcp__server` or
# `mcp__server__*`) are valid runtime syntax but forbidden here: they silently acquire whatever a
# future server release adds. That is already unsafe for GitHits, whose read-only evidence tools
# sit beside `feedback`, an external write.
EVIDENCE_MCP_TOOLS = {
    "mcp__claude_ai_Context7__query-docs",
    "mcp__claude_ai_Context7__resolve-library-id",
    "mcp__plugin_context7_context7__query-docs",
    "mcp__plugin_context7_context7__resolve-library-id",
    "mcp__plugin_githits_githits__code_files",
    "mcp__plugin_githits_githits__code_grep",
    "mcp__plugin_githits_githits__code_read",
    "mcp__plugin_githits_githits__docs_list",
    "mcp__plugin_githits_githits__docs_read",
    "mcp__plugin_githits_githits__get_example",
    "mcp__plugin_githits_githits__pkg_changelog",
    "mcp__plugin_githits_githits__pkg_deps",
    "mcp__plugin_githits_githits__pkg_info",
    "mcp__plugin_githits_githits__pkg_upgrade_review",
    "mcp__plugin_githits_githits__pkg_vulns",
    "mcp__plugin_githits_githits__search",
    "mcp__plugin_githits_githits__search_language",
    "mcp__plugin_githits_githits__search_status",
}
FLEET_MCP_TOOLS = set(EVIDENCE_MCP_TOOLS)
LOCAL_REPOSITORY_TOOLS = {"Glob", "Grep", "Read"}
EXTERNAL_RESEARCH_TOOLS = {"ToolSearch", "WebFetch", "WebSearch", *EVIDENCE_MCP_TOOLS}
# Investigation roles are deliberately split at the tool layer. A role that holds private source
# and fetched external content can leak one into the other through prompt injection even when its
# prose says not to. Pin both required and forbidden authority so a one-line frontmatter edit cannot
# silently collapse that trust boundary.
REQUIRED_AGENT_TOOLS = {
    "application-security-auditor": set(LOCAL_REPOSITORY_TOOLS),
    "repository-investigator": set(LOCAL_REPOSITORY_TOOLS),
    "researcher": set(EXTERNAL_RESEARCH_TOOLS),
}
FORBIDDEN_AGENT_TOOLS = {
    "application-security-auditor": {
        "Agent", "Bash", "Edit", "NotebookEdit", "ToolSearch", "WebFetch", "WebSearch", "Write",
        *EVIDENCE_MCP_TOOLS,
    },
    "repository-investigator": {
        "Agent", "Bash", "Edit", "NotebookEdit", "ToolSearch", "WebFetch", "WebSearch", "Write",
        *EVIDENCE_MCP_TOOLS,
    },
    "researcher": {
        "Agent", "Bash", "Edit", "Glob", "Grep", "NotebookEdit", "Read", "Write",
    },
}
# These references connect cooperative role instructions to executable controls. A script can
# remain present while the only agent or skill that should use it silently stops naming it; the
# inverse is just as dangerous, because a stale prompt path reads like enforcement but resolves to
# nothing at runtime. Pin both ends here and let generated-adapter byte checks cover translation.
RUNTIME_CONTROL_WIRING = {
    "scripts/verification_sandbox.py": "agents/verification-engineer.md",
    "scripts/run_state.py": "skills/sre-tool/SKILL.md",
    "scripts/effect_broker.py": "agents/homelab-platform.md",
}
RUNTIME_EVIDENCE_PRODUCERS = {
    "scripts/verification_sandbox.py",
    "scripts/run_state.py",
    "scripts/effect_broker.py",
}
# Real tools that a SUBAGENT never receives, however they are listed, because they depend on the main
# conversation's UI or session state (code.claude.com/docs/en/sub-agents). Everything in agents/ is a
# subagent definition, so granting one of these is a no-op that reads like a capability.
SUBAGENT_UNAVAILABLE_TOOLS = {
    "AskUserQuestion",
    "EnterPlanMode",
    "ExitPlanMode",  # unless permissionMode is `plan`
    "ScheduleWakeup",
    "WaitForMcpServers",
}
# A tools entry: a bare name, or a name with a parenthesized scope, e.g. `Agent(worker, researcher)`.
TOOL_ENTRY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\((.*)\))?$")
# Exact MCP names use the runtime's `mcp__<server>__<tool>` convention. Hyphens are real in tool
# names (`query-docs`, `resolve-library-id`), so the built-in-name grammar above cannot parse them.
# Server names are normalized to one underscore-delimited segment; `__` remains the separator.
MCP_EXACT_TOOL_RE = re.compile(r"^mcp__[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+$")
MCP_SERVER_GRANT_RE = re.compile(r"^mcp__[A-Za-z0-9_.-]+(?:__\*)?$")


def split_tools(raw: str) -> list[str]:
    """Split a `tools:` value on top-level commas only.

    A naive ``raw.split(",")`` shreds a scoped grant: `Agent(worker, researcher)` becomes
    `Agent(worker` and `researcher)`. Splitting at paren depth 0 keeps the scope intact so it can be
    judged rather than mangled into two bogus tool names.
    """
    entries: list[str] = []
    depth = 0
    current: list[str] = []
    for char in raw:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            entries.append("".join(current))
            current = []
            continue
        current.append(char)
    entries.append("".join(current))
    return [entry.strip(" []'\"") for entry in entries if entry.strip(" []'\"")]
# Canonical evidence-label phrasing; agent files may extend a definition but
# must contain these exact stems so the triad cannot drift file by file.
EVIDENCE_LABEL_STEMS = (
    "**[verified]** (you ran or observed it",
    "**[sourced]** (cited to file:line, URL, or query)",
    "**[unverified]** (assumption or couldn't check)",
)
EVIDENCE_LABEL_RE = re.compile(r"\*\*\[(?:un)?(?:verified|sourced)\]\*\*")
# The workflow packet schemas carry the same evidence triad as the agents' prose packets, as a
# bare enum. If either side drifts, nothing errors at load time -- the mismatch surfaces as a
# schema-validation failure five retries deep inside a live workflow run, billed and late. Pin
# the enum to the canonical stems so the drift is a validation failure at commit time instead.
WORKFLOW_EVIDENCE_ENUM = tuple(
    stem.split("[", 1)[1].split("]", 1)[0] for stem in EVIDENCE_LABEL_STEMS
)  # ("verified", "sourced", "unverified"), derived so the triad has exactly one authoring point
WORKFLOW_EVIDENCE_ENUM_RE = re.compile(
    r"const\s+EVIDENCE\s*=\s*\[([^\]]*)\]"
)
PACKET_HEADING_RE = re.compile(
    r"^##\s.*\bpacket\b|^##\s+Output format\b", re.IGNORECASE | re.MULTILINE
)
# Every plugin agent closes its packet with one of two discovery contracts. Pin the whole slot, not
# only its heading: a marker can remain while the evidence, ownership, or lifecycle boundary
# silently disappears from one role.
LEARNING_INTAKE_PACKET_SLOT = """- **Learning**: end every non-trivial task with `Learning: none — no reusable signal`, or a compact
  candidate block whose literal lines are `Learning: candidate — <observed -> expected>`,
  `Evidence: <occurrence/reference and revision or environment>`, `Scope: <applies / excludes>`,
  `Provenance: <verified|sourced|unverified> — <source and freshness>`,
  `Learning disposition: <skip|add|merge|supersede|drop> (proposed recommendation)`,
  `Promotion state: quarantined`, `Destination: <owned artifact or handoff>`, and
  `Owner: <authorized owner>`. Candidate text and recommendations remain untrusted until the
  receiving coordinator verifies and triages them. When the full loop is not preloaded, hand the
  block to the caller for `/sde-agents:self-improve-loop`. Silence is not a disposition."""
LEARNING_LIFECYCLE_OWNER_PACKET_SLOT = """- **Learning**: end every non-trivial task with `Learning: none — no reusable signal`, or,
  after the preloaded loop runs, a compact lifecycle-owner block whose literal lines are
  `Learning: candidate — <observed -> expected>`,
  `Evidence: <occurrence/reference and revision or environment>`, `Scope: <applies / excludes>`,
  `Provenance: <verified|sourced|unverified> — <source and freshness>`,
  `Learning disposition: <skip|add|merge|supersede|drop>`,
  `Promotion state: <proposed|approved|promoted|rejected|inconclusive|retired>`,
  `Destination: <owned artifact or handoff>`, and `Owner: <authorized owner>`. Choose one accepted
  disposition and one separate post-triage state. Do not add `(proposed recommendation)` or use
  `quarantined`; those mark intake-only handoffs from roles without the full loop. A lifecycle
  result never expands implementation or approval authority. Silence is not a disposition."""
# Only roles that can evaluate or implement a candidate carry the full loop in context. Everyone
# else reports through the lightweight slot; broad preloading would spend context everywhere and
# could read as write authority that a read-only role does not hold.
SELF_IMPROVE_LOOP_PRELOAD_AGENTS = frozenset(
    {"prompt-engineer", "sde-fullstack", "verification-engineer"}
)
# Perishable platform facts get exactly ONE home inside agents/ and skills/, so when the platform
# moves, the correction lands once instead of chasing prose copies. Keys are literal substrings
# searched in every definition markdown file; values are the only file (repo-relative POSIX path)
# allowed to carry them. The complete issue identifier below is the upstream
# disable-model-invocation-ignored-for-plugin-skills bug: it had already been copied into an agent
# body once, and a stale copy keeps teaching the old platform behavior with no runtime error after
# the issue closes. Pin the full identifier rather than its common numeric suffix so unrelated
# ports, record IDs, and metrics remain valid definition content.
PERISHABLE_TOKENS = {
    "anthropics/claude-code#22345": "skills/prompt-craft/references/claude-code-frontmatter.md",
}
# AGENTS.md drift tripwires. The guide paraphrases the validator and the repo layout, and prose has
# no runtime: Claude Code loads CLAUDE.md (not AGENTS.md), so a lost `@AGENTS.md` import orphans the
# guide without an error; a renamed script leaves it pointing at nothing; an alias change leaves it
# teaching a stale policy. Same doctrine as EVIDENCE_LABEL_STEMS — pin the paraphrase to its source
# and fail loudly when they part.
GUIDE_IMPORT = "@AGENTS.md"
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
# A path-shaped token inside an inline code span. Deliberately excludes glob/placeholder characters
# (`*`, `<`, `>`, `$`, `{`) so illustrative forms like `agents/*.md` and `skills/<name>/SKILL.md`
# self-exclude and only concrete, resolvable paths are asserted.
GUIDE_PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_.][A-Za-z0-9_./-]*")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(path: Path) -> dict[str, str] | None:
    """Parse the small YAML subset used by the fleet frontmatter."""

    lines = read_text(path).splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None

    fields: dict[str, str] = {}
    i = 1
    while i < end:
        if not lines[i].strip() or lines[i].lstrip().startswith("#"):
            i += 1
            continue

        match = TOP_LEVEL_KEY_RE.match(lines[i])
        if not match:
            # Skipping an unparseable line loses whatever it configured without a word: a typo'd
            # `tools Read, Write` would read as no tools authority at all, and the file would
            # validate. Refuse the block instead so the caller reports it.
            return None

        key, value = match.groups()
        if key in fields:
            # YAML keeps the last duplicate. A file carrying `model: opus` then `model: inherit`
            # would validate against a value its author never intended to be the live one.
            return None
        value = value.strip()
        if value in {">", ">-", "|", "|-"}:
            parts: list[str] = []
            i += 1
            while i < end and not TOP_LEVEL_KEY_RE.match(lines[i]):
                parts.append(lines[i].strip())
                i += 1
            fields[key] = " ".join(part for part in parts if part).strip()
            continue

        if not value:
            # An empty inline value can mean a YAML block sequence follows (`skills:` then indented
            # `- item` lines). Collect it so a value like `skills:` doesn't silently become "" with
            # nothing downstream ever able to check it -- see LIST_ITEM_RE.
            # Skip blank lines and comments within the sequence, mirroring the outer loop, so that
            # `skills:\n  # note\n  - item` doesn't leave `- item` stranded in the outer loop
            # where it fails TOP_LEVEL_KEY_RE and returns None.
            items: list[str] = []
            j = i + 1
            while j < end:
                line = lines[j]
                if not line.strip() or line.lstrip().startswith("#"):
                    j += 1
                    continue
                item_match = LIST_ITEM_RE.match(line)
                if not item_match:
                    break
                items.append(item_match.group(1).strip("'\""))
                j += 1
            if items:
                fields[key] = ", ".join(items)
                i = j
                continue

        fields[key] = value.strip("'\"")
        i += 1

    return fields


def validate_name(name: str, kind: str, source: Path) -> list[str]:
    issues: list[str] = []
    if not name:
        return [f"{source}: missing {kind} name"]
    if len(name) > 64:
        issues.append(f"{source}: {kind} name exceeds 64 characters")
    if not NAME_RE.fullmatch(name):
        issues.append(f"{source}: invalid {kind} name {name!r}")
    return issues


def validate_description(fields: dict[str, str], kind: str, source: Path) -> list[str]:
    description = fields.get("description", "").strip()
    if not description:
        return [f"{source}: missing {kind} description"]
    if len(description) > 1024:
        return [f"{source}: {kind} description exceeds 1024 characters"]
    return []


def validate_agents(root: Path) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    names: list[str] = []
    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        return [f"{agents_dir}: missing agents directory"], names

    for path in sorted(agents_dir.glob("*.md")):
        fields = parse_frontmatter(path)
        if fields is None:
            issues.append(f"{path}: missing or malformed frontmatter")
            continue

        for key in fields:
            if key not in KNOWN_AGENT_FIELDS:
                issues.append(
                    f"{path}: unknown frontmatter key {key!r} is not a Claude Code agent field. "
                    f"An unrecognized key does not fail loudly at load time, so a typo here silently "
                    f"drops whatever it was meant to configure."
                )
            elif key in PLUGIN_INERT_AGENT_FIELDS:
                issues.append(
                    f"{path}: frontmatter key {key!r} is SILENTLY IGNORED for a plugin-shipped agent, "
                    f"and this fleet ships as a plugin. Declaring it configures nothing while reading "
                    f"as though it does. The read-only guard belongs in hooks/hooks.json, scoped on "
                    f"the payload's 'agent_type'."
                )

        name = fields.get("name", "")
        names.append(name or path.stem)
        issues.extend(validate_name(name, "agent", path))
        if name and name != path.stem:
            issues.append(f"{path}: agent name {name!r} must match filename {path.stem!r}")
        issues.extend(validate_description(fields, "agent", path))

        tools = fields.get("tools", "").strip()
        parsed_tools: list[str] = []
        if not tools:
            # Not a harmless omission: an absent `tools:` INHERITS EVERY TOOL rather than granting
            # none, so a reviewer meant to be read-only would silently receive Write and Edit.
            issues.append(f"{path}: missing explicit tools authority (omitting it inherits ALL tools)")
        else:
            parsed_tools = split_tools(tools)
            if len(parsed_tools) != len(set(parsed_tools)):
                issues.append(f"{path}: duplicate tool in tools authority")
            for tool in parsed_tools:
                if tool.startswith("mcp__"):
                    if MCP_EXACT_TOOL_RE.fullmatch(tool):
                        if tool not in FLEET_MCP_TOOLS:
                            issues.append(
                                f"{path}: MCP tool {tool!r} is structurally valid but is not adopted "
                                f"by this fleet; add it to FLEET_MCP_TOOLS deliberately if the agent "
                                f"needs it"
                            )
                    elif MCP_SERVER_GRANT_RE.fullmatch(tool):
                        issues.append(
                            f"{path}: server-wide MCP grant {tool!r} is real Claude Code syntax but "
                            f"is not adopted by this fleet. It silently acquires future tools from "
                            f"that server, so list each required exact tool in FLEET_MCP_TOOLS"
                        )
                    else:
                        issues.append(
                            f"{path}: malformed MCP tool entry {tool!r} in tools authority; expected "
                            f"an exact mcp__<server>__<tool> name"
                        )
                    continue

                entry = TOOL_ENTRY_RE.match(tool)
                if not entry:
                    issues.append(f"{path}: malformed tool entry {tool!r} in tools authority")
                    continue
                base, scope = entry.group(1), entry.group(2)

                if base not in RUNTIME_TOOLS:
                    issues.append(f"{path}: unknown tool {base!r} in tools authority is not a Claude Code tool")
                elif base in SUBAGENT_UNAVAILABLE_TOOLS:
                    issues.append(
                        f"{path}: tool {base!r} is never available to a subagent regardless of this "
                        f"grant (it needs the main conversation's UI or session state); granting it "
                        f"reads like a capability the agent does not have"
                    )
                elif base not in FLEET_TOOLS:
                    issues.append(
                        f"{path}: tool {base!r} is a real Claude Code tool but is not adopted by this "
                        f"fleet; add it to FLEET_TOOLS deliberately if the agent needs it"
                    )

                if scope is not None and base == "Agent":
                    # The trap: `Agent(worker)` restricts spawning ONLY for an agent running as the
                    # main thread (`claude --agent`). In a subagent definition the parenthesized type
                    # list is IGNORED, so this grants UNRESTRICTED spawn while reading like a limit.
                    issues.append(
                        f"{path}: scoped grant {tool!r} does not restrict anything here. The "
                        f"Agent(type) allowlist applies only to a main-thread agent (claude --agent); "
                        f"in a subagent definition the type list is ignored and spawning is "
                        f"unrestricted. Use a bare 'Agent' so the grant matches reality"
                    )
                elif scope is not None:
                    issues.append(
                        f"{path}: scoped grant {tool!r} uses permission-rule syntax that the "
                        f"frontmatter 'tools:' field SILENTLY IGNORES. Probed on CLI 2.1.200: an agent "
                        f"granted `Bash(git diff:*)` ran `git status` exactly like one granted a bare "
                        f"`Bash` — the specifier restricts nothing while reading as though it does. "
                        f"Specifiers work only in settings.json permission rules (session-wide) or a "
                        f"PreToolUse hook; narrow there, not here."
                    )

        required_tools = REQUIRED_AGENT_TOOLS.get(name, set())
        missing_required_tools = sorted(required_tools - set(parsed_tools))
        if missing_required_tools:
            issues.append(
                f"{path}: evidence role {name!r} is missing required tools "
                f"{missing_required_tools}. Its investigation method depends on this exact side of "
                f"the local-versus-external trust boundary, so removing authority silently makes "
                f"the method impossible"
            )
        forbidden_tools = sorted(FORBIDDEN_AGENT_TOOLS.get(name, set()) & set(parsed_tools))
        if forbidden_tools:
            issues.append(
                f"{path}: trust-separated role {name!r} holds forbidden tools {forbidden_tools}. "
                f"Local/private repository access and external fetched content must not coexist in "
                f"one subordinate role; prose cannot enforce that boundary"
            )

        # `skills:` is in KNOWN_AGENT_FIELDS, which only checks that the KEY is real -- it says
        # nothing about whether each listed VALUE resolves to anything. Two ways that silently
        # disarms preloading: a typo'd or dropped skill name (skills/<name>/SKILL.md doesn't exist),
        # and a skill that sets `disable-model-invocation: true` -- such a skill cannot be preloaded
        # ("preloading draws from the same set of skills Claude can invoke"), so listing it here is a
        # no-op that reads like a guarantee.
        for skill_name in (entry.strip() for entry in fields.get("skills", "").split(",")):
            if not skill_name:
                continue
            skill_file = root / "skills" / skill_name / "SKILL.md"
            if not skill_file.is_file():
                issues.append(
                    f"{path}: skills: entry {skill_name!r} does not resolve to "
                    f"skills/{skill_name}/SKILL.md -- preloading silently drops it"
                )
                continue
            skill_fields = parse_frontmatter(skill_file) or {}
            if skill_fields.get("disable-model-invocation", "").strip().lower() == "true":
                issues.append(
                    f"{path}: skills: entry {skill_name!r} names {skill_file}, which sets "
                    f"disable-model-invocation: true -- a skill so marked CANNOT be preloaded "
                    f"(preloading draws from the same set of skills Claude can invoke), so listing "
                    f"it here configures nothing"
                )

        model = fields.get("model", "").strip()
        aliases = ", ".join(sorted(ALIAS_MODELS))
        if not model:
            issues.append(f"{path}: missing model")
        elif model in ALIAS_MODELS:
            pass
        elif FULL_MODEL_ID_RE.match(model):
            issues.append(
                f"{path}: model {model!r} is a valid Claude Code model but is pinned; "
                f"this fleet requires an alias ({aliases}) so agents follow model upgrades "
                f"instead of rotting on a stale pin"
            )
        else:
            issues.append(f"{path}: unknown model {model!r} (expected one of: {aliases})")

        content = read_text(path)
        if EVIDENCE_LABEL_RE.search(content):
            for stem in EVIDENCE_LABEL_STEMS:
                if stem not in content:
                    issues.append(
                        f"{path}: evidence labels drifted from canonical phrasing; expected {stem!r}"
                    )
        if not PACKET_HEADING_RE.search(content):
            issues.append(
                f"{path}: missing end-of-task packet ('## ... packet' or '## Output format' section)"
            )

    if not names:
        issues.append(f"{agents_dir}: no agent definitions found")
    if len(names) != len(set(names)):
        issues.append(f"{agents_dir}: duplicate agent names")
    return issues, sorted(names)


def bundle_references(skill_file: Path) -> set[str]:
    """Every bundle path named in SKILL.md, normalized so `./references/x.md` and `references/x.md`
    are the same reference. Both direction checks read this, so they cannot disagree on spelling.
    """
    return {
        match.group(0).rstrip(".,;:)]}").removeprefix("./")
        for match in BUNDLE_REF_RE.finditer(read_text(skill_file))
    }


def validate_bundle_references(root: Path, skill_dir: Path, skill_file: Path) -> list[str]:
    issues: list[str] = []
    for reference in sorted(bundle_references(skill_file)):
        local_target = skill_dir / Path(reference)
        shared_target = root / Path(reference)
        if not local_target.exists() and not shared_target.exists():
            issues.append(f"{skill_file}: referenced file does not exist: {reference}")
    return issues


def validate_reference_orphans(skill_dir: Path, skill_file: Path) -> list[str]:
    """The other direction from validate_bundle_references: every file under references/ must be
    named by at least one link in SKILL.md.

    validate_bundle_references only ever asks "does the thing this link points at exist?" -- it never
    asks the reverse. So a references/*.md file with no routing-table row is invisible to it: the
    validator stays green, the tests stay green, and the probe only ever exercises the rows that DO
    have links. Dead knowledge that looks shipped.
    """
    issues: list[str] = []
    references_dir = skill_dir / "references"
    if not references_dir.is_dir():
        return issues
    linked = bundle_references(skill_file)
    for ref_file in sorted(references_dir.rglob("*")):
        if not ref_file.is_file():
            continue
        rel = ref_file.relative_to(skill_dir).as_posix()
        if rel not in linked:
            issues.append(
                f"{ref_file}: orphaned -- no skill-relative link to {rel!r} found in {skill_file}; a "
                f"reference file with no routing-table row is unreachable by any means. Routing-table "
                f"links must be written skill-relative (e.g. {rel!r}) -- a full path such as "
                f"'{skill_dir.name}/{rel}' will not be recognized by this check"
            )
    return issues


def validate_skills(root: Path) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    names: list[str] = []
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return [f"{skills_dir}: missing skills directory"], names

    for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            issues.append(f"{skill_dir}: missing SKILL.md")
            continue

        fields = parse_frontmatter(skill_file)
        if fields is None:
            issues.append(f"{skill_file}: missing or malformed frontmatter")
            continue

        for key in fields:
            if key not in KNOWN_SKILL_FIELDS:
                issues.append(
                    f"{skill_file}: unknown frontmatter key {key!r} is not a Claude Code skill field. "
                    f"An unrecognized key is not guaranteed to fail loudly, so a typo silently drops "
                    f"what it configured (e.g. 'disable-model-invocaton' would leave a side-effect "
                    f"skill model-invocable)."
                )

        name = fields.get("name", "")
        names.append(name or skill_dir.name)
        issues.extend(validate_name(name, "skill", skill_file))
        if name and name != skill_dir.name:
            issues.append(
                f"{skill_file}: skill name {name!r} must match directory {skill_dir.name!r}"
            )
        issues.extend(validate_description(fields, "skill", skill_file))
        issues.extend(validate_bundle_references(root, skill_dir, skill_file))
        issues.extend(validate_reference_orphans(skill_dir, skill_file))

    if not names:
        issues.append(f"{skills_dir}: no skill definitions found")
    if len(names) != len(set(names)):
        issues.append(f"{skills_dir}: duplicate skill names")
    return issues, sorted(names)


def definition_markdown_files(root: Path) -> list[Path]:
    """Every markdown file the fleet ships as behavior: agent bodies, SKILL.md files, and each
    skill's references/ and assets/ — the surface a cross-reference or platform-fact rule must
    cover, because all of it is loaded (or read by path) into real sessions."""
    files = sorted((root / "agents").glob("*.md")) if (root / "agents").is_dir() else []
    if (root / "skills").is_dir():
        files += sorted((root / "skills").rglob("*.md"))
    return files


def validate_bare_skill_references(root: Path, skill_names: list[str]) -> list[str]:
    """A bare backticked skill name in an agent body asserts "already in context".

    AGENTS.md reserves the bare form for preloaded content; everything else must be namespaced.
    The failure this catches is silent by construction: an agent told to work `some-skill` with no
    preload, no Skill grant, and no path has an instruction that cannot execute — the model just
    proceeds without the skill's content, and nothing errors. Observed for real: sde-fullstack
    said "invoke `code-craft`" while holding no route to it, and the fleet's flagship pipeline
    forbade its callers from working around the gap.
    """
    issues: list[str] = []
    known = set(skill_names)
    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        return issues
    for path in sorted(agents_dir.glob("*.md")):
        fields = parse_frontmatter(path) or {}
        preloaded = {entry.strip() for entry in fields.get("skills", "").split(",") if entry.strip()}
        for span in sorted(set(INLINE_CODE_RE.findall(read_text(path)))):
            if span in known and span not in preloaded:
                issues.append(
                    f"{path}: bare backticked skill name `{span}` claims the skill is already in "
                    f"this agent's context, but it is not in the skills: preload — the reference "
                    f"is unreachable authority that reads as configured, and nothing errors at "
                    f"runtime. Preload it; use the namespaced form if routing is the intent; or "
                    f"give an explicit, resolvable "
                    f"${{CLAUDE_PLUGIN_ROOT}}/skills/{span}/SKILL.md path if the agent must read it."
                )
    return issues


def validate_perishable_tokens(root: Path) -> list[str]:
    """Each perishable platform fact may appear in exactly one declared owner file."""
    issues: list[str] = []
    for token, owner in PERISHABLE_TOKENS.items():
        for path in definition_markdown_files(root):
            if path.relative_to(root).as_posix() == owner:
                continue
            if token in read_text(path):
                issues.append(
                    f"{path}: carries perishable platform token {token!r}, whose only allowed home "
                    f"is {owner}. A second copy stays behind when the platform moves and keeps "
                    f"teaching the stale behavior with no runtime error — state the role-local "
                    f"consequence here and point at the owner file for the fact."
                )
    return issues


def render_inventory(agent_names: list[str], skill_names: list[str]) -> str:
    agents = ", ".join(f"`{name}`" for name in agent_names)
    skills = ", ".join(f"`{name}`" for name in skill_names)
    return "\n".join(
        [
            "<!-- fleet-inventory:start -->",
            f"- **Agents ({len(agent_names)}):** {agents}",
            f"- **Skills ({len(skill_names)}):** {skills}",
            "<!-- fleet-inventory:end -->",
        ]
    )


def replace_inventory(content: str, expected: str) -> str:
    if not INVENTORY_RE.search(content):
        raise ValueError("missing fleet inventory markers")
    newline = "\r\n" if "\r\n" in content else "\n"
    return INVENTORY_RE.sub(expected.replace("\n", newline), content, count=1)


def write_inventory(readme: Path, expected: str) -> None:
    if not readme.is_file():
        raise ValueError(f"{readme}: missing README.md")
    content = readme.read_bytes().decode("utf-8")
    try:
        updated = replace_inventory(content, expected)
    except ValueError as exc:
        raise ValueError(f"{readme}: {exc}") from exc
    readme.write_bytes(updated.encode("utf-8"))


def validate_inventory(root: Path, expected: str) -> list[str]:
    readme = root / "README.md"
    if not readme.is_file():
        return [f"{readme}: missing README.md"]
    match = INVENTORY_RE.search(read_text(readme))
    if not match:
        return [f"{readme}: missing fleet inventory markers"]
    if match.group(0) != expected:
        return [
            f"{readme}: fleet inventory drifted; run "
            "`python scripts/validate_fleet.py --write-inventory`"
        ]
    return []


def validate_agent_guide(root: Path) -> list[str]:
    """Drift tripwires for the repo's own agent guide (AGENTS.md plus the CLAUDE.md bridge).

    Self-gating: a repo with no AGENTS.md (the synthetic fixtures under tests/) is not making any
    guide claims, so there is nothing to check and this returns [].
    """
    issues: list[str] = []
    guide = root / "AGENTS.md"
    bridge = root / "CLAUDE.md"

    def has_import(path: Path) -> bool:
        return path.is_file() and any(
            line.strip() == GUIDE_IMPORT for line in read_text(path).splitlines()
        )

    if not guide.is_file():
        if has_import(bridge):
            issues.append(
                f"{bridge}: imports {GUIDE_IMPORT} but AGENTS.md does not exist — the import "
                f"resolves to nothing and the project context silently loads empty."
            )
        return issues

    if not has_import(bridge):
        issues.append(
            f"{guide}: exists but {root / 'CLAUDE.md'} does not carry a line reading "
            f"{GUIDE_IMPORT!r}. Claude Code reads CLAUDE.md, not AGENTS.md (the README's own "
            f"bridge convention), so without the import this guide is never loaded by the tool "
            f"it is written for."
        )

    text = read_text(guide)
    for span in INLINE_CODE_RE.findall(text):
        for token in GUIDE_PATH_TOKEN_RE.findall(span):
            token = token.rstrip(".,;:")
            # Bare filenames and lone directory mentions (`references/`) are prose, not resolvable
            # claims; only a multi-segment path asserts a location worth checking.
            if len([part for part in token.split("/") if part]) < 2:
                continue
            if not (root / token.rstrip("/")).exists():
                issues.append(
                    f"{guide}: names '{token}', which does not exist in this repository. A stale "
                    f"path in the guide fails nowhere at runtime — it just misleads every future "
                    f"session that loads it."
                )

    for alias in sorted(ALIAS_MODELS):
        if f"`{alias}`" not in text:
            issues.append(
                f"{guide}: the model-alias paraphrase omits `{alias}`; ALIAS_MODELS in "
                f"scripts/validate_fleet.py is the source of truth — fix the paraphrase, never "
                f"the source."
            )
    return issues


def load_guard(root: Path):
    """Import scripts/readonly-guard.py by path — the hyphen makes it un-importable by name."""
    source = root / "scripts" / "readonly-guard.py"
    spec = importlib.util.spec_from_file_location("readonly_guard", source)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hook_command(root: Path) -> str | None:
    """The PreToolUse/Bash command string from hooks/hooks.json, following the real key path."""
    path = root / "hooks" / "hooks.json"
    if not path.is_file():
        return None
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    for entry in config.get("hooks", {}).get("PreToolUse", []):
        if entry.get("matcher") == "Bash":
            for hook in entry.get("hooks", []):
                if hook.get("type") == "command" and hook.get("command"):
                    return hook["command"]
    return None


def agent_tool_bases(path: Path) -> set[str]:
    fields = parse_frontmatter(path) or {}
    bases: set[str] = set()
    for entry in split_tools(fields.get("tools", "")):
        match = TOOL_ENTRY_RE.match(entry)
        if match:
            bases.add(match.group(1))
    return bases


def validate_plugin(root: Path, agent_names: list[str], skill_names: list[str]) -> list[str]:
    """Checks that only apply to a repo which SHIPS AS A PLUGIN.

    Returns [] when there is no manifest, so the synthetic fixtures under tests/ — bare agents/ and
    skills/ trees that are not plugins — stay valid.

    Every rule here is a tripwire for a failure that is SILENT at runtime. A plugin-shipped agent
    cannot carry its own `hooks:`, so the read-only guard has exactly one place to live and exactly
    one way to find its subject; get any link in that chain wrong and nothing errors, nothing logs,
    and `code-reviewer` simply runs Bash unguarded against the repository it is reviewing.
    """
    manifest_path = root / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        return []

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [f"{manifest_path}: unreadable plugin manifest: {exc}"]

    issues: list[str] = []
    plugin_name = str(manifest.get("name", "")).strip()
    if not plugin_name:
        issues.append(f"{manifest_path}: manifest is missing the required 'name'")
    if not manifest.get("author"):
        # `claude plugin validate --strict` treats a missing author as an error; say so here rather
        # than letting CI be the first to find out.
        issues.append(
            f"{manifest_path}: missing 'author' — `claude plugin validate --strict` fails without it"
        )

    # Generic validator fixtures deliberately do not carry this fleet's learning contract. Enforce
    # it here, after the plugin manifest proves this is the shipped fleet, and before any guard
    # failure can return early. Search only the first packet section: mentioning the marker in an
    # example, boundary, or rationale must not make a missing closeout slot look configured.
    loop_preloads: set[str] = set()
    for path in sorted((root / "agents").glob("*.md")):
        fields = parse_frontmatter(path) or {}
        preloaded = {
            entry.strip()
            for entry in fields.get("skills", "").split(",")
            if entry.strip()
        }
        if "self-improve-loop" in preloaded:
            loop_preloads.add(path.stem)

        content = read_text(path)
        packet = PACKET_HEADING_RE.search(content)
        if packet is None:
            continue  # validate_agents owns the missing-packet error
        later_heading = re.search(r"^##\s+", content[packet.end():], re.MULTILINE)
        packet_end = (
            packet.end() + later_heading.start()
            if later_heading is not None
            else len(content)
        )
        packet_text = content[packet.start():packet_end]
        is_lifecycle_owner = path.stem in SELF_IMPROVE_LOOP_PRELOAD_AGENTS
        expected_mode = "lifecycle-owner" if is_lifecycle_owner else "intake-only"
        unexpected_mode = "intake-only" if is_lifecycle_owner else "lifecycle-owner"
        expected_slot = (
            LEARNING_LIFECYCLE_OWNER_PACKET_SLOT
            if is_lifecycle_owner
            else LEARNING_INTAKE_PACKET_SLOT
        )
        unexpected_slot = (
            LEARNING_INTAKE_PACKET_SLOT
            if is_lifecycle_owner
            else LEARNING_LIFECYCLE_OWNER_PACKET_SLOT
        )
        if expected_slot not in packet_text:
            variant_detail = (
                f" It contains the canonical {unexpected_mode} variant instead."
                if unexpected_slot in packet_text
                else ""
            )
            issues.append(
                f"{path}: end-of-task packet omits or drifted from the canonical {expected_mode} "
                f"Learning closeout.{variant_detail} Intake-only roles must hand off a proposed "
                "recommendation in "
                "quarantine; lifecycle owners must record an accepted disposition and separate "
                "post-triage state. A discovery can otherwise disappear at handoff; confusing the "
                "variants either grants apparent triage authority or prevents a full retro from "
                "completing."
            )
        elif unexpected_slot in packet_text:
            issues.append(
                f"{path}: end-of-task packet contains both the {expected_mode} and "
                f"{unexpected_mode} Learning closeouts. One role cannot be both an untriaged "
                "intake source and the lifecycle owner for the same result."
            )

    if loop_preloads != SELF_IMPROVE_LOOP_PRELOAD_AGENTS:
        issues.append(
            "agents/: self-improve-loop preload roster drifted: expected "
            f"{sorted(SELF_IMPROVE_LOOP_PRELOAD_AGENTS)}, found {sorted(loop_preloads)}. Only the "
            "three disposition owners receive the full loop; every other agent uses the "
            "lightweight Learning handoff."
        )

    guard_path = root / "scripts" / "readonly-guard.py"
    if not guard_path.is_file():
        return issues + [f"{guard_path}: missing the read-only guard"]
    try:
        guard = load_guard(root)
    except Exception as exc:  # a guard that cannot even import guards nothing
        return issues + [f"{guard_path}: cannot load guard: {exc}"]

    if plugin_name and guard.PLUGIN_NAME != plugin_name:
        issues.append(
            f"{guard_path}: PLUGIN_NAME {guard.PLUGIN_NAME!r} does not match the manifest name "
            f"{plugin_name!r}. The guard recognizes its subject by a NAMESPACED agent_type, so a "
            f"mismatch means it matches nobody and silently guards nothing."
        )

    command = hook_command(root)
    if command is None:
        issues.append(
            f"{root / 'hooks' / 'hooks.json'}: no PreToolUse hook with matcher 'Bash' and a command. "
            f"A plugin-shipped agent cannot carry its own hooks, so this file is the ONLY place the "
            f"read-only guard can be attached — without it, code-reviewer holds Bash unguarded."
        )
    else:
        if "readonly-guard.py" not in command:
            issues.append(
                f"{root / 'hooks' / 'hooks.json'}: the PreToolUse/Bash hook does not run "
                f"scripts/readonly-guard.py"
            )
        if "${CLAUDE_PLUGIN_ROOT}" not in command:
            issues.append(
                f"{root / 'hooks' / 'hooks.json'}: the PreToolUse/Bash hook must run the guard from "
                f"${{CLAUDE_PLUGIN_ROOT}} — the plugin's own installed copy. Resolving it any other "
                f"way risks executing a guard supplied by the repository under review."
            )
        # The hook string carries TWO independent copies of the roster, and each one can disarm the
        # guard on its own:
        #   1. the `case` FAST-PATH, which exits 0 for any payload not naming a guarded agent --
        #      a name missing here means the guard is never even invoked for that agent;
        #   2. the no-interpreter FALLBACK deny patterns, which are what fails closed when no
        #      Python answers -- a name missing there means that agent gets an open Bash exactly
        #      when the guard is broken or absent.
        # Searching the whole command string cannot tell them apart: a name present in only one
        # block satisfies a substring check while the other block silently lets the agent through
        # (caught in review of this very rule). So each block is located and asserted separately.
        blocks = [segment.split("esac", 1)[0] for segment in command.split('case "$IN" in')[1:]]
        if len(blocks) < 2:
            issues.append(
                f"{root / 'hooks' / 'hooks.json'}: expected the PreToolUse/Bash hook to contain two "
                f"`case \"$IN\" in` blocks (the fast-path filter and the no-interpreter fallback), "
                f"found {len(blocks)}. The roster cross-check below cannot verify a hook it does not "
                f"recognize, so this fails rather than passing a hook it did not actually check."
            )
        else:
            for label, block in (("fast-path filter", blocks[0]), ("no-interpreter fallback", blocks[-1])):
                for name in sorted(guard.GUARDED_AGENT_NAMES):
                    if name not in block:
                        issues.append(
                            f"{root / 'hooks' / 'hooks.json'}: the hook's {label} never names "
                            f"{name!r}, but scripts/readonly-guard.py lists it in "
                            f"GUARDED_AGENT_NAMES. The fast-path decides whether the guard runs at "
                            f"all and the fallback is what fails closed when no interpreter "
                            f"answers, so a name missing from EITHER leaves that agent's 'read-only' "
                            f"a promise with no control behind it — silently, because the hook "
                            f"still exits 0."
                        )

    # The guard's subject list and the agent roster must agree, in both directions.
    guarded = set(guard.GUARDED_AGENT_NAMES)
    for name in sorted(guarded - set(agent_names)):
        issues.append(
            f"{guard_path}: GUARDED_AGENT_NAMES lists {name!r}, which is not an agent in agents/"
        )
    for path in sorted((root / "agents").glob("*.md")):
        tools = agent_tool_bases(path)
        if "Bash" in tools and not (tools & WRITE_TOOLS) and path.stem not in guarded:
            issues.append(
                f"{path}: agent {path.stem!r} holds Bash and no write tool — a read-only agent whose "
                f"only route to mutation is the shell — but it is absent from GUARDED_AGENT_NAMES in "
                f"scripts/readonly-guard.py, so the guard ignores it and its 'read-only' is a promise, "
                f"not a control."
            )

    # Cross-references and paths, across every agent and skill definition.
    fleet = set(agent_names) | set(skill_names)
    definitions = [(path, path.stem) for path in sorted((root / "agents").glob("*.md"))]
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        definitions += [
            (directory / "SKILL.md", directory.name)
            for directory in sorted(p for p in skills_dir.iterdir() if p.is_dir())
            if (directory / "SKILL.md").is_file()
        ]

    for path, own in definitions:
        text = read_text(path)
        description = (parse_frontmatter(path) or {}).get("description", "")
        for other in sorted(fleet - {own}):
            if re.search(rf"(?<![\w:-]){re.escape(other)}(?![\w-])", description):
                issues.append(
                    f"{path}: description names {other!r} without the plugin namespace. Every "
                    f"component a plugin ships is namespaced, so the real name is "
                    f"{plugin_name}:{other} — a bare reference points at nothing and degrades "
                    f"the routing this description exists to drive."
                )
        # `~/.claude/agents|skills/` does NOT contain this fleet once it ships as a plugin; its files
        # live under ${CLAUDE_PLUGIN_ROOT}. The `(?!\*)` spares the doc-reference form
        # (`~/.claude/agents/*.md`, which correctly describes where USER-level agents live) and
        # catches only a path being resolved to a specific file — the thing that silently stops
        # resolving, taking `service-onboard` (unreachable any other way) down with it.
        for match in re.finditer(r"~/\.claude/(agents|skills)/(?!\*)", text):
            kind = match.group(1)
            issues.append(
                f"{path}: resolves a fleet file under '~/.claude/{kind}/', which will NOT contain this "
                f"fleet once it ships as a plugin — those files live under ${{CLAUDE_PLUGIN_ROOT}}. "
                f"Use '${{CLAUDE_PLUGIN_ROOT}}/{kind}/...' instead."
            )

    # Every namespaced cross-reference must be one complete, well-formed token that resolves to
    # the right kind of fleet member. The corpus is a densely linked graph (hundreds of
    # `<plugin>:<name>` references) and NOTHING at runtime checks one: a prefix-only matcher can
    # certify `code-reviewer_v2` as `code-reviewer`, while union membership can certify a slash
    # command that names an agent even though slash commands invoke skills. Both failures are
    # silent. The token matcher therefore captures uppercase and invalid punctuation too, so
    # syntax is rejected explicitly instead of being skipped or truncated to a valid prefix.
    if plugin_name:
        ns_ref_re = re.compile(
            rf"(?<![\w/.-])(?P<slash>/)?{re.escape(plugin_name)}:"
            r"(?P<target>[^\s`'\"<>()\[\]{},;!?]*)"
        )
        agents = set(agent_names)
        skills = set(skill_names)
        for path in definition_markdown_files(root):
            references = {
                (bool(match.group("slash")), match.group("target").rstrip(".:"))
                for match in ns_ref_re.finditer(read_text(path))
            }
            for is_slash_command, target in sorted(references):
                reference = f"{'/' if is_slash_command else ''}{plugin_name}:{target}"
                if not NAME_RE.fullmatch(target):
                    issues.append(
                        f"{path}: malformed namespaced reference {reference!r}; the complete target "
                        f"must be a kebab-case fleet name. Prefix matching would silently certify "
                        f"a different live member while this token fails to resolve at runtime."
                    )
                    continue
                if is_slash_command and target not in skills:
                    target_kind = "an agent" if target in agents else "no shipped skill"
                    issues.append(
                        f"{path}: slash-command reference {reference!r} names {target_kind}; a "
                        f"slash-command reference must target a skill, or the invocation cannot "
                        f"resolve at runtime."
                    )
                    continue
                if target not in fleet:
                    issues.append(
                        f"{path}: references {reference}, which is not an agent or "
                        f"skill in this fleet. A dangling cross-reference fails nowhere at "
                        f"runtime — routing and handoffs just quietly stop resolving — so a "
                        f"rename or removal must update every referrer, and this rule is what "
                        f"makes the miss loud."
                    )

    return issues


def validate_platform_adapters(root: Path) -> list[str]:
    """Load the repository's adapter generator and verify every non-Claude install surface.

    Synthetic fixtures do not ship a Claude manifest and skip this rule. A real plugin must carry
    the generator: otherwise generated copies can drift while the canonical fleet remains green.
    """

    if not (root / ".claude-plugin" / "plugin.json").is_file():
        return []

    source = root / "scripts" / "generate_platform_adapters.py"
    if not source.is_file():
        return [
            f"{source}: missing platform adapter generator. The Copilot, VS Code, and Codex "
            f"copies would have no mechanical link to the canonical Claude definitions."
        ]

    module_name = f"platform_adapters_{abs(hash(str(root.resolve())))}"
    spec = importlib.util.spec_from_file_location(module_name, source)
    if spec is None or spec.loader is None:
        return [f"{source}: cannot load platform adapter generator"]
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module.validate_platform_support(root)
    except Exception as exc:
        return [
            f"{source}: platform adapter validation crashed: {exc}. A broken checker must fail "
            f"loudly rather than certifying stale host copies."
        ]


def validate_routing_clusters(root: Path, agent_names: list[str], skill_names: list[str]) -> list[str]:
    """Schema integrity for evals/routing/*.json — the rules that keep the scorer honest.

    Every rule here is a tripwire for a measurement that would silently lie. The scorer grades a
    positive against its own expect_fires but reports the CLUSTER's fire rate, so a positive
    naming a component outside the declared members can pass while the reported rate reads zero
    (observed live in pos-ci-actions-harden, which accepted code-reviewer). Both target lists
    match components BY NAME, so a typo'd member or target expects or forbids nothing and passes
    vacuously. A misspelled polarity used to fall through to the negative branch, and an empty
    explicit forbidden set therefore passed every run. Case ids are also the keys a before/after
    diff aligns on, so a duplicate makes two measurements read as one.
    """
    issues: list[str] = []
    routing = root / "evals" / "routing"
    if not routing.is_dir():
        return issues
    components = set(agent_names) | set(skill_names)
    for path in sorted(routing.glob("*.json")):
        rel = path.relative_to(root).as_posix()
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            issues.append(
                f"{rel}: unreadable cluster file ({exc}) — the runner would fail loudly, but a "
                f"cluster nobody can run measures nothing while still looking like coverage."
            )
            continue
        if not isinstance(doc, dict):
            issues.append(
                f"{rel}: top-level JSON value is not an object — the runner needs named cluster, "
                f"members, and cases fields, so this file cannot describe a measurement."
            )
            continue
        cluster = doc.get("cluster")
        if not isinstance(cluster, str) or not cluster.strip():
            issues.append(
                f"{rel}: missing non-empty 'cluster' string — benchmark artifacts need a stable "
                f"cluster identity or results cannot be aligned."
            )
        members = doc.get("members")
        if not isinstance(members, list) or not members:
            issues.append(
                f"{rel}: no non-empty 'members' list — every routing assertion grades against the "
                f"member set, so without one the file asserts nothing."
            )
            continue
        member_set: set[str] = set()
        for index, member in enumerate(members, start=1):
            if not isinstance(member, str) or not member.strip():
                issues.append(
                    f"{rel}: member #{index} is not a non-empty component name — target matching "
                    f"is string-based, so a malformed member can never fire."
                )
                continue
            member_set.add(member)
            if member not in components:
                issues.append(
                    f"{rel}: member {member!r} is not a fleet component — a name that resolves to "
                    f"nothing can be expected or forbidden and never match, passing vacuously."
                )

        cases = doc.get("cases")
        if not isinstance(cases, list) or not cases:
            issues.append(
                f"{rel}: no non-empty 'cases' list — a cluster without runnable assertions can "
                f"look like coverage while measuring nothing."
            )
            continue
        seen_ids: set[str] = set()
        for index, case in enumerate(cases, start=1):
            if not isinstance(case, dict):
                issues.append(
                    f"{rel}: case #{index} is not an object — the runner cannot read its identity, "
                    f"prompt, polarity, or expectations."
                )
                continue
            case_id = case.get("id")
            if not isinstance(case_id, str) or not case_id.strip():
                issues.append(
                    f"{rel}: case #{index} has no non-empty 'id' — results without a stable key "
                    f"cannot be aligned across benchmark runs."
                )
                case_label = f"#{index}"
            else:
                case_label = repr(case_id)
                if case_id in seen_ids:
                    issues.append(
                        f"{rel}: duplicate case id {case_id!r} — ids are what a before/after diff "
                        f"aligns on, so a duplicate makes two measurements read as one."
                    )
                seen_ids.add(case_id)

            prompt = case.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                issues.append(
                    f"{rel}: case {case_label} has no non-empty 'prompt' — a case with no runnable "
                    f"input cannot produce routing evidence."
                )

            polarity = case.get("polarity")
            if polarity not in ("positive", "negative"):
                issues.append(
                    f"{rel}: case {case_label} polarity must be exactly positive or negative "
                    f"(got {polarity!r}) — any other value used to fall through as a negative and "
                    f"could pass without testing the intended route."
                )
                continue

            if polarity == "positive":
                field = "expect_fires"
            elif "expect_not_fires" in case:
                field = "expect_not_fires"
            else:
                # Omission deliberately means the whole cluster; only an explicitly empty list is
                # invalid because it overrides that useful default with a vacuous prohibition.
                continue

            targets = case.get(field)
            if not isinstance(targets, list) or not targets:
                issues.append(
                    f"{rel}: case {case_label} {field} must be a non-empty list — an empty or "
                    f"wrongly typed target set can make the assertion vacuous."
                )
                continue
            for target in targets:
                if not isinstance(target, str) or not target.strip():
                    issues.append(
                        f"{rel}: case {case_label} {field} contains {target!r}, not a non-empty "
                        f"component name — malformed targets can never match a firing."
                    )
                    continue
                if target not in member_set:
                    if field == "expect_fires":
                        issues.append(
                            f"{rel}: case {case_label} expects {target!r}, outside the cluster's "
                            f"members — the scorer would pass the case on a fire the cluster rate "
                            f"does not count, so the case can pass while the reported rate reads zero."
                        )
                    else:
                        issues.append(
                            f"{rel}: case {case_label} forbids {target!r}, outside the cluster's "
                            f"members — a non-member can never fire as this cluster, so the "
                            f"prohibition matches nothing and the negative passes vacuously."
                        )
    return issues


def validate_behavioral_contracts(
    root: Path, agent_names: list[str], skill_names: list[str]
) -> list[str]:
    """Run the behavioral runner's public exact-schema validator in the ordinary fleet gate."""
    behavior_dir = root / "evals" / "behavioral"
    if not behavior_dir.is_dir():
        return []
    runner = root / "scripts" / "eval_behavioral.py"
    if not runner.is_file():
        return [
            f"{runner}: behavioral case files exist without their schema validator; typoed "
            "assertions could be ignored until an expensive live run."
        ]
    module_name = f"eval_behavioral_validator_{abs(hash(str(root.resolve())))}"
    spec = importlib.util.spec_from_file_location(module_name, runner)
    if spec is None or spec.loader is None:
        return [f"{runner}: cannot load behavioral case schema validator"]
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        return [
            f"{runner}: behavioral case schema validator could not load ({exc}); the fleet "
            "gate refuses to certify definitions it cannot validate."
        ]

    issues: list[str] = []
    components = set(agent_names) | set(skill_names)
    seen_case_ids: dict[str, str] = {}
    paths = sorted(behavior_dir.glob("*.json"))
    if not paths:
        return [
            f"{behavior_dir}: no behavioral case documents; an empty directory looks like "
            "coverage while executing no contract."
        ]
    for path in paths:
        rel = path.relative_to(root).as_posix()
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            issues.append(f"{rel}: unreadable behavioral case document ({exc})")
            continue
        findings = module.validate_case_document(document, components=components)
        issues.extend(
            f"{rel}: {finding}. Behavioral definitions fail before sessions so a typo or "
            "empty oracle cannot produce a false-green benchmark."
            for finding in findings
        )
        if isinstance(document, dict) and isinstance(document.get("cases"), list):
            for case in document["cases"]:
                if not isinstance(case, dict) or not isinstance(case.get("id"), str):
                    continue
                prior = seen_case_ids.get(case["id"])
                if prior is not None:
                    issues.append(
                        f"{rel}: case id {case['id']!r} duplicates {prior}; benchmark arrays align "
                        "by id, so cross-document duplicates make two contracts read as one."
                    )
                else:
                    seen_case_ids[case["id"]] = rel
    return issues


def validate_host_conformance_manifest(root: Path) -> list[str]:
    """Pin required host/static coverage and the operator-selected GPT-5.6 Sol baseline lane."""

    if not (root / ".claude-plugin" / "plugin.json").is_file():
        return []
    path = root / "evals" / "conformance" / "hosts.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [
            f"{path}: host conformance manifest is missing or unreadable ({exc}). Without the "
            f"versioned matrix, unavailable hosts and model lanes can silently disappear from the "
            f"fleet's baseline."
        ]
    lanes = document.get("lanes") if isinstance(document, dict) else None
    if not isinstance(lanes, list):
        return [f"{path}: host conformance manifest has no lanes array"]
    issues: list[str] = []
    static_hosts = {
        lane.get("host")
        for lane in lanes
        if isinstance(lane, dict) and lane.get("kind") == "static"
    }
    missing_hosts = sorted({"claude", "codex", "copilot", "vscode"} - static_hosts)
    if missing_hosts:
        issues.append(
            f"{path}: static conformance lanes are missing hosts {missing_hosts}. A generated host "
            f"surface could drift while the cross-host report still looks complete."
        )
    sol_lanes = [
        lane
        for lane in lanes
        if isinstance(lane, dict) and lane.get("model") == "gpt-5.6-sol"
    ]
    if len(sol_lanes) != 1:
        issues.append(
            f"{path}: expected exactly one explicit gpt-5.6-sol baseline lane, found "
            f"{len(sol_lanes)}. The operator selected Sol as a required, separately reported Codex "
            f"baseline; an alias or omitted lane silently changes what was measured."
        )
    else:
        lane = sol_lanes[0]
        expected = {
            "host": "codex",
            "kind": "model-baseline",
            "reasoning_effort": "high",
            "sandbox": "read-only",
            "required": True,
        }
        drift = {key: (lane.get(key), value) for key, value in expected.items() if lane.get(key) != value}
        if drift:
            issues.append(
                f"{path}: gpt-5.6-sol baseline conditions drifted: {drift}. Model, effort, sandbox, "
                f"and required status are one comparison contract; changing one invalidates the "
                f"baseline rather than tuning it."
            )
    return issues


def validate_runtime_control_wiring(root: Path) -> list[str]:
    """Require every runtime control to exist, stay reachable, and retain typed evidence wiring."""

    # Generic validator fixtures and downstream fleets need not implement this repository-specific
    # control plane. Once any control, canonical consumer, or the README section declares it, the
    # complete contract becomes mandatory so partial deletion cannot silently self-disable checks.
    readme = root / "README.md"
    try:
        readme_declares_controls = (
            readme.is_file()
            and "## Runtime control plane" in readme.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError):
        readme_declares_controls = False
    control_paths = {
        root / "scripts" / "evidence_envelope.py",
        *(root / path for path in RUNTIME_CONTROL_WIRING),
        *(root / path for path in RUNTIME_CONTROL_WIRING.values()),
    }
    if not readme_declares_controls and not any(path.exists() for path in control_paths):
        return []

    issues: list[str] = []
    evidence_path = root / "scripts" / "evidence_envelope.py"
    if not evidence_path.is_file():
        issues.append(
            "scripts/evidence_envelope.py: typed runtime evidence control is missing; state, "
            "sandbox, and approval results would fall back to unauthenticated prose silently"
        )

    for script_relative, consumer_relative in RUNTIME_CONTROL_WIRING.items():
        script = root / script_relative
        consumer = root / consumer_relative
        if not script.is_file():
            issues.append(
                f"{script_relative}: runtime control named by {consumer_relative} is missing; "
                "the prompt would claim an enforcement path that resolves to nothing"
            )
            continue
        if not consumer.is_file():
            issues.append(
                f"{consumer_relative}: runtime-control consumer is missing; {script_relative} "
                "would remain shipped but unreachable from the fleet workflow"
            )
            continue
        reference = f"${{CLAUDE_PLUGIN_ROOT}}/{script_relative}"
        try:
            consumer_text = consumer.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(f"{consumer_relative}: cannot inspect runtime-control wiring: {exc}")
            continue
        if reference not in consumer_text:
            issues.append(
                f"{consumer_relative}: does not name `{reference}`; {script_relative} would "
                "silently stop enforcing the role's runtime boundary"
            )

    for script_relative in sorted(RUNTIME_EVIDENCE_PRODUCERS):
        script = root / script_relative
        if not script.is_file():
            continue
        try:
            source = script.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(f"{script_relative}: cannot inspect typed-evidence wiring: {exc}")
            continue
        if "import evidence_envelope" not in source:
            issues.append(
                f"{script_relative}: no longer imports evidence_envelope; its result would "
                "silently lose the fleet's typed evidence contract"
            )

    if readme.is_file():
        try:
            readme_text = readme.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(f"README.md: cannot inspect runtime-control inventory: {exc}")
        else:
            documented = {"scripts/evidence_envelope.py", *RUNTIME_CONTROL_WIRING}
            missing = sorted(path for path in documented if f"`{path}`" not in readme_text)
            if missing:
                issues.append(
                    "README.md: runtime-control inventory omits "
                    f"{missing}; shipped enforcement would be undiscoverable to operators"
                )
    return issues


def validate_workflow_evidence_enums(root: Path) -> list[str]:
    """Every workflow script that declares an EVIDENCE enum must match the canonical triad."""
    issues: list[str] = []
    workflows_dir = root / "workflows"
    if not workflows_dir.is_dir():
        return issues
    for path in sorted(workflows_dir.glob("*.js")):
        text = read_text(path)
        matches = WORKFLOW_EVIDENCE_ENUM_RE.findall(text)
        if "evidence" in text and not matches:
            issues.append(
                f"{path}: declares an evidence field without a parseable `const EVIDENCE = [...]` "
                f"enum, so the canonical triad cannot be pinned and drift would be invisible "
                f"until a live run fails schema validation."
            )
        for group in matches:
            values = tuple(v.strip().strip("'\"") for v in group.split(",") if v.strip())
            if values != WORKFLOW_EVIDENCE_ENUM:
                issues.append(
                    f"{path}: workflow evidence enum {values!r} does not match the canonical "
                    f"triad {WORKFLOW_EVIDENCE_ENUM!r} from EVIDENCE_LABEL_STEMS; a drifted enum "
                    f"ships a packet contract that fails five retries deep with no load-time error."
                )
    return issues


# Workflows are Claude-only: the other hosts have no workflow runtime, so a generated adapter
# that mentions one teaches an instruction that cannot execute there -- it reads as configured
# and fails silently, the exact failure class the bare-skill-reference rule already catches for
# skills. Match both the invocation form and the directory form. .py is included because the
# generated skills trees ship script/asset .py files too, and a workflow reference buried in one
# would be just as silently unexecutable as one in a .md or .yaml adapter.
GENERATED_ADAPTER_TREES = (
    ".github/agents",
    ".codex/agents",
    ".claude/agents",
    "platforms/copilot/skills",
    "plugins/sde-agents/skills",
)


def validate_workflow_host_boundary(root: Path) -> list[str]:
    """No generated non-Claude adapter may reference a plugin workflow."""
    issues: list[str] = []
    workflow_names = set()
    workflows_dir = root / "workflows"
    if workflows_dir.is_dir():
        workflow_names = {p.stem for p in workflows_dir.glob("*.js")}
    if not workflow_names:
        return issues
    for tree in GENERATED_ADAPTER_TREES:
        base = root / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in {".md", ".json", ".toml", ".yaml", ".yml", ".py"}:
                continue
            text = read_text(path)
            for name in sorted(workflow_names):
                if f"/sde-agents:{name}" in text or f"workflows/{name}" in text:
                    issues.append(
                        f"{path}: generated non-Claude adapter references the Claude-only "
                        f"workflow {name!r}; that host has no workflow runtime, so the "
                        f"instruction reads as available and fails silently at use time."
                    )
    return issues


def validate_learning_ledger(root: Path) -> list[str]:
    """Validate the repository-local candidate store whenever this repo ships one.

    Unit tests prove the writer in isolation, but CI previously never opened the tracked records.
    A malformed candidate could therefore merge while the ordinary fleet gate remained green.
    The lock and temporary-file ignore rules are pinned here because they are transactional state;
    committing either can make future writers fail closed while looking like durable evidence.
    """
    script = root / "scripts" / "learning_ledger.py"
    learning = root / "learning"
    if not script.exists() and not learning.exists():
        return []
    issues: list[str] = []
    if not script.is_file():
        return [
            "learning/: candidate store exists without scripts/learning_ledger.py; CI cannot "
            "validate records that may later be treated as durable learning evidence."
        ]
    if not learning.is_dir():
        return [
            "scripts/learning_ledger.py: ledger writer exists without learning/; the documented "
            "repository-local intake has no canonical store to validate."
        ]

    ignore_path = root / ".gitignore"
    ignore_lines = {
        line.strip()
        for line in read_text(ignore_path).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    } if ignore_path.is_file() else set()
    for required in (
        "learning/candidates/.learning-ledger.lock",
        "learning/candidates/.lc_*.tmp",
    ):
        if required not in ignore_lines:
            issues.append(
                f".gitignore: missing {required!r}; transactional ledger writer state can be "
                "committed by `git add -A` and later block safe mutation."
            )

    module_name = f"learning_ledger_{abs(hash(str(root.resolve())))}"
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        issues.append(f"{script}: cannot load learning-ledger validator")
        return issues
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        module.LearningLedger(root).check()
    except Exception as exc:
        issues.append(
            f"learning/candidates/: ledger validation failed ({exc}). Tracked learning evidence "
            "must fail the ordinary fleet gate rather than drift outside CI."
        )
    return issues


def validate_repo(root: Path, *, check_inventory: bool = True) -> tuple[list[str], list[str], list[str]]:
    agent_issues, agent_names = validate_agents(root)
    skill_issues, skill_names = validate_skills(root)
    issues = agent_issues + skill_issues
    issues.extend(validate_plugin(root, agent_names, skill_names))
    issues.extend(validate_platform_adapters(root))
    issues.extend(validate_agent_guide(root))
    issues.extend(validate_routing_clusters(root, agent_names, skill_names))
    issues.extend(validate_behavioral_contracts(root, agent_names, skill_names))
    issues.extend(validate_host_conformance_manifest(root))
    issues.extend(validate_runtime_control_wiring(root))
    issues.extend(validate_bare_skill_references(root, skill_names))
    issues.extend(validate_perishable_tokens(root))
    issues.extend(validate_workflow_evidence_enums(root))
    issues.extend(validate_workflow_host_boundary(root))
    issues.extend(validate_learning_ledger(root))
    if check_inventory:
        issues.extend(validate_inventory(root, render_inventory(agent_names, skill_names)))
    return issues, agent_names, skill_names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the validator's parent repository)",
    )
    parser.add_argument(
        "--write-inventory",
        action="store_true",
        help="rewrite the generated README inventory before validating",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    issues, agent_names, skill_names = validate_repo(root, check_inventory=False)
    if args.write_inventory and not issues:
        try:
            write_inventory(root / "README.md", render_inventory(agent_names, skill_names))
        except ValueError as exc:
            issues.append(str(exc))

    if not issues:
        issues.extend(validate_inventory(root, render_inventory(agent_names, skill_names)))

    if issues:
        print("Fleet validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print(f"Validated {len(agent_names)} agents and {len(skill_names)} skills; inventory is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
