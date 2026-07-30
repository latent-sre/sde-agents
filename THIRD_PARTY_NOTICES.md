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
