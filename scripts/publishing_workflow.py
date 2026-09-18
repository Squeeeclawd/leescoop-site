#!/usr/bin/env python3
"""Offline publishing control plane. Never fetches, invokes models, or publishes."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta
import fcntl
import hashlib
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo
import leescoop_posts as posts

ROOT = Path(__file__).resolve().parents[1]
NY = ZoneInfo('America/New_York')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


@contextmanager
def lock(state):
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'workflow.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('another workflow run owns the lock') from None
        yield


def timestamp(value):
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('timestamp requires explicit UTC offset')
    return dt


def route(config, tier, now):
    entry = config['routes'][tier]
    if not entry.get('model') or entry.get('auth') != 'oauth' or not entry.get('evidence'):
        raise ValueError(f'{tier} OAuth route not verified')
    if not (timestamp(entry['verifiedAt']) <= now < timestamp(entry['expiresAt'])):
        raise ValueError(f'{tier} route evidence expired or future-dated')
    if tier == 'image' and (entry['model'] != 'openai/gpt-image-2' or entry.get('directOverrideAbsent') is not True):
        raise ValueError('image route must prove Codex OAuth without direct override')
    return entry['model']


def plan(config, day):
    sources = [s for s in config['sources'] if s['lane'] != 'nearby' or config['nearbyEnabled']]
    anchors = [s for s in sources if s.get('anchor')]
    rotating = sorted((s for s in sources if not s.get('anchor')), key=lambda s: s['id'])
    offset = day.toordinal() * config['rotationSize'] % len(rotating)
    selected = anchors + (rotating + rotating)[offset:offset + config['rotationSize']]
    return {'date': str(day), 'sources': selected, 'limits': config['network'],
            'windowsDays': [0, 14, 45, 180], 'goals': config['goals'],
            'queries': [f"{city} public events this weekend {day:%B %Y}" for city in config['cities']]}


def validate(item, config, now):
    if not isinstance(item, dict):
        raise ValueError('candidate must be an object')
    kind = item.get('kind')
    if kind not in ('event', 'news'):
        raise ValueError('kind must be event or news')
    required = ['slug', 'title', 'sourceUrl', 'sourceName', 'city', 'category', 'excerpt', 'summary', 'date', 'evidence']
    if kind == 'event':
        required += ['eventDate', 'eventTime', 'venue', 'cost', 'eventType', 'organizer']
    if any(not isinstance(item.get(k), str) or not item[k].strip() for k in required):
        raise ValueError('missing required string fields')
    if posts.slugify(item['slug']) != item['slug']:
        raise ValueError('unsafe slug')
    from urllib.parse import urlsplit
    for key in ('sourceUrl', 'verificationUrl'):
        parsed = urlsplit(item.get(key, item['sourceUrl']))
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('source URL must be public HTTPS without credentials')
    if item.get('verified') is not True or item.get('reviewed') is not True:
        raise ValueError('requires source verification and strong editorial review')
    checked = timestamp(item['verifiedAt'])
    if not now - timedelta(hours=24) <= checked <= now:
        raise ValueError('source verification must be within 24 hours')
    published = timestamp(item['date'])
    if published > now or (kind == 'news' and now - published > timedelta(days=21)):
        raise ValueError('invalid publication date/freshness')
    if len(item['summary'].split()) > (80 if kind == 'news' else 140):
        raise ValueError('brief exceeds word budget')
    if item['city'] not in config['cities']:
        if not (config['nearbyEnabled'] and item['city'] in config['nearbyCities'] and item.get('coverageLabel') == 'Nearby Southwest Florida' and item.get('exceptionReason')):
            raise ValueError('outside Lee County; exceptional nearby lane not approved/labeled')
    if item.get('status') != 'scheduled' and kind == 'event':
        raise ValueError('event not confirmed scheduled')
    if kind == 'event':
        start = timestamp(item['eventDate'])
        end = timestamp(item.get('eventEndDate', item['eventDate']))
        if end < start or end < now:
            raise ValueError('event expired or reversed date range')
        if start > now + timedelta(days=180) and not item.get('marqueeReason'):
            raise ValueError('ordinary event beyond 180 days')
    elif posts.has_expired_deadline(item, now):
        raise ValueError('expired news deadline')
    if type(item.get('score')) is not int or not 9 <= item['score'] <= 14:
        raise ValueError('quality score must be 9..14; never fill quotas')


def keys(item):
    values = ['slug:' + item['slug'], 'title:' + posts.norm_text(item['title']), 'url:' + posts.norm_url(item['sourceUrl'])]
    if item['kind'] == 'event':
        values.append('event:' + posts.event_start_key(item['eventDate']) + ':' + posts.norm_text(item['venue']))
    return values


def cover(item, root, config, now):
    value = item.get('coverImage', '')
    if not re.fullmatch(r'/covers/[a-z0-9][a-z0-9._-]*', value):
        raise ValueError('cover missing or unsafe path')
    path = root / 'public' / value.lstrip('/')
    if path.is_symlink() or not path.is_file():
        raise ValueError('cover incomplete/missing')
    from PIL import Image
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        if item['kind'] == 'event' and (image.format != 'PNG' or image.size != (1216, 704)):
            raise ValueError('event cover must decode as 1216x704 PNG')
    if item.get('coverOrigin') == 'generated':
        route(config, 'image', now)
        if item['kind'] == 'news':
            raise ValueError('news AI art disabled by default')
        if not item.get('imageTaskId') or not item.get('imageEvidence'):
            raise ValueError('generated cover needs completed task and OAuth evidence')
    elif item.get('coverOrigin') == 'existing':
        if not item.get('coverPreservationEvidence'):
            raise ValueError('existing cover needs provenance; not an OAuth bypass')
    elif item.get('coverOrigin') != 'source' or not item.get('sourceImageUrl'):
        raise ValueError('cover provenance missing')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(items, config, now, root, ledger):
    if not isinstance(items, list):
        raise ValueError('items must be an array')
    accepted, rejected, seen = [], [], set()
    index = posts.existing_index()
    for item in items:
        try:
            validate(item, config, now)
            identity = keys(item)
            duplicate = posts.duplicate_reason(item['kind'], item, index)
            if duplicate or any(k in seen for k in identity):
                raise ValueError(duplicate or 'duplicate inside batch')
            if any(set(identity) & set(v['keys']) for v in ledger.values() if v.get('published')):
                raise ValueError('already published in ledger')
            seen.update(identity)
            accepted.append(item)
        except (ValueError, KeyError, TypeError) as exc:
            rejected.append({'slug': item.get('slug') if isinstance(item, dict) else None, 'reason': str(exc)})
    accepted.sort(key=lambda i: (i['kind'] != 'event', 0 if i['kind'] == 'event' and timestamp(i['eventDate']) <= now + timedelta(days=14) else 1, -i['score'], i['slug']))
    selected, counts, venues = [], {'event': 0, 'news': 0}, set()
    for item in accepted:
        kind = item['kind']
        venue = posts.norm_text(item.get('organizer', ''))
        if counts[kind] >= config['goals'][kind] or (kind == 'event' and venue in venues):
            rejected.append({'slug': item['slug'], 'reason': 'reserve: cap/organizer diversity'})
            continue
        selected.append(item)
        counts[kind] += 1
        if kind == 'event':
            venues.add(venue)
    assets = {i['slug']: cover(i, root, config, now) for i in selected}
    return selected, rejected, assets


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, default=ROOT / 'docs/workflow/sources.json')
    p.add_argument('--state', type=Path, default=ROOT / 'tmp/publishing')
    p.add_argument('--now', help='explicit offset timestamp; testing/replay only')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('plan')
    sub.add_parser('status')
    r = sub.add_parser('route'); r.add_argument('tier', choices=['routine', 'review', 'image'])
    for name in ('prepare', 'gate'):
        c = sub.add_parser(name); c.add_argument('--run', required=True); c.add_argument('--input', required=True, type=Path)
    args = p.parse_args(argv)
    now = timestamp(args.now) if args.now else datetime.now(NY)
    try:
        config = json.loads(args.config.read_text())
        if args.command == 'plan':
            result = plan(config, now.astimezone(NY).date())
        elif args.command == 'route':
            result = {'tier': args.tier, 'model': route(config, args.tier, now)}
        elif args.command == 'status':
            result = {'runs': [json.loads(f.read_text()) for f in sorted((args.state / 'runs').glob('*.json'))]}
        else:
            if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', args.run):
                raise ValueError('invalid run identifier')
            with lock(args.state):
                report_path = args.state / 'runs' / (args.run + '.json')
                report = {'run': args.run, 'status': 'running', 'at': now.isoformat(), 'command': args.command}
                previous = json.loads(report_path.read_text()) if report_path.exists() else {}
                if previous.get('inputHash'):
                    report['inputHash'] = previous['inputHash']
                report['attempt'] = previous.get('attempt', 0) + 1
                try:
                    data = json.loads(args.input.read_text())
                    fingerprint = digest(data)
                    if previous.get('inputHash') not in (None, fingerprint):
                        raise ValueError('run input changed; use a new run id')
                    report['inputHash'] = fingerprint
                    save(report_path, report)
                    ledger_path = args.state / 'ledger.json'
                    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
                    selected, rejected, assets = evaluate(data['items'], config, now, ROOT, ledger)
                    if args.command == 'gate':
                        checkpoint = json.loads((args.state / 'checkpoints' / (args.run + '.json')).read_text())
                        if checkpoint != {'inputHash': fingerprint, 'assets': assets, 'selected': selected}:
                            raise ValueError('checkpoint changed; prepare again and rerun quality gates')
                    for item in data['items']:
                        if isinstance(item, dict) and item.get('slug'):
                            ledger[digest(item)] = {'slug': item['slug'], 'keys': keys(item) if item in selected else [], 'run': args.run, 'published': False, 'state': 'selected' if item in selected else 'rejected_or_reserve'}
                    save(ledger_path, ledger)
                    save(args.state / 'checkpoints' / (args.run + '.json'), {'inputHash': fingerprint, 'assets': assets, 'selected': selected})
                    report.update(status='ready' if selected else 'no_op', selected=[i['slug'] for i in selected], rejected=rejected, assets=assets)
                except (ValueError, KeyError, TypeError, OSError, ImportError) as exc:
                    report.update(status='blocked', error=str(exc))
                save(report_path, report)
                result = report
        print(json.dumps(result, indent=2))
        return 2 if result.get('status') == 'blocked' else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
