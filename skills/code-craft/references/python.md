# Python — contracts, lifetimes, concurrency, and the traps that stay green

Read before writing Python. The universal rules live in `skills/code-craft/SKILL.md`. On any
conflict, SKILL.md wins; the repository's own conventions and declared Python floor outrank both.

## Establish the runtime and package contract

- **Read `pyproject.toml`, lockfiles, tool configuration, and CI before choosing syntax or APIs.**
  `[project].requires-python`, classifiers, tox/nox environments, and the tested interpreter matrix
  define compatibility; the interpreter on PATH does not.
- Version-gate behavior, not just syntax. `TaskGroup` and `ExceptionGroup` require 3.11;
  `typing.override` requires 3.12; optional free-threaded CPython starts at 3.13; annotation
  evaluation changes in 3.14. Use a backport only when the repository already adopts it.
- Keep imports cheap and deterministic. Importing a module must not connect to a service, start a
  thread, parse process arguments, mutate global configuration, or depend on the working directory.
  Put application startup behind an explicit function and scripts behind `if __name__ == "__main__"`.
- Import package data through `importlib.resources.files()` when the supported floor permits it,
  rather than assuming `__file__` names a normal unpacked directory.
- Do not name local modules `types.py`, `queue.py`, `logging.py`, `typing.py`, or after an installed
  package. Shadowed imports fail far from the file that caused them.

## Aliasing and values that silently change meaning

- **Function defaults are evaluated once.** Use `None` plus construction inside the function for a
  mutable optional default. Dataclass fields use `field(default_factory=list)`, not `[]`.
- **Closures capture names, not historical values.** A callback created in a loop reads the final
  binding unless the value is bound deliberately, for example `lambda item=item: item`.
- **Mutation during iteration is a behavioral hazard.** Dictionary and set mutation can invalidate
  traversal; list mutation is legal but can skip or repeat elements. Iterate over a snapshot or
  construct a new collection when the mutation changes membership.
- Assignment aliases mutable objects; it does not copy them. Choose shallow copy, deep copy, or
  immutable data based on the ownership boundary, and test nested aliasing explicitly.
- **Truthiness is not absence.** `0`, `False`, `""`, empty containers, and `None` are all falsey.
  Use `is None` when absence is the contract. Use `is` for `None`, sentinels, and intentional
  identity—not ordinary strings, numbers, or booleans.
- Binary floating point is not exact decimal arithmetic. Use integer minor units or `Decimal` when
  the domain requires decimal rounding, and make the rounding policy part of the boundary.
- Use timezone-aware datetimes for instants. Parse and emit an explicit offset; do not mix naive and
  aware values or let the host's local timezone become hidden input.

## Exceptions are API and control flow

- Catch the narrow exception you can handle. `except Exception` does not catch `KeyboardInterrupt`,
  `SystemExit`, `GeneratorExit`, or `asyncio.CancelledError`; it can be appropriate at a process,
  request, or task boundary only when that boundary reports, translates, or re-raises the failure.
  A broad catch that silently continues is corruption with a calm face.
- **Bare `raise` re-raises the active exception with its traceback.** Raising a new exception while
  handling another records the prior one as implicit `__context__`; `raise DomainError(...) from
  exc` makes it the explicit `__cause__`. Use `from None` only when deliberately hiding internal
  context at a caller-facing boundary.
- Translate an implementation exception only when the caller should not depend on it. Preserve
  stable domain errors and structured fields; never make callers parse error-message text.
- Cleanup belongs in `finally` or a context manager, but do not `return`, `break`, or `continue`
  from `finally`: it can suppress the active exception and turn failure into success.
- On Python 3.11+, concurrent failures may arrive as `ExceptionGroup`. Use `except*` only when each
  selected subgroup has a real handling policy; do not flatten multiple causes into the first one.
- Assertions document programmer invariants, not validation of external input. Optimized execution
  can remove `assert` statements.

## Public APIs and typing

- Use positional-only `/` when a parameter name should not become caller API and keyword-only `*`
  when names prevent ambiguous calls. Both forms require a Python 3.8+ floor.
- **Annotations are not runtime validation.** Type public boundaries and run the repository's
  checker, but still validate decoded JSON, environment variables, database rows, and user input.
