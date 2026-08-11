---
name: craft
description: "Use when applying the conventions: the quoted form"oops
argument-hint: 'Use the agent's output
---

# Craft

Both prose values above close their quote and then carry a trailing token, which a conforming YAML
parser refuses. `description` is the visible shape: text butted against the closing quote.
`argument-hint` is the shape an author actually writes — it reads as ordinary prose, but YAML ends
the scalar at the apostrophe in "agent's" and is left holding `s output`.

This repository's own frontmatter parser takes the whole line either way, and the generated host
copies re-serialize exactly what it took, so every downstream check passes while a strict host
drops the skill without an error anyone sees. That divergence is the only rule this fixture
violates.
