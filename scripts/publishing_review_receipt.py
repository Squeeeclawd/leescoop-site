#!/usr/bin/env python3
"""Bind an actual model step to its report; optionally refresh its runtime route."""
import argparse
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from publishing_workflow import ROOT, load_json, save, timestamp, route_entry, lock, active_path

def extract(export, report, expected_session_id, now, config, tier='review', refresh=False, session_key=None):
    # A new real step may renew an expired attestation. Never require the expired
    # attestation to be renewed by hand before inspecting the evidence that renews it.
    entry = config['routes'][tier] if refresh else route_entry(config, tier, now)
    if not entry.get('model') or entry.get('auth') != 'oauth':
        raise ValueError('configured route must select an OAuth model')
    model = entry['model']
    provider, model_name = model.split('/', 1)
    expected_api = entry.get('api')
    review_key = session_key or entry.get('sessionKey')
    if not review_key:
        raise ValueError('actual stored session key is required')
    metadata_path = export / 'metadata.json'
    # Active-turn exports have a manifest/transcript but no terminal runtime metadata.
    # Metadata identifies the session only. The actual assistant response below is
    # the sole provider/model/API proof, because requested model aliases may route
    # to a different runtime model/API.
    metadata = load_json(metadata_path) if metadata_path.exists() else load_json(export / 'manifest.json')
    if metadata.get('sessionKey') != review_key or metadata.get('sessionId') != expected_session_id:
        raise ValueError('export belongs to a different reviewer session')
    report_hash = hashlib.sha256(report.read_bytes()).hexdigest()
    value = load_json(report)
    if value.get('model') != model or (expected_api and value.get('api') != expected_api) or not value.get('inputSha256'):
        raise ValueError('review report lacks model/input binding')
    completed = timestamp(value['completedAt'])
    if not now - timedelta(hours=24) <= completed <= now:
        raise ValueError('review report is stale or future dated')
    input_file = Path(value['inputPath'])
    if hashlib.sha256(input_file.read_bytes()).hexdigest() != value['inputSha256']:
        raise ValueError('reviewed input changed')
    events_path = export / 'events.jsonl'
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    assistants = {}
    for event in events:
        message = event.get('data', {}).get('message', {})
        if event.get('type') == 'assistant.message' and event.get('sessionId') == expected_session_id and message.get('role') == 'assistant':
            for block in message.get('content', []):
                if block.get('type') == 'toolCall':
                    assistants[block['id']] = (event, message)
    for event in reversed(events):
        if event.get('type') != 'tool.result' or event.get('sessionId') != expected_session_id:
            continue
        message = event.get('data', {}).get('message', {})
        if message.get('isError') or message.get('details', {}).get('exitCode') not in (None, 0):
            continue
        text = '\n'.join(block.get('text', '') for block in message.get('content', []))
        if report_hash not in text or value['inputSha256'] not in text or report.name not in text:
            continue
        pair = assistants.get(message.get('toolCallId'))
        if not pair:
            continue
        assistant_event, assistant = pair
        if assistant.get('provider') != provider or assistant.get('model') != model_name or (expected_api and assistant.get('api') != expected_api) or assistant.get('stopReason') != 'toolUse':
            continue
        if value.get('api') and value['api'] != assistant.get('api'):
            continue
        native = None
        if not assistant.get('responseId'):
            a, t = assistant.get('__openclaw', {}), message.get('__openclaw', {})
            call_id = message.get('toolCallId')
            if (not call_id or a.get('mirrorOrigin') != 'codex-app-server'
                or t.get('mirrorOrigin') != 'codex-app-server'
                or not a.get('runId') or a['runId'] != t.get('runId')
                or not assistant_event.get('entryId') or not event.get('entryId')
                or event.get('parentEntryId') != assistant_event['entryId']
                or not a.get('mirrorSourceFingerprint') or not t.get('mirrorSourceFingerprint')
                or not a.get('mirrorIdentity', '').endswith(':tool:' + call_id + ':call')
                or t.get('mirrorIdentity') != a['mirrorIdentity'][:-4] + 'result'
                or message.get('isError') is not False):
                continue
            native = {'runtime': 'codex-app-server', 'runId': a['runId'],
                      'assistantMessageId': assistant_event['entryId'], 'toolResultMessageId': event['entryId']}
        step_time = timestamp(event['ts'])
        if not completed <= step_time <= now:
            continue
        return {'schema': f'leescoop.{tier}.model-step-receipt.v1', 'model': model,
                'provider': provider, 'api': assistant.get('api'), 'sessionKey': review_key, 'sessionId': expected_session_id,
                'receipt': (f"openclaw-native:{expected_session_id};run:{native['runId']};message:{native['assistantMessageId']};toolResult:{native['toolResultMessageId']}" if native else f"openclaw-response:{assistant['responseId']};message:{assistant_event['entryId']}"),
                'responseId': assistant.get('responseId'), **({'nativeIdentity': native} if native else {}), 'messageId': assistant_event['entryId'],
                'toolCallId': message['toolCallId'], 'completedAt': step_time.isoformat(),
                'receiptType': 'completed-model-step-not-terminal-automation-run',
                'reportPath': str(report), 'reportSha256': report_hash,
                'inputSha256': value['inputSha256'], 'exportPath': str(export),
                'exportEventsSha256': hashlib.sha256(events_path.read_bytes()).hexdigest()}
    raise ValueError('no actual successful reviewer response/tool result binds this exact report and input')


