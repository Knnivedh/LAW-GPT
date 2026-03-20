# LAW-GPT Design Rules

## Product Fit

LAW-GPT should feel like a serious legal tool.

- Prefer charcoal, off-white, deep red, steel, muted gold, and restrained accent colors.
- Avoid default AI-purple branding unless a page already uses it and the user asks to keep it.
- Avoid emoji as product icons in final polished UI.
- Avoid gimmick-heavy motion, neon glow, crypto aesthetics, and gaming-style chrome.

## Typography

- Headings should feel authoritative, not playful.
- Body text must stay readable at small sizes; default body should generally land at 16px on mobile.
- Use clear contrast and moderate line length.
- Reserve decorative typography for hero or brand accents only.

## Layout

- Keep a clear primary action on each screen.
- Favor strong section spacing and obvious grouping.
- Avoid overpacking cards or auth forms.
- For legal content, reduce ambiguity: labels beat placeholders, visible headings beat implied sections.

## Auth Screens

- Auth surfaces must feel secure and deliberate.
- Error messages should appear near the action area and state what the user should do next.
- Sign In and Sign Up should be clearly separated if both exist in one card.
- If OTP exists, treat it as a guided step, not a surprise branch.
- If the user asks for screenshot fidelity, match the provided structure before introducing new affordances.

## Chat Screens

- Conversation area should dominate the page, but controls must remain obvious.
- Input affordance must be persistent and easy to target.
- Streaming, thinking, or loading states should be subtle and readable.
- Citations, filters, and actions must not compete with the message content.

## Motion

- Prefer opacity and transform transitions.
- Keep common UI motion roughly in the 150ms to 300ms range.
- Use stronger animation only for high-value surfaces like first-load hero moments or deliberate reveal effects.
- Respect reduced-motion where feasible.

## Accessibility

- Preserve visible focus indicators.
- Do not rely on color alone to communicate errors or selection.
- Ensure touch targets remain usable on mobile.
- Avoid hover-only discovery for essential actions.

## Visual Anti-Patterns

- Purple-on-black AI default styling with no legal-brand reason
- Too many floating panels competing for attention
- Flat low-contrast gray-on-gray text
- Tiny auth inputs and cramped CTA spacing
- Decorative blur without hierarchy or purpose
- Page transitions that hide state problems instead of solving them