# Task Playbooks

## Screenshot Match

Use this when the user says a page is wrong compared with an image.

1. Identify the exact target route and component.
2. Compare structure first: sections, card size, alignment, tabs, copy blocks, artwork layers.
3. Compare hierarchy second: title scale, CTA weight, supporting text, spacing rhythm.
4. Compare finish third: color, blur, borders, shadows, motion.
5. Generate screenshots after changes and verify the requested state, not only the default route.

## Auth Flow Fix

Use this for login, sign up, OTP, or redirect issues.

1. Read router entry points and auth component state logic.
2. Verify all UI states: idle, submit, loading, error, success, redirect.
3. Remove dead or misleading tabs before polishing visuals.
4. Keep messages explicit about what happens next.
5. Check that route behavior matches the visible screen flow.

## General UI Review

Use this when the user asks to improve or review a page without a specific screenshot.

1. Start with product fit: does the page feel like LAW-GPT?
2. Review hierarchy, spacing, typography, and contrast.
3. Check responsive behavior and touch affordances.
4. Check focus, hover, loading, empty, and error states.
5. Prefer a few structural improvements over many decorative tweaks.

## Design-System Cleanup

1. Find repeated hardcoded colors, radii, shadows, and spacing values.
2. Normalize repeated patterns into shared classes, tokens, or utility conventions already used by the repo.
3. Avoid introducing a new design language unless the user asked for a redesign.
4. Keep changes incremental so visual regressions stay reviewable.