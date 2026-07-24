# Go — errors, lifetimes, and the aliasing traps

Read before writing Go. The universal rules live in `skills/code-craft/SKILL.md`. On any conflict,
SKILL.md wins; the repository's own conventions outrank both.

## Errors are values, and the handling is the program

- **Wrap with context on the way up**: `fmt.Errorf("load config %s: %w", path, err)`. The `%w` keeps
  the chain so `errors.Is`/`errors.As` still work; `%v` breaks it and turns a typed error into a
  string nobody can branch on.
- **Sentinels for expected conditions** (`var ErrNotFound = errors.New("not found")`), compared with
  `errors.Is` — never by string matching, which breaks the moment someone improves the message.
- **Never `_ =` an error you haven't reasoned about**, and never ignore `Close()` on a writer — that's
  where the flush failure lives, and a silently unflushed file is a corrupt file.
- **A nil error is not a nil result.** Check both when the API can return neither.
- **The typed-nil trap**: a nil pointer stored in an error interface is *not* `nil`. Return
  `error` explicitly rather than a concrete `*MyError`, or `if err != nil` is true when nothing failed.
- `panic` is for programmer error and process startup, not for control flow across a package
  boundary. Recover only at a boundary you own (a request handler), and log what you recovered.

## Lifetimes: defer, context, goroutines

- **`defer` runs at function exit, not scope exit.** A `defer` inside a loop accumulates until the
  function returns — file handles exhausted at iteration 1024. Extract the body into a function.
- `defer` arguments evaluate immediately; the call is deferred. `defer f(time.Now())` records the
  wrong time.
- **`context.Context` is the first parameter of anything that blocks**, and it must actually be
  honored: pass it to the call you make, select on `ctx.Done()` in your own loop. A context threaded
  through and never checked is decoration.
- **Every goroutine needs a defined end.** A goroutine writing to an unbuffered channel nobody reads
  leaks the goroutine and everything it references, forever, with no error anywhere. Use
  `errgroup`/`WaitGroup`, or pass a context and select on it.
- Don't start a goroutine you can't wait for; "fire and forget" means "leak and never know".
- `time.After` in a loop allocates a timer per iteration that lives until it fires — use
  `time.NewTimer` and `Stop()`.

## Aliasing and copies

- **Slices share backing arrays.** `b := a[:2]` then `append(b, x)` can overwrite `a[2]`. Copy
  explicitly (`append([]T(nil), a...)` or `slices.Clone`) when the caller keeps the original.
- **A range variable is reused** (before Go 1.22) — capturing `&v` or closing over `v` in a goroutine
  gives every iteration the last value. Even on 1.22+, write it explicitly if the file targets an
  older toolchain.
- **Maps are references; structs are values.** Passing a struct copies it, so a method on a value
  receiver mutating a field mutates nothing the caller sees. Pointer receiver when it mutates, and be
  consistent across a type's method set.
- Maps have no defined iteration order — code that depends on it fails intermittently, which is
  worse than failing.

## Shape and tooling

- Accept interfaces, return structs. Define the interface where it's *consumed*, not beside the
  implementation — a one-method interface at the consumer is the idiom.
- Zero values should be useful; a type that requires a constructor should say so by being
  unexported.
- Standard tooling settles style: `gofmt` (non-negotiable), `go vet`, `golangci-lint` if the repo
  uses it. `go test -race` on anything concurrent — the race detector finds what review cannot.
- Table-driven tests with named subtests (`t.Run(tc.name, ...)`); `t.Helper()` in assertion helpers so
  failures point at the caller.

## Verify

`go build ./...`, `go vet ./...`, `gofmt -l .` empty, and `go test ./... -race` — paste the command and
result. For anything with goroutines, a test that would hang if the goroutine leaked (bounded by
`t.Deadline` or a context timeout) is the only real proof it terminates.
