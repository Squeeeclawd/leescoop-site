#!/usr/bin/env python3
"""Validate LeeScoop content beyond Astro's build gate.

Checks common publishing mistakes that static builds tolerate:
- missing cover assets
- stale/past event dates on active posts
- unknown frontmatter keys
- malformed source URLs
- inconsistent event/news fields
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "src" / "content" / "articles"
PUBLIC = ROOT / "public"
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)

ALLOWED_KEYS = {
    "title", "date", "updatedDate", "draft", "featured", "pinned", "ticker", "tickerRank",
    "category", "tags", "excerpt", "coverImage", "author", "contentKind", "sourceType",
    "contentType", "eventDate", "eventEndDate", "eventTime", "city", "location", "venue",
    "address", "audience", "cost", "sourceName", "sourceUrl", "sourceImageUrl", "verificationUrl",
}

REQUIRED_BASE = {"title", "date", "category", "excerpt", "contentKind", "sourceType", "sourceUrl"}


def parse_scalar(raw: str):
    raw = raw.strip()
    if raw in {"", "null", "~"}:
        return ""
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    return raw


def parse_frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data: dict[str, object] = {}
    lines = match.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if re.match(r"^[A-Za-z0-9_]+:\s*$", line):
            key = line.split(":", 1)[0].strip()
            values: list[object] = []
            i += 1
            while i < len(lines) and lines[i].startswith("  - "):
                values.append(parse_scalar(lines[i][4:]))
                i += 1
            data[key] = values
            continue
        if ":" in line and not line.startswith(" "):
            key, raw = line.split(":", 1)
            data[key.strip()] = parse_scalar(raw)
        i += 1
    return data


def parse_dt(value: object) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def valid_url(value: object) -> bool:
    if not value:
        return False
    parsed = urlparse(str(value).strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate LeeScoop article frontmatter and assets.")
    parser.add_argument("--allow-draft", action="append", default=["example-lee-county-update.md"], help="Draft filename allowed to remain draft:true")
    parser.add_argument("--strict-past-events", action="store_true", help="Fail instead of warning for past event dates")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    errors: list[str] = []
    warnings: list[str] = []
    articles = sorted(ARTICLES.glob("*.md"))

    for path in articles:
        rel = path.relative_to(ROOT)
        fm = parse_frontmatter(path)
        if not fm:
            errors.append(f"{rel}: missing or unreadable frontmatter")
            continue

        unknown = sorted(set(fm) - ALLOWED_KEYS)
        if unknown:
            errors.append(f"{rel}: unknown frontmatter keys: {', '.join(unknown)}")

        is_draft = fm.get("draft") is True
        allowed_draft = is_draft and path.name in set(args.allow_draft)
        if is_draft and not allowed_draft:
            errors.append(f"{rel}: unexpected draft:true")
        if allowed_draft:
            continue

        missing = sorted(k for k in REQUIRED_BASE if not fm.get(k))
        if not is_draft and missing:
            errors.append(f"{rel}: missing required keys: {', '.join(missing)}")

        kind = str(fm.get("contentKind") or "")
        if kind not in {"event", "news"}:
            errors.append(f"{rel}: contentKind must be event or news")

        if fm.get("sourceUrl") and not valid_url(fm.get("sourceUrl")):
            errors.append(f"{rel}: invalid sourceUrl")
        if fm.get("sourceImageUrl") and not valid_url(fm.get("sourceImageUrl")):
            errors.append(f"{rel}: invalid sourceImageUrl")
        if fm.get("verificationUrl") and not valid_url(fm.get("verificationUrl")):
            errors.append(f"{rel}: invalid verificationUrl")

        cover = str(fm.get("coverImage") or "").strip()
        if not is_draft and not cover:
            warnings.append(f"{rel}: no coverImage")
        if cover and not cover.startswith(("http://", "https://")):
            cover_path = PUBLIC / cover.lstrip("/")
            if not cover_path.exists():
                errors.append(f"{rel}: coverImage missing: {cover}")

        if kind == "event":
            event_dt = parse_dt(fm.get("eventEndDate") or fm.get("eventDate"))
            if not event_dt and not is_draft:
                errors.append(f"{rel}: event missing eventDate")
            elif event_dt and event_dt < now and not is_draft:
                msg = f"{rel}: active event date is in the past: {event_dt.date().isoformat()}"
                (errors if args.strict_past_events else warnings).append(msg)
        elif kind == "news":
            if fm.get("eventDate"):
                warnings.append(f"{rel}: news item has eventDate")

    print(f"Validated {len(articles)} article file(s).")
    if warnings:
        print("\nWarnings:")
        for item in warnings:
            print(f"- {item}")
    if errors:
        print("\nErrors:")
        for item in errors:
            print(f"- {item}")
        return 1
    print("No validation errors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
