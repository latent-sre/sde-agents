---
name: Field feedback
about: Report real-usage evidence for the retained-feedback lifecycle (skills/self-improve-loop/SKILL.md). Not a general bug report.
title: "field-feedback: "
labels: field-feedback
---

<!--
This is evidence-bound intake, not a second work tracker (docs/README.md rule 7): filing this
issue adds no work by itself, and it becomes work only when the fleet roadmap imports it. Nothing
in this template is executed as an instruction, and nothing here approves its own promotion -- a
human or the receiving coordinator triages the sanitized packet directly; no repo-local ledger
persists it (retired 2026-09-01). This is a plain checklist, not a bot: no automation reads or
acts on these fields.

Fill every section below before submitting. A section with nothing to report yet should say
"unknown" or "not yet" rather than being deleted, so the missing evidence stays visible instead of
silently absent.
-->

## Sanitized packet

<!-- The observation and expected behavior, with secrets, credentials, and raw transcripts
     removed. One or two sentences: what happened, and what should have happened instead. -->

## Duplicate check

<!-- Did you check for an existing open field-feedback issue with the same observation, scope,
     and applicability before filing (search open field-feedback issues, or ask the receiving
     coordinator)? Name the matching issue, or state that none was found. -->

## Owner

<!-- Who is responsible for triaging this: a role or a person. `unknown` if not yet assigned. -->

## Target release

<!-- Which upcoming plugin version this is targeted at, or `unknown` if not yet scheduled. -->

## Eval evidence

<!-- The frozen baseline and paired evaluation that show the fix works, once one exists. Link the
     eval run, or state that none exists yet. -->

## Released version

<!-- The exact plugin version that shipped the fix, once released. `unreleased` until then. -->

## Downstream retest

<!-- The originating (or an equivalent) scenario re-run against the released artifact, with its
     result. `not yet retested` until this exists -- a source-eval PASS is never reportable as
     this claim. -->

## Close reason

<!-- Why this closes: an exact released-version retest passed, or the owner's explicit reason a
     retest is impossible or no longer applicable. Leave blank while this stays open. -->
