---
name: lawgpt-ui-ux
description: 'UI and UX workflow for the LAW-GPT frontend. Use when designing, fixing, reviewing, or matching pages and components in frontend/, especially login/auth flows, chat screens, landing pages, navigation, responsive layout, visual hierarchy, accessibility, motion, design-system consistency, and screenshot-based UI restoration.'
argument-hint: '[page, component, or UI issue]'
user-invocable: true
---

# LAW-GPT UI/UX

Focused UI workflow for this repository's main frontend application.

## Target App

- Primary frontend target: `frontend/`
- Stack: React + Vite + Tailwind + Framer Motion
- Product type: legal AI assistant, not a generic SaaS dashboard

## When To Use

Use this skill when the task involves:

- restoring or matching a screenshot
- login, signup, onboarding, or auth flow UI
- chat UI, navigation, cards, filters, headers, loaders, or layout polish
- accessibility, motion, spacing, typography, color, and responsive behavior
- design-system cleanup or consistency review
- deciding whether a UI idea fits a legal product versus a generic AI product

## Default Product Direction

- Trust before novelty
- Calm hierarchy over visual noise
- Strong readability and explicit states
- Motion only when it clarifies interaction
- Premium legal product feel, not crypto, gaming, or neon AI branding

Read [LAW-GPT design rules](./references/lawgpt-design-rules.md) for concrete styling guidance.

## Procedure

1. Confirm the target surface.
   Usually this means `frontend/`, not older side apps or archived UI folders.

2. Determine the request type.
   Use [task playbooks](./references/task-playbooks.md) for screenshot-match work, auth flow work, or general UI review.

3. Inspect before editing.
   Read the relevant component, routing entry point, and any styling file that controls the surface.

4. Protect product fit.
   Keep LAW-GPT visually credible: restrained palette, strong contrast, clear form states, and legal-product seriousness.

5. Implement the smallest coherent change.
   Fix root UI structure, not just one-off CSS overrides, unless the task is explicitly narrow.

6. Verify the real states.
   Check default, hover, focus, loading, error, success, empty, and responsive states when applicable.

7. If the user provided a screenshot, optimize for screenshot parity over abstract redesign ideas.

## Review Checklist

- Is the hierarchy immediately clear?
- Are primary and secondary actions visually distinct?
- Is body text readable on mobile and desktop?
- Are focus, error, loading, and disabled states obvious?
- Does motion support the interaction instead of distracting from it?
- Does the page still feel like a legal assistant product?
- Did the change introduce generic AI-purple or unrelated design drift?

## References

- [LAW-GPT design rules](./references/lawgpt-design-rules.md)
- [Task playbooks](./references/task-playbooks.md)

## Source Note

This skill is a LAW-GPT-specific adaptation informed by the cloned reference package in `external_skills/ui-ux-pro-max-skill/`. Use that repository for deeper exploration only when the task genuinely needs broader design-system patterns.