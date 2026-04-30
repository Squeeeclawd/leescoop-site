#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "Usage: ./scripts/new-article.sh <event|news> <slug> \"Title\" \"Category/City\"" >&2
  exit 1
fi

kind="$1"
slug="$2"
title="$3"
category="$4"
out="src/content/articles/${slug}.md"

if [[ "$kind" != "event" && "$kind" != "news" ]]; then
  echo "First argument must be event or news" >&2
  exit 1
fi

if [ -e "$out" ]; then
  echo "Post already exists: $out" >&2
  exit 1
fi

mkdir -p src/content/articles
now="$(date --iso-8601=seconds)"

if [ "$kind" = "event" ]; then
  cat > "$out" <<POST
---
title: "${title}"
slug: ${slug}
date: ${now}
draft: true
category: ${category}
tags:
  - ${category}
excerpt: Short summary of what is happening and who might want to go.
author: LeeScoop
contentKind: event
sourceType: official
contentType: brief
eventDate:
eventTime:
city: ${category}
location: ${category}
venue:
address:
audience:
cost:
sourceName:
sourceUrl:
coverImage:
---

## What is it?

Short description.

## Who is it for?

Short audience note.

## Official source

Add the official source link above in frontmatter.
POST
else
  cat > "$out" <<POST
---
title: "${title}"
slug: ${slug}
date: ${now}
draft: true
category: ${category}
tags:
  - ${category}
excerpt: Short summary of the local news item.
author: LeeScoop
contentKind: news
sourceType: news
contentType: brief
city: ${category}
location: ${category}
sourceName:
sourceUrl:
coverImage:
---

Brief local summary.

## Source

Add the source link above in frontmatter.
POST
fi

echo "Created $out"
