import copy
from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import unittest
import publishing_health as h

class HealthTests(unittest.TestCase):
    def fixture(self, root):
        now=datetime(2026,9,22,20,0,tzinfo=h.NY)
        def put(name,v):
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v))
        put('discovery/today.json',{'schema':'leescoop.discovery.report.v1','runDate':'2026-09-22','completedAt':now.isoformat(),'model':'openai/gpt-5.6-luna'})
        put('reports/review.json',{'schema':'leescoop.review.report.v1','runDate':'2026-09-22','completedAt':now.isoformat(),'model':'openai/gpt-5.6-sol','mode':'no_op','publishable':False})
        return now,put
    def test_noop_is_not_preview(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);now,put=self.fixture(root);result=h.health(root,now)
            self.assertEqual(result['issues'],[])
            self.assertEqual(result['timedUnattendedPublication'],'unproven')
            self.assertEqual(result['schedulerState'],'not_inspected')
    def test_stale_and_hold(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);now,put=self.fixture(root);(root/'READ_ONLY_REVIEW_TEST').touch()
            result=h.health(root,now+timedelta(days=1))
            self.assertIn('read_only_review_hold',result['issues']);self.assertIn('discovery:stale',result['issues'])
    def test_malformed_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);now,put=self.fixture(root);(root/'ledger.json').write_text('broken')
            self.assertTrue(any(x.startswith('malformed:ledger') for x in h.health(root,now)['issues']))
    def test_mixed_finalized_batch_and_legacy_binding(self):
        now=datetime(2026,9,22,20,0,tzinfo=h.NY);commit='a'*40;deployment='12345678-1234-1234-1234-123456789abc'
        item={'slug':'sample','kind':'event','date':now.isoformat(),'title':'Sample','sourceUrl':'https://example.com/event','coverImage':'/covers/sample.png'}
        cp={'selected':[item],'assets':{'sample':'hash'}}
        receipt={'run':'test','commit':commit,'productionCommit':commit,'canonicalOrigin':'https://leescoop.com','checkedAt':now.isoformat(),'verifiedBy':'parent-liveverify','deploymentReceipt':f'cloudflare-pages:deployment:{deployment};github-check-run:123','deploymentProof':{'provider':'cloudflare-pages','deploymentId':deployment,'githubCheckRunId':123,'headSha':commit,'conclusion':'success','completedAt':now.isoformat(),'detailsUrl':'https://github.com/Squeeeclawd/leescoop-site/runs/123','previewUrl':'https://12345678.leescoop-site.pages.dev'},'articles':[{'slug':'sample','url':'https://leescoop.com/sample/','coverUrl':'https://leescoop.com/covers/sample.png','httpStatus':200,'title':'Sample','sourceUrl':'https://example.com/event','coverSha256':'hash',**{k:True for k in ('titleVerified','sourceLinkVerified','coverHashVerified','coverDecoded')}}]}
        ledger={h.digest(item):{'run':'test','slug':'sample','published':True,'state':'published','commit':commit,'receiptHash':h.digest(receipt)},'reserve':{'run':'test','slug':'reserve','published':False,'state':'rejected_or_reserve'}}
        self.assertIn('legacy',h.receipt_summary(receipt,cp,ledger,now)['verification'])
        ledger['reserve']['state']='selected'
        with self.assertRaises(ValueError):h.receipt_summary(receipt,cp,ledger,now)
        ledger.pop('reserve');ledger.clear()
        with self.assertRaises(ValueError):h.receipt_summary(receipt,cp,ledger,now)
    def test_nested_discovery_requires_bound_source_journal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);now,put=self.fixture(root)
            journal={'run':'fresh','requests':[{'host':'example.com','startedEpoch':now.timestamp()-10,'fetchedAt':(now-timedelta(seconds=10)).isoformat()}]}
            put('source-access/runs/fresh.json',journal)
            path=root/'source-access/runs/fresh.json'
            report={'run':{'runId':'fresh','model':'openai/gpt-5.6-luna','completedAt':now.isoformat(),'currentDate':'2026-09-22'},'sourceAccess':{'requestJournal':str(path),'requestJournalSha256':h.hashlib.sha256(path.read_bytes()).hexdigest()}}
            put('discovery/today.json',report)
            self.assertEqual(h.health(root,now)['discovery']['status'],'current')
            self.assertEqual(h.health(root,now)['issues'],[])
            report['sourceAccess']['requestJournalSha256']='wrong'
            put('discovery/today.json',report)
            self.assertTrue(any('journal hash mismatch' in x for x in h.health(root,now)['issues']))
    def test_current_day_before_due_time_accepts_yesterday(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);now,put=self.fixture(root)
            result=h.health(root,now+timedelta(hours=10))
            self.assertEqual(result['discovery']['status'],'current')

if __name__=='__main__':unittest.main()
