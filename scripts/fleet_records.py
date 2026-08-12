#!/usr/bin/env python3
"""Typed, read-only records of what the canonical fleet declares.

This module owns the fleet's ONE parser for frontmatter, `tools:` values, and namespaced
cross-references. `validate_fleet.py` re-exports the parsing helpers it used to define here, so a
second implementation cannot drift into existence behind a different consumer -- the failure mode
being that a reference the graph counts and the validator skips (or the reverse) makes two reports
about the same tree disagree with nothing to arbitrate them.

It records; it never judges. Every policy question -- is this tool adopted, is this description too
long, is this reference resolvable -- stays in `validate_fleet.py`. A collector that also enforced
would make the graph a second gate, and this round's plan is explicit that no new gate ships.

The inspected tree is DATA. Nothing under the caller-supplied root is imported or executed, so a
foreign checkout or a frozen baseline is safe to parse.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")
LIST_ITEM_RE = re.compile(r"^\s*-\s+(\S.*?)\s*$")


# --------------------------------------------------------------------------------------
# Parsing primitives (moved verbatim from validate_fleet.py, which re-exports them)
# --------------------------------------------------------------------------------------


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def is_runtime_byproduct(path: Path) -> bool:
    """Return whether a path is Python execution residue, not distributable fleet source."""

    return "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".pyo"}


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


def frontmatter_span(lines: list[str]) -> int | None:
    """Return the closing marker index for a complete frontmatter block."""

    if not lines or lines[0].strip() != "---":
        return None
    return next(
        (index for index in range(1, len(lines)) if lines[index].strip() == "---"),
        None,
    )


def parse_frontmatter_lines(lines: list[str], end: int) -> dict[str, str] | None:
    """Parse the fleet's YAML subset from one already-decoded source snapshot."""

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


def parse_frontmatter(path: Path) -> dict[str, str] | None:
    """Parse the small YAML subset used by the fleet frontmatter."""

    lines = read_text(path).splitlines()
    end = frontmatter_span(lines)
    return None if end is None else parse_frontmatter_lines(lines, end)


def definition_markdown_files(root: Path) -> list[Path]:
    """Every markdown file the fleet ships as behavior: agent bodies, SKILL.md files, and each
    skill's references/ and assets/ — the surface a cross-reference or platform-fact rule must
    cover, because all of it is loaded (or read by path) into real sessions."""
    files = sorted((root / "agents").glob("*.md")) if (root / "agents").is_dir() else []
    if (root / "skills").is_dir():
        files += sorted((root / "skills").rglob("*.md"))
    return files


def namespaced_reference_re(plugin_name: str) -> re.Pattern[str]:
    """The fleet's one namespaced-reference matcher.

    Captures uppercase and invalid punctuation deliberately so malformed syntax is REJECTED by the
    validator rather than skipped or truncated to a valid prefix -- a prefix matcher would certify
    `code-reviewer_v2` as `code-reviewer`, and nothing at runtime checks either.
    """
    return re.compile(
        rf"(?<![\w/.-])(?P<slash>/)?{re.escape(plugin_name)}:"
        r"(?P<target>[^\s`'\"<>()\[\]{},;!?]*)"
    )


# --------------------------------------------------------------------------------------
# Typed records
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Member:
    """One canonical fleet member: an agent or a skill."""

    name: str
    kind: str  # "agent" | "skill"
    path: Path
    fields: dict[str, str]
    body: str

    @property
    def description(self) -> str:
        return self.fields.get("description", "")

    @property
    def declares_tools(self) -> bool:
        """Whether `tools:` is present at all.

        Absence is not least privilege: Claude Code grants an agent with no `tools:` EVERY tool.
        Any consumer reasoning about authority must branch on this before reading `tools`, because
        the two states produce the same empty list and mean opposite things. A docstring saying so
        is not enough -- it was exactly this property's warning that a consumer then ignored.
        """
        return "tools" in self.fields

    @property
    def tools(self) -> list[str]:
        """The DECLARED tool list, empty when `tools:` is absent.

        Read `declares_tools` first: an empty list here means "declared nothing" only when
        `declares_tools` is true, and means "inherits everything" when it is false.
        """
        return split_tools(self.fields.get("tools", ""))

    @property
    def preloaded_skills(self) -> list[str]:
        return [s.strip() for s in self.fields.get("skills", "").split(",") if s.strip()]


