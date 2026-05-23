#!/usr/bin/env python3
"""LeeScoop candidate safety check + markdown writer.

Input is the strict JSON produced from prompts/leescoop_daily_gpt54mini.md.
This script intentionally does not commit, push, or overwrite existing files.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "src" / "content" / "articles"
COVERS = ROOT / "public" / "covers"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


def norm_text(value: str | None) -> str:
    value = value or ""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value).strip().lower()
    return re.sub(r"\s+", " ", value)


def norm_url(value: str | None) -> str:
    if not value:
        return ""
    try:
        parts = urlsplit(value.strip())
        # Strip fragments and common tracking query noise for duplicate matching.
        query_parts = []
        for piece in parts.query.split("&") if parts.query else []:
            key = piece.split("=", 1)[0].lower()
            if key.startswith("utm_") or key in {"fbclid", "gclid", "mc_cid", "mc_eid"}:
                continue
            query_parts.append(piece)
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "&".join(query_parts), ""))
    except Exception:
        return value.strip().lower()


def registrable_domain(value: str | None) -> str:
    """Small dependency-free domain comparison for source-image sanity checks."""
    if not value:
        return ""
    try:
        host = urlsplit(value.strip()).netloc.lower().split("@")[-1].split(":")[0]
    except Exception:
        host = str(value).lower()
    if host.startswith("www."):
        host = host[4:]
    parts = [p for p in host.split(".") if p]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except Exception:
        return None


def has_expired_deadline(item: dict[str, Any], now: datetime | None = None) -> str | None:
    """Catch obvious stale news like a March deadline discovered in May."""
    now = now or datetime.now().astimezone()
    text = " ".join(str(item.get(k, "")) for k in ["title", "excerpt", "summary"])
    if not re.search(r"\b(deadline|until|by|before|postmarked by)\b", text, re.I):
        return None
    month_re = r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    for match in re.finditer(month_re + r"\s+(\d{1,2})(?:,\s*(\d{4}))?", text, re.I):
        month_name, day_raw, year_raw = match.groups()
        month = datetime.strptime(month_name[:3], "%b").month
        year = int(year_raw) if year_raw else now.year
        try:
            deadline = datetime(year, month, int(day_raw), 23, 59, tzinfo=now.tzinfo)
        except ValueError:
            continue
        if deadline < now:
            return deadline.date().isoformat()
    return None


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "untitled"


def parse_scalar(raw: str) -> Any:
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


def parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data: dict[str, Any] = {}
    lines = match.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if re.match(r"^[A-Za-z0-9_]+:\s*$", line):
            key = line.split(":", 1)[0]
            arr: list[str] = []
            i += 1
            while i < len(lines) and lines[i].startswith("  - "):
                arr.append(parse_scalar(lines[i][4:]))
                i += 1
            data[key] = arr
            continue
        if ":" in line and not line.startswith(" "):
            key, raw = line.split(":", 1)
            data[key.strip()] = parse_scalar(raw)
        i += 1
    return data


def existing_index() -> dict[str, Any]:
    idx = {"titles": {}, "urls": {}, "slugs": {}, "event_keys": {}}
    ARTICLES.mkdir(parents=True, exist_ok=True)
    for path in ARTICLES.glob("*.md"):
        fm = parse_frontmatter(path)
        slug = path.stem
        idx["slugs"][slug] = str(path.relative_to(ROOT))
        title_key = norm_text(str(fm.get("title", "")))
        if title_key:
            idx["titles"][title_key] = str(path.relative_to(ROOT))
        url_key = norm_url(str(fm.get("sourceUrl", "")))
        if url_key:
            idx["urls"][url_key] = str(path.relative_to(ROOT))
        if str(fm.get("contentKind", "")) == "event":
            event_date = str(fm.get("eventDate", ""))[:10]
            venue_key = norm_text(str(fm.get("venue", "")))
            if event_date and venue_key:
                idx["event_keys"][(event_date, venue_key)] = str(path.relative_to(ROOT))
    return idx


def load_candidates(path: Path) -> dict[str, list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Input JSON must be an object with events/news arrays")
    events = data.get("events", []) or []
    news = data.get("news", []) or []
    if not isinstance(events, list) or not isinstance(news, list):
        raise ValueError("events and news must be arrays")
    return {"events": events, "news": news}


def duplicate_reason(kind: str, item: dict[str, Any], idx: dict[str, Any]) -> str | None:
    title = norm_text(str(item.get("title", "")))
    source_url = norm_url(str(item.get("sourceUrl", "")))
    slug = slugify(str(item.get("slug") or item.get("title") or ""))
    if slug in idx["slugs"]:
        return f"same slug as {idx['slugs'][slug]}"
    if title and title in idx["titles"]:
        return f"same title as {idx['titles'][title]}"
    if source_url and source_url in idx["urls"]:
        return f"same sourceUrl as {idx['urls'][source_url]}"
    if kind == "event":
        event_date = str(item.get("eventDate", ""))[:10]
        venue_key = norm_text(str(item.get("venue", "")))
        if event_date and venue_key and (event_date, venue_key) in idx["event_keys"]:
            return f"same event date + venue as {idx['event_keys'][(event_date, venue_key)]}"
    return None


def yaml_string(value: Any) -> str:
    if value is None:
        return ""
    value = str(value).replace("\\", "\\\\").replace('"', '\\"')
    if value == "" or any(ch in value for ch in [":", "#", "[", "]", "{", "}", ",", "&", "*", "\n", "'", '"']):
        return f'"{value}"'
    return value


def yaml_array(values: Any) -> str:
    if not values:
        return "[]"
    if not isinstance(values, list):
        values = [values]
    return "\n" + "\n".join(f"  - {yaml_string(v)}" for v in values if str(v).strip())


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def body_from_summary(kind: str, item: dict[str, Any]) -> str:
    summary = str(item.get("summary") or item.get("description") or item.get("excerpt") or "").strip()
    source_label = "Official source" if kind == "event" else "Source"
    if kind == "event":
        audience = str(item.get("audience") or "").strip()
        return (
            "## What is it?\n\n"
            f"{summary}\n\n"
            "## Who is it for?\n\n"
            f"{audience or 'Anyone looking for a local event in Lee County.'}\n\n"
            f"## {source_label}\n\n"
            f"Use the {item.get('sourceName') or 'linked'} page for current details, tickets, policies, and schedule changes.\n"
        )
    return (
        "## What happened?\n\n"
        f"{summary}\n\n"
        "## Why it matters\n\n"
        "This is a local update worth knowing for residents, visitors, or nearby businesses.\n\n"
        f"## {source_label}\n\n"
        f"Use the {item.get('sourceName') or 'linked'} source for the latest details.\n"
    )


def frontmatter(kind: str, item: dict[str, Any], slug: str, cover: str) -> str:
    title = item.get("title", "Untitled")
    date = item.get("date") or now_iso()
    category = item.get("category") or (item.get("city") or "Local News")
    tags = item.get("tags") or [category]
    excerpt = item.get("excerpt") or item.get("summary") or "Brief LeeScoop local update."
    source_type = item.get("sourceType") or ("official" if kind == "event" else "news")
    lines = [
        "---",
        f"title: {yaml_string(title)}",
        f"date: {date}",
        "draft: false",
        "featured: false",
        "pinned: false",
        "ticker: false",
        f"category: {yaml_string(category)}",
        f"tags:{yaml_array(tags)}",
        f"excerpt: {yaml_string(excerpt)}",
        "author: LeeScoop",
        f"contentKind: {kind}",
        f"sourceType: {source_type}",
        "contentType: brief",
    ]
    if kind == "event":
        lines.extend([
            f"eventDate: {item.get('eventDate', '')}",
            f"eventTime: {yaml_string(item.get('eventTime', ''))}",
            f"city: {yaml_string(item.get('city', ''))}",
            f"location: {yaml_string(item.get('location') or item.get('city') or '')}",
            f"venue: {yaml_string(item.get('venue', ''))}",
            f"address: {yaml_string(item.get('address', ''))}",
            f"audience: {yaml_string(item.get('audience', ''))}",
            f"cost: {yaml_string(item.get('cost', ''))}",
        ])
    else:
        lines.extend([
            f"city: {yaml_string(item.get('city', ''))}",
            f"location: {yaml_string(item.get('location') or item.get('city') or '')}",
        ])
        if item.get("verificationUrl"):
            lines.append(f"verificationUrl: {yaml_string(item.get('verificationUrl'))}")
        if item.get("sourceImageUrl"):
            lines.append(f"sourceImageUrl: {yaml_string(item.get('sourceImageUrl'))}")
    lines.extend([
        f"sourceName: {yaml_string(item.get('sourceName', ''))}",
        f"sourceUrl: {yaml_string(item.get('sourceUrl', ''))}",
        f"coverImage: {yaml_string(cover)}",
        "---",
        "",
    ])
    return "\n".join(lines)


def validate_item(kind: str, item: dict[str, Any], max_news_age_days: int = 21) -> list[str]:
    required = ["title", "sourceUrl", "excerpt", "summary"]
    if kind == "event":
        required += ["eventDate", "eventTime", "city", "venue", "category", "sourceName"]
    else:
        required += ["date", "category", "sourceName"]
    problems = [field for field in required if not str(item.get(field, "")).strip()]
    if kind == "news":
        dt = parse_dt(str(item.get("date", "")))
        if dt:
            age = datetime.now(dt.tzinfo or timezone.utc) - dt
            if age > timedelta(days=max_news_age_days):
                problems.append(f"date older than {max_news_age_days} days")
        expired = has_expired_deadline(item)
        if expired:
            problems.append(f"expired deadline/date mentioned: {expired}")
    return problems


def maybe_download_source_image(item: dict[str, Any], slug: str) -> str:
    url = str(item.get("sourceImageUrl") or "").strip()
    if not url:
        return ""
    image_domain = registrable_domain(url)
    allowed_domains = {registrable_domain(str(item.get("sourceUrl", ""))), registrable_domain(str(item.get("verificationUrl", "")))}
    allowed_domains.discard("")
    extra_allowed: set[str] = set()
    source_url = str(item.get("sourceUrl", ""))
    verification_url = str(item.get("verificationUrl", ""))
    combined = f"{source_url} {verification_url}".lower()
    if "winknews.com" in combined:
        extra_allowed.update({"townnews.com", "chicago2.vip.townnews.com"})
    if allowed_domains and image_domain not in allowed_domains and image_domain not in extra_allowed:
        raise ValueError(f"sourceImageUrl domain {image_domain!r} does not match source/verification domain(s): {sorted(allowed_domains | extra_allowed)}")
    ext = Path(urlsplit(url).path).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ext = ".jpg"
    out = COVERS / f"{slug}{ext}"
    if out.exists():
        raise FileExistsError(f"Cover already exists: {out.relative_to(ROOT)}")
    COVERS.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 LeeScoopBot/1.0"})
    with urlopen(req, timeout=45) as response:
        out.write_bytes(response.read())
    return f"/covers/{out.name}"


def check_command(args: argparse.Namespace) -> int:
    data = load_candidates(Path(args.input))
    idx = existing_index()
    report = {"ok": True, "accepted": [], "skipped": [], "invalid": []}
    seen_slugs: set[str] = set()
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    for kind in ["events", "news"]:
        singular = "event" if kind == "events" else "news"
        for item in data[kind]:
            slug = slugify(str(item.get("slug") or item.get("title") or ""))
            item["slug"] = slug
            missing = validate_item(singular, item, max_news_age_days=args.max_news_age_days)
            if missing:
                report["ok"] = False
                report["invalid"].append({"kind": singular, "slug": slug, "reason": f"invalid/missing fields: {', '.join(missing)}"})
                continue
            dup = duplicate_reason(singular, item, idx)
            title_key = norm_text(str(item.get("title", "")))
            url_key = norm_url(str(item.get("sourceUrl", "")))
            if slug in seen_slugs or title_key in seen_titles or url_key in seen_urls:
                dup = dup or "duplicate inside candidate batch"
            if dup:
                report["skipped"].append({"kind": singular, "slug": slug, "title": item.get("title"), "reason": dup})
                continue
            seen_slugs.add(slug); seen_titles.add(title_key); seen_urls.add(url_key)
            report["accepted"].append({"kind": singular, "slug": slug, "title": item.get("title")})
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 2


def write_command(args: argparse.Namespace) -> int:
    data = load_candidates(Path(args.input))
    idx = existing_index()
    report = {"created": [], "skipped": [], "invalid": [], "images": []}
    for kind in ["events", "news"]:
        singular = "event" if kind == "events" else "news"
        max_count = args.max_events if singular == "event" else args.max_news
        written = 0
        for item in data[kind]:
            if written >= max_count:
                continue
            slug = slugify(str(item.get("slug") or item.get("title") or ""))
            item["slug"] = slug
            missing = validate_item(singular, item, max_news_age_days=args.max_news_age_days)
            if missing:
                report["invalid"].append({"kind": singular, "slug": slug, "reason": f"invalid/missing fields: {', '.join(missing)}"})
                continue
            dup = duplicate_reason(singular, item, idx)
            if dup:
                report["skipped"].append({"kind": singular, "slug": slug, "title": item.get("title"), "reason": dup})
                continue
            out = ARTICLES / f"{slug}.md"
            if out.exists():
                report["skipped"].append({"kind": singular, "slug": slug, "title": item.get("title"), "reason": "file exists"})
                continue
            cover = ""
            if singular == "event":
                cover = f"/covers/{slug}.png" if args.set_event_cover else ""
            elif args.download_news_images and item.get("sourceImageUrl"):
                try:
                    cover = maybe_download_source_image(item, slug)
                    report["images"].append({"kind": singular, "slug": slug, "coverImage": cover, "sourceImageUrl": item.get("sourceImageUrl")})
                except Exception as exc:
                    report["images"].append({"kind": singular, "slug": slug, "error": str(exc), "sourceImageUrl": item.get("sourceImageUrl")})
            if args.dry_run:
                report["created"].append({"kind": singular, "slug": slug, "path": str(out.relative_to(ROOT)), "dryRun": True})
            else:
                text = frontmatter(singular, item, slug, cover) + body_from_summary(singular, item) + "\n"
                out.write_text(text, encoding="utf-8")
                report["created"].append({"kind": singular, "slug": slug, "path": str(out.relative_to(ROOT))})
                # Update index to prevent duplicates later in same write run.
                idx = existing_index()
            written += 1
    print(json.dumps(report, indent=2))
    return 0 if not report["invalid"] else 2


def set_featured_command(args: argparse.Namespace) -> int:
    slug = slugify(args.slug)
    target = ARTICLES / f"{slug}.md"
    if not target.exists():
        print(json.dumps({"ok": False, "error": f"article not found: {target.relative_to(ROOT)}"}, indent=2))
        return 2

    changed: list[str] = []
    for path in sorted(ARTICLES.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        desired = "featured: true" if path == target else "featured: false"
        if "\nfeatured: true\n" in text or "\nfeatured: false\n" in text:
            updated = re.sub(r"\nfeatured: (true|false)\n", f"\n{desired}\n", text, count=1)
        else:
            updated = text.replace("\ndraft: false\n", f"\ndraft: false\n{desired}\n", 1)
        if updated != text:
            changed.append(str(path.relative_to(ROOT)))
            if not args.dry_run:
                path.write_text(updated, encoding="utf-8")

    print(json.dumps({"ok": True, "featured": slug, "changed": changed, "dryRun": args.dry_run}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Validate candidates and report duplicates")
    p_check.add_argument("--input", required=True)
    p_check.add_argument("--max-news-age-days", type=int, default=21, help="Reject news older than this many days")
    p_check.set_defaults(func=check_command)

    p_write = sub.add_parser("write", help="Write non-duplicate candidates as markdown")
    p_write.add_argument("--input", required=True)
    p_write.add_argument("--max-events", type=int, default=5)
    p_write.add_argument("--max-news", type=int, default=5)
    p_write.add_argument("--dry-run", action="store_true")
    p_write.add_argument("--set-event-cover", action="store_true", help="Set event coverImage to /covers/<slug>.png; generate image separately")
    p_write.add_argument("--download-news-images", action="store_true", help="Download news sourceImageUrl if supplied")
    p_write.add_argument("--max-news-age-days", type=int, default=21, help="Reject news older than this many days")
    p_write.set_defaults(func=write_command)

    p_featured = sub.add_parser("feature", help="Set exactly one article as homepage featured and clear all others")
    p_featured.add_argument("--slug", required=True, help="Article slug to feature")
    p_featured.add_argument("--dry-run", action="store_true")
    p_featured.set_defaults(func=set_featured_command)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
