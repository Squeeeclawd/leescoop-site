#!/usr/bin/env python3
"""Deterministic LeeScoop release workflow; it never invokes an LLM or fetches sources."""
from __future__ import annotations

import argparse
import calendar
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True
import leescoop_posts as posts

ROOT = Path(__file__).resolve().parents[1]
NY = ZoneInfo("America/New_York")
RUN_RE = re.compile(r"[a-zA-Z0-9_-]{1,80}")
CF_DEPLOYMENT_RECEIPT_RE = re.compile(
    r"cloudflare-pages:deployment:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12});github-check-run:([1-9][0-9]*)"
)
QUALITY_COMMANDS = (
    (sys.executable, "-m", "unittest", "discover", "-s", "scripts", "-p", "test_*.py"),
    ("node", "scripts/test_event_dates.mjs"),
    ("node", "scripts/test_event_discovery.mjs"),
    ("node", "scripts/test_homepage_date_labels.mjs"),
    ("node", "scripts/test_homepage_today_filters.mjs"),
    ("npm", "run", "quality"),
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    """Atomic durable JSON replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


@contextmanager
def lock(state):
    state.mkdir(parents=True, exist_ok=True)
    with (state / "workflow.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("another workflow process owns the state lock") from None
        yield


def load_json(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def workflow_status(state):
    """Report final receipts as authoritative over stale pre-finalize attempt files."""
    ledger_file = state / "ledger.json"
    ledger = load_json(ledger_file) if ledger_file.exists() else {}
    runs = []
    for path in sorted((state / "runs").glob("*.json")):
        report = load_json(path)
        run = report.get("run") or path.stem
        final_file = state / "receipts" / f"{run}.json"
        records = [record for record in ledger.values() if record.get("run") == run]
        if final_file.exists() and records:
            receipt = load_json(final_file)
            receipt_hash = digest(receipt)
            if all(
                record.get("published") is True
                and record.get("state") == "published"
                and record.get("commit") == receipt.get("commit")
                and record.get("receiptHash") == receipt_hash
                for record in records
            ):
                prior_status = report.get("status")
                prior_error = report.pop("error", None)
                report = {
                    **report,
                    "status": "published",
                    "commit": receipt.get("commit"),
                    "receiptHash": receipt_hash,
                }
                if prior_status != "published":
                    report["reconciledFromStatus"] = prior_status
                if prior_error:
                    report["priorError"] = prior_error
        runs.append(report)
    return {
        "active": load_json(active_path(state)) if active_path(state).exists() else None,
        "runs": runs,
    }


def timestamp(value):
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp requires explicit UTC offset")
    return dt


def parse_event_value(value, *, end=False):
    """Date-only event values are Lee County civil days; datetimes require offsets."""
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        day = date.fromisoformat(text)
        return datetime.combine(day, time.max if end else time.min, NY)
    return timestamp(text)


def event_cutoff(item):
    if item.get("eventEndDate"):
        return parse_event_value(item["eventEndDate"], end=True)
    raw_start = str(item["eventDate"]).strip()
    start = parse_event_value(raw_start)
    # A date-only value carries day precision, so it remains active through that Lee County day.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_start):
        return datetime.combine(start.date(), time.max, NY)
    text = item.get("eventTime", "")
    clocks = re.findall(r"(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)", text, re.I)
    if re.search(r"\d(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)\s*[-–—]\s*\d", text, re.I) and len(clocks) == 2:
        hour, minute, period = clocks[-1]
        hour, minute = int(hour), int(minute or 0)
        if 1 <= hour <= 12 and 0 <= minute <= 59:
            hour = hour % 12 + (12 if period.lower().startswith("p") else 0)
            cutoff = datetime.combine(start.astimezone(NY).date(), time(hour, minute), NY)
            if cutoff < start:
                cutoff += timedelta(days=1)
            return cutoff
    return datetime.combine(start.astimezone(NY).date(), time.max, NY)


def public_https_url(value, label="URL"):
    parsed = urlsplit(str(value).strip())
    host = (parsed.hostname or "").rstrip(".").lower()
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        raise ValueError(f"{label} must be public HTTPS without credentials")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError(f"{label} must not target a private/local host")
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        address = None
    if address and not address.is_global:
        raise ValueError(f"{label} must not target a private/local address")
    return parsed


def registered_host(value):
    host = (public_https_url(value).hostname or "").lower()
    labels = host.split(".")
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def source_entry(item, config):
    source_id = item.get("sourceId")
    matches = [entry for entry in config["sources"] if entry["id"] == source_id]
    if len(matches) != 1:
        raise ValueError("sourceId must identify one configured bounded source")
    source = matches[0]
    candidate_host = registered_host(item["sourceUrl"])
    allowed = {registered_host(source["url"])}
    allowed.update(source.get("articleHosts", []))
    if candidate_host not in allowed:
        raise ValueError("sourceUrl host is outside the configured source registry")
    return source


def route(config, tier, now):
    entry = config["routes"][tier]
    if not entry.get("model") or entry.get("auth") != "oauth" or not entry.get("evidence"):
        raise ValueError(f"{tier} OAuth route not verified")
    if not (timestamp(entry["verifiedAt"]) <= now < timestamp(entry["expiresAt"])):
        raise ValueError(f"{tier} route evidence expired or future-dated")
    if not entry.get("successfulInferenceReceipt"):
        raise ValueError(f"{tier} route lacks a successful inference receipt")
    if tier == "image" and (
        entry["model"] != "openai/gpt-image-2"
        or entry.get("directOverrideAbsent") is not True
        or entry.get("mustSpecifyExactModel") is not True
        or entry.get("liveGenerationTested") is not True
    ):
        raise ValueError("image route requires live exact-model Codex OAuth proof without direct override")
    return entry["model"]


def route_evidence(data, config, tier, now):
    model = route(config, tier, now)
    evidence = data.get("workflowEvidence", {}).get(tier)
    if not isinstance(evidence, dict) or evidence.get("model") != model or not evidence.get("receipt"):
        raise ValueError(f"candidate input lacks matching {tier} job receipt")
    completed = timestamp(evidence.get("completedAt"))
    if not now - timedelta(hours=24) <= completed <= now:
        raise ValueError(f"{tier} job receipt is stale or future-dated")
    return evidence


def plan(config, day):
    sources = [s for s in config["sources"] if s["lane"] != "nearby" or config["nearbyEnabled"]]
    anchors = [s for s in sources if s.get("anchor")]
    rotating = sorted((s for s in sources if not s.get("anchor")), key=lambda s: s["id"])
    offset = day.toordinal() * config["rotationSize"] % len(rotating)
    selected = anchors + (rotating + rotating)[offset:offset + config["rotationSize"]]
    return {
        "date": str(day), "sources": selected, "limits": config["network"],
        "windowsDays": [0, 14, 45, 180], "goals": config["goals"],
        "queries": [f"{city} public events this weekend {day:%B %Y}" for city in config["cities"]],
        "fetchMode": "agent_tools_only", "automaticFetchAdapter": False,
    }


def verify_event_extraction(item, now):
    evidence = item.get("eventVerification")
    required = ("eventPageUrl", "observedTitle", "observedDateText", "observedStart", "accessedAt", "receipt")
    if not isinstance(evidence, dict) or any(not isinstance(evidence.get(key), str) or not evidence[key].strip() for key in required):
        raise ValueError("event requires actual title/date extraction evidence")
    event_page = public_https_url(evidence["eventPageUrl"], "event evidence URL")
    candidate_hosts = {public_https_url(item["sourceUrl"]).hostname}
    if item.get("verificationUrl"):
        candidate_hosts.add(public_https_url(item["verificationUrl"]).hostname)
    if event_page.hostname not in candidate_hosts:
        raise ValueError("event evidence URL host differs from source/verification host")
    accessed = timestamp(evidence["accessedAt"])
    if not now - timedelta(hours=24) <= accessed <= now:
        raise ValueError("event extraction evidence is stale or future-dated")
    observed = parse_event_value(evidence["observedStart"])
    claimed = parse_event_value(item["eventDate"])
    observed_day = observed.astimezone(NY).date()
    claimed_day = claimed.astimezone(NY).date()
    if observed_day != claimed_day:
        raise ValueError("observed event date does not match claimed eventDate")
    date_text = evidence["observedDateText"].lower()
    month_tokens = {calendar.month_name[claimed_day.month].lower(), calendar.month_abbr[claimed_day.month].lower()}
    if not re.search(rf"(?<!\d)0?{claimed_day.day}(?!\d)", date_text) or not any(token in date_text for token in month_tokens):
        raise ValueError("observedDateText does not contain the claimed calendar date")
    if item.get("eventEndDate"):
        if not evidence.get("observedEnd"):
            raise ValueError("multi-day event requires observedEnd evidence")
        observed_end = parse_event_value(evidence["observedEnd"], end=True).astimezone(NY).date()
        claimed_end = parse_event_value(item["eventEndDate"], end=True).astimezone(NY).date()
        if observed_end != claimed_end:
            raise ValueError("observed event end does not match claimed eventEndDate")
    title_words = set(posts.norm_text(item["title"]).split()) - {"the", "a", "an", "in", "at", "to", "and", "for", "of"}
    observed_words = set(posts.norm_text(evidence["observedTitle"]).split())
    if not title_words or len(title_words & observed_words) < min(2, len(title_words)):
        raise ValueError("observed event title does not identify the candidate")
    return evidence


def validate(item, config, now):
    if not isinstance(item, dict):
        raise ValueError("candidate must be an object")
    kind = item.get("kind")
    if kind not in ("event", "news"):
        raise ValueError("kind must be event or news")
    required = ["slug", "title", "sourceId", "sourceUrl", "sourceName", "city", "category", "excerpt", "summary", "date", "evidence"]
    if kind == "event":
        required += ["eventDate", "eventTime", "venue", "cost", "eventType", "organizer"]
    if any(not isinstance(item.get(key), str) or not item[key].strip() for key in required):
        raise ValueError("missing required string fields")
    if posts.slugify(item["slug"]) != item["slug"]:
        raise ValueError("unsafe slug")
    public_https_url(item["sourceUrl"], "source URL")
    if item.get("verificationUrl"):
        public_https_url(item["verificationUrl"], "verification URL")
    source_entry(item, config)
    if item.get("verified") is not True or item.get("reviewed") is not True:
        raise ValueError("requires source verification and strong editorial review")
    checked = timestamp(item["verifiedAt"])
    if not now - timedelta(hours=24) <= checked <= now:
        raise ValueError("source verification must be within 24 hours")
    published = timestamp(item["date"])
    if published > now or (kind == "news" and now - published > timedelta(days=21)):
        raise ValueError("invalid publication date/freshness")
    if len(item["summary"].split()) > (80 if kind == "news" else 140):
        raise ValueError("brief exceeds word budget")
    if item["city"] not in config["cities"]:
        if not (config["nearbyEnabled"] and item["city"] in config["nearbyCities"] and item.get("coverageLabel") == "Nearby Southwest Florida" and item.get("exceptionReason")):
            raise ValueError("outside Lee County; exceptional nearby lane not approved/labeled")
    if kind == "event":
        if item.get("status") != "scheduled":
            raise ValueError("event not confirmed scheduled")
        verify_event_extraction(item, now)
        start = parse_event_value(item["eventDate"])
        cutoff = event_cutoff(item)
        if cutoff < start or cutoff < now:
            raise ValueError("event expired or reversed date range")
        if start > now + timedelta(days=180) and not item.get("marqueeReason"):
            raise ValueError("ordinary event beyond 180 days")
    elif posts.has_expired_deadline(item, now):
        raise ValueError("expired news deadline")
    if type(item.get("score")) is not int or not 9 <= item["score"] <= 14:
        raise ValueError("quality score must be 9..14; never fill quotas")


def keys(item):
    values = ["slug:" + item["slug"], "title:" + posts.norm_text(item["title"]), "url:" + posts.norm_url(item["sourceUrl"])]
    if item["kind"] == "event":
        values.append("event:" + posts.event_start_key(item["eventDate"]) + ":" + posts.norm_text(item["venue"]))
    return values


def tracked_pristine(path, root):
    rel = str(path.relative_to(root))
    shown = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=root, capture_output=True)
    return shown.returncode == 0 and hashlib.sha256(shown.stdout).hexdigest() == file_hash(path)


def cover(item, root, config, now):
    value = item.get("coverImage", "")
    if not re.fullmatch(r"/covers/[a-z0-9][a-z0-9._-]*", value):
        raise ValueError("cover missing or unsafe path")
    path = root / "public" / value.lstrip("/")
    if path.is_symlink() or not path.is_file():
        raise ValueError("cover incomplete/missing")
    from PIL import Image
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        if item["kind"] == "event" and (image.format != "PNG" or image.size != (1216, 704)):
            raise ValueError("event cover must decode as 1216x704 PNG")
    origin = item.get("coverOrigin")
    if item["kind"] == "event":
        if origin == "generated":
            route(config, "image", now)
            if not item.get("imageTaskId") or not item.get("imageEvidence"):
                raise ValueError("generated event cover needs completed OAuth task evidence")
        elif origin == "existing":
            if item.get("coverReviewed") is not True or not item.get("coverPreservationEvidence") or not tracked_pristine(path, root):
                raise ValueError("existing event cover must be reviewed, evidenced, and unchanged from HEAD")
        else:
            raise ValueError("new event covers must be generatedOAuth; only reviewed existing covers may be preserved")
    else:
        if origin == "generated":
            raise ValueError("news AI art disabled by default")
        if origin == "existing":
            if item.get("coverReviewed") is not True or not item.get("coverPreservationEvidence") or not tracked_pristine(path, root):
                raise ValueError("existing news cover must be reviewed, evidenced, and unchanged from HEAD")
        elif origin == "source":
            source_url = item.get("sourceImageUrl")
            if not source_url or not item.get("sourceImageAttribution") or not item.get("sourceImageRightsEvidence"):
                raise ValueError("news source image requires URL, attribution, and rights/access evidence")
            image_host = registered_host(source_url)
            source = source_entry(item, config)
            allowed = {registered_host(item["sourceUrl"]), registered_host(source["url"])}
            allowed.update(source.get("imageHosts", []))
            if image_host not in allowed:
                raise ValueError("news source image host is outside attributable source policy")
        else:
            raise ValueError("news cover must be attributable source or reviewed existing")
    return file_hash(path)


def evaluate(items, config, now, root, ledger):
    if not isinstance(items, list):
        raise ValueError("items must be an array")
    accepted, rejected, seen = [], [], set()
    index = posts.existing_index(root / "src/content/articles")
    for item in items:
        try:
            validate(item, config, now)
            identity = keys(item)
            duplicate = posts.duplicate_reason(item["kind"], item, index)
            if duplicate or any(key in seen for key in identity):
                raise ValueError(duplicate or "duplicate inside batch")
            if any(set(identity) & set(value["keys"]) for value in ledger.values() if value.get("published")):
                raise ValueError("already published in ledger")
            seen.update(identity)
            accepted.append(item)
        except (ValueError, KeyError, TypeError) as exc:
            rejected.append({"slug": item.get("slug") if isinstance(item, dict) else None, "reason": str(exc)})
    accepted.sort(key=lambda item: (item["kind"] != "event", 0 if item["kind"] == "event" and parse_event_value(item["eventDate"]) <= now + timedelta(days=14) else 1, -item["score"], item["slug"]))
    selected, counts, organizers = [], {"event": 0, "news": 0}, set()
    for item in accepted:
        kind = item["kind"]
        organizer = posts.norm_text(item.get("organizer", ""))
        if counts[kind] >= config["goals"][kind] or (kind == "event" and organizer in organizers):
            rejected.append({"slug": item["slug"], "reason": "reserve: cap/organizer diversity"})
            continue
        selected.append(item)
        counts[kind] += 1
        if kind == "event":
            organizers.add(organizer)
    assets = {item["slug"]: cover(item, root, config, now) for item in selected}
    return selected, rejected, assets


def checkpoint_value(input_hash, selected, assets, routes):
    return {"inputHash": input_hash, "selected": selected, "assets": assets, "routes": routes}


def run_path(state, run):
    return state / "runs" / f"{run}.json"


def active_path(state):
    return state / "active-release.json"


def acquire_release(state, run, input_hash, head):
    path = active_path(state)
    active = load_json(path) if path.exists() else None
    expected = {"run": run, "inputHash": input_hash, "releaseHead": head}
    if active:
        if any(active.get(key) != value for key, value in expected.items()):
            raise ValueError(f"release lease held by {active.get('run')}")
        return active
    active = {**expected, "status": "preparing", "startedAt": datetime.now(NY).isoformat()}
    save(path, active)
    return active


def require_release(state, run, input_hash=None):
    path = active_path(state)
    if not path.exists():
        raise ValueError("no active release lease; run prepare first")
    active = load_json(path)
    if active.get("run") != run or (input_hash and active.get("inputHash") != input_hash):
        raise ValueError("active release lease does not match run/input")
    return active


def git(root, *args, check=True):
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True)
    if check and result.returncode:
        raise ValueError((result.stderr or result.stdout or "git command failed").strip())
    return result.stdout.strip()


def release_head(root):
    return git(root, "rev-parse", "HEAD")


def status_paths(root):
    raw = subprocess.run(["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=root, capture_output=True, check=True).stdout
    entries, paths, index = raw.split(b"\0"), set(), 0
    while index < len(entries) and entries[index]:
        entry = entries[index]
        code, path = entry[:2], entry[3:].decode()
        paths.add(path)
        if code[:1] in (b"R", b"C"):
            index += 1
            if index < len(entries) and entries[index]:
                paths.add(entries[index].decode())
        index += 1
    return paths


def selected_paths(checkpoint):
    articles = {f"src/content/articles/{item['slug']}.md" for item in checkpoint["selected"]}
    covers = {"public/" + item["coverImage"].lstrip("/") for item in checkpoint["selected"]}
    return articles, covers


def verify_checkpoint_assets(checkpoint, root):
    for item in checkpoint["selected"]:
        path = root / "public" / item["coverImage"].lstrip("/")
        expected = checkpoint["assets"].get(item["slug"])
        if path.is_symlink() or not path.is_file() or file_hash(path) != expected:
            raise ValueError(f"cover changed after checkpoint: {item['slug']}")


def materialized_item(item):
    value = dict(item)
    if value["kind"] == "event":
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value["eventDate"])):
            day = date.fromisoformat(value["eventDate"])
            value["eventDate"] = datetime.combine(day, time(12), NY).isoformat()
        if value.get("eventEndDate") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value["eventEndDate"])):
            day = date.fromisoformat(value["eventEndDate"])
            value["eventEndDate"] = datetime.combine(day, time(23, 59, 59), NY).isoformat()
    return value


def render_articles(checkpoint):
    rendered = {}
    for original in checkpoint["selected"]:
        item = materialized_item(original)
        slug = item["slug"]
        text = posts.frontmatter(item["kind"], item, slug, item["coverImage"]) + posts.body_from_summary(item["kind"], item).rstrip() + "\n"
        rel = f"src/content/articles/{slug}.md"
        rendered[rel] = {"sha256": hashlib.sha256(text.encode()).hexdigest(), "content": text}
    return rendered


def exclusive_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def prepare_or_gate(args, config, now, command):
    data = load_json(args.input)
    fingerprint = digest(data)
    routine = route_evidence(data, config, "routine", now)
    review = route_evidence(data, config, "review", now)
    report_file = run_path(args.state, args.run)
    previous = load_json(report_file) if report_file.exists() else {}
    if previous.get("inputHash") not in (None, fingerprint):
        raise ValueError("run input changed; use a new run id")
    head = release_head(ROOT)
    active = acquire_release(args.state, args.run, fingerprint, head)
    if active["releaseHead"] != head:
        raise ValueError("release checkout HEAD changed during active release")
    ledger_file = args.state / "ledger.json"
    ledger = load_json(ledger_file) if ledger_file.exists() else {}
    selected, rejected, assets = evaluate(data["items"], config, now, ROOT, ledger)
    routes = {"routine": routine, "review": review}
    checkpoint = checkpoint_value(fingerprint, selected, assets, routes)
    checkpoint_file = args.state / "checkpoints" / f"{args.run}.json"
    if command == "prepare":
        if checkpoint_file.exists() and load_json(checkpoint_file) != checkpoint:
            raise ValueError("existing checkpoint differs; use a new run id")
        save(checkpoint_file, checkpoint)
        for item in data["items"]:
            if isinstance(item, dict) and item.get("slug"):
                key = digest(item)
                prior = ledger.get(key, {})
                ledger[key] = {**prior, "slug": item["slug"], "keys": keys(item) if item in selected else [], "run": args.run, "published": prior.get("published", False), "state": "selected" if item in selected else "rejected_or_reserve"}
        save(ledger_file, ledger)
    else:
        if not checkpoint_file.exists() or load_json(checkpoint_file) != checkpoint:
            raise ValueError("checkpoint/input/assets/routes changed; prepare again with a new run id")
        if selected:
            active["checkpointHash"] = digest(checkpoint)
            active["status"] = "gated"
            save(active_path(args.state), active)
        else:
            save(args.state / "no-ops" / f"{args.run}.json", {**active, "status": "no_op", "completedAt": now.isoformat()})
            active_path(args.state).unlink()
    report = {
        "run": args.run, "status": "ready" if selected else "no_op", "stage": command,
        "at": now.isoformat(), "inputHash": fingerprint, "checkpointHash": digest(checkpoint),
        "selected": [item["slug"] for item in selected], "rejected": rejected, "assets": assets,
        "attempt": previous.get("attempt", 0) + 1,
    }
    save(report_file, report)
    return report


def bound_checkpoint(args, active):
    checkpoint = load_json(args.state / "checkpoints" / f"{args.run}.json")
    if digest(checkpoint) != active.get("checkpointHash"):
        raise ValueError("checkpoint changed after gate")
    for item in checkpoint["selected"]:
        path = args.release_root / "public" / item["coverImage"].lstrip("/")
        if path.is_symlink() or file_hash(path) != checkpoint["assets"][item["slug"]]:
            raise ValueError("cover changed after gate")
    return checkpoint


def verify_materialization(args, active):
    checkpoint = bound_checkpoint(args, active)
    manifest = load_json(args.state / "materializations" / f"{args.run}.json")
    expected = {path: value["sha256"] for path, value in render_articles(checkpoint).items()}
    if manifest["checkpointHash"] != digest(checkpoint) or manifest["files"] != expected:
        raise ValueError("materialization journal changed")
    for rel, expected_hash in expected.items():
        path = args.release_root / rel
        if path.is_symlink() or file_hash(path) != expected_hash:
            raise ValueError("article changed after materialization")
    return checkpoint, manifest


def materialize(args):
    data = load_json(args.input)
    fingerprint = digest(data)
    active = require_release(args.state, args.run, fingerprint)
    if active.get("status") not in ("gated", "materialized"):
        raise ValueError("materialization requires a successful gate")
    checkpoint = bound_checkpoint(args, active)
    if checkpoint["inputHash"] != fingerprint:
        raise ValueError("input no longer matches checkpoint")
    if release_head(args.release_root) != active["releaseHead"]:
        raise ValueError("release checkout HEAD changed since prepare")
    verify_checkpoint_assets(checkpoint, args.release_root)
    articles, covers = selected_paths(checkpoint)
    dirty = status_paths(args.release_root)
    if not dirty <= covers | articles:
        raise ValueError(f"unrelated dirty paths in release checkout: {sorted(dirty - covers - articles)}")
    rendered = render_articles(checkpoint)
    manifest_file = args.state / "materializations" / f"{args.run}.json"
    expected = {path: value["sha256"] for path, value in rendered.items()}
    manifest = load_json(manifest_file) if manifest_file.exists() else None
    identity = {"run": args.run, "inputHash": fingerprint, "checkpointHash": digest(checkpoint), "releaseHead": active["releaseHead"], "files": expected}
    if manifest and any(manifest.get(key) != value for key, value in identity.items()):
        raise ValueError("materialization journal differs from checkpoint")
    if args.dry_run:
        return {**identity, "status": "dry_run", "covers": sorted(covers)}
    if not manifest:
        if any((args.release_root / rel).exists() for rel in rendered):
            raise ValueError("refusing to adopt existing file without journal")
        manifest = {**identity, "status": "writing"}
        save(manifest_file, manifest)
    for rel, value in rendered.items():
        target = args.release_root / rel
        if target.exists():
            if target.is_symlink() or file_hash(target) != value["sha256"]:
                raise ValueError(f"refusing to overwrite existing file: {rel}")
        else:
            exclusive_write(target, value["content"])
    if any(file_hash(args.release_root / rel) != expected_hash for rel, expected_hash in expected.items()):
        raise ValueError("materialized file hash verification failed")
    manifest["status"] = "materialized"
    manifest["completedAt"] = datetime.now(NY).isoformat()
    save(manifest_file, manifest)
    active["status"] = "materialized"
    save(active_path(args.state), active)
    return manifest


def quality(args):
    active = require_release(args.state, args.run)
    if active.get("status") not in ("materialized", "quality_passed"):
        raise ValueError("quality requires completed materialization")
    manifest = load_json(args.state / "materializations" / f"{args.run}.json")
    checkpoint = load_json(args.state / "checkpoints" / f"{args.run}.json")
    if release_head(args.release_root) != active["releaseHead"]:
        raise ValueError("release checkout HEAD changed before quality")
    verify_checkpoint_assets(checkpoint, args.release_root)
    allowed = set(manifest["files"])
    _, covers = selected_paths(checkpoint)
    dirty = status_paths(args.release_root)
    if not dirty <= allowed | covers:
        raise ValueError("unrelated dirty paths appeared before quality")
    log_dir = args.state / "logs" / args.run
    log_dir.mkdir(parents=True, exist_ok=True)
    receipts = []
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "MALLOC_ARENA_MAX": "2", "UV_THREADPOOL_SIZE": "2", "NODE_OPTIONS": "--max-old-space-size=2048"}
    for index, command in enumerate(QUALITY_COMMANDS, 1):
        result = subprocess.run(command, cwd=args.release_root, text=True, capture_output=True, env=env)
        log = log_dir / f"{index:02d}.log"
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
        receipts.append({"command": list(command), "exitCode": result.returncode, "log": str(log), "logSha256": file_hash(log)})
        if result.returncode:
            raise ValueError(f"quality command failed: {' '.join(command)}; see {log}")
    verify_materialization(args, active)
    receipt = {"run": args.run, "status": "passed", "at": datetime.now(NY).isoformat(), "commands": receipts, "manifestHash": digest(manifest)}
    save(args.state / "quality" / f"{args.run}.json", receipt)
    active["status"] = "quality_passed"
    save(active_path(args.state), active)
    return receipt


def commit_release(args):
    active = require_release(args.state, args.run)
    if active.get("status") not in ("quality_passed", "committed"):
        raise ValueError("commit requires passing fixed quality suite")
    checkpoint, manifest = verify_materialization(args, active)
    if active.get("commit"):
        if git(args.release_root, "rev-parse", "HEAD") != active["commit"]:
            raise ValueError("recorded commit is not checkout HEAD")
        return {"run": args.run, "status": "committed", "commit": active["commit"], "idempotent": True}
    if active.get("commitTree"):
        head = git(args.release_root, "rev-parse", "HEAD")
        if head != active["releaseHead"]:
            parent = git(args.release_root, "rev-parse", "HEAD^")
            tree = git(args.release_root, "rev-parse", "HEAD^{tree}")
            if parent == active["releaseHead"] and tree == active["commitTree"]:
                active.update(status="committed", commit=head)
                save(active_path(args.state), active)
                return {"run": args.run, "status": "committed", "commit": head, "recovered": True}
            raise ValueError("checkout HEAD changed to an unrecognized commit")
    verify_checkpoint_assets(checkpoint, args.release_root)
    _, covers = selected_paths(checkpoint)
    allow = set(manifest["files"]) | covers
    dirty = status_paths(args.release_root)
    if not dirty or not dirty <= allow:
        raise ValueError("commit has no release changes or includes unrelated paths")
    subprocess.run(["git", "add", "--", *sorted(allow)], cwd=args.release_root, check=True)
    staged = set(filter(None, git(args.release_root, "diff", "--cached", "--name-only", "-z").split("\0")))
    if not staged or not staged <= allow or not set(manifest["files"]) <= staged:
        raise ValueError("staged path set does not match release manifest")
    subprocess.run(["git", "diff", "--cached", "--check"], cwd=args.release_root, check=True)
    active["commitTree"] = git(args.release_root, "write-tree")
    save(active_path(args.state), active)
    subprocess.run(["git", "commit", "-m", args.message], cwd=args.release_root, check=True)
    commit = git(args.release_root, "rev-parse", "HEAD")
    active.update(status="committed", commit=commit)
    save(active_path(args.state), active)
    return {"run": args.run, "status": "committed", "commit": commit, "paths": sorted(staged)}


def push_release(args, config):
    active = require_release(args.state, args.run)
    if active.get("status") not in ("committed", "pushed") or not active.get("commit"):
        raise ValueError("push requires a workflow-created commit")
    publication = config["publication"]
    if args.remote != publication["remote"] or args.branch != publication["branch"]:
        raise ValueError("remote/branch differ from attested publication config")
    if active.get("status") == "pushed":
        return {"run": args.run, "status": "pushed", "commit": active["commit"], "published": False, "idempotent": True}
    remote_before = git(args.release_root, "ls-remote", "--heads", args.remote, f"refs/heads/{args.branch}").split()
    if remote_before and remote_before[0] == active["commit"]:
        active["status"] = "pushed"
        save(active_path(args.state), active)
        return {"run": args.run, "status": "pushed", "commit": active["commit"], "published": False, "recovered": True}
    if not remote_before or remote_before[0] != active["releaseHead"]:
        raise ValueError("remote production branch moved since prepare; rebuild from current base")
    subprocess.run(["git", "push", args.remote, f"{active['commit']}:{args.branch}"], cwd=args.release_root, check=True)
    remote_after = git(args.release_root, "ls-remote", "--heads", args.remote, f"refs/heads/{args.branch}").split()
    if not remote_after or remote_after[0] != active["commit"]:
        raise ValueError("remote did not confirm release commit")
    active["status"] = "pushed"
    save(active_path(args.state), active)
    return {"run": args.run, "status": "pushed", "commit": active["commit"], "published": False}


def finalize(args, config):
    receipt = load_json(args.receipt)
    final_file = args.state / "receipts" / f"{args.run}.json"
    if not active_path(args.state).exists() and final_file.exists():
        existing = load_json(final_file)
        if existing == receipt:
            return {"run": args.run, "status": "published", "commit": receipt.get("commit"), "receiptHash": digest(receipt), "idempotent": True}
        raise ValueError("release already finalized with a different receipt")
    active = require_release(args.state, args.run)
    if active.get("status") not in ("pushed", "published") or not active.get("commit"):
        raise ValueError("live verification receipt requires a confirmed push")
    checkpoint = load_json(args.state / "checkpoints" / f"{args.run}.json")
    expected = {item["slug"]: item for item in checkpoint["selected"]}
    if receipt.get("run") != args.run or receipt.get("commit") != active["commit"]:
        raise ValueError("receipt run/commit does not match pushed release")
    if receipt.get("canonicalOrigin") != config["publication"]["canonicalOrigin"] or receipt.get("productionCommit") != active["commit"]:
        raise ValueError("receipt lacks production deployment proof for exact commit")
    checked = timestamp(receipt.get("checkedAt"))
    now = datetime.now(NY)
    if not now - timedelta(hours=24) <= checked <= now + timedelta(minutes=2):
        raise ValueError("live verification receipt is stale or future-dated")
    deployment_match = CF_DEPLOYMENT_RECEIPT_RE.fullmatch(str(receipt.get("deploymentReceipt", "")))
    deployment_proof = receipt.get("deploymentProof")
    if receipt.get("verifiedBy") != "parent-liveverify" or not deployment_match or not isinstance(deployment_proof, dict):
        raise ValueError("receipt lacks parent live-verification evidence")
    deployment_id, check_run_id = deployment_match.groups()
    if (
        deployment_proof.get("provider") != "cloudflare-pages"
        or deployment_proof.get("deploymentId") != deployment_id
        or str(deployment_proof.get("githubCheckRunId")) != check_run_id
        or deployment_proof.get("headSha") != active["commit"]
        or deployment_proof.get("conclusion") != "success"
    ):
        raise ValueError("deployment proof does not identify a successful Cloudflare Pages build of the release commit")
    completed = timestamp(deployment_proof.get("completedAt"))
    if completed > checked or checked - completed > timedelta(hours=24):
        raise ValueError("deployment proof completion time is inconsistent with live verification")
    details_url = public_https_url(deployment_proof.get("detailsUrl"), "deployment details URL")
    preview_url = public_https_url(deployment_proof.get("previewUrl"), "deployment preview URL")
    if (
        details_url.hostname != "github.com"
        or details_url.path != f"/Squeeeclawd/leescoop-site/runs/{check_run_id}"
        or preview_url.hostname != f"{deployment_id.split('-', 1)[0]}.leescoop-site.pages.dev"
    ):
        raise ValueError("deployment proof URLs do not match the Cloudflare Pages deployment")
    articles = receipt.get("articles")
    if not isinstance(articles, list) or {entry.get("slug") for entry in articles if isinstance(entry, dict)} != set(expected):
        raise ValueError("receipt article set differs from checkpoint")
    canonical_host = public_https_url(config["publication"]["canonicalOrigin"], "canonical origin").hostname
    for entry in articles:
        item = expected[entry["slug"]]
        article_url = public_https_url(entry.get("url"), "published article URL")
        cover_url = public_https_url(entry.get("coverUrl"), "published cover URL")
        if article_url.hostname != canonical_host or cover_url.hostname != canonical_host:
            raise ValueError(f"live URLs are outside canonical origin for {entry['slug']}")
        if article_url.path.rstrip('/') != '/' + entry['slug'] or cover_url.path != item['coverImage']:
            raise ValueError(f"live URL paths differ from checkpoint for {entry['slug']}")
        if article_url.query or article_url.fragment or cover_url.query or cover_url.fragment:
            raise ValueError("live proof must use canonical URLs without query or fragment")
        required_true = ("titleVerified", "sourceLinkVerified", "coverHashVerified", "coverDecoded")
        if entry.get("httpStatus") != 200 or any(entry.get(key) is not True for key in required_true):
            raise ValueError(f"incomplete live proof for {entry['slug']}")
        if entry.get("title") != item["title"] or posts.norm_url(entry.get("sourceUrl")) != posts.norm_url(item["sourceUrl"]):
            raise ValueError(f"live title/source mismatch for {entry['slug']}")
        if entry.get("coverSha256") != checkpoint["assets"][entry["slug"]]:
            raise ValueError(f"live cover hash mismatch for {entry['slug']}")
    receipt_hash = digest(receipt)
    if final_file.exists() and digest(load_json(final_file)) != receipt_hash:
        raise ValueError("different final receipt already recorded")
    ledger_file = args.state / "ledger.json"
    ledger = load_json(ledger_file) if ledger_file.exists() else {}
    for record in ledger.values():
        if record.get("run") == args.run and record.get("state") == "selected":
            record.update(published=True, state="published", commit=active["commit"], receiptHash=receipt_hash)
    save(ledger_file, ledger)
    save(final_file, receipt)
    active.update(status="published", receiptHash=receipt_hash)
    save(active_path(args.state), active)
    active_path(args.state).unlink()
    return {"run": args.run, "status": "published", "commit": active["commit"], "receiptHash": receipt_hash}


def abort(args):
    active = require_release(args.state, args.run)
    if active.get("status") in ("committed", "pushed", "published"):
        raise ValueError("cannot abort after commit; reconcile or finalize the release")
    record = {**active, "status": "aborted", "reason": args.reason, "abortedAt": datetime.now(NY).isoformat()}
    save(args.state / "aborted" / f"{args.run}.json", record)
    active_path(args.state).unlink()
    return record


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=ROOT / "docs/workflow/sources.json")
    p.add_argument("--state", type=Path, default=Path("/home/shmee/.openclaw/workspace/state/leescoop-publishing"))
    p.add_argument("--now", help="explicit offset timestamp; testing/replay only")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    sub.add_parser("status")
    route_parser = sub.add_parser("route"); route_parser.add_argument("tier", choices=["routine", "review", "image"])
    for name in ("prepare", "gate"):
        command = sub.add_parser(name); command.add_argument("--run", required=True); command.add_argument("--input", required=True, type=Path)
    materialize_parser = sub.add_parser("materialize"); materialize_parser.add_argument("--run", required=True); materialize_parser.add_argument("--input", required=True, type=Path); materialize_parser.add_argument("--release-root", required=True, type=Path); materialize_parser.add_argument("--dry-run", action="store_true")
    quality_parser = sub.add_parser("quality"); quality_parser.add_argument("--run", required=True); quality_parser.add_argument("--release-root", required=True, type=Path)
    commit_parser = sub.add_parser("commit"); commit_parser.add_argument("--run", required=True); commit_parser.add_argument("--release-root", required=True, type=Path); commit_parser.add_argument("--message", required=True)
    push_parser = sub.add_parser("push"); push_parser.add_argument("--run", required=True); push_parser.add_argument("--release-root", required=True, type=Path); push_parser.add_argument("--remote", default="origin"); push_parser.add_argument("--branch", default="main")
    final_parser = sub.add_parser("finalize"); final_parser.add_argument("--run", required=True); final_parser.add_argument("--receipt", required=True, type=Path)
    abort_parser = sub.add_parser("abort"); abort_parser.add_argument("--run", required=True); abort_parser.add_argument("--reason", required=True)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    now = timestamp(args.now) if args.now else datetime.now(NY)
    try:
        config = load_json(args.config)
        if hasattr(args, "run") and not RUN_RE.fullmatch(args.run):
            raise ValueError("invalid run identifier")
        if hasattr(args, "release_root"):
            args.release_root = args.release_root.resolve()
            if args.release_root != ROOT.resolve():
                raise ValueError("run this workflow script from the isolated release checkout it will modify")
        if args.command == "plan":
            result = plan(config, now.astimezone(NY).date())
        elif args.command == "route":
            result = {"tier": args.tier, "model": route(config, args.tier, now)}
        elif args.command == "status":
            result = workflow_status(args.state)
        else:
            with lock(args.state):
                if args.command in ("prepare", "gate"):
                    result = prepare_or_gate(args, config, now, args.command)
                elif args.command == "materialize":
                    result = materialize(args)
                elif args.command == "quality":
                    result = quality(args)
                elif args.command == "commit":
                    result = commit_release(args)
                elif args.command == "push":
                    result = push_release(args, config)
                elif args.command == "finalize":
                    result = finalize(args, config)
                elif args.command == "abort":
                    result = abort(args)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2 if result.get("status") == "blocked" else 0
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        blocked = {"status": "blocked", "error": str(exc)}
        if hasattr(args, "run"):
            blocked["run"] = args.run
            try:
                prior = load_json(run_path(args.state, args.run)) if run_path(args.state, args.run).exists() else {}
                blocked["attempt"] = prior.get("attempt", 0) + 1
                save(run_path(args.state, args.run), blocked)
            except OSError:
                pass
        print(json.dumps(blocked, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
