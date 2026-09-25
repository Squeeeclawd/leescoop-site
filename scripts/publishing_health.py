#!/usr/bin/env python3
"""Read-only publishing evidence summary. No workflow imports or scheduler inference."""
import argparse
from datetime import datetime, time, timedelta
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def timestamp(value):
    result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timestamp requires timezone')
    return result


def require(condition, message):
    if not condition:
        raise ValueError(message)


def receipt_summary(receipt, checkpoint, ledger, now):
    run, commit = receipt['run'], receipt['commit']
    require(re.fullmatch('[a-zA-Z0-9_-]{1,80}', run), 'invalid run')
    require(re.fullmatch('[0-9a-f]{40}', commit), 'invalid commit')
    checked = timestamp(receipt['checkedAt'])
    require(checked <= now, 'future receipt')
    require(receipt['productionCommit'] == commit and receipt['canonicalOrigin'] == 'https://leescoop.com', 'production identity mismatch')
    require(receipt['verifiedBy'] == 'parent-liveverify', 'missing live verifier')
    proof = receipt['deploymentProof']
    match = re.fullmatch(r'cloudflare-pages:deployment:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12});github-check-run:([1-9][0-9]*)', receipt['deploymentReceipt'])
    require(match is not None, 'missing deployment identity')
    deployment, check = match.groups()
    require(proof['provider'] == 'cloudflare-pages' and proof['deploymentId'] == deployment and str(proof['githubCheckRunId']) == check and proof['headSha'] == commit and proof['conclusion'] == 'success', 'deployment mismatch')
    require(timedelta(0) <= checked - timestamp(proof['completedAt']) <= timedelta(hours=24), 'deployment time mismatch')
    require(proof['detailsUrl'] == f'https://github.com/Squeeeclawd/leescoop-site/runs/{check}' and proof['previewUrl'] == f'https://{deployment.split("-")[0]}.leescoop-site.pages.dev', 'deployment URLs mismatch')
    selected = checkpoint['selected']
    articles = receipt['articles']
    expected = {item['slug']: item for item in selected}
    require(bool(expected) and len(expected) == len(selected) == len(articles) and {a['slug'] for a in articles} == set(expected), 'article set mismatch')
    identities = {digest(item): item for item in selected}
    require(all(isinstance(r, dict) for r in ledger.values()), 'malformed ledger record')
    relevant = {k: r for k, r in ledger.items() if r.get('run') == run}
    records = [r for k, r in relevant.items() if k in identities]
    require({k for k in relevant if k in identities} == set(identities), 'ledger set mismatch')
    require(all(relevant[k].get('slug') == item['slug'] for k, item in identities.items()), 'ledger identity mismatch')
    require(all(r.get('published') is False and r.get('state') in ('rejected_or_reserve', 'rejected') and r.get('slug') not in expected for k, r in relevant.items() if k not in identities), 'unexpected selected or published ledger record')
    require(all(r.get('published') is True and r.get('state') == 'published' and r.get('commit') == commit and r.get('receiptHash') == digest(receipt) for r in records), 'ledger receipt mismatch')
    for article in articles:
        item = expected[article['slug']]
        require(article['url'].rstrip('/') == 'https://leescoop.com/' + item['slug'] and article['coverUrl'] == 'https://leescoop.com' + item['coverImage'], 'canonical URLs mismatch')
        require(article['httpStatus'] == 200 and all(article.get(k) is True for k in ('titleVerified', 'sourceLinkVerified', 'coverHashVerified', 'coverDecoded')), 'incomplete live verification')
        require(article['title'] == item['title'] and article['sourceUrl'].rstrip('/') == item['sourceUrl'].rstrip('/') and article['coverSha256'] == checkpoint['assets'][item['slug']], 'checkpoint evidence mismatch')
    legacy = 'checkpointHash' not in receipt
    require(legacy or receipt['checkpointHash'] == digest(checkpoint), 'checkpoint hash mismatch')
    return {'run': run, 'commit': commit, 'checkedAt': checked.isoformat(), 'contentCount': len(articles), 'contentDates': sorted({item['date'] for item in selected}), 'verification': 'legacy_ledger_hash_matched_checkpoint_unbound' if legacy else 'complete_checkpoint_and_ledger_bound', 'timedUnattendedPublication': 'unproven'}


