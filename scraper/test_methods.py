"""Each method against a small saved copy of its source in scraper/fixtures/. No network.
Run with `python -m unittest`."""

import json
import os
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from zoneinfo import ZoneInfo

import httpx

from . import methods
from .run import clean

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LA = ZoneInfo("America/Los_Angeles")
TODAY = "2026-10-30"  # the day the fixtures were saved


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeFetcher:
    """Answers a URL that starts with one of `routes` with a fixture file name, a function of the request's
    params, or a ready httpx.Response. Records every request."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, params=None):
        self.calls.append((url, params))
        for prefix, answer in self.routes.items():
            if url.startswith(prefix):
                if isinstance(answer, httpx.Response):
                    return answer
                return httpx.Response(200, text=answer(params) if callable(answer) else fixture(answer))
        raise AssertionError(f"unexpected request: {url}")


def by_title(events):
    return {e["title"]: e for e in events}


class FixedDate(date):
    """date with a chosen today(), for code that asks for today's date."""
    today_is = date(2026, 10, 28)

    @classmethod
    def today(cls):
        return cls.today_is


@mock.patch.dict(os.environ, {"TICKETMASTER_API_KEY": "test-key"})
class TicketmasterTest(unittest.TestCase):
    def setUp(self):
        pages = json.loads(fixture("ticketmaster.json"))
        self.fetcher = FakeFetcher({methods.TICKETMASTER: lambda p: json.dumps(pages[p["venueId"]][p["page"]])})

    def test_events(self):
        raw = methods.ticketmaster({"params": {"venue_ids": ["KovZ917A967"]}}, self.fetcher, {})
        self.assertEqual([(p["page"], p["apikey"]) for _, p in self.fetcher.calls], [(0, "test-key"), (1, "test-key")])
        self.assertNotIn("Upgrade: Premium Viewing Deck", [e["title"] for e in raw])  # a seat upgrade, not a show

        events = clean(raw, "The Echo", LA, TODAY)
        self.assertEqual(events[0], {
            "venue": "The Echo",
            "title": "Francis of Delirium",
            "support": ["Beatrix"],
            "start": "2026-10-30T20:00",  # "Show: 8PM" in the note; localTime 19:00 is the doors time
            "doors": "19:00",
            "age": "All ages",
            "url": "https://www.ticketmaster.com/francis-of-delirium-with-beatrix-los-angeles-california-10-30-2026/event/09006491C882C986",
            "ticket_url": "https://www.ticketmaster.com/francis-of-delirium-with-beatrix-los-angeles-california-10-30-2026/event/09006491C882C986",
            "image": "https://s1.ticketm.net/dam/a/88a/5888d1c2-93fe-4d66-a5c5-4d8fd92ca88a_RETINA_LANDSCAPE_16_9.jpg",
            "source_id": "tm:vv1AaZk3oGkdFOiJk",
        })
        events = by_title(events)
        self.assertEqual(sorted(events), ["Francis of Delirium", "Ninajirachi", "Qendresa", "Spill It", "untitled (halo)"])
        self.assertEqual(events["untitled (halo)"]["details"], "PBW Presents · California Melancholia Tour")
        self.assertEqual(events["untitled (halo)"]["support"], ["Dalhaus"])
        self.assertEqual(events["Qendresa"]["status"], "sold_out")
        self.assertEqual(events["Ninajirachi"]["age"], "18+")
        # Only a doors time is known: it goes in doors, and start keeps the date only.
        self.assertEqual((events["Spill It"]["start"], events["Spill It"]["doors"]), ("2026-11-04", "18:30"))
        self.assertEqual((events["Spill It"]["details"], events["Spill It"]["age"]), ("3 Min Mic Tour", "21+"))

    def test_second_room(self):
        venue = {"params": {"venue_ids": ["KovZ917AiI3", "KovZ917AReX"]}}
        events = by_title(clean(methods.ticketmaster(venue, self.fetcher, {}), "The Bellwether", LA, TODAY))
        jai = events["Jai Wolf"]
        self.assertEqual((jai["details"], jai["doors"], jai.get("room")), ("10 Year Anniversary Tour", "19:00", None))
        camilles = events["Chikafuji Lisa, False Start, These Severed Hands, Hazel, Double XP"]
        self.assertEqual((camilles["room"], camilles["price"], camilles["age"]),
                         ("Camille's at The Bellwether", "$24–60.21", "21+"))

    def test_no_date_yet(self):
        event = methods.tm_event({"name": "Band", "id": "1", "dates": {"start": {"dateTBA": True}}, "pleaseNote": "Show: 8PM"})
        self.assertIsNone(event["start"])  # clean drops it; the venue's other events stay

    def test_missing_key(self):
        with mock.patch.dict(os.environ, {"TICKETMASTER_API_KEY": ""}):
            with self.assertRaisesRegex(RuntimeError, "TICKETMASTER_API_KEY is not set"):
                methods.ticketmaster({"params": {"venue_ids": ["x"]}}, self.fetcher, {})


