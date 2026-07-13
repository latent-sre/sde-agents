# Auth (client side)

Read this once the app is not localhost-only — login, tokens, refresh, route guarding.

The server still enforces; the UI is convenience, not the security boundary. The universal frontend
rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Auth (once the app isn't localhost-only)

- Access token in memory; refresh via an **httpOnly, Secure cookie** — never localStorage for anything an XSS could steal.
- One fetch/Query wrapper does **401 → refresh once → retry, else redirect to login**; every call inherits it instead of reinventing it.
- Route guards gate whole areas and hide actions the user lacks — but the server still enforces; the UI is convenience, not the security boundary.