- Model domain distinctions explicitly: `NewType` can separate same-shaped identifiers at check
  time; `Protocol` describes a consumer-owned capability. A closed variant can use a
  `Literal`-discriminated union and an exhaustiveness check, while an open extension surface may
  legitimately use protocols or a class hierarchy.
- Modern typing features follow the declared floor. `assert_never` is available in 3.11,
  `@override` in 3.12, and `TypeIs` in 3.13. Do not emit them unconditionally for a wider support
  matrix.
- Python 3.14 lazily evaluates annotations. Do not assume raw `__annotations__` already contains
  final runtime values; use supported inspection APIs. Resolving annotations may execute code, so
  never evaluate annotations from an untrusted source.
- Dataclasses are typed record machinery, not input validation. Use the repository's validation
  layer when coercion and boundary validation are the point.

## Resource and file lifetimes

- Use `with`/`async with` for owned files, locks, responses, database resources, and transactions.
  `try/finally` remains the underlying cleanup primitive and may be clearest for one local lifetime;
  a reusable context manager should clarify—not hide—ownership.
- `ExitStack` owns a dynamic number of resources; `AsyncExitStack` coordinates async cleanup;
  `contextlib.aclosing` closes async generators on a Python 3.10+ floor.
- A generator that owns a file, response, or cursor retains it until exhaustion or explicit close.
  Prefer an iterator whose caller enters a context, or materialize bounded results before returning.
- `Path.read_text()` and `write_text()` close correctly but materialize the whole file. Specify the
  encoding and stream data whose size is not tightly bounded.
- **Atomic replacement is not the same as crash durability.** Write a temporary file in the same
  directory, flush it, sync it when durability is required, then `os.replace` it. If the contract
  must survive power loss, follow the platform's directory-sync and storage guarantees as well.

## Async and concurrent ownership

- Every created task needs an owner, a cancellation path, and a join point. Retain a strong
  reference to intentionally backgrounded tasks and surface their exceptions; "fire and forget"
  otherwise means "failure may be garbage-collected or noticed too late."
- **Cancellation is control flow.** Use `try/finally` for cleanup. If `CancelledError` is caught,
  normally re-raise it after cleanup; swallowing it can break `TaskGroup`, timeouts, and the caller's
  shutdown contract.
- On Python 3.11+, prefer `asyncio.TaskGroup` when sibling tasks form one operation: the group waits
  for all children and cancels siblings after a non-cancellation failure. On older floors, implement
  equivalent cancel-and-join behavior deliberately rather than merely awaiting the first task.
- Use `asyncio.timeout()` on 3.11+ or the repository's compatible timeout primitive. A timeout must
  cancel or otherwise retire the underlying operation; returning early while work continues is not
  a timeout.
- Never block the event loop with synchronous network, filesystem, subprocess, or CPU-heavy work.
  Use an async API, `asyncio.to_thread()` for appropriate blocking I/O on 3.9+, or the repository's
  executor/process boundary. CPU work needs measurement and often a process or native implementation.
- The GIL is not an ownership model, and optional free-threaded builds exist from Python 3.13.
  Protect multi-step invariants with locks, queues, immutability, or single-owner state rather than
  relying on incidental atomicity of a built-in operation.
- Process workers require serializable inputs and explicit startup ownership. Keep process creation
  behind the main guard and test the repository's supported start methods instead of assuming fork.
- Request/task-local metadata belongs in `contextvars`, not a mutable module global.

## Security-sensitive standard-library boundaries

- Pass argument lists to `subprocess.run`; avoid `shell=True` with data. Set a timeout and check the
  return code or handle it explicitly.
- Never unpickle untrusted data. `ast.literal_eval` avoids code execution but can still exhaust
  memory or the C stack, so it is not an unrestricted hostile-input parser.
- Archive extraction is version-sensitive. Use the `tarfile` data filter where available (added in
  3.12 and the default in 3.14), feature-detect security backports, and fail closed or validate paths,
  links, counts, and expanded size on older targets. A filter does not prevent resource exhaustion.
- Generate credentials and reset tokens with `secrets`, not `random`; compare secret values with
  `hmac.compare_digest` where timing exposure matters.
- Use `tempfile` for unpredictable temporary names and context-managed cleanup. Do not construct a
  "temporary" path from user input in a shared directory.

## Packaging and dependency contracts