def discovery_shape(value, state, config):
    """Recognize the observed nested producer format only with a bound source journal."""
    if value is None or value.get('schema') == 'leescoop.discovery.report.v1':
        return value
    run = value.get('run')
    if 'schema' in value or not isinstance(run, dict) or 'sourceAccess' not in value:
        return value
    require(run.get('model') == config['routes']['routine']['model'], 'nested discovery model mismatch')
    access = value['sourceAccess']
    path = Path(access['requestJournal']).resolve()
    require(path.is_relative_to((state / 'source-access' / 'runs').resolve()), 'discovery journal outside state')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == access['requestJournalSha256'], 'discovery journal hash mismatch')
    journal = json.loads(raw)
    require(journal['run'] == run['runId'], 'discovery source run mismatch')
    stamp = timestamp(run['completedAt'])
    require(run['currentDate'] == stamp.astimezone(NY).date().isoformat(), 'discovery date mismatch')
    requests = journal['requests']
    require(len(requests) <= 24, 'discovery request cap exceeded')
    hosts, starts = {}, {}
    for record in requests:
        host = record['host']
        start = record['startedEpoch']
        hosts[host] = hosts.get(host, 0) + 1
        require(hosts[host] <= 3 and (host not in starts or start - starts[host] >= 5), 'discovery host cap/pacing violation')
        require(timestamp(record['fetchedAt']) <= stamp, 'discovery completed before source access')
        starts[host] = start
    return {**value, 'schema': 'leescoop.discovery.report.v1', 'runDate': run['currentDate'],
            'completedAt': run['completedAt'], 'model': run['model'], 'mode': 'discovery_journal_bound_compatibility'}


