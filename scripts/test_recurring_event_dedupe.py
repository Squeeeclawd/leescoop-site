import tempfile
import unittest
from pathlib import Path

import leescoop_posts as posts


class RecurringEventDedupeTests(unittest.TestCase):
    def test_only_dated_event_occurrences_are_normalized(self):
        self.assertEqual(posts.recurring_event_url("https://www.artinlee.org/event/gallery-2026/2026-09-22/?utm_source=x"),
                         "https://www.artinlee.org/event/gallery-2026")
        for url in ("https://example.com/calendar/2026-09-22/", "https://example.com/event/123/",
                    "https://example.com/event/gallery/2026-02-30/"):
            self.assertEqual(posts.recurring_event_url(url), "")

    def test_gallery_occurrence_rejects_existing_same_exhibition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "existing.md").write_text('''---
title: Previously covered fiber art
contentKind: event
eventDate: 2026-09-26T09:00:00-04:00
venue: Alliance for the Arts
sourceUrl: https://www.artinlee.org/event/august-september-galleries-2026/2026-08-21/
---
''')
            idx = posts.existing_index(root)
            item = {"slug": "new-occurrence", "title": "In the galleries", "eventDate": "2026-09-22",
                    "eventEndDate": "2026-09-26", "venue": "Alliance for the Arts",
                    "sourceUrl": "https://www.artinlee.org/event/august-september-galleries-2026/2026-09-22/"}
            self.assertIn("same recurring event series", posts.duplicate_reason("event", item, idx))
            item["sourceUrl"] = "https://www.artinlee.org/event/new-exhibition/2026-09-22/"
            self.assertIsNone(posts.duplicate_reason("event", item, idx))
            item.update(sourceUrl="https://www.artinlee.org/event/august-september-galleries-2026/2026-12-01/",
                        eventDate="2026-12-01", eventEndDate="2026-12-01")
            self.assertIsNone(posts.duplicate_reason("event", item, idx))

    def test_distinct_nonseries_same_venue_starts_remain_distinct(self):
        idx = {"titles": {}, "urls": {}, "slugs": {}, "event_keys": {
            (posts.event_start_key("2026-10-01T18:00:00-04:00"), "same venue"): "first.md"}}
        item = {"title": "Second performance", "eventDate": "2026-10-01T20:00:00-04:00", "venue": "Same Venue",
                "sourceUrl": "https://example.com/show/second"}
        self.assertIsNone(posts.duplicate_reason("event", item, idx))


if __name__ == "__main__":
    unittest.main()
