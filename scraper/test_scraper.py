"""Run with `python -m unittest`."""

import json
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from .fetch import is_challenge
from .methods import jsonld_events, to_event
from .run import clean, parse_start
from .venues import load_venues

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
        self.assertEqual(events[0]["price"], "$25")
        self.assertEqual(events[0]["venue"], "Test Hall")

    def test_is_challenge(self):
        page = "<html><title>Just a moment...</title><script src='/cdn-cgi/challenge-platform/x.js'></script>"
        self.assertTrue(is_challenge(httpx.Response(403, text=page)))
        self.assertTrue(is_challenge(httpx.Response(200, headers={"cf-mitigated": "challenge"}, text="")))
        self.assertFalse(is_challenge(httpx.Response(200, text=page)))  # a normal page with Cloudflare scripts
        self.assertFalse(is_challenge(httpx.Response(403, text="Forbidden")))

    def test_venues_file(self):
        self.assertEqual(len(load_venues()[1]), 24)  # the real venues.json
        venues = [{"name": "A", "website": "https://a.example/", "method": "ticketmaster", "params": {"venue_ids": "KovZ1"}},
                  {"name": "B", "website": "https://b.example/", "method": "dice_venue"},
                  {"name": "C", "website": "https://c.example/"}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "venues.json"
            path.write_text(json.dumps({"timezone": "America/Chicago", "venues": venues}))
            with self.assertRaises(SystemExit) as stop:
                load_venues(path)
        self.assertIn("2 problem(s)", str(stop.exception))
        self.assertIn('Venue #1 (A): "venue_ids" must be a list', str(stop.exception))
        self.assertIn('Venue #2 (B): method "dice_venue" needs "events_page"', str(stop.exception))


if __name__ == "__main__":
    unittest.main()
