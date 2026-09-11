"""Regression checks for event identity and multi-day article output."""
import unittest
import leescoop_posts as posts


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

    def test_identical_source_still_blocks_different_time(self):
        self.index['urls'][posts.norm_url(self.item['sourceUrl'])] = 'existing.md'
        self.assertIn('same sourceUrl', posts.duplicate_reason('event', self.item, self.index))

    def test_writer_preserves_run_end(self):
        self.item['eventEndDate'] = '2026-11-08T17:00:00-05:00'
        output = posts.frontmatter('event', self.item, self.item['slug'], '')
        self.assertIn('eventEndDate: 2026-11-08T17:00:00-05:00', output)

    def test_writer_omits_absent_run_end(self):
        self.assertNotIn('eventEndDate:', posts.frontmatter('event', self.item, self.item['slug'], ''))


if __name__ == '__main__':
    unittest.main()
