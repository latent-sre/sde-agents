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
    "WebFetch", "WebSearch", "Write",
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
PACKET_HEADING_RE = re.compile(
    r"^##\s.*\bpacket\b|^##\s+Output format\b", re.IGNORECASE | re.MULTILINE
)
# Perishable platform facts get exactly ONE home inside agents/ and skills/, so when the platform
# moves, the correction lands once instead of chasing prose copies. Keys are literal substrings
# searched in every definition markdown file; values are the only file (repo-relative POSIX path)
# allowed to carry them. "22345" is the upstream disable-model-invocation-ignored-for-plugin-skills
# bug: its number had already been copied into an agent body once, and a stale copy keeps teaching
# the old platform behavior with no runtime error after the issue closes — the drift is silent,
# which is why a validator rule and not a convention holds the line.
PERISHABLE_TOKENS = {
    "22345": "skills/prompt-craft/references/claude-code-frontmatter.md",
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
        if not tools:
            # Not a harmless omission: an absent `tools:` INHERITS EVERY TOOL rather than granting
            # none, so a reviewer meant to be read-only would silently receive Write and Edit.
            issues.append(f"{path}: missing explicit tools authority (omitting it inherits ALL tools)")
        else:
            parsed_tools = split_tools(tools)
            if len(parsed_tools) != len(set(parsed_tools)):
                issues.append(f"{path}: duplicate tool in tools authority")
            for tool in parsed_tools:
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
                    f"runtime. Preload it, or use the namespaced form with a resolvable "
                    f"${{CLAUDE_PLUGIN_ROOT}} path."
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

    # Every namespaced cross-reference must resolve to a live fleet member. The corpus is a
    # densely linked graph (hundreds of `<plugin>:<name>` references) and NOTHING at runtime
    # checks one: a renamed or deleted member leaves dangling pointers that pass every gate while
    # routing and handoffs quietly degrade — the reference is prose, so it fails nowhere. This is
    # the mirror of the bare-name rule above: that one demands the namespace, this one demands the
    # namespace point at something.
    if plugin_name:
        ns_ref_re = re.compile(rf"(?<![\w-]){re.escape(plugin_name)}:([a-z0-9][a-z0-9-]*)")
        for path in definition_markdown_files(root):
            for target in sorted({m.group(1) for m in ns_ref_re.finditer(read_text(path))}):
                if target not in fleet:
                    issues.append(
                        f"{path}: references {plugin_name}:{target}, which is not an agent or "
                        f"skill in this fleet. A dangling cross-reference fails nowhere at "
                        f"runtime — routing and handoffs just quietly stop resolving — so a "
                        f"rename or removal must update every referrer, and this rule is what "
                        f"makes the miss loud."
                    )

    return issues


def validate_routing_clusters(root: Path, agent_names: list[str], skill_names: list[str]) -> list[str]:
    """Schema integrity for evals/routing/*.json — the rules that keep the scorer honest.

    Every rule here is a tripwire for a measurement that would silently lie. The scorer grades a
    positive against its own expect_fires but reports the CLUSTER's fire rate, so a positive
    naming a component outside the declared members can pass while the reported rate reads zero
    (observed live in pos-ci-actions-harden, which accepted code-reviewer). Both target lists
    match components BY NAME, so a typo'd member or target expects or forbids nothing and passes
    vacuously. And case ids are the keys a before/after diff aligns on, so a duplicate makes two
    measurements read as one. The runner raises no error for any of these at grade time.
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
        members = doc.get("members") if isinstance(doc, dict) else None
        if not isinstance(members, list) or not members:
            issues.append(
                f"{rel}: no non-empty 'members' list — every routing assertion grades against the "
                f"member set, so without one the file asserts nothing."
            )
            continue
        for member in members:
            if member not in components:
                issues.append(
                    f"{rel}: member {member!r} is not a fleet component — a name that resolves to "
                    f"nothing can be expected or forbidden and never match, passing vacuously."
                )
        member_set = set(members)
        seen_ids: set[str] = set()
        for case in doc.get("cases", []) if isinstance(doc.get("cases"), list) else []:
            if not isinstance(case, dict):
                continue
            case_id = case.get("id", "<missing id>")
            if case_id in seen_ids:
                issues.append(
                    f"{rel}: duplicate case id {case_id!r} — ids are what a before/after diff "
                    f"aligns on, so a duplicate makes two measurements read as one."
                )
            seen_ids.add(case_id)
            for target in case.get("expect_fires", []):
                if target not in member_set:
                    issues.append(
                        f"{rel}: case {case_id!r} expects {target!r}, outside the cluster's members "
                        f"— the scorer would pass the case on a fire the cluster rate does not "
                        f"count, so the case can pass while the reported rate reads zero."
                    )
            for target in case.get("expect_not_fires", []):
                if target not in member_set:
                    issues.append(
                        f"{rel}: case {case_id!r} forbids {target!r}, outside the cluster's members "
                        f"— a non-member can never fire as this cluster, so the prohibition matches "
                        f"nothing and the negative passes vacuously."
                    )
    return issues


def validate_repo(root: Path, *, check_inventory: bool = True) -> tuple[list[str], list[str], list[str]]:
    agent_issues, agent_names = validate_agents(root)
    skill_issues, skill_names = validate_skills(root)
    issues = agent_issues + skill_issues
    issues.extend(validate_plugin(root, agent_names, skill_names))
    issues.extend(validate_agent_guide(root))
    issues.extend(validate_routing_clusters(root, agent_names, skill_names))
    issues.extend(validate_bare_skill_references(root, skill_names))
    issues.extend(validate_perishable_tokens(root))
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
