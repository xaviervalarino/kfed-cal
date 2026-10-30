"""Run with `python -m unittest`."""

import unittest
from zoneinfo import ZoneInfo

from .methods import jsonld_events, to_event
from .run import clean, parse_start

CHICAGO = ZoneInfo("America/Chicago")

PAGE = """
<script type="application/ld+json">{"@graph": [
  {"@type": "WebSite", "name": "not an event"},
  {"@type": "MusicEvent", "name": "Band &amp; Friends", "startDate": "2099-11-14T20:00:00-06:00",
   "url": "/shows/1", "image": ["/a.jpg"], "offers": {"price": "25"}},
  {"@type": "MusicEvent", "name": "Band & Friends", "startDate": "2099-11-14T20:00:00-06:00"},
  {"@type": "Event", "name": "Old Show", "startDate": "2000-01-01T20:00"}
]}</script>
<script type="application/ld+json">{"@type": "ItemList", "itemListElement": [
  {"@type": "ListItem", "item": {"@type": "Festival", "name": "Fest", "startDate": "2099-11-20"}}]}</script>
<script type="application/ld+json">{"@type": "Place", "name": "Club", "event": [
  {"@type": "MusicEvent", "name": "Nested", "startDate": "2099-11-21"}]}</script>
<script type="application/ld+json">{ broken json </script>
"""


class ScraperTest(unittest.TestCase):
    def test_parse_start(self):
        self.assertEqual(parse_start("2026-11-16T03:30:00Z", CHICAGO), "2026-11-15T21:30")
        self.assertEqual(parse_start("2026-11-14T20:00:00-06:00", CHICAGO), "2026-11-14T20:00")
        self.assertEqual(parse_start("2026-11-14T20:00", CHICAGO), "2026-11-14T20:00")
        self.assertEqual(parse_start("2026-11-14", CHICAGO), "2026-11-14")
        self.assertIsNone(parse_start("Fri Nov 14", CHICAGO))
        self.assertIsNone(parse_start(None, CHICAGO))

    def test_jsonld_to_clean_events(self):
        raw = [to_event(e, "https://venue.example/calendar") for e in jsonld_events(PAGE)]
        self.assertEqual(len(raw), 5)
        self.assertEqual(raw[0]["url"], "https://venue.example/shows/1")
        self.assertEqual(raw[0]["image"], "https://venue.example/a.jpg")

        events = clean(raw, "Test Hall", CHICAGO)
        self.assertEqual([(e["title"], e["start"]) for e in events],
                         [("Band & Friends", "2099-11-14T20:00"), ("Fest", "2099-11-20"),
                          ("Nested", "2099-11-21")])
        self.assertEqual(events[0]["price"], "25")
        self.assertEqual(events[0]["venue"], "Test Hall")


if __name__ == "__main__":
    unittest.main()
