# LeeScoop

Local Lee County happenings, built as a static Astro site.

## Core rules
- static site
- markdown articles as source of truth
- GitHub + Cloudflare Pages deployment
- no database for v1
- no server-status gimmicks
- short, kind, useful local updates

## Stack
- Astro
- Astro content collections
- Markdown
- Pagefind
- GitHub
- Cloudflare Pages

## Commands
```bash
npm install
npm run dev
npm run build
npm run preview
```

## Structure
- `src/content/articles/` article markdown
- `src/components/` reusable UI
- `src/layouts/` page layouts
- `src/pages/` routes
- `src/lib/` article helpers
- `src/styles/` design tokens and site styles
- `public/` static assets
- `docs/` project notes and runbooks

## Deployment
Cloudflare Pages should build with:

```bash
npm run build
```

Output directory:

```bash
dist
```

Production branch: `main`.
