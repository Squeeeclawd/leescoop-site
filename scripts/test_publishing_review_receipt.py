from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import publishing_review_receipt as r

class ReviewReceiptTests(unittest.TestCase):
    def fixture(self, root):
        now=datetime(2026,9,22,21,0,tzinfo=timezone.utc)
        source=root/'leads.json';source.write_text('{"leads":[]}')
        input_hash=hashlib.sha256(source.read_bytes()).hexdigest()
        report=root/'review.json';report.write_text(json.dumps({'model':r.MODEL,'inputPath':str(source),'inputSha256':input_hash,'completedAt':now.isoformat()}))
        report_hash=hashlib.sha256(report.read_bytes()).hexdigest()
        (root/'metadata.json').write_text(json.dumps({'sessionKey':r.REVIEW_KEY,'sessionId':'session','model':{'provider':'openai','name':'gpt-5.6-sol'}}))
        events=[{'type':'assistant.message','sessionId':'session','entryId':'message','data':{'message':{'role':'assistant','provider':'openai','model':'gpt-5.6-sol','stopReason':'toolUse','responseId':'fixture-response','content':[{'type':'toolCall','id':'tool'}]}}},
                {'type':'tool.result','sessionId':'session','ts':now.isoformat(),'data':{'message':{'toolCallId':'tool','isError':False,'details':{'exitCode':0},'content':[{'text':f'review.json {report_hash} {input_hash}'}]}}}]
        (root/'events.jsonl').write_text('\n'.join(map(json.dumps,events)))
        return now,report,source,events
    def test_exact_report_is_bound_to_actual_model_step_not_whole_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);now,report,source,events=self.fixture(root)
            proof=r.extract(root,report,'session',now)
            self.assertEqual(proof['responseId'],'fixture-response')
            self.assertIn('not-terminal',proof['receiptType'])
    def test_wrong_session_and_changed_input_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);now,report,source,events=self.fixture(root)
            with self.assertRaises(ValueError):r.extract(root,report,'different',now)
            source.write_text('{}')
            with self.assertRaisesRegex(ValueError,'input changed'):r.extract(root,report,'session',now)
    def test_failed_or_unmatched_tool_record_does_not_prove_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);now,report,source,events=self.fixture(root)
            events[1]['data']['message']['details']['exitCode']=1
            (root/'events.jsonl').write_text('\n'.join(map(json.dumps,events)))
            with self.assertRaisesRegex(ValueError,'no actual successful'):r.extract(root,report,'session',now)

if __name__=='__main__':unittest.main()
