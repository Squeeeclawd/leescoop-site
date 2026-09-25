#!/usr/bin/env python3
"""Resolve an actual reviewer model-step receipt from a supported redacted export."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from publishing_workflow import ROOT, load_json, save, timestamp, route_entry

def extract(export, report, expected_session_id, now, config):
    entry = route_entry(config, 'review', now)
    model = entry['model']
    provider, model_name = model.split('/', 1)
    expected_api = entry.get('api')
    review_key = entry['sessionKey']
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
        if event.get('type') == 'assistant.message' and message.get('role') == 'assistant':
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
        if assistant.get('provider') != provider or assistant.get('model') != model_name or (expected_api and assistant.get('api') != expected_api) or assistant.get('stopReason') != 'toolUse' or not assistant.get('responseId'):
            continue
        step_time = timestamp(event['ts'])
        if not completed <= step_time <= now:
            continue
        return {'schema': 'leescoop.review.model-step-receipt.v1', 'model': model,
                'provider': provider, **({'api': expected_api} if expected_api else {}), 'sessionKey': review_key, 'sessionId': expected_session_id,
                'receipt': f"openclaw-response:{assistant['responseId']};message:{assistant_event['entryId']}",
                'responseId': assistant['responseId'], 'messageId': assistant_event['entryId'],
                'toolCallId': message['toolCallId'], 'completedAt': step_time.isoformat(),
                'receiptType': 'completed-model-step-not-terminal-automation-run',
                'reportPath': str(report), 'reportSha256': report_hash,
                'inputSha256': value['inputSha256'], 'exportPath': str(export),
                'exportEventsSha256': hashlib.sha256(events_path.read_bytes()).hexdigest()}
    raise ValueError('no actual successful reviewer response/tool result binds this exact report and input')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, default=ROOT / 'docs/workflow/sources.json')
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--session-id', required=True)
    p.add_argument('--export', type=Path, help='Inspect an existing supported export instead of creating one')
    args = p.parse_args()
    try:
        config = load_json(args.config)
        entry = route_entry(config, 'review', datetime.now(timezone.utc))
        review_key = entry['sessionKey']
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
        result = extract(export, report, args.session_id, datetime.now(timezone.utc), config)
        output = report.with_name(report.stem + '-model-receipt.json')
        save(output, result)
        print(json.dumps({'receiptPath': str(output), **result}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
