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
BUNDLE_REF_RE = re.compile(
    r"(?<![\w./])(?:references|assets|scripts)/[A-Za-z0-9._/-]*[A-Za-z0-9_-]"
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
        match = TOP_LEVEL_KEY_RE.match(lines[i])
        if not match:
            i += 1
            continue

        key, value = match.groups()
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
            items: list[str] = []
            j = i + 1
            while j < end:
                item_match = LIST_ITEM_RE.match(lines[j])
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
                        f"{path}: scoped grant {tool!r} uses permission-rule syntax, which is not "
                        f"documented for the frontmatter 'tools:' field; express narrowing in "
                        f"permission rules or the guard hook instead"
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


def validate_bundle_references(root: Path, skill_dir: Path, skill_file: Path) -> list[str]:
    issues: list[str] = []
    for match in BUNDLE_REF_RE.finditer(read_text(skill_file)):
        reference = match.group(0).rstrip(".,;:)]}")
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
    linked = {
        match.group(0).rstrip(".,;:)]}")
        for match in BUNDLE_REF_RE.finditer(read_text(skill_file))
    }
    for ref_file in sorted(references_dir.rglob("*")):
        if not ref_file.is_file():
            continue
        rel = ref_file.relative_to(skill_dir).as_posix()
        if rel not in linked:
            issues.append(
                f"{ref_file}: orphaned -- no link to {rel!r} in {skill_file}; a reference file with "
                f"no routing-table row is unreachable by any means"
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
        for line in text.splitlines():
            if not line.startswith("description:"):
                continue
            for other in sorted(fleet - {own}):
                if re.search(rf"(?<![\w:-]){re.escape(other)}(?![\w-])", line):
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

    return issues


def validate_repo(root: Path, *, check_inventory: bool = True) -> tuple[list[str], list[str], list[str]]:
    agent_issues, agent_names = validate_agents(root)
    skill_issues, skill_names = validate_skills(root)
    issues = agent_issues + skill_issues
    issues.extend(validate_plugin(root, agent_names, skill_names))
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