@dataclass(frozen=True)
class Reference:
    """One namespaced cross-reference occurrence.

    An OCCURRENCE, not an edge: `source` may name the same target many times across surfaces and
    lines. Collapsing to an edge is the consumer's job, because the stable topology identity
    (source, target) and the surface series count different things on purpose.
    """

    source: str  # owning member; a skill's references/ file is attributed to that skill
    target: str
    path: Path
    line: int  # 1-indexed
    surface: str  # "description" | "body"
    in_core_definition: bool  # agents/*.md or skills/*/SKILL.md, vs a bundled references/ file
    is_slash_command: bool
    raw: str  # exact reference form as written


@dataclass(frozen=True)
class RoutingCase:
    """One routing-eval case. Measurement overlay, never authored topology."""

    cluster: str
    case_id: str
    polarity: str  # "positive" | "negative"
    expect_fires: tuple[str, ...]
    tags: tuple[str, ...]


@dataclass(frozen=True)
class RoutingCluster:
    name: str
    path: Path
    members: tuple[str, ...]
    cases: tuple[RoutingCase, ...]


@dataclass(frozen=True)
class FleetRecords:
    root: Path
    plugin_name: str
    members: tuple[Member, ...] = ()
    references: tuple[Reference, ...] = ()
    clusters: tuple[RoutingCluster, ...] = ()
    # None means UNKNOWN -- the guard could not be read -- and is deliberately distinct from an
    # empty set, which means "read it, nothing is guarded". Collapsing the two would let a report
    # state that no agent is guarded on the strength of a file it failed to open.
    guarded_agents: frozenset[str] | None = None
    unparseable: tuple[Path, ...] = ()  # frontmatter the parser refused; the validator reports it

    @property
    def agents(self) -> tuple[Member, ...]:
        return tuple(m for m in self.members if m.kind == "agent")

    @property
    def skills(self) -> tuple[Member, ...]:
        return tuple(m for m in self.members if m.kind == "skill")

    def by_name(self, name: str) -> Member | None:
        return next((m for m in self.members if m.name == name), None)


# --------------------------------------------------------------------------------------
# Collection
# --------------------------------------------------------------------------------------


def _member_for_path(path: Path, root: Path) -> str:
    """The member a definition file belongs to.

    A skill's references/ and assets/ files are not members; they are that skill's surface, so
    their references are attributed to the owning skill rather than dropped.
    """
    rel = path.relative_to(root)
    if rel.parts[0] == "agents":
        return path.stem
    return rel.parts[1]


def _split_frontmatter(text: str) -> tuple[dict[str, str] | None, str, int]:
    """Return (fields, body, body_start_line). body_start_line is 1-indexed."""
    lines = text.splitlines()
    end = frontmatter_span(lines)
    if end is None:
        return None, text, 1
    return parse_frontmatter_lines(lines, end), "\n".join(lines[end + 1:]), end + 2


def _surface_of_line(index: int, end: int | None, description_lines: set[int]) -> str:
    """Classify one 0-indexed source line as description, other frontmatter, or body."""
    if end is None or index > end:
        return "body"
    if index in description_lines:
        return "description"
    # A namespaced reference in some OTHER frontmatter field is neither routing text nor prose.
    # It gets its own label rather than being folded into either series, because silently counting
    # it as one of them is how a surface metric starts disagreeing with what a reader sees.
    return "frontmatter"


def _description_line_span(lines: list[str], end: int) -> set[int]:
    """0-indexed lines carrying the description value, including YAML continuations."""
    span: set[int] = set()
    capturing = False
    for index in range(1, end):
        line = lines[index]
        match = TOP_LEVEL_KEY_RE.match(line)
        if match:
            capturing = match.group(1) == "description"
            if capturing:
                span.add(index)
            continue
        if capturing and line.strip():
            span.add(index)
    return span


