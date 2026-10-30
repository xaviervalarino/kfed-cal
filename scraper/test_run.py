"""The cleanup rules in run.clean, and the files run.main writes. No network. Run with `python -m unittest`."""

import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from . import run

LA = ZoneInfo("America/Los_Angeles")


def one(title, **fields):
    """Clean a single raw event and return it (or None if clean drops it)."""
    events = run.clean([{"title": title, "start": "2099-11-14T20:00", "url": "https://venue.example/1", **fields}],
                       "The Echo", LA, "2099-11-01")
    return events[0] if events else None


class CleanTest(unittest.TestCase):
    def test_names(self):
        cases = [
            # (title, other raw fields) -> fields expected after cleaning
            (("PBW Presents: untitled (halo) - California Melancholia Tour", {}),
             {"title": "untitled (halo)", "details": "PBW Presents · California Melancholia Tour"}),
            (("Francis of Delirium with Beatrix", {"support": ["Beatrix"]}),
             {"title": "Francis of Delirium", "support": ["Beatrix"]}),
            (("Josh Garrels with special guest Taylor Armstrong", {}),
             {"title": "Josh Garrels", "support": ["Taylor Armstrong"]}),
            (("Lucy Bedroque w/ pinponpanpon", {}), {"title": "Lucy Bedroque", "support": ["pinponpanpon"]}),
            (("An Evening with River Shook", {}), {"title": "An Evening with River Shook"}),
            (("The Red Clay Strays with Special Guest St. Paul and the Broken Bones", {}),
             {"title": "The Red Clay Strays", "support": ["St. Paul and the Broken Bones"]}),
            (("Qendresa - SOLD OUT", {}), {"title": "Qendresa", "status": "sold_out"}),
            (("Ninajirachi (18 and Over)", {}), {"title": "Ninajirachi", "age": "18+"}),
            (("Band (Moved from The Echo)", {}), {"title": "Band", "status": "rescheduled"}),
            (("Rescheduled: Band", {}), {"title": "Band", "status": "rescheduled"}),
            (("The Sheepdogs- Out All Night Tour", {}), {"title": "The Sheepdogs", "details": "Out All Night Tour"}),
            (("Allah-Las", {}), {"title": "Allah-Las"}),
            (("Club Nevermore", {"details": "3RD ANNUAL HALLOWEEN"}), {"title": "Club Nevermore", "details": "3RD ANNUAL HALLOWEEN"}),
            (("Sonderfest feat. Truman Sinclair + more", {"support": ["Truman Sinclair", "Tom Siletto", "etc", "SUPERNOVA & MORE"]}),
             {"support": ["Tom Siletto", "SUPERNOVA"]}),
            (("Sarah Jamiah", {"support": ["Ra", "Mia"]}), {"support": ["Ra", "Mia"]}),  # not inside "Sarah"
            (("Band", {"support": ["Grand More", "Brother Ali +more"]}), {"support": ["Grand More", "Brother Ali"]}),
            (("Band (Moved from The Echo)", {"status": "on_sale"}), {"title": "Band", "status": "rescheduled"}),
            (("Sueco (moved to The Regent DTLA)", {}), {"title": "Sueco", "status": "rescheduled"}),
            (("Headache w/Special Guests: Baba Stiltz, John Keek", {}),
             {"title": "Headache", "support": ["Baba Stiltz", "John Keek"], "details": None}),
            (("Mixed Feelings Presents - Kim Petras: De-Tour", {}),
             {"title": "Kim Petras", "details": "Mixed Feelings Presents · De-Tour"}),
        ]
        for (title, fields), expected in cases:
            event = one(title, **fields)
            self.assertEqual({k: event.get(k) for k in expected}, expected, title)

    def test_dropped(self):
        self.assertIsNone(one("CANCELED - Sex Mex"))
        self.assertIsNone(one("MOVED TO THE BELASCO - KCRW Presents: [MANIC STREET PREACHERS]"))  # points at the real listing
        self.assertIsNone(one("Band", status="cancelled"))
        self.assertIsNone(one("Band", start="2099-10-31T20:00"))  # past
        self.assertIsNone(one("", start="2099-11-14"))

    def test_fields(self):
        self.assertEqual(one("Band", price="$0").get("price"), None)  # "$0" is how some feeds say "no price"
        self.assertEqual(one("Band", price="25")["price"], "$25")
        self.assertEqual(one("Band", price="Free")["price"], "free")
        self.assertEqual(one("Band", start="2099-11-14T00:00:01")["start"], "2099-11-14")  # placeholder time
        self.assertEqual(one("Band", start="2099-11-15T04:00:00Z")["start"], "2099-11-14T20:00")  # to venue time
        self.assertEqual(one("Band", status="onsale").get("status"), None)
        self.assertEqual(one("Band", room="THE ECHO").get("room"), None)
        self.assertEqual(one("Band", room="Camille's")["room"], "Camille's")
        self.assertEqual(one("Band", url="https://t.example/e/1?utm_source=ig&id=4&fbclid=abc")["url"],
                         "https://t.example/e/1?id=4")
        self.assertEqual(list(one("Band", image=None, support=[], source_id="tm:1")),
                         ["venue", "title", "start", "url", "source_id"])  # unknown fields are left out

    def test_duplicates(self):
        raw = [{"title": "Band", "start": "2099-11-14T20:00", "url": "u", "source_id": "tm:1"},
               {"title": "Band (Early Show)", "start": "2099-11-14T18:00", "url": "u", "source_id": "tm:1"},
               {"title": "Band", "start": "2099-11-14T18:00", "url": "u", "source_id": "tm:2"},
               {"title": "Other", "start": "2099-11-14T20:00", "url": "u"},
               {"title": "OTHER", "start": "2099-11-14", "url": "u"}]  # the same show, listed again without a time
        events = run.clean(raw, "The Echo", LA, "2099-11-01")
        self.assertEqual([(e["title"], e["start"]) for e in events],
                         [("Band", "2099-11-14T20:00"), ("Band", "2099-11-14T18:00"), ("Other", "2099-11-14T20:00")])

    def test_next_run(self):
        utc = timezone.utc
        self.assertEqual(run.next_run(datetime(2026, 11, 3, 23, 0, tzinfo=utc)), datetime(2026, 11, 4, 10, 17, tzinfo=utc))
        self.assertEqual(run.next_run(datetime(2026, 11, 4, 10, 20, tzinfo=utc)), datetime(2026, 11, 11, 10, 17, tzinfo=utc))