def health(state, now, config=None):
    if config is None:
        config = json.loads((Path(__file__).resolve().parents[1] / 'docs/workflow/sources.json').read_text())
    now = now.astimezone(NY)
    issues = []
    def load(path):
        try:
            value = json.loads(path.read_text())
            require(isinstance(value, dict), 'expected object')
            return value
        except (OSError, ValueError) as exc:
            issues.append(f'malformed:{path.relative_to(state)}:{exc}')
            return None
    def documents(folder):
        return [(p, load(p)) for p in sorted((state / folder).glob('*.json'))]
    def latest(folder, schema, fields, due, strong=False):
        found = []
        for path, value in documents(folder):
            if not strong:
                try:
                    value = discovery_shape(value, state, config)
                except (ValueError, KeyError, TypeError, OSError) as exc:
                    issues.append(f'invalid_report:{path.name}:{exc}')
                    continue
            if value is None or value.get('schema') != schema:
                if not strong and path.name == now.date().isoformat() + '-discovery-report.json':
                    issues.append(f'invalid_report:{path.name}:unrecognized current discovery format')
                continue
            try:
                stamp = timestamp(next(value[k] for k in fields if k in value))
                require(stamp <= now, 'future report')
                require(value['runDate'] == stamp.astimezone(NY).date().isoformat(), 'runDate mismatch')
                tier = 'review' if strong else 'routine'
                require(value.get('model', value.get('reviewModel')) == config['routes'][tier]['model'], 'report model differs from configured route')
                found.append((stamp, str(path.relative_to(state)), value))
            except (ValueError, KeyError, StopIteration, TypeError) as exc:
                issues.append(f'invalid_report:{path.name}:{exc}')
        deadline = datetime.combine(now.date(), time(*due), NY)
        required = now.date() if now >= deadline else now.date() - timedelta(days=1)
        result = {'dueTime': deadline.isoformat(), 'requiredDate': required.isoformat(), 'latest': None, 'status': 'missing'}
        if found:
            stamp, path, value = max(found, key=lambda x: (x[0], x[1]))
            mode = value.get('mode', 'unspecified')
            result.update(status='current' if stamp.astimezone(NY).date() >= required else 'stale', latest={'path': path, 'timestamp': stamp.isoformat(), 'mode': mode, 'model': value.get('model', value.get('reviewModel'))})
            if strong and ('read_only' in mode or 'preview' in mode or bool(value.get('readOnlySwitch')) or value.get('summary', {}).get('publicationBlockedBy') == 'READ_ONLY_REVIEW_TEST'):
                issues.append('review_preview_not_publication')
        if result['status'] != 'current':
            issues.append(('review' if strong else 'discovery') + ':' + result['status'])
        return result
    require(state.is_dir(), 'state directory missing')
    discovery = latest('discovery', 'leescoop.discovery.report.v1', ('completedAt', 'computedAt'), (6, 15))
    review = latest('reports', 'leescoop.review.report.v1', ('completedAt', 'reviewedAt'), (8, 15), True)
    hold = (state / 'READ_ONLY_REVIEW_TEST').exists()
    if hold:
        issues.append('read_only_review_hold')
    active = load(state / 'active-release.json') if (state / 'active-release.json').exists() else None
    if active is not None:
        issues.append('active_release_requires_reconciliation')
    ledger = load(state / 'ledger.json') if (state / 'ledger.json').exists() else {}
    valid = []
    for path, receipt in documents('receipts'):
        try:
            require(receipt is not None, 'unreadable receipt')
            require(receipt['run'] == path.stem, 'receipt filename mismatch')
            checkpoint = load(state / 'checkpoints' / path.name)
            valid.append(receipt_summary(receipt, checkpoint, ledger, now))
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            issues.append(f'invalid_receipt:{path.name}:{exc}')
    finalized = {r['run'] for r in valid}
    noops = set()
    for path, value in documents('no-ops'):
        try:
            checkpoint = load(state / 'checkpoints' / path.name)
            require(value['run'] == path.stem and value['status'] == 'no_op' and checkpoint['selected'] == [] and value['inputHash'] == checkpoint['inputHash'] and timestamp(value['completedAt']) <= now, 'invalid no-op')
            noops.add(path.stem)
        except (ValueError, KeyError, TypeError) as exc:
            issues.append(f'invalid_noop:{path.name}:{exc}')
    pending = []
    for path, value in documents('runs'):
        if value is not None and path.stem not in finalized | noops and value.get('status') != 'aborted':
            pending.append({'run': path.stem, 'status': value.get('status', 'unknown')})
    if pending:
        issues.append('unfinalized_releases')
    if ledger is not None:
        for record in ledger.values():
            if not isinstance(record, dict) or (record.get('published') is True and record.get('run') not in finalized):
                issues.append('unmatched_published_ledger_record')
    valid.sort(key=lambda r: (timestamp(r['checkedAt']), r['run']))
    return {'schema': 'leescoop.publishing.health.v1', 'checkedAt': now.isoformat(), 'status': 'action_required' if issues else 'no_actionable_file_findings', 'schedulerState': 'not_inspected', 'timedUnattendedPublication': 'unproven', 'discovery': discovery, 'strongReview': review, 'readOnlyReviewHold': hold, 'activeLease': active, 'pendingReleases': pending, 'finalizedContentCount': sum(r['contentCount'] for r in valid), 'finalizedContentDates': sorted({d for r in valid for d in r['contentDates']}), 'latestPublishedReceipt': valid[-1] if valid else None, 'validNoOpRuns': sorted(noops), 'issues': sorted(set(issues))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path(__file__).resolve().parents[1] / 'docs/workflow/sources.json')
    parser.add_argument('--state', required=True, type=Path)
    parser.add_argument('--now', help='Timezone-aware ISO time; defaults to current time')
    args = parser.parse_args()
    try:
        result = health(args.state, timestamp(args.now) if args.now else datetime.now(NY), json.loads(args.config.read_text()))
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        result = {'status': 'action_required', 'schedulerState': 'not_inspected', 'timedUnattendedPublication': 'unproven', 'issues': [f'invalid_state:{exc}']}
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return 1 if result['issues'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
