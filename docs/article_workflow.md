# LeeScoop article workflow

LeeScoop articles should be short, kind, local, and useful.

## Create one draft manually

Use the current script signature:

```bash
./scripts/new-article.sh <event|news> <slug> "Article title" "Cape Coral"
```

Examples:

```bash
./scripts/new-article.sh event hurricane-expo-2026 "Hurricane Expo returns to Fort Myers" "Fort Myers"
./scripts/new-article.sh news cape-coral-road-vote "Cape Coral road vote moves forward" "Cape Coral"
```

That creates a draft markdown file in:

```bash
src/content/articles/
```

For batch posts, prefer the canonical writer instead of hand-copying templates:

```bash
python3 scripts/leescoop_posts.py check --input tmp/candidates.json
python3 scripts/leescoop_posts.py write --input tmp/candidates.json
```

## Required frontmatter

The Astro schema lives in `src/content/config.ts`. Keep article frontmatter aligned with it.

Base fields:

```yaml
---
title: "Article title"
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
contentKind: event # event | news
sourceType: official # official | community | news | local
contentType: brief # brief | standard | guide
sourceName: City of Example
sourceUrl: https://example.com/source
coverImage: /covers/example.png
---
```

Event-specific fields:

```yaml
eventDate: 2026-05-15T18:00:00-04:00
eventEndDate:
eventTime: 6:00 PM - 8:00 PM
city: Cape Coral
location: Cape Coral
venue: Example Park
address:
audience:
cost:
```

Optional verification/image metadata:

```yaml
sourceImageUrl: https://example.com/image.jpg
verificationUrl: https://example.com/official-confirmation
```

## Gates before publishing

Run:

```bash
npm run validate
npm run check
npm run build
```

Or all together:

```bash
npm run quality
```

The validator catches mistakes Astro can tolerate, including missing covers, unknown frontmatter keys, stale active events, malformed source URLs, and surprise drafts.

## Tone

- Clear
- Kind
- Local
- Short
- No ads
- No promotion
- No manufactured outrage