def show(title, start, source_id=None):
    return {"title": title, "start": start, "url": "https://venue.example/" + title, "source_id": source_id}


def good(venue, fetcher, report):
    return [show("Band", "2099-11-14T20:00", "tm:1"), show("Late Band", "2099-12-01")]


def twin(venue, fetcher, report):
    return [show("Band", "2099-11-14T20:00", "tm:1"), show("Other Band", "2099-11-20T21:00", "tm:2")]


def capped(venue, fetcher, report):
    report["partial"] = "The page shows only the next show."
    return [show("Capped Band", "2099-11-16T20:00")]


def broken(venue, fetcher, report):
    raise ValueError("The page changed.")


def flyer(venue, fetcher, report):
    report["haiku"] = {"input_tokens": 2605, "output_tokens": 1543}
    return [show("DJ Night", "2099-11-18T21:00")]


VENUES = [
    {"name": "Good Hall", "website": "https://good.example/", "method": "good"},
    {"name": "Twin Hall", "website": "https://twin.example/", "method": "twin"},
    {"name": "Capped", "website": "https://capped.example/", "method": "capped"},
    {"name": "Broken", "website": "https://broken.example/", "method": "broken"},
    {"name": "Gone", "website": "https://gone.example/", "method": "broken"},
    {"name": "Quiet", "website": "https://quiet.example/", "method": "empty"},
    {"name": "Flyer", "website": "https://flyer.example/", "method": "flyer"},
    {"name": "Unlisted", "website": "https://unlisted.example/", "notes": "No listings online yet."},
]


