#!/usr/bin/env python3
"""Validate this repository's canonical agent and skill definitions.

The validator intentionally uses only the Python standard library. It checks
the local ``agents/`` and ``skills/`` layout instead of assuming a particular
runtime's generated directories.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BUNDLE_REF_RE = re.compile(
    r"(?<![\w./])(?:references|assets|scripts)/[A-Za-z0-9._/-]*[A-Za-z0-9_-]"
)
TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")
INVENTORY_RE = re.compile(
    r"<!-- fleet-inventory:start -->.*?<!-- fleet-inventory:end -->",
    re.DOTALL,
)
ALLOWED_MODELS = {"inherit", "haiku", "sonnet", "opus"}
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

        name = fields.get("name", "")
        names.append(name or path.stem)
        issues.extend(validate_name(name, "agent", path))
        if name and name != path.stem:
            issues.append(f"{path}: agent name {name!r} must match filename {path.stem!r}")
        issues.extend(validate_description(fields, "agent", path))

        tools = fields.get("tools", "").strip()
        if not tools:
            issues.append(f"{path}: missing explicit tools authority")
        else:
            parsed_tools = [tool.strip(" []'\"") for tool in tools.split(",") if tool.strip()]
            if len(parsed_tools) != len(set(parsed_tools)):
                issues.append(f"{path}: duplicate tool in tools authority")

        model = fields.get("model", "").strip()
        if not model:
            issues.append(f"{path}: missing model")
        elif model not in ALLOWED_MODELS:
            issues.append(f"{path}: unsupported model {model!r}")

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


def validate_repo(root: Path, *, check_inventory: bool = True) -> tuple[list[str], list[str], list[str]]:
    agent_issues, agent_names = validate_agents(root)
    skill_issues, skill_names = validate_skills(root)
    issues = agent_issues + skill_issues
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