def collect_references(root: Path, plugin_name: str) -> tuple[Reference, ...]:
    """Every namespaced-reference occurrence across the fleet's markdown surface.

    Matching runs over RAW source lines, not over parsed field values. The validator's dangling-
    reference rule reads the same raw text, and a collector that scanned re-joined frontmatter
    instead would silently stop seeing references the validator still rejects -- two views of one
    tree that disagree, which is exactly what this module exists to prevent.

    Line and surface are recorded here because the validator's messages and the graph's witness
    diagnostics both need to point at one exact place; neither can be recovered from a deduped set.
    """
    if not plugin_name:
        return ()
    pattern = namespaced_reference_re(plugin_name)
    core = core_definition_paths(root)
    found: list[Reference] = []

    for path in definition_markdown_files(root):
        lines = read_text(path).splitlines()
        end = frontmatter_span(lines)
        description_lines = _description_line_span(lines, end) if end is not None else set()
        source = _member_for_path(path, root)
        in_core = path in core
        for index, line_text in enumerate(lines):
            for match in pattern.finditer(line_text):
                found.append(
                    Reference(
                        source=source,
                        target=match.group("target").rstrip(".:"),
                        path=path,
                        line=index + 1,
                        surface=_surface_of_line(index, end, description_lines),
                        in_core_definition=in_core,
                        is_slash_command=bool(match.group("slash")),
                        raw=match.group(0),
                    )
                )
    return tuple(found)


def core_definition_paths(root: Path) -> set[Path]:
    """The files a member's own identity is declared in: agents/*.md and skills/*/SKILL.md.

    The stable topology identity is measured over these alone. Reproducing the decision's dated
    140-edge measure at its own snapshot returns 140 under this scope and under no other, so the
    boundary is load-bearing rather than stylistic (see the GRAPH-002 plan's edge-identity record).
    """
    paths = set((root / "agents").glob("*.md")) if (root / "agents").is_dir() else set()
    if (root / "skills").is_dir():
        paths |= set((root / "skills").glob("*/SKILL.md"))
    return paths


def collect_routing_clusters(root: Path) -> tuple[RoutingCluster, ...]:
    """Routing clusters as a measurement overlay.

    Cluster co-membership is NOT behavioral coverage of a relationship: two members sharing a
    cluster only means someone graded them together. Only a case naming a member in `expect_fires`
    asserts anything about it, and the report must keep that distinction visible.
    """
    directory = root / "evals" / "routing"
    if not directory.is_dir():
        return ()
    clusters: list[RoutingCluster] = []
    for path in sorted(directory.glob("*.json")):
        try:
            spec = json.loads(read_text(path))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # A malformed cluster is the validator's finding to report, not this collector's to
            # raise: refusing here would take the whole graph down over one unrelated file.
            continue
        if not isinstance(spec, dict):
            continue
        cases = tuple(
            RoutingCase(
                cluster=str(spec.get("cluster", path.stem)),
                case_id=str(case.get("id", "")),
                polarity=str(case.get("polarity", "")),
                expect_fires=tuple(case.get("expect_fires") or ()),
                tags=tuple(case.get("tags") or ()),
            )
            for case in spec.get("cases", [])
            if isinstance(case, dict)
        )
        clusters.append(
            RoutingCluster(
                name=str(spec.get("cluster", path.stem)),
                path=path,
                members=tuple(spec.get("members") or ()),
                cases=cases,
            )
        )
    return tuple(clusters)


