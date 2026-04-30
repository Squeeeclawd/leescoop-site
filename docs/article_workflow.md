# LeeScoop article workflow

LeeScoop articles should be short, kind, local, and useful.

## Create an article

```bash
./scripts/new-article.sh my-local-slug "Article title" "Cape Coral"
```

That creates a markdown file in:

```bash
src/content/articles/
```

## Required frontmatter

```yaml
---
title: "Article title"
slug: my-local-slug
date: 2026-04-30T10:00:00-04:00
draft: false
featured: false
pinned: false
ticker: false
category: Cape Coral
tags:
  - Cape Coral
excerpt: One short sentence explaining what happened.
author: LeeScoop
sourceType: local
contentType: brief
coverImage:
---
```

## Tone
- Clear
- Kind
- Local
- Short
- No ads
- No promotion
- No manufactured outrage