class DiceTest(unittest.TestCase):
    def test_events(self):
        report = {}
        raw = methods.dice_venue({"events_page": "https://dice.fm/venue/zebulon-y8bv"},
                                 FakeFetcher({"https://dice.fm/": "dice_venue.html"}), report)
        self.assertEqual(report, {"partial": "DICE shows only the next 5 shows."})
        events = by_title(clean(raw, "Zebulon", LA, TODAY))
        self.assertEqual(events["The Tubs"], {
            "venue": "Zebulon",
            "title": "The Tubs",
            "support": ["Touch Girl Apple Blossom"],
            "start": "2026-10-30T19:00",
            "price": "$26.78",
            "url": "https://dice.fm/event/6a30e7a3a3a6de0001ce1ea7",
            "image": "https://dice-media.imgix.net/attachments/2026-06-23/20d26da1-fe44-4989-be76-50c6cb8ca1a4.jpg?rect=544%2C0%2C5295%2C5295",
            "source_id": "dice:6a30e7a3a3a6de0001ce1ea7",
        })
        kulture = events["Kulture Klub"]
        self.assertEqual((kulture["details"], kulture["support"], kulture["price"]),
                         ("The '80s Dance Party", ["DJ Geneva Jacuzzi"], "free"))
        self.assertEqual(events["Alex Cameron"]["status"], "sold_out")
        self.assertEqual(events["Bodysnatcher"]["details"], "Hell Is Here, Hell Is Home Tour")
        self.assertEqual(events["Viva! Pomona"]["price"], "from $43.85")

    def test_page_without_data(self):
        fetcher = FakeFetcher({"https://dice.fm/": lambda p: "<html><title>Just a moment...</title></html>"})
        with self.assertRaisesRegex(ValueError, "no event data"):
            methods.dice_venue({"events_page": "https://dice.fm/venue/x"}, fetcher, {})


class TesseraTest(unittest.TestCase):
    def test_events(self):
        fetcher = FakeFetcher({"https://www.lodgeroomhlp.com/": "tessera.html"})
        raw = methods.tessera({"events_page": "https://www.lodgeroomhlp.com/"}, fetcher, {})
        events = by_title(clean(raw, "Lodge Room", LA, TODAY))
        self.assertEqual(sorted(events), ["Desire", "Improvement Movement", "Jamila Woods"])
        self.assertEqual(events["Improvement Movement"], {
            "venue": "Lodge Room",
            "title": "Improvement Movement",
            "support": ["Adron", "Languid Machinations (DJ Set)"],
            "details": "Your Perfect Real LIVE ’26",
            "start": "2026-10-30T20:00",
            "doors": "19:00",
            "url": "https://www.lodgeroomhlp.com/shows/improvement-movement-your-perfect-real-live-26/",
            "image": "https://www.lodgeroomhlp.com/wp-content/uploads/2026/07/2026.10.30-Improvement-Movement-web.jpg",
            "source_id": "tessera:34884",
        })


class TribeEventsTest(unittest.TestCase):
    def test_events(self):
        fetcher = FakeFetcher({"https://www.vermonthollywood.com/": "tribe_events.json"})
        raw = methods.tribe_events({"events_page": "https://www.vermonthollywood.com/wp-json/tribe/events/v1/events?per_page=50"},
                                   fetcher, {})
        events = by_title(clean(raw, "The Vermont", LA, TODAY))
        self.assertEqual(events["Pangea Espooky Halloween"]["support"], ["TAYLAH ELAINE", "FALCONS", "JOAQU.N", "SUPERNOVA"])
        self.assertEqual(events["Pangea Espooky Halloween"]["price"], "$16.50")
        self.assertEqual(events["SYSTEM ERROR"]["ticket_url"], "https://pear.us/systemerror/post/richard-finger")  # utm_* and fbclid gone
        self.assertEqual(events["Tuna USA World Tour"]["price"], "free")
        self.assertNotIn("support", events["Tuna USA World Tour"])  # the performer is already in the title


