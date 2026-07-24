<!--
Title: one imperative sentence that stands alone in a log — "Close two exec holes in the
read-only guard", not "guard fixes". Someone skimming history a year from now should not have to
open the PR to know what it did.

Every section below exists because something went wrong without it. Delete a section that
genuinely does not apply and say so in one line; do not leave a heading with nothing under it.
-->

## Summary

<!-- Two or three sentences: the problem, and what this does about it. Lead with consequence, not
     inventory — "the guard allowed a flag that executes arbitrary code" beats "updated guard". -->

## What changed, and why

<!-- One entry per meaningful change. State the claim AND its consequence: not "removed `ag`", but
     "removed `ag` — its exec-flag surface can't be enumerated without the binary, and rg/grep
     already cover it". A reviewer should be able to disagree with a decision, which requires
     knowing what it was. -->

## Verification

<!-- Show evidence, don't assert it. Paste the command and the result. Label load-bearing claims
     [verified] (you ran it), [sourced] (cited), or [unverified] (couldn't check) — the same rule
     the fleet's own agents follow, and `scripts/packet_lint.py` flags an unevidenced "tests pass".
     Every box below is checkable in well under a minute; if a box needs a paragraph, it belongs
     above instead. -->

- [ ] `python3 scripts/validate_fleet.py` — clean
- [ ] `python3 -m unittest discover -s tests` — all passing (count: )
- [ ] `claude plugin validate . --strict` — passing

**Conditional gates — fill only the rows this PR trips, and delete the rest:**

| If this PR touched… | It must show |
|---|---|
| a `description:` on any agent or skill | the overlapping routing cluster run **before and after**, with the rate diff (a near-miss that starts firing is a defect at any rate) |
| `scripts/readonly-guard.py` or `hooks/hooks.json` | `python3 scripts/probe_plugin.py` re-run — the guard's contract rests on an undocumented payload field, so only the probe proves it still fires |
| a validator rule | a fixture or mutation test that **fails without the change** (state that you checked it fails) |
| an added, renamed, or removed component | `--write-inventory` re-run, and a routing cluster seeded or extended |
| text another file declares itself the owner of | which side you fixed — the paraphrase, never the source |
| anything users install | whether `.claude-plugin/plugin.json` needs a version bump |
| an import from another repo | provenance (`adapted from <repo>`, license) in the commit message |

## Risk

<!-- What breaks if this is wrong, how far it spreads, and how you would find out. Then: how to
     revert, and what a revert would NOT undo. One-way doors get named here, not discovered later. -->

## Deliberately not done

<!-- Shortcomings, deferrals, and rejected alternatives, each with its reason. This section is not
     an apology — an unexplained gap reads as an oversight, an explained one reads as judgment, and
     "I chose not to, because" is the most useful sentence in a review. If a reviewer's suggestion
     lost to a measurement, that belongs here. -->

<!--
Reading order (large PRs only): review effectiveness falls off sharply past a few hundred changed
lines and about an hour of attention. If this PR is bigger than that and could not be split, say
where to start and what can be skimmed — a reviewer rationing attention on the wrong files is the
same as no review.
-->
