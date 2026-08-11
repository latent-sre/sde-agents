---
name: craft
description: "Use when applying the conventions: the quote below never closes
argument-hint: [the file to change]
---

# Craft

The description above opens a double quote and runs to end of line without closing it. This
repository's own frontmatter parser stops at the newline and reads a truncated but plausible
value, so every downstream check — including the generated host copies, which re-serialize what
that parser returned — passes. A conforming YAML parser keeps hunting the closing quote past the
newline and refuses the file, so the skill is silently absent on any host that loads frontmatter
strictly. That divergence is the only rule this fixture violates.
