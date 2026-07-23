# Interaction accessibility — overlays, widgets, announcements

Read this when the view involves a modal, drawer, menu, tooltip, or tabs — any custom interactive
widget — or announces async status (toasts, inline save/error states, live-updating values).

The universal frontend rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md
wins. The baseline (semantic elements, labeled inputs, keyboard reachability, visible focus) lives
there; this file owns the interaction-level wiring. Attribute names are the web platform's and
apply in any stack; form-field wiring (labels, error linking) lives in `references/forms.md`.

## Overlays — focus is part of the state change

- Opening moves focus into the overlay; closing returns it to the element that opened it. Store
  the opener before moving focus — the browser won't restore it for you.
- Trap Tab/Shift+Tab inside while open, using native `<dialog>` or the repo's established
  dialog/focus-trap primitive — never hand-rolled: dynamic content and nested portals break naive
  traps.
- `role="dialog"`, `aria-modal="true"`, labeled by the overlay's heading; Escape closes it.

## Custom widgets — you own the whole keyboard grammar

- Reach for the platform element (`<select>`, `<details>`, `<dialog>`) or the repo's component
  library first; building custom means owning everything below.
- The trigger carries `aria-expanded` and `aria-controls`; options carry `role="option"` and
  `aria-selected`. When focus stays on the trigger while arrow keys move a highlight (combobox,
  listbox), set `aria-activedescendant` to the highlighted option's id — without it, a screen
  reader announces nothing as the user arrows through the options.
- Keyboard grammar: arrows move within the widget, Enter/Space activates, Escape closes or
  cancels, Tab leaves the widget — it never cycles inside one.

## Announcing async status

- Status that appears without navigation — a toast, "Saved", an inline error, a failed background
  action — renders into a live region (`role="status"`; `role="alert"` only for urgent errors),
  or assistive tech never hears it. Mount the region once and swap its text content; a region
  injected together with its first message is often not announced.
- This completes the Resilience UX rule in SKILL.md: every designed loading/error/empty
  transition a sighted user can see, a screen-reader user can hear.

## Icons and images

- An icon-only button gets `aria-label`; the icon inside it gets `aria-hidden="true"`.
- Decorative images: `alt=""`. Meaningful images: alt text that says what the image conveys, not
  that it exists.

## Anti-patterns

- Positive `tabIndex` values — they create an unpredictable tab order; only `0` and `-1`.
- `aria-hidden` on a focusable element — keyboard focus lands on something assistive tech says
  isn't there.
- `role="button"` (or an onClick) on a div without `tabIndex="0"` and Enter/Space handling — the
  role announces an ability the element doesn't have.
- ARIA replacing a native element that already does the job — wrong ARIA is worse than no ARIA.
- A placeholder as the only label — it vanishes on focus. `references/ux-writing.md` carries the
  voice half of this rule, `references/forms.md` the wiring half.
