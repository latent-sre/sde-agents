# A real package, deliberately: as a bare namespace directory, `tests` loses import resolution
# to ANY installed regular package of the same name anywhere on sys.path — regular packages beat
# namespace portions regardless of path order — and every `from tests.support import ...` in the
# suite would raise ModuleNotFoundError in such an environment (caught in review on #91).