def parse_guarded_agents(root: Path) -> frozenset[str] | None:
    """Read the inspected tree's guard roster WITHOUT importing or executing it.

    The tree under inspection may be a foreign or baseline checkout, so its scripts are data. This
    reads `GUARDED_AGENT_NAMES` out of the module's AST -- `ast.literal_eval` on the set literal
    inside the `frozenset(...)` call -- which cannot run whatever else the file contains.

    Returns None when the roster cannot be established, which the caller must not treat as "no
    agent is guarded". See `_resolve_guard_coverage`.
    """
    source = root / "scripts" / "readonly-guard.py"
    if not source.is_file():
        return None
    try:
        tree = ast.parse(read_text(source))
    except (SyntaxError, UnicodeDecodeError):
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(t, ast.Name) and t.id == "GUARDED_AGENT_NAMES" for t in node.targets
        ):
            continue
        value = node.value
        # `frozenset({...})` is a Call, not a literal, so unwrap the single set argument.
        if isinstance(value, ast.Call) and getattr(value.func, "id", "") == "frozenset":
            value = value.args[0] if value.args else None
        try:
            names = ast.literal_eval(value) if value is not None else None
        except (ValueError, TypeError, SyntaxError):
            return None
        if isinstance(names, (set, frozenset, list, tuple)):
            return frozenset(str(n) for n in names)
    return None


def collect(root: Path, plugin_name: str = ""):
    """Collect every canonical record from one tree. Parses; never judges."""

    members: list[Member] = []
    unparseable: list[Path] = []

    agents_dir = root / "agents"
    if agents_dir.is_dir():
        for path in sorted(agents_dir.glob("*.md")):
            fields, body, _ = _split_frontmatter(read_text(path))
            if fields is None:
                unparseable.append(path)
                continue
            members.append(
                Member(fields.get("name", path.stem), "agent", path, dict(fields), body)
            )

    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for path in sorted(skills_dir.glob("*/SKILL.md")):
            fields, body, _ = _split_frontmatter(read_text(path))
            if fields is None:
                unparseable.append(path)
                continue
            members.append(
                Member(fields.get("name", path.parent.name), "skill", path, dict(fields), body)
            )

    return FleetRecords(
        root=root,
        plugin_name=plugin_name,
        members=tuple(members),
        references=collect_references(root, plugin_name),
        clusters=collect_routing_clusters(root),
        # The roster is read from the tree being reported on, never accepted from the caller. A
        # caller holding THIS repo's roster while pointing root at a foreign or baseline checkout
        # would otherwise attribute one tree's guard coverage to another -- the same class of
        # error as relabeling one host's control as another host's guarantee, one level down.
        guarded_agents=parse_guarded_agents(root),
        unparseable=tuple(unparseable),
    )


# --------------------------------------------------------------------------------------
# Topology views
# --------------------------------------------------------------------------------------


def stable_edges(records: FleetRecords) -> set[tuple[str, str]]:
    """The dated, comparable topology measure: distinct (source, target) pairs over core
    definition files, self-loops included, surface and slash form collapsed.

    Verified against the decision's own snapshot `c02d8e12`, where it returns exactly 140.
    """
    names = {m.name for m in records.members}
    return {
        (r.source, r.target)
        for r in records.references
        if r.in_core_definition and r.target in names
    }


def surface_occurrences(records: FleetRecords) -> dict[str, int]:
    """A SEPARATE series from `stable_edges`, counting occurrences split by surface.

    Never differenced against the 140-edge measure: a new surface dimension is useful metadata and
    is not topology drift. Keeping the two functions apart is what makes that misuse take a
    deliberate edit rather than a careless one.
    """
    names = {m.name for m in records.members}
    counts = {"description": 0, "body": 0}
    for r in records.references:
        if r.target in names:
            counts[r.surface] = counts.get(r.surface, 0) + 1
    return counts


def preload_edges(records: FleetRecords) -> set[tuple[str, str]]:
    """Frontmatter `skills:` preloads, as (agent, skill) pairs.

    A DISTINCT series from `stable_edges`, and a stronger relationship than a reference: a preload
    puts the skill in the agent's context, while a reference only names it. A concentration measure
    built on references alone reports 8 inbound for `self-improve-loop` when all 11 agents reach
    it -- ranking the weaker relationship above the stronger one.
    """
    return {
        (m.name, skill)
        for m in records.members
        if m.kind == "agent"
        for skill in m.preloaded_skills
    }
