When a task changes UI, UX, layout, animation, auth screens, visual polish, responsive behavior, accessibility, or screenshot parity in LAW-GPT, load the `lawgpt-ui-ux` skill first.

Use the deployed frontend target at `frontend/` for UI work unless the user explicitly asks for another app.

For LAW-GPT UI decisions:
- preserve the product's legal-assistant tone: credible, calm, high-contrast, and trust-oriented
- avoid generic AI styling defaults like purple-heavy gradients, emoji-as-icons, and noisy motion unless the user explicitly requests them
- prioritize screenshot fidelity when the user gives a visual reference
- validate desktop and mobile states after meaningful visual changes

When reviewing or editing auth flows, check both visual structure and working states: sign in, sign up, loading, error, success, and route transitions.