class MainTest(unittest.TestCase):
    def test_files(self):
        with tempfile.TemporaryDirectory() as folder:
            output, status = Path(folder) / "events.json", Path(folder) / "status.json"
            kept = {"venue": "Broken", "title": "Old Band", "start": "2099-11-15T20:00", "url": "https://broken.example/1"}
            output.write_text(json.dumps({"events": [kept, {**kept, "start": "2000-01-01"}]}))
            status.write_text(json.dumps({"venues": [{"name": "Broken", "last_success": "2026-10-01T10:00:00+00:00"}]}))
            methods = {"good": good, "twin": twin, "capped": capped, "broken": broken, "flyer": flyer,
                       "empty": lambda venue, fetcher, report: []}
            with mock.patch.multiple(run, OUTPUT=output, STATUS=status, METHODS=methods, Fetcher=mock.Mock(),
                                     load_venues=lambda: ("America/Los_Angeles", VENUES)), \
                    contextlib.redirect_stdout(io.StringIO()) as printed:
                run.main()
            events, report = json.loads(output.read_text()), json.loads(status.read_text())

        self.assertIn("::warning::Broken: scrape failed (ValueError: The page changed.). The scraper keeps the "
                      "last run's events.", printed.getvalue())
        self.assertEqual(events["timezone"], "America/Los_Angeles")
        self.assertEqual(events["venues"][0], {"name": "Good Hall", "website": "https://good.example/"})
        self.assertEqual(len(events["venues"]), 8)
        self.assertEqual([(e["venue"], e["title"]) for e in events["events"]], [
            ("Good Hall", "Band"),  # Twin Hall's copy of tm:1 is left out
            ("Broken", "Old Band"),  # kept from the last run; the 2000 event is past
            ("Capped", "Capped Band"),
            ("Flyer", "DJ Night"),
            ("Twin Hall", "Other Band"),
            ("Good Hall", "Late Band"),
        ])

        self.assertEqual(report["totals"], {"events": 6, "venues": 8})
        self.assertEqual(report["haiku"], {"model": "claude-haiku-5-5", "input_tokens": 2605, "output_tokens": 1543,
                                           "dollars": 0.00103})
        self.assertLess(report["run"]["started"], report["run"]["next"])
        rows = {row["name"]: row for row in report["venues"]}
        self.assertEqual([row["name"] for row in report["venues"]], [v["name"] for v in VENUES])
        good_row = rows["Good Hall"]
        self.assertEqual({k: good_row[k] for k in ("method", "source", "status", "events", "through", "with_time")},
                         {"method": "good", "source": "none", "status": "ok", "events": 2, "through": "2099-12-01",
                          "with_time": 0.5})
        self.assertGreater(good_row["last_success"], "2026-10-30")
        self.assertEqual(rows["Twin Hall"]["events"], 1)
        self.assertEqual((rows["Capped"]["status"], rows["Capped"]["note"]), ("partial", "The page shows only the next show."))
        self.assertEqual(rows["Broken"], {"name": "Broken", "method": "broken", "source": "none", "status": "kept",
                                          "events": 1, "through": "2099-11-15", "with_time": 1.0,
                                          "last_success": "2026-10-01T10:00:00+00:00",
                                          "note": "ValueError: The page changed."})
        self.assertEqual(rows["Gone"], {"name": "Gone", "method": "broken", "source": "none", "status": "failed",
                                        "events": 0, "note": "ValueError: The page changed."})
        self.assertEqual((rows["Quiet"]["status"], rows["Quiet"]["events"]), ("ok", 0))
        self.assertEqual(rows["Unlisted"], {"name": "Unlisted", "source": "none", "status": "no_source", "events": 0,
                                            "note": "No listings online yet."})


if __name__ == "__main__":
    unittest.main()