def refreshed_config(config, tier, proof, report, now):
    """Renew only from the bound step plus its fresh, secret-free auth observation."""
    if hashlib.sha256(report.read_bytes()).hexdigest() != proof['reportSha256']:
        raise ValueError('report changed after receipt extraction')
    value = load_json(report)
    auth_checked = timestamp(value.get('authCheckedAt'))
    step = timestamp(proof['completedAt'])
    if value.get('auth') != 'oauth' or not value.get('authEvidence'):
        raise ValueError('route renewal needs observed OAuth auth/evidence in the bound report')
    if not now - timedelta(hours=24) <= auth_checked <= step <= now:
        raise ValueError('auth observation or successful model step is stale/future-dated')
    if not proof.get('api') or value.get('api') != proof['api']:
        raise ValueError('route renewal requires the actual API in report and export')
    result = copy.deepcopy(config)
    result['routes'][tier].update(
        api=proof['api'], auth='oauth', sessionKey=proof['sessionKey'],
        verifiedAt=auth_checked.isoformat(), expiresAt=(auth_checked + timedelta(hours=24)).isoformat(),
        evidence=f"Observed OAuth: {value['authEvidence']}; bound report {report}; SHA-256 {proof['reportSha256']}; export SHA-256 {proof['exportEventsSha256']}",
        successfulInferenceReceipt=proof['receipt'],
    )
    route_entry(result, tier, now)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, default=ROOT / 'docs/workflow/sources.json')
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--session-id', required=True)
    p.add_argument('--session-key', help='Actual stored session key, not a transient run alias')
    p.add_argument('--tier', choices=['routine', 'review'], default='review')
    p.add_argument('--refreshed-config', type=Path, help='Renew this route from actual step/auth proof into state/runtime-config.json or below state/config/; usable when prior route is expired')
    p.add_argument('--export', type=Path, help='Inspect an existing supported export instead of creating one')
    args = p.parse_args()
    try:
        config = load_json(args.config)
        refresh = args.refreshed_config is not None
        entry = config['routes'][args.tier] if refresh else route_entry(config, args.tier, datetime.now(timezone.utc))
        review_key = args.session_key or entry.get('sessionKey')
        if not review_key:
            raise ValueError('actual stored session key is required')
        state = args.state.resolve()
        report = args.report.resolve()
        if not report.is_relative_to(state / 'reports'):
            raise ValueError('report must be under canonical state/reports')
        export = args.export
        if export is None:
            suffix = hashlib.sha256(report.read_bytes()).hexdigest()[:16]
            result = subprocess.run(['openclaw', 'sessions', 'export-trajectory', '--session-key', review_key,
                                     '--workspace', str(state / 'reports'), '--output', 'review-step-' + suffix, '--json'],
                                    check=True, capture_output=True, text=True, timeout=60)
            exported = json.loads(result.stdout)
            if exported.get('sessionId') != args.session_id:
                raise ValueError('stored reviewer session changed during export')
            export = Path(exported['outputDir'])
        now = datetime.now(timezone.utc)
        result = extract(export, report, args.session_id, now, config, args.tier, refresh, review_key)
        output = report.with_name(report.stem + '-model-receipt.json')
        if refresh:
            target = args.refreshed_config.resolve()
            if target != state / 'runtime-config.json' and state / 'config' not in target.parents:
                raise ValueError('refreshed config must be canonical state/runtime-config.json or below state/config/')
            updated = refreshed_config(config, args.tier, result, report, now)
            with lock(state):
                if active_path(state).exists():
                    raise ValueError('cannot refresh route during active release; preserve its checkpoint')
                save(target, updated)
        save(output, result)
        print(json.dumps({'receiptPath': str(output), **({'configPath': str(target)} if refresh else {}), **result}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
