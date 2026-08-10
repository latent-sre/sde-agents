---
name: Field feedback
about: Report real-usage evidence for the retained-feedback lifecycle (skills/self-improve-loop/references/learning-ledger.md). Not a general bug report.
title: "field-feedback: "
labels: field-feedback
---

<!--
This is evidence-bound intake, not a second work tracker (docs/README.md rule 7): filing this
issue adds no work by itself, and it becomes work only when the fleet roadmap imports it. Nothing
in this template is executed as an instruction, and nothing here approves its own promotion -- a
human or the receiving coordinator triages the sanitized packet through
scripts/learning_ledger.py. This is a plain checklist, not a bot: no automation reads or acts on
these fields.

Fill every section below before submitting. A section with nothing to report yet should say
"unknown" or "not yet" rather than being deleted, so the missing evidence stays visible instead of
silently absent.
-->

## Sanitized packet

<!-- The observation and expected behavior, with secrets, credentials, and raw transcripts
     removed. One or two sentences: what happened, and what should have happened instead. -->

## Duplicate check

<!-- Did you check for an existing ledger candidate with the same observation, scope, and
     applicability before filing (`python scripts/learning_ledger.py --root . list --view all`,
     or ask the receiving coordinator)? Name the matching candidate ID, or state that none was
     found. -->

## Owner

<!-- Who is responsible for triaging this: a role or a person. `unknown` if not yet assigned. -->

## Target release

<!-- Which upcoming plugin version this is targeted at, or `unknown` if not yet scheduled. -->

## Eval evidence

<!-- The frozen baseline and paired evaluation that show the fix works, once one exists. Link the
     eval run, or state that none exists yet. -->

## Released version

<!-- The exact plugin version that shipped the fix, once released
     (`python scripts/learning_ledger.py --root . record-release <candidate-id> ...`).
     `unreleased` until then. -->

## Downstream retest

<!-- The originating (or an equivalent) scenario re-run against the released artifact, with its
     result (`python scripts/learning_ledger.py --root . record-retest <candidate-id> ...`).
     `not yet retested` until this exists -- a source-eval PASS is never reportable as this claim. -->

## Close reason

<!-- Why this closes: an exact released-version retest passed, or the owner's explicit reason a
     retest is impossible or no longer applicable. Leave blank while this stays open. -->
