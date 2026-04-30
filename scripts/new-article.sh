#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: ./scripts/new-article.sh <slug> \"Title\" \"Category\"" >&2
  exit 1
fi

slug="$1"
title="$2"
category="$3"
out="src/content/articles/${slug}.md"

if [ -e "$out" ]; then
  echo "Article already exists: $out" >&2
  exit 1
fi

mkdir -p src/content/articles
now="$(date --iso-8601=seconds)"

cat > "$out" <<ARTICLE
---
title: "${title}"
slug: ${slug}
date: ${now}
draft: true
featured: false
pinned: false
ticker: false
category: ${category}
tags:
  - ${category}
excerpt: Short summary of what’s happening.
author: LeeScoop
sourceType: local
contentType: brief
coverImage:
---

Short, kind local update goes here.
ARTICLE

echo "Created $out"
