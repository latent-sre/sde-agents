# Forms

Read this when the view collects user input for submission.

The universal frontend rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Forms

- State via **@mantine/form** (or react-hook-form): validate on blur *and* submit, never only on submit.
- **The server is the source of validation truth** — mirror obvious rules client-side for speed, but always map the server's field errors back to the offending fields inline.
- **Dirty tracking**: Save disabled until something changed; warn before leaving unsaved edits (route guard + `beforeunload`). Never make the user retype after an error.