- A distributable project declares its build system and project metadata in `pyproject.toml`.
  Preserve the repository's lock and installation workflow; do not introduce a second package
  manager or regenerate unrelated dependency state.
- `[project.optional-dependencies]` are published extras for users. PEP 735
  `[dependency-groups]` are internal requirement lists excluded from built distribution metadata;
  support depends on the packaging tool, not the Python interpreter. Use either only when the
  repository's chosen tool supports it.
- Keep import packages separate from CLI/process wiring. A library import should not read `.env`,
  configure root logging, or choose production defaults.

## Logging is a boundary, not string decoration

- Use the repository's logging facade and parameterized messages such as
  `logger.info("saved %s", name)` when supported. This defers formatting until a handler needs the
  record, but it does not guarantee that a broken or hostile `__str__` succeeds at emission.
- Log stable event names and structured fields useful for correlation. Do not make dashboards,
  alerts, or callers parse prose whose wording changes during ordinary maintenance.
- Never log credentials, tokens, session identifiers, raw authorization headers, or unrestricted
  request bodies. Redaction happens before data reaches any handler or exporter.
- Libraries do not configure the application's root logger. Applications own handlers, levels,
  destinations, sampling, and shutdown/flush behavior.

## Tests and tooling that prove the right property

- Run the formatter, linter, type checker, and test runner already configured by the repository.
  Ruff, Black, mypy/pyright, pytest, uv, tox, and nox are examples—not language standards.
- Patch where the dependency is looked up, not where it was originally defined. Use `autospec` or
  `spec_set` when a mock should reject nonexistent attributes; use `AsyncMock` for async contracts.
- Make time, randomness, environment, working directory, and network behavior explicit inputs or
  controlled boundaries. A fixed random seed reproduces one path; it does not prove the space.
- Async tests exercise cancellation, timeout, and cleanup—not only successful completion. Assert
  that owned tasks finish and resources close before the test ends.
- Use Development Mode, warnings-as-errors where compatible, `faulthandler`, or `tracemalloc` when
  the changed failure class calls for them. These are diagnostics, not unconditional CI flags.
- Profile before optimizing. A shorter implementation or a faster microbenchmark is not evidence
  of lower end-to-end latency, bounded memory, or unchanged results.

## Dry-run: one decision path, one gated effect

A dry-run that reimplements the decision is a second code path, so it proves little about the real
operation. Compute one plan and gate only the effect:

```python
def sync(items, *, dry_run: bool, delete=os.remove):
    planned = [item for item in items if _should_delete(item)]
    if not dry_run:
        for item in planned:
            delete(item)
    return planned
```

Prove both halves with an injected effect:

```python
def test_dry_run_decides_without_deleting():
    calls = []
    planned = sync(["a.tmp", "keep.txt"], dry_run=True, delete=calls.append)
    assert planned == ["a.tmp"]
    assert calls == []
```

## Verify

Run the repository's declared commands first and test every supported interpreter when behavior is
version-sensitive. An ordinary evidence packet names:

```text
<repository formatter/linter command>
<repository type-check command>
<repository test command>
```

Add focused cancellation/cleanup tests for async work, a subprocess boundary test for command
construction, and a dry-run spy for side effects when those paths changed. Report the exact Python
versions exercised; one green local interpreter does not prove the declared support matrix.

## Primary evidence anchors

- Python language reference — `raise`:
  <https://docs.python.org/3/reference/simple_stmts.html#the-raise-statement>
- Built-in exceptions: <https://docs.python.org/3/library/exceptions.html>
- `asyncio` tasks and structured concurrency: <https://docs.python.org/3/library/asyncio-task.html>
- Context-manager utilities: <https://docs.python.org/3/library/contextlib.html>
- Typing specification and APIs: <https://docs.python.org/3/library/typing.html>
- Annotation semantics: <https://docs.python.org/3/library/annotationlib.html>
- Mocking contracts: <https://docs.python.org/3/library/unittest.mock.html>
- Python free-threading guidance: <https://docs.python.org/3/howto/free-threading-python.html>
- `tarfile` extraction filters: <https://docs.python.org/3/library/tarfile.html#extraction-filters>
- Packaging project metadata: <https://packaging.python.org/en/latest/specifications/pyproject-toml/>
- Dependency groups: <https://packaging.python.org/en/latest/specifications/dependency-groups/>
