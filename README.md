# Landing Project Documentation

## Project Overview

Single-page landing for a product mentorship offer.

- Main entry point: `index.html`
- Stack: static HTML + Tailwind utility classes + vanilla JavaScript
- No build step, no framework runtime, no package manager required

## Project Structure

- `index.html` - all page markup, styles (inside `<style>`), and scripts (inside `<script>`)
- `assets/` - media files (videos, images, social icons, documents)
- `fonts/` - local OTF font files used via `@font-face`

## Local Run

You can open `index.html` directly in the browser, but recommended:

1. Start a static server in project root.
2. Open the local URL in browser.

Example:

```bash
python3 -m http.server 8080
```

Then open `http://localhost:8080`.

## Editing Guidelines

- Keep section IDs stable (`#expert`, `#reviews`, `#pricing`, etc.), because nav and anchors depend on them.
- Prefer editing existing classes before adding new wrappers.
- If you add a new media file, put it under `assets/` and reference it with a relative path from `index.html`.
- Keep scripts in the bottom `<script>` block to avoid load order issues.

## Main Page Sections

- Hero (video background, CTA, navigation)
- Expert (`#expert`)
- Audience (`#audience`)
- Curriculum (`#curriculum`)
- Outcomes (`#outcomes`)
- Pricing (`#pricing`)
- Guide (`#guide`)
- Reviews (`#reviews`)
- FAQ (`#faq`)
- Contacts (`#contacts`)

## JS Features Implemented

- Header/nav active-link sync on scroll
- Hero video mode switching and reduced-motion handling
- Review video controls (play/pause overlay button)
- Document preview modal for certificate image
- FAQ accordion behavior
- Mobile reviews carousel controls (left/right arrows)

## Asset Policy

Project was cleaned from unused files. Current rule:

- Keep only files referenced by `index.html`.
- Remove duplicate exports and temporary render files (`test2.*`, backups, etc.).
- Avoid storing system metadata files like `.DS_Store`.

## Deployment Notes

This is a static site, so it can be deployed to:

- GitHub Pages
- Netlify
- Vercel (static)
- Any Nginx/Apache static hosting

Deploy command depends on platform, but source is always this project root.

## Maintenance Checklist

- Validate all media links after renaming files
- Check section anchors after layout edits
- Test mobile and desktop breakpoints
- Keep documentation updated when adding/removing sections
