import copy
from datetime import datetime, timedelta
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import publishing_workflow as w


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((w.ROOT / 'docs/workflow/sources.json').read_text())
        self.now = datetime.fromisoformat('2026-09-18T14:00:00-04:00')
        self.item = dict(kind='event', slug='fixture-only', title='Fixture only', sourceUrl='https://example.org/fixture', sourceName='Fixture', city='Cape Coral', category='Arts', excerpt='Fixture', summary='Fixture', date=self.now.isoformat(), evidence='Test only', verified=True, reviewed=True, verifiedAt=self.now.isoformat(), score=11, eventDate='2026-09-19T10:00:00-04:00', eventTime='10 am', venue='Fixture Hall', organizer='Fixture', eventType='arts', cost='free', status='scheduled')

    def test_plan_rotation_and_timezone(self):
        a = w.plan(self.config, self.now.date())
        self.assertEqual(a, w.plan(self.config, self.now.date()))
        self.assertNotEqual(a['sources'], w.plan(self.config, (self.now + timedelta(days=1)).date())['sources'])
        self.assertFalse(any(s['lane'] == 'nearby' for s in a['sources']))

    def test_dates(self):
        w.validate(self.item, self.config, self.now)
        for date in ['bad', '2026-09-19', '2026-09-17T10:00:00-04:00']:
            with self.subTest(date=date), self.assertRaises(ValueError):
                w.validate(dict(self.item, eventDate=date), self.config, self.now)
        w.validate(dict(self.item, eventDate='2026-09-17T10:00:00-04:00', eventEndDate='2026-09-20T10:00:00-04:00'), self.config, self.now)

    def test_nearby_explicit(self):
        item = dict(self.item, city='Naples', coverageLabel='Nearby Southwest Florida', exceptionReason='Exceptional fixture')
        with self.assertRaises(ValueError): w.validate(item, self.config, self.now)
        self.config['nearbyEnabled'] = True
        w.validate(item, self.config, self.now)

    def test_dedupe(self):
        other = dict(self.item, slug='different', title='Different', sourceUrl='https://example.org/fixture?utm_source=test')
        with patch.object(w, 'cover', return_value='hash'):
            accepted, rejected, _ = w.evaluate([self.item, other], self.config, self.now, w.ROOT, {})
        self.assertEqual(len(accepted), 1)
        self.assertIn('duplicate', rejected[0]['reason'])

    def test_missing_cover_blocks(self):
        with self.assertRaises(ValueError):
            w.evaluate([self.item], self.config, self.now, w.ROOT, {})

    def test_cover_decode_size_and_provenance(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); covers = root/'public/covers'; covers.mkdir(parents=True)
            path = covers/'fixture.png'
            item = dict(self.item, coverImage='/covers/fixture.png', coverOrigin='existing', coverPreservationEvidence='fixture-only test')
            path.write_text('<html>not an image</html>')
            with self.assertRaises(OSError): w.cover(item,root,self.config,self.now)
            Image.new('RGB',(10,10)).save(path)
            with self.assertRaises(ValueError): w.cover(item,root,self.config,self.now)
            Image.new('RGB',(1216,704)).save(path)
            self.assertEqual(len(w.cover(item,root,self.config,self.now)),64)
            item['coverOrigin']='generated'
            with self.assertRaises(ValueError): w.cover(item,root,self.config,self.now)

    def test_routes_fail_closed(self):
        for tier in ['routine', 'review', 'image']:
            with self.assertRaises(ValueError): w.route(self.config, tier, self.now)
        self.config['routes']['image'].update(evidence='fixture', verifiedAt=self.now.isoformat(), expiresAt=(self.now+timedelta(hours=1)).isoformat(), directOverrideAbsent=True)
        self.assertEqual(w.route(self.config, 'image', self.now), 'openai/gpt-image-2')
        self.config['routes']['image']['auth'] = 'api-key'
        with self.assertRaises(ValueError): w.route(self.config, 'image', self.now)

    def test_lock_concurrent_process(self):
        with tempfile.TemporaryDirectory() as d:
            with w.lock(Path(d)):
                code = 'from pathlib import Path; from publishing_workflow import lock;\nwith lock(Path('+repr(d)+')): pass'
                p = subprocess.run([sys.executable, '-c', code], cwd=Path(__file__).parent, capture_output=True)
                self.assertNotEqual(p.returncode, 0)
                self.assertIn(b'owns the lock', p.stderr)
            with w.lock(Path(d)): pass

    def test_failure_report_resumption_and_gate(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d); source = base/'input.json'
            source.write_text(json.dumps({'items':[self.item]}))
            args = ['--state',d,'--now',self.now.isoformat(),'prepare','--run','fixture','--input',str(source)]
            self.assertEqual(w.main(args),2)
            report = json.loads((base/'runs/fixture.json').read_text())
            self.assertEqual(report['status'],'blocked')
            with patch.object(w, 'cover', return_value='fixturehash'):
                self.assertEqual(w.main(args),0)
                gate = [a if a!='prepare' else 'gate' for a in args]
                self.assertEqual(w.main(gate),0)
            with patch.object(w,'cover',return_value='changedhash'):
                self.assertEqual(w.main(gate),2)
            source.write_text('{bad')
            self.assertEqual(w.main(args),2)

    def test_legacy_writer_cannot_publish(self):
        p = subprocess.run([sys.executable,str(w.ROOT/'scripts/leescoop_posts.py'),'write','--input','nonexistent.json'],capture_output=True)
        self.assertEqual(p.returncode,2)
        self.assertIn(b'Legacy writer disabled',p.stdout)

    def test_empty_pool_noop(self):
        self.assertEqual(w.evaluate([],self.config,self.now,w.ROOT,{}),([],[],{}))

    def test_news_brief_and_freshness(self):
        item = dict(self.item,kind='news',summary='word '*81)
        with self.assertRaises(ValueError): w.validate(item,self.config,self.now)
        item.update(summary='Brief',date='2026-08-01T10:00:00-04:00')
        with self.assertRaises(ValueError): w.validate(item,self.config,self.now)

if __name__ == '__main__': unittest.main()
