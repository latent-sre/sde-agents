# Third-party notices

This repository contains selectively adapted design material from
[`latent-sre/sre-agents`](https://github.com/latent-sre/sre-agents), reviewed at commit
`1cfe7cbd08d54fa8c9dac0f5ca1a10587d5575e3`.

Copyright 2026 SRE + SDE Agent Fleet contributors.

The upstream material is licensed under the MIT License:

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial
portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Adapted material is identified in the files that use it; no upstream agent, skill, hook, or script
was copied wholesale.

---

This repository also contains debugging discipline adapted from the `systematic-debugging` skill
of [`obra/superpowers`](https://github.com/obra/superpowers), reviewed at tag `v6.2.0`, which is
commit `3dcbd5c4b48e02263fbf4a3c01e3fe4f81d584d9`.

Copyright (c) 2025 Jesse Vincent. Licensed under the MIT License (text as above).

The adapted material is four techniques re-expressed as new sentences in
`skills/root-cause/SKILL.md` (bisection, boundary instrumentation, backward tracing to the
origin, defense-in-depth after the fix); the adjudication is recorded in
`docs/archive/2026-07/systematic-debugging-import-notes.md`. No upstream file was copied.

---

The 2026-07-30 external-donor graft round adapted techniques — always re-expressed as new
sentences, never copied files — from the following sources. The adjudication is recorded in
`docs/archive/2026-07/external-donor-import-notes.md`.

- [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills), reviewed at commit
  `7c180d9044c9ae2b442b567aad4e42a28dd5ed62`. React performance and composition rules distilled
  into `skills/code-craft/references/typescript.md`. The repository carries no LICENSE file; the
  source skills (`react-best-practices`, `composition-patterns`) each declare `license: MIT` in
  their own SKILL.md frontmatter (author: vercel), which is the grant relied on here.
- [`stareezy-1/frontend-architecture-skill`](https://github.com/stareezy-1/frontend-architecture-skill),
  reviewed at commit `d7f0c53dcd0c2c43f455bd5ce88aa6797c585fe0`. MIT. Optimistic write-path
  discipline distilled into `skills/code-craft/references/typescript.md`. (Reached via a credited
  copy in `sickn33/agentic-awesome-skills`; this upstream is the origin.)
- [`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills), reviewed at commit
  `7829ffd90d973b6325f5f12f1b1226dcace74443`. MIT, Copyright Addy Osmani. TypeScript domain-typing
  patterns into `skills/code-craft/references/typescript.md`; AI-aesthetic component tells into
  `skills/frontend-craft/SKILL.md`.
- [`alirezarezvani/claude-skills`](https://github.com/alirezarezvani/claude-skills), reviewed at
  commit `aa8d778811a557a2c28ccadda4cf3d0bd028a4cc`. MIT, Copyright Alireza Rezvani. Endpoint
  failure-matrix testing into `skills/backend-craft/SKILL.md`; spec-diff CI gating into
  `skills/backend-craft/references/api-design.md`; the fork kill-criterion into
  `agents/sde-fullstack.md`.
- [`alleneubank/claude-code`](https://github.com/alleneubank/claude-code), reviewed at commit
  `2921eb8a685a2589c4c3e6ecbc8eaa12ffadde73`. Apache License 2.0, Copyright 2025 Allen Eubank.
  Python domain-typing idioms (NewType, Literal unions, Protocol) into
  `skills/code-craft/references/python.md`.
- [`Neeeophytee/finding-unknowns-skills`](https://github.com/Neeeophytee/finding-unknowns-skills),
  reviewed at commit `84404a24a12545dd250cbe90b593c472d4ef7832`. MIT (Copyright 2026 Neeeophytee),
  with an attribution clause crediting Thariq Shihipar for the underlying technique.
  Progressive-disclosure splitting heuristics into `skills/prompt-craft/references/context.md`.
- [`trailofbits/skills`](https://github.com/trailofbits/skills), reviewed at commit
  `ca08fc8a91f64d80b00d48597907c579d0a85c6f`. Creative Commons Attribution-ShareAlike 4.0
  International. **Concepts only, no expression copied or adapted**: the PEP 735
  dependency-groups rule restated from the PEP itself in
  `skills/code-craft/references/python.md`, and the dependency-cooldown rationale restated in the
  fleet's own words in `skills/ci-actions/SKILL.md`. Attribution given here; no CC BY-SA-licensed
  text appears in this repository.

Claude 5-era authoring guidance adapted into `skills/prompt-craft/SKILL.md`,
`skills/prompt-craft/references/context.md`, and `skills/self-improve-loop/SKILL.md` derives from
Anthropic's own published posts (claude.com/blog, 2026) and platform documentation
(code.claude.com/docs), cited in the adjudication notes and commit messages.
