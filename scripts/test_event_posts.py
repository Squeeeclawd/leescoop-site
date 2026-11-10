"""Regression checks for event identity and multi-day article output."""
import unittest
import tempfile
from pathlib import Path
from datetime import datetime
import leescoop_posts as posts
import publishing_workflow as workflow


class EventPostTests(unittest.TestCase):
    def setUp(self):
        self.item = {'slug': 'new-morning-workshop', 'title': 'Morning workshop',
                     'sourceUrl': 'https://example.com/morning', 'venue': 'Shared Arts Center',
                     'eventDate': '2026-09-19T10:00:00-04:00'}
        self.index = {'slugs': {}, 'titles': {}, 'urls': {}, 'event_keys': {
            (posts.event_start_key('2026-09-19T20:00:00-04:00'), 'shared arts center'): 'evening-dance.md'
        }}

    def test_different_times_same_venue_are_distinct(self):
        self.assertIsNone(posts.duplicate_reason('event', self.item, self.index))

    def test_same_time_same_venue_remains_duplicate(self):
        self.item['eventDate'] = '2026-09-19T20:00:00-04:00'
        self.assertIsNotNone(posts.duplicate_reason('event', self.item, self.index))

    def test_equivalent_offsets_match(self):
        self.assertEqual(posts.event_start_key('2026-09-19T10:00:00-04:00'), posts.event_start_key('2026-09-19T14:00:00Z'))

    def test_curly_and_ascii_venue_apostrophes_identify_the_same_place(self):
        self.assertEqual(posts.norm_text("FGCU’s Alico Arena"),posts.norm_text("FGCU's Alico Arena"))

    def test_news_deadlines_require_date_bound_to_deadline_language(self):
        now=datetime.fromisoformat('2026-11-10T10:00:00-05:00')
        for summary in ('A pilot was rescued November 8. The spot could not be reached by land.', 'Closures began September 8, 2026. Check the guide before heading out.'):
            self.assertIsNone(posts.has_expired_deadline({'summary':summary},now))
        for summary in ('Apply by November 8, 2026.', 'Deadline: Sunday, Nov. 8, 2026.', 'Register before November 8.'):
            self.assertEqual(posts.has_expired_deadline({'summary':summary},now),'2026-11-08')
        self.assertIsNone(posts.has_expired_deadline({'summary':'Apply by November 18, 2026.'},now))

    def test_identical_source_still_blocks_different_time(self):
        self.index['urls'][posts.norm_url(self.item['sourceUrl'])] = 'existing.md'
        self.assertIn('same sourceUrl', posts.duplicate_reason('event', self.item, self.index))

    def test_writer_preserves_run_end(self):
        self.item['eventEndDate'] = '2026-11-08T17:00:00-05:00'
        output = posts.frontmatter('event', self.item, self.item['slug'], '')
        self.assertIn('eventEndDate: 2026-11-08T17:00:00-05:00', output)

    def test_writer_omits_absent_run_end(self):
        self.assertNotIn('eventEndDate:', posts.frontmatter('event', self.item, self.item['slug'], ''))

    def test_collection_identity_survives_materialization_and_reindexing(self):
        first=dict(self.item,kind='event',coverImage='/covers/first.png',eventDate='2026-09-19',sourceUrlScope='collection',eventVerification={'observedTitle':'Morning workshop','observedStart':'2026-09-19'})
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            rendered=workflow.render_articles({'selected':[first]})
            article=root/'first.md'
            article.write_text(next(iter(rendered.values()))['content'])
            self.assertIn('sourceEventStart: "2026-09-19"',article.read_text())
            persisted=posts.parse_frontmatter(article)
            self.assertEqual(persisted['eventDate'],'2026-09-19T12:00:00-04:00')
            self.assertEqual(persisted['sourceEventStart'],'2026-09-19')
            self.assertEqual(posts.collection_event_identity(first),posts.collection_event_identity(persisted))
            idx=posts.existing_index(root)
            second=dict(first,title='Evening show',slug='second',eventDate='2026-09-20T20:00:00-04:00',eventVerification={'observedTitle':'Evening show','observedStart':'2026-09-20T20:00:00-04:00'})
            self.assertIsNone(posts.duplicate_reason('event',second,idx))
            repeated=dict(first,title='Workshop rewrite',slug='rewritten')
            self.assertIsNotNone(posts.duplicate_reason('event',repeated,idx))

    def test_news_brief_omits_generic_section_but_preserves_supplied_context(self):
        item=dict(self.item,contentType='brief',summary='The beach parking lot is closed.')
        body=posts.body_from_summary('news',item)
        self.assertNotIn('## Why it matters',body)
        self.assertNotIn('This is a local update worth knowing',body)
        context='## Why it matters\n\nBeach access remains open, but visitors need another parking location.'
        item['summary']+='\n\n'+context
        body=posts.body_from_summary('news',item)
        self.assertIn(context,body)
        self.assertEqual(body.count('## Why it matters'),1)


if __name__ == '__main__':
    unittest.main()
