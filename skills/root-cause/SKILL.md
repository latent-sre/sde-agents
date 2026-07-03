---
name: root-cause
description: Use when debugging any bug, test failure, or unexpected behavior — before proposing a fix — and especially after a fix attempt has already failed, or when guessing has started ("maybe it's X, let me try changing it").
argument-hint: [the bug or unexpected behavior]
---

Announce at start: "Using root-cause: reproduce → evidence → hypothesis → verify → fix."

Core rule: **find the root cause before attempting any fix.** A fix without a diagnosis is a guess, and guesses compound — each one changes the system you're debugging.

## The loop

1. **Reproduce it.** A bug you can't trigger on demand isn't understood. Capture the exact command and the exact output. If it's intermittent, find what makes it more likely before proceeding.
2. **Read the actual evidence.** The full error (not the summary line), the logs around the failure, and what changed recently — code (`git log -p`), config, dependencies, environment. Most bugs are new; most new bugs come from the last change.
3. **Form ranked hypotheses.** Two or three, most likely first — each paired with the observation that would confirm or kill it. A hypothesis you can't test against evidence is a hunch, not a hypothesis.
4. **Test the cheapest one first.** One instrumented check or experiment per hypothesis — add a log line, run the narrower test, inspect the actual state. Change no behavior yet.
5. **Fix the cause and prove it.** Where the codebase supports it: write the failing test that reproduces the bug, make it pass, then re-run the original reproduction from step 1.

## The three-strikes rule

Three failed fix attempts means the diagnosis is wrong — not that a fourth patch is needed. Stop. Re-read the evidence from scratch, and question the layer: the bug may live in the architecture, the environment, or your mental model of the system, not in the line you keep editing.

## Red flags — stop and restart the loop

- "Let me just try changing X and see"
- "It's probably X" — without an observation that distinguishes X from the alternatives
- Fixing a symptom in a different place each attempt
- Wanting to delete and rewrite a component because the bug is annoying rather than understood
