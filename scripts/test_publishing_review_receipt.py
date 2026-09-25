from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
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

if __name__=='__main__':unittest.main()
