# Bash — the failure modes that continue silently

Read before writing a shell script. The universal rules live in `skills/code-craft/SKILL.md`. On any
conflict, SKILL.md wins; the repository's own conventions outrank both.

Shell is the language where the default behavior on error is *keep going with wrong state*. Every
rule below exists because of that.

## The header, and what it does not cover

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
```

`-e` exit on error · `-u` unset variable is an error · `-o pipefail` a pipeline fails if any stage
does. Necessary and **not sufficient** — `set -e` has documented holes, and these are the ones that
bite:

- **`-e` is ignored in a condition context.** In `if cmd; then`, `cmd && other`, `cmd || fallback`,
  or a `while` test, a failure is data, not an exit. That is usually what you want — but it means a
  function called from an `if` runs to completion with `-e` disabled *inside it too*.
- **`((i++))` exits your script.** Arithmetic returns exit status 1 when the result is zero, so
  `((i++))` when `i` is 0 is a "failure" under `-e`. Use `i=$((i+1))`, or `((i++)) || true`.
- **A failing command in a pipeline you `|| true`'d** masks everything, not just the part you meant.
- **`local x=$(cmd)`** takes `local`'s exit status, not `cmd`'s — the failure vanishes. Declare, then
  assign: `local x; x=$(cmd)`.
- **Command substitution in a string** (`echo "$(cmd)"`) does not trip `-e` on `cmd`'s failure.
- **`-u` and arrays**: an empty array under `${arr[@]}` is unbound in older bash; write
  `${arr[@]+"${arr[@]}"}` for portability.
- **A trap on ERR does not inherit into functions** without `set -o errtrace`.

The honest conclusion: check the exit statuses that matter explicitly, rather than trusting `-e` to
notice. `set -e` is a backstop, not a policy.

## Quoting and the destructive commands

- **Quote every expansion**: `"$var"`, `"$@"` (never `$*`), `"${arr[@]}"`. An unquoted variable
  containing a space becomes two arguments; containing a `*` it becomes the directory listing.
- **`rm -rf "${dir:?}"/`** — the `:?` makes an empty or unset `dir` abort with an error instead of
  expanding to `rm -rf /`. Any `rm -rf` with a variable in it gets `:?`, without exception. Same for
  `mv`, `chown -R`, `find -delete`, and `truncate`.
- Prefer `--` before user-controlled arguments (`rm -- "$file"`) so a filename starting with `-`
  isn't parsed as a flag.
- **`[[ ]]` over `[ ]`** in bash: no word-splitting surprises, `=~` for regex, `&&`/`||` inside.
- `mktemp -d` for scratch space, removed by a trap: `trap 'rm -rf "${tmp:?}"' EXIT` — set the trap
  immediately after creating it, not at the end of the script you might exit early from.
- **`cd` can fail.** `cd "$dir" || exit 1`, or the rest of the script runs somewhere else entirely —
  and the next `rm -rf ./build` deletes a different build.

## Structure

- A script over ~100 lines with data structures and error handling wants to be Python. That is a
  finding about the choice of language, not a challenge to write cleverer shell.
- Functions with `local` variables; `main "$@"` at the bottom so the file is readable top-down.
- Idempotent where possible — a script that is safe to re-run after a partial failure is worth more
  than one that is fast.
- **Dry-run means the effect is gated, not a second code path** — same rule as
  [`python.md`](python.md): compute the plan always, guard only the mutation, and print what would
  happen.
- `shellcheck` is not optional; it finds most of the above mechanically. Fix or annotate every
  finding with a reason.

## Verify

Run it with `bash -n` (syntax), `shellcheck` (clean), and then for real on a scratch copy — including
the failure path: make a command fail deliberately and confirm the script stops rather than
continuing. A shell script whose error path was never exercised is the definition of unverified.