class PermanentRecordsTest(unittest.TestCase):
    def test_events(self):
        page = "http://roadhouse.permanentrecordsla.com/"
        raw = methods.permanent_records_events(fixture("permanent_records.html"), page, date(2026, 10, 30))
        self.assertEqual([(e["start"], e["title"]) for e in raw], [
            ("2026-10-30T18:00", "Pharoah Chromium (Chrome)"),
            ("2026-11-01T18:00", "Nate Varrone"),
            ("2026-11-05T18:00", "Music Trivia"),
            ("2026-11-20T21:00", "Stepping Stone Presents: Sebastien Bordeaux"),
            ("2027-01-21T21:00", "KFM"),  # no year on the page: January comes after October
        ])  # "Details coming soon..." and a night closed for a private event are left out
        self.assertEqual(raw[0]["support"], ["The B-69s (The B-52s)", "That's Russ / Wild Cover Nation (Arthur Russell)"])
        self.assertEqual(raw[0]["image"], "http://roadhouse.permanentrecordsla.com/images/2026/10oct/1030.jpg")
        self.assertTrue(raw[0]["ticket_url"].startswith("https://app.opendate.io/e/pharaoh-chromium"))
        self.assertEqual([e["price"] for e in raw[1:3]], ["$15 ADVANCE / $20 DOS", "$5 PER PLAYER"])

        sebastien = by_title(clean(raw, "Permanent Records Roadhouse", LA, TODAY))["Sebastien Bordeaux"]
        self.assertEqual(sebastien["details"], "Stepping Stone Presents")

    def test_odd_rows(self):
        rows = ["<tr><td></td><td><i>Friday, October 30th<br>- 6PM</i><br>Band</td><td>$10</td></tr>",
                "<tr><td></td><td><i>Monday, February 30th - 6PM</i><br>Typo Band</td><td>$10</td></tr>"]
        raw = methods.permanent_records_events(f"<table>{''.join(rows)}</table>", "http://x/", date(2026, 10, 30))
        self.assertEqual([(e["start"], e["title"], e["support"]) for e in raw], [("2026-10-30T18:00", "Band", [])])


@mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
@mock.patch.object(methods, "date", FixedDate)
class MontyFlyerTest(unittest.TestCase):
    VENUE = {"events_page": "https://montybar.com/"}

    def setUp(self):
        self.fetcher = FakeFetcher({
            "https://montybar.com/wp-content/": httpx.Response(200, content=b"\x89PNG", headers={"content-type": "image/png"}),
            "https://montybar.com/": "monty_flyer.html",
        })
        reply = SimpleNamespace(content=[SimpleNamespace(type="text", text=fixture("monty_flyer.json"))],
                                usage=SimpleNamespace(input_tokens=2605, output_tokens=1543), stop_reason="end_turn")
        patcher = mock.patch.object(methods.anthropic, "Anthropic")
        self.client = patcher.start().return_value
        self.client.messages.create.return_value = reply
        self.addCleanup(patcher.stop)
        FixedDate.today_is = date(2026, 10, 28)

    def test_events(self):
        report = {}
        raw = methods.monty_flyer(self.VENUE, self.fetcher, report)
        flyer = "https://montybar.com/wp-content/uploads/2026/10/MONTY-weekly-2026-43.png"  # full size, not 1024x1024
        self.assertEqual(self.fetcher.calls[1][0], flyer)
        self.assertEqual(report, {"haiku": {"input_tokens": 2605, "output_tokens": 1543}})
        request = self.client.messages.create.call_args.kwargs
        self.assertEqual(request["model"], "claude-haiku-5-5")
        self.assertEqual(request["output_config"]["format"]["type"], "json_schema")

        self.assertEqual(len(raw), 5)
        self.assertEqual(raw[2], {
            "title": "CLUB NEVERMORE",
            "details": "3RD ANNUAL HALLOWEEN | BANDS + DJs + PERFORMANCES | $5 ADV $10 DOORS",
            "start": "2026-10-30T20:00",
            "price": "$5 ADV $10 DOORS",
            "url": "https://montybar.com/",
            "image": flyer,
        })
        events = clean(raw, "Monty Bar", LA, TODAY)  # Oct 28 and 29 are past
        self.assertEqual([e["title"] for e in events], ["CLUB NEVERMORE", "DANSE-X", "BATASTROPHE"])
        self.assertEqual(events[2]["price"], "free")

    def test_last_weeks_flyer(self):
        FixedDate.today_is = date(2026, 11, 4)
        report = {}
        with self.assertRaisesRegex(ValueError, "past week"):
            methods.monty_flyer(self.VENUE, self.fetcher, report)
        self.assertIn("haiku", report)  # the tokens were spent either way

    def test_missing_key(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            with self.assertRaisesRegex(RuntimeError, "ANTHROPIC_API_KEY is not set"):
                methods.monty_flyer(self.VENUE, self.fetcher, {})
        self.client.messages.create.assert_not_called()


class ParserTest(unittest.TestCase):
    def test_clock(self):
        for text, expected in [("7PM", "19:00"), ("7:30 pm", "19:30"), ("12AM", "00:00"), ("19:00:00", "19:00"),
                               ("Doors 8 p.m.", "20:00"), ("12-8PM", "12:00"), ("9-11pm", "21:00"), ("tonight", None),
                               (None, None)]:
            self.assertEqual(methods.clock(text), expected, text)

    def test_find_age(self):
        for text, expected in [("All Ages", "All ages"), ("18 & Over", "18+"), ("21+ ONLY", "21+"),
                               ("This event is 21 and over.", "21+"), ("no limits", None)]:
            self.assertEqual(methods.find_age(text), expected, text)

    def test_dollars(self):
        self.assertEqual([methods.dollars(16, 19), methods.dollars(26.5), methods.dollars(25, 25)],
                         ["$16–19", "$26.50", "$25"])


if __name__ == "__main__":
    unittest.main()
