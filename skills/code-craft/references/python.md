# Python — idioms and the traps that pass review

Read before writing Python. The universal rules live in `skills/code-craft/SKILL.md`. On any conflict,
SKILL.md wins; the repository's own conventions outrank both.

## The traps that produce wrong behavior, not errors

- **Mutable default arguments** are created once, at definition:
  `def add(item, into=[])` shares that list across every call. Use `None` and build inside.
- **Late-binding closures.** `[lambda: i for i in range(3)]` gives three functions all returning 2.
  Bind explicitly: `lambda i=i: i`.
- **`except:` and `except Exception:` too wide** — they swallow `KeyboardInterrupt`/`SystemExit` (bare)
  and, worse, the bug you haven't found yet. Catch the exception you can handle; re-raise the rest.
  `except Exception: pass` is the single most expensive line in Python.
- **A bare `raise` loses the cause if you re-wrap.** `raise MyError(...) from exc` keeps the chain;
  without `from`, the traceback that would have told you why is gone.
- **Truthiness on the wrong things.** `if not x` is True for `0`, `""`, `[]`, and `None` alike — use
  `if x is None` when None is what you mean. This is how an intentional `0` becomes a default.
- **Modifying a collection while iterating it** — iterate over a copy (`list(d)`) or build a new one.
- **Floating point for money.** `Decimal`, or integer minor units.
- **`is` for value comparison** works for small ints and interned strings by accident, then fails in
  production. `is` is for `None`, `True`, `False`, and identity.
- **Shadowing the stdlib** — a local `types.py`, `queue.py`, or `logging.py` breaks imports in ways
  the error message won't explain.

## Idioms that earn their place

- **`pathlib` over string paths**; `Path.read_text()`/`write_text()` over open-and-forget.
- **Context managers for every resource** — files, locks, connections, transactions. If you wrote
  `try/finally` for cleanup, a `contextlib.contextmanager` says it better.
- **f-strings** for formatting, **except in logging**: `log.info("saved %s", name)` defers the
  formatting and survives a name that blows up `__str__`.
- **`dataclasses`** (or `pydantic` where validation is the point) instead of dicts-as-records — a
  typo in a dict key is a runtime `KeyError`, in a dataclass it's caught by the type checker.
- **Type the domain, not just the shape.** `NewType("UserId", str)` costs nothing at runtime and
  stops an order id crossing into a user-id slot at check time. Variants are a
  `Literal`-discriminated union dispatched with `match`, not a string field plus `if`s; accept
  capabilities structurally with `Protocol` ("has a `read()`"), not by inheritance.
- **Type hints on public functions**, and run the checker the repo runs. Hints nobody checks are
  comments that rot.
- **`enumerate`/`zip`/comprehensions** over index arithmetic; a comprehension that needs a comment is
  a `for` loop.
- **`subprocess.run([...])` with a list, never `shell=True`** with interpolated values — that is
  command injection with extra steps. Capture output explicitly, check the return code (`check=True`
  or handle it), and set a `timeout`.
- **Generators for large streams** so memory doesn't scale with input.
- Standard tooling settles style: `ruff`/`black` for format and lint, `pytest` for tests, `uv` or the
  repo's chosen manager for dependencies. Don't hand-argue formatting. Dev-only tools belong in
  PEP 735 `[dependency-groups]`, not `[project.optional-dependencies]` — extras ship to your
  users, groups don't.

## Dry-run: prove the decision and the effect are separable

A dry-run that is a second code path is not a dry-run — it proves nothing about the real one. The
decision must be computed by the same code either way; only the effect is gated:

```python
def sync(items, *, dry_run: bool, delete=os.remove):     # effect injected, decision shared
    planned = [i for i in items if _should_delete(i)]     # the DECISION — always runs
    if not dry_run:
        for item in planned:
            delete(item)                                 # the EFFECT — the only gated line
    return planned                                       # what it did, or would have done
```

And prove it with a spy, because "it printed the right thing" is not evidence that nothing happened:

```python
def test_dry_run_decides_but_does_not_delete():
    calls = []
    planned = sync(["a.tmp", "keep.txt"], dry_run=True, delete=calls.append)
    assert planned == ["a.tmp"]      # the decision is real
    assert calls == []               # and nothing was actually deleted
```

The spy is the assertion that matters: it fails if someone later moves an effect above the `if`.

## Verify

Before "done": the tests pass (paste the command and the tail of its output), the type checker and
linter the repo uses are clean, and anything with side effects was exercised with its dry-run
asserted by a spy as above. An untested `except` branch is the branch that will run in production.
