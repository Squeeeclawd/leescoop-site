from datetime import datetime, timezone
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import copy
import publishing_review_receipt as r

class ReviewReceiptTests(unittest.TestCase):
    def fixture(self, root):
        self.config=json.loads((r.ROOT/'docs/workflow/sources.json').read_text())
        self.config['routes']['review'].update(model='openai/gpt-6-astra', requestedModel='openai/gpt-5.5', api='openai-chatgpt-responses', verifiedAt='2026-09-22T20:00:00+00:00', expiresAt='2026-09-23T20:00:00+00:00')
        now=datetime(2026,9,22,21,0,tzinfo=timezone.utc)
        source=root/'leads.json';source.write_text('{"leads":[]}')
        input_hash=hashlib.sha256(source.read_bytes()).hexdigest()
        report=root/'review.json';report.write_text(json.dumps({'model':self.config['routes']['review']['model'],'requestedModel':self.config['routes']['review']['requestedModel'],'api':self.config['routes']['review']['api'],'inputPath':str(source),'inputSha256':input_hash,'completedAt':now.isoformat()}))
        report_hash=hashlib.sha256(report.read_bytes()).hexdigest()
        (root/'metadata.json').write_text(json.dumps({'sessionKey':self.config['routes']['review']['sessionKey'],'sessionId':'session','model':{'provider':'openai','name':'gpt-5.5'}}))
        events=[{'type':'assistant.message','sessionId':'session','entryId':'message','data':{'message':{'role':'assistant','provider':'openai','model':'gpt-6-astra','api':'openai-chatgpt-responses','stopReason':'toolUse','responseId':'fixture-response','content':[{'type':'toolCall','id':'tool'}]}}},
                {'type':'tool.result','sessionId':'session','ts':now.isoformat(),'data':{'message':{'toolCallId':'tool','isError':False,'details':{'exitCode':0},'content':[{'text':f'review.json {report_hash} {input_hash}'}]}}}]
        (root/'events.jsonl').write_text('\n'.join(map(json.dumps,events)))
        return now,report,source,events
    def test_exact_report_is_bound_to_actual_model_step_not_whole_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);now,report,source,events=self.fixture(root)
            proof=r.extract(root,report,'session',now,self.config)
            self.assertEqual(proof['responseId'],'fixture-response')
            self.assertIn('not-terminal',proof['receiptType'])
    def test_active_export_without_terminal_metadata_still_requires_response_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);now,report,source,events=self.fixture(root)
            metadata=json.loads((root/'metadata.json').read_text())
            (root/'manifest.json').write_text(json.dumps({k:metadata[k] for k in ('sessionKey','sessionId')}))
            (root/'metadata.json').unlink()
            self.assertEqual(r.extract(root,report,'session',now,self.config)['responseId'],'fixture-response')
            events[0]['data']['message']['model']='gpt-5.6-luna'
            (root/'events.jsonl').write_text('\n'.join(map(json.dumps,events)))
            with self.assertRaisesRegex(ValueError,'no actual successful'):
                r.extract(root,report,'session',now,self.config)
    def test_changed_or_expired_route_cannot_relabel_old_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);now,report,source,events=self.fixture(root)
            self.config['routes']['review']['model']='openai/replacement'
            with self.assertRaises(ValueError):r.extract(root,report,'session',now,self.config)
            self.config['routes']['review']['model']='openai/gpt-6-astra'
            self.config['routes']['review']['expiresAt']=now.isoformat()
            with self.assertRaisesRegex(ValueError,'expired'):r.extract(root,report,'session',now,self.config)

    def test_actual_api_must_match_when_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);now,report,source,events=self.fixture(root)
            proof=r.extract(root,report,'session',now,self.config)
            self.assertEqual(proof['model'],'openai/gpt-6-astra')
            self.assertEqual(proof['api'],'openai-chatgpt-responses')
            events[0]['data']['message']['api']='other-api'
            (root/'events.jsonl').write_text('\n'.join(map(json.dumps,events)))
            with self.assertRaisesRegex(ValueError,'no actual successful'):
                r.extract(root,report,'session',now,self.config)

    def test_wrong_session_and_changed_input_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);now,report,source,events=self.fixture(root)
            with self.assertRaises(ValueError):r.extract(root,report,'different',now,self.config)
            source.write_text('{}')
            with self.assertRaisesRegex(ValueError,'input changed'):r.extract(root,report,'session',now,self.config)
    def test_failed_or_unmatched_tool_record_does_not_prove_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);now,report,source,events=self.fixture(root)
            events[1]['data']['message']['details']['exitCode']=1
            (root/'events.jsonl').write_text('\n'.join(map(json.dumps,events)))
            with self.assertRaisesRegex(ValueError,'no actual successful'):r.extract(root,report,'session',now,self.config)

    def test_native_receipt_and_pairing_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);now,report,source,events=self.fixture(root)
            assistant=events[0]['data']['message'];assistant.pop('responseId')
            assistant['__openclaw']={'mirrorOrigin':'codex-app-server','runId':'run','mirrorIdentity':'turn:tool:tool:call','mirrorSourceFingerprint':'assistant-hash'}
            events[1].update(entryId='result',parentEntryId='message')
            events[1]['data']['message']['__openclaw']={'mirrorOrigin':'codex-app-server','runId':'run','mirrorIdentity':'turn:tool:tool:result','mirrorSourceFingerprint':'result-hash'}
            def check(rows):
                (root/'events.jsonl').write_text('\n'.join(map(json.dumps,rows)))
                return r.extract(root,report,'session',now,self.config)
            proof=check(events)
            self.assertIsNone(proof['responseId'])
            self.assertEqual(proof['nativeIdentity']['runId'],'run')
            for index,key,value in [(0,'sessionId','wrong'),(0,'model','wrong'),(0,'api','wrong'),(1,'isError',True),(0,'mirrorOrigin','wrong'),(1,'runId','wrong'),(1,'parentEntryId','wrong'),(1,'mirrorIdentity','other:tool:tool:result'),(0,'mirrorSourceFingerprint','')]:
                bad=copy.deepcopy(events)
                if key in ('sessionId','parentEntryId'):bad[index][key]=value
                elif key in ('model','api','isError'):bad[index]['data']['message'][key]=value
                else:bad[index]['data']['message']['__openclaw'][key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):check(bad)

    def test_expired_route_renews_only_from_bound_real_step_and_fresh_auth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);now,report,source,events=self.fixture(root)
            value=json.loads(report.read_text())
            value.update(auth='oauth',authCheckedAt=now.isoformat(),authEvidence='fixture session_status observed OAuth profile')
            report.write_text(json.dumps(value))
            events[1]['data']['message']['content'][0]['text']=f'{report.name} {hashlib.sha256(report.read_bytes()).hexdigest()} {value["inputSha256"]}'
            (root/'events.jsonl').write_text('\n'.join(map(json.dumps,events)))
            self.config['routes']['review']['expiresAt']=now.isoformat()
            proof=r.extract(root,report,'session',now,self.config,refresh=True)
            renewed=r.refreshed_config(self.config,'review',proof,report,now)
            self.assertEqual(renewed['routes']['review']['successfulInferenceReceipt'],proof['receipt'])
            self.assertEqual(renewed['routes']['routine'],self.config['routes']['routine'])
            self.assertEqual(r.route_entry(renewed,'review',now)['model'],'openai/gpt-6-astra')
            # Merely asking to renew does not allow a wrong actual model.
            events[0]['data']['message']['model']='retired'
            (root/'events.jsonl').write_text('\n'.join(map(json.dumps,events)))
            with self.assertRaises(ValueError):r.extract(root,report,'session',now,self.config,refresh=True)
            for changes in ({'auth':'api-key'},{'authEvidence':''},{'authCheckedAt':'2026-09-20T21:00:00+00:00'}):
                altered=dict(value,**changes);report.write_text(json.dumps(altered))
                rebound=dict(proof,reportSha256=hashlib.sha256(report.read_bytes()).hexdigest())
                with self.subTest(changes=changes),self.assertRaises(ValueError):r.refreshed_config(self.config,'review',rebound,report,now)

    def test_routine_uses_same_export_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);now,report,source,events=self.fixture(root)
            self.config['routes']['routine']=copy.deepcopy(self.config['routes']['review'])
            result=r.extract(root,report,'session',now,self.config,tier='routine')
            self.assertEqual(result['schema'],'leescoop.routine.model-step-receipt.v1')

    def run_refresh_cli(self, state, target):
        reports=state/'reports';reports.mkdir(parents=True,exist_ok=True)
        now,report,source,events=self.fixture(reports)
        value=json.loads(report.read_text())
        value.update(auth='oauth',authCheckedAt=now.isoformat(),authEvidence='fixture observed OAuth profile')
        report.write_text(json.dumps(value))
        events[1]['data']['message']['content'][0]['text']=f'{report.name} {hashlib.sha256(report.read_bytes()).hexdigest()} {value["inputSha256"]}'
        (reports/'events.jsonl').write_text('\n'.join(map(json.dumps,events)))
        config=state/'source-config.json';config.write_text(json.dumps(self.config))
        argv=['publishing_review_receipt.py','--config',str(config),'--state',str(state),
              '--report',str(report),'--session-id','session','--export',str(reports),
              '--refreshed-config',str(target)]
        output=io.StringIO()
        with patch('sys.argv',argv),patch.object(r,'datetime') as clock,redirect_stdout(output):
            clock.now.return_value=now
            code=r.main()
        return code,json.loads(output.getvalue()),report.with_name('review-model-receipt.json')

    def test_refresh_cli_accepts_canonical_runtime_and_config_descendants(self):
        for relative in ('runtime-config.json','config/manual.json','config/nested/manual.json'):
            with self.subTest(path=relative),tempfile.TemporaryDirectory() as tmp:
                state=Path(tmp)/'state';target=state/relative
                code,result,receipt=self.run_refresh_cli(state,target)
                self.assertEqual(code,0,result)
                self.assertEqual(result['configPath'],str(target))
                renewed=json.loads(target.read_text())
                self.assertEqual(renewed['routes']['review']['successfulInferenceReceipt'],result['receipt'])
                self.assertEqual(renewed['routes']['routine'],self.config['routes']['routine'])
                self.assertTrue(receipt.is_file())

    def test_refresh_cli_rejects_other_paths_without_writing(self):
        for relative in ('other.json','reports/config.json','config-other/manual.json',
                         'config/../other.json','../runtime-config.json',
                         'runtime-config.json/child.json','config'):
            with self.subTest(path=relative),tempfile.TemporaryDirectory() as tmp:
                state=Path(tmp)/'state';target=state/relative
                code,result,receipt=self.run_refresh_cli(state,target)
                self.assertEqual(code,2,result)
                self.assertIn('canonical state/runtime-config.json or below state/config/',result['error'])
                self.assertFalse(target.resolve().exists())
                self.assertFalse(receipt.exists())

    def test_refresh_cli_rejects_symlink_escapes(self):
        for relative in ('runtime-config.json','config/manual.json'):
            with self.subTest(path=relative),tempfile.TemporaryDirectory() as tmp:
                state=Path(tmp)/'state';target=state/relative
                target.parent.mkdir(parents=True)
                outside=Path(tmp)/'outside.json';outside.write_text('untouched')
                target.symlink_to(outside)
                code,result,receipt=self.run_refresh_cli(state,target)
                self.assertEqual(code,2,result)
                self.assertIn('canonical state/runtime-config.json or below state/config/',result['error'])
                self.assertEqual(outside.read_text(),'untouched')
                self.assertFalse(receipt.exists())

    def test_refresh_cli_preserves_config_during_active_release_or_locked_state(self):
        for relative in ('runtime-config.json','config/manual.json'):
            for protection in ('active-release','lock'):
                with self.subTest(path=relative,protection=protection),tempfile.TemporaryDirectory() as tmp:
                    state=Path(tmp)/'state';target=state/relative
                    target.parent.mkdir(parents=True)
                    target.write_text('untouched')
                    if protection=='active-release':
                        active=r.active_path(state);active.write_text('{"run":"existing"}')
                        code,result,receipt=self.run_refresh_cli(state,target)
                        self.assertEqual(active.read_text(),'{"run":"existing"}')
                        self.assertIn('active release',result['error'])
                    else:
                        with r.lock(state):
                            code,result,receipt=self.run_refresh_cli(state,target)
                        self.assertIn('owns the state lock',result['error'])
                    self.assertEqual(code,2,result)
                    self.assertEqual(target.read_text(),'untouched')
                    self.assertFalse(receipt.exists())

if __name__=='__main__':unittest.main()
