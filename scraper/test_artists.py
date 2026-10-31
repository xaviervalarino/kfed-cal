"""Artist info from Ticketmaster attractions, MusicBrainz and Wikipedia, against saved copies in scraper/fixtures/.
No network. Run with `python -m unittest`."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock
from urllib.robotparser import RobotFileParser

import httpx

from . import artists, methods, run
from .artists import MUSICBRAINZ, WIKIDATA, WIKIPEDIA
from .fetch import Fetcher
from .test_methods import LA, TODAY, FakeFetcher, fixture

FAILURE = "f0ed9f50-70b9-4406-9374-7d76ae21a04a"  # the US band, in mb_artist.json
FRANCIS = "4332dc29-35a4-406f-855f-8df891462993"
FRANCIS_RELS = json.dumps({"type": "Group", "area": {"name": "Luxembourg"}, "life-span": {"begin": "2019-01-01"},
                           "relations": [{"type": "bandcamp", "url": {"resource": "https://francisofdelirium.bandcamp.com/"}},
                                         {"type": "official homepage", "url": {"resource": "http://www.francisofdelirium.com/"}},
                                         {"type": "interview", "url": {"resource": "https://www.londoninstereo.com/x/"}}]})
SEARCHES = {"Francis of Delirium": "mb_search_one.json", "Failure": "mb_search_several.json",
            "Beatrix": "mb_search_inexact.json"}


class Services:
    """Answers MusicBrainz, Wikidata and Wikipedia requests from fixtures, and records each one: a search as
    'search <name>', anything else as its URL. `fail` lists requests that answer 503, `missing` ones that answer 404."""

    def __init__(self, fail=(), missing=()):
        self.requests, self.fail, self.missing = [], fail, missing

    def get(self, url, params=None, headers=None):
        request = f"search {params['query'][8:-1]}" if url == MUSICBRAINZ else url
        self.requests.append(request)
        status = 503 if request in self.fail else 404 if request in self.missing else None
        if status:
            response = httpx.Response(status, request=httpx.Request("GET", url))
            raise httpx.HTTPStatusError(f"{url} answered {status}.", request=response.request, response=response)
        answers = {f"{MUSICBRAINZ}/{FAILURE}": fixture("mb_artist.json"), f"{MUSICBRAINZ}/{FRANCIS}": FRANCIS_RELS,
                   WIKIDATA.format("Q2701586"): fixture("wikidata.json"),
                   WIKIPEDIA + "Failure_%28band%29": fixture("wikipedia_summary.json"),
                   **{f"search {name}": fixture(file) for name, file in SEARCHES.items()}}
        return httpx.Response(200, text=answers[request])


@mock.patch.dict(os.environ, {"TICKETMASTER_API_KEY": "test-key"})
class TicketmasterArtistsTest(unittest.TestCase):
    def test_attractions(self):
        report = {}
        raw = methods.ticketmaster({"params": {"venue_ids": ["KovZ917A967"]}},
                                   FakeFetcher({methods.TICKETMASTER: "tm_attractions.json"}), report)
        found = report["artists"]
        self.assertEqual(found["Chris Farren"], {
            "image": "https://s1.ticketm.net/dam/a/d82/f448b311-a3aa-4d3e-bc63-2ff213560d82_RETINA_LANDSCAPE_16_9.jpg",
            "links": {"youtube": "https://www.youtube.com/channel/UC1JMVKkY-bEVOMn7HFecM8Q",
                      "apple_music": "https://music.apple.com/us/artist/chris-farren/257342",
                      "spotify": "https://open.spotify.com/artist/6wnLSjE93qaj9uf3rVaM3N",
                      "instagram": "https://www.instagram.com/chrisfarren/",
                      "homepage": "https://www.chrisfarren.com/"},  # twitter and facebook are left out
            "mbid": "fa0a983e-8e69-41b2-83da-ebeb27aed0dd",
        })
        # Mislabelled keys: an "instagram" link to Spotify, a "homepage" link to Apple Music.
        self.assertEqual(found["Misery Whip"]["links"], {"spotify": "https://open.spotify.com/artist/5wVnqLy20pqllcxY8QB4iM"})
        self.assertEqual(found["Sex Mex"]["links"], {"apple_music": "https://music.apple.com/za/artist/sex-mex/1569936178"})
        self.assertEqual(set(found["Ant Clemons"]), {"image"})  # no externalLinks at all

        events = run.clean(raw, "The Echo", LA, TODAY)
        self.assertEqual(len(events), 3)  # Sex Mex is cancelled
        self.assertTrue(all(set(e) <= set(run.FIELDS) for e in events))

    def test_odd_attractions(self):
        page = {"_embedded": {"events": [{
            "name": "Band", "id": "1", "dates": {"start": {"localDate": "2099-11-14"}},
            "_embedded": {"attractions": [{"name": "Band", "images": ["not an image"]}, {"id": "no name"},
                                          {"name": "Opener"}]}}]}}
        report = {}
        raw = methods.ticketmaster({"params": {"venue_ids": ["x"]}},
                                   FakeFetcher({methods.TICKETMASTER: lambda p: json.dumps(page)}), report)
        self.assertEqual(raw[0]["support"], ["Opener"])  # the nameless attraction is skipped
        self.assertEqual(report["artists"], {"Opener": {}})  # Band's broken images lose only its artist info

    def test_image(self):
        big = [{"url": "a", "width": 2048}, {"url": "b", "width": 2426, "ratio": "3_2"}]
        self.assertEqual(artists.tm_artist({"images": big + [{"url": "c", "width": 1136}, {"url": "d", "width": 640}]}),
                         {"image": "c"})
        self.assertEqual(artists.tm_artist({"images": big}), {"image": "b"})  # none at or under 1200px: the widest
        self.assertEqual(artists.tm_artist({"externalLinks": {"musicbrainz": [{"id": "not-an-id"}]}}), {})


class MusicBrainzTest(unittest.TestCase):
    def test_link_kinds(self):
        cases = {
            "https://open.spotify.com/artist/1": "spotify",
            "https://failureband.bandcamp.com/": "bandcamp",
            "https://www.qobuz.com/us-en/interpreter/x/1": "qobuz",
            "https://itunes.apple.com/us/artist/id1646309": "apple_music",
            "https://music.apple.com/us/artist/1646309": "apple_music",
            "https://soundcloud.com/failuremusic": "soundcloud",
            "https://music.youtube.com/channel/1": "youtube",
            "https://youtu.be/1": "youtube",
            "https://www.instagram.com/failurebandig/": "instagram",
            "https://notspotify.com/artist/1": None,
            "http://failureband.com/": None,  # another site counts as the homepage only when labelled so
        }
        for url, kind in cases.items():
            with self.subTest(url):
                self.assertEqual(artists.link_kind(url), kind)
        self.assertEqual(artists.link_kind("http://failureband.com/", homepage=True), "homepage")
        self.assertIsNone(artists.link_kind("https://www.facebook.com/Failureband", homepage=True))

    def test_matching(self):
        self.assertEqual(artists.fold(" Beyoncé  KNOWLES"), artists.fold("beyonce knowles"))
        mb = Services()
        self.assertEqual(artists.mb_search("Francis of Delirium", mb), FRANCIS)  # one exact match
        self.assertIsNone(artists.mb_search("Failure", mb))  # several bands with that name
        self.assertIsNone(artists.mb_search("Beatrix", mb))  # the top hit is Beatrix Potter
        low = FakeFetcher({MUSICBRAINZ: lambda p: json.dumps({"artists": [{"id": "1", "name": "Hazel", "score": 90}]})})
        self.assertIsNone(artists.mb_search("Hazel", low))  # the only exact name, but a low score
        artists.mb_search('Say "Hi"', low)
        self.assertEqual(low.calls[-1][1], {"query": 'artist:"Say \\"Hi\\""', "fmt": "json", "limit": 5})

    def test_url_relations(self):
        self.assertEqual(artists.mb_artist(FAILURE, Services()), {
            "about": "Group from United States, formed 1990.",
            "about_source": f"https://musicbrainz.org/artist/{FAILURE}",
            "links": {"bandcamp": "https://failureband.bandcamp.com/",
                      "spotify": "https://open.spotify.com/artist/3grvcGPaLhfrD5CYsecr4j",
                      "homepage": "http://failureband.com/",
                      "apple_music": "https://itunes.apple.com/us/artist/id1646309",
                      "instagram": "https://www.instagram.com/failurebandig/",
                      "soundcloud": "https://soundcloud.com/failuremusic",
                      "youtube": "https://www.youtube.com/@FailureBand"},
            "mbid": FAILURE,
            "wikidata": "Q2701586",
        })

    @mock.patch.object(artists, "BUSY_WAIT", 0)
    def test_busy(self):
        response = httpx.Response(503, request=httpx.Request("GET", MUSICBRAINZ))
        busy = httpx.HTTPStatusError("busy", request=response.request, response=response)
        mb = mock.Mock()
        mb.get.side_effect = [busy, httpx.Response(200, json={"artists": []})]
        self.assertIsNone(artists.mb_search("Hazel", mb))  # a 503, then an answer
        mb.get.side_effect = [busy, busy]
        with self.assertRaises(httpx.HTTPStatusError):  # busy twice: the lookup fails
            artists.mb_search("Hazel", mb)
        self.assertEqual(mb.get.call_count, 4)

    def test_about(self):
        self.assertEqual(artists.mb_about({"type": "Person", "area": {"name": "Los Angeles"}, "life-span": {"begin": "1990-04"}}),
                         "Person from Los Angeles, born 1990.")
        self.assertEqual(artists.mb_about({"type": "Other", "life-span": {"begin": "2019"}}), "Formed 2019.")
        self.assertIsNone(artists.mb_about({"type": "Other"}))


class WikipediaTest(unittest.TestCase):
    def test_summary(self):
        self.assertEqual(artists.wikipedia("Q2701586", Services()), {
            "about": "Failure is an American alternative rock band from Los Angeles that was active from 1990 to 1997 "
                     "and again since 2014. They have released seven full-length albums and five EPs.",
            "about_source": "https://en.wikipedia.org/wiki/Failure_(band)",
        })

    def test_disambiguation(self):
        wiki = FakeFetcher({WIKIDATA.format("Q2701586"): "wikidata.json", WIKIPEDIA: "wikipedia_disambiguation.json"})
        self.assertEqual(artists.wikipedia("Q2701586", wiki), {})

    def test_first_sentences(self):
        self.assertEqual(artists.first_sentences("One is short. Two is too. Three is left out."),
                         "One is short. Two is too.")
        self.assertEqual(artists.first_sentences("Long. " + "X" * 300), "Long.")
        self.assertEqual(artists.first_sentences("She was born in St. Louis. She moved. Then left."),
                         "She was born in St. Louis. She moved.")
        self.assertEqual(artists.first_sentences("They toured with Dr. Dog. Then they split. Later more."),
                         "They toured with Dr. Dog. Then they split.")
        self.assertEqual(artists.first_sentences("St. Vincent is an American musician. Her name is Annie Clark. More."),
                         "St. Vincent is an American musician. Her name is Annie Clark.")


class FindArtistsTest(unittest.TestCase):
    TICKETMASTER = {
        # Ticketmaster knows which Failure: its MusicBrainz id skips the ambiguous search.
        "Failure": {"image": "https://s1.ticketm.net/failure.jpg", "links": {"spotify": "https://open.spotify.com/artist/tm"},
                    "mbid": FAILURE},
        "Misery Whip": {"links": {"spotify": "https://open.spotify.com/artist/5wVnqLy20pqllcxY8QB4iM"}},
    }
    NAMES = ["Francis of Delirium", "Beatrix", "Failure", "Misery Whip", "Francis of Delirium"]

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.cache = Path(folder.name) / "cache" / "artists.json"

    def find(self, mb, names=NAMES, today=date(2026, 10, 31), wiki=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return artists.find_artists(names, self.TICKETMASTER, mb, wiki or mb, today, self.cache)

    def test_lookups_and_cache(self):
        services = Services()
        found, errors = self.find(services)
        self.assertEqual(services.requests, ["search Francis of Delirium", f"{MUSICBRAINZ}/{FRANCIS}", "search Beatrix",
                                             f"{MUSICBRAINZ}/{FAILURE}", WIKIDATA.format("Q2701586"),
                                             WIKIPEDIA + "Failure_%28band%29"])
        self.assertEqual(errors, {"MusicBrainz": [], "Wikipedia": []})
        self.assertEqual(found["Francis of Delirium"], {
            "about": "Group from Luxembourg, formed 2019.",
            "about_source": f"https://musicbrainz.org/artist/{FRANCIS}",
            "links": {"bandcamp": "https://francisofdelirium.bandcamp.com/", "homepage": "http://www.francisofdelirium.com/"},
            "mbid": FRANCIS,
        })
        self.assertNotIn("Beatrix", found)  # nothing known
        failure = found["Failure"]
        self.assertEqual(failure["about_source"], "https://en.wikipedia.org/wiki/Failure_(band)")  # over MusicBrainz's
        self.assertEqual((failure["image"], failure["mbid"]), ("https://s1.ticketm.net/failure.jpg", FAILURE))
        self.assertEqual(list(failure["links"]),  # Ticketmaster's, then MusicBrainz's, in page order
                         ["spotify", "bandcamp", "apple_music", "soundcloud", "youtube", "homepage", "instagram"])
        self.assertEqual(failure["links"]["spotify"], "https://open.spotify.com/artist/tm")
        self.assertEqual(found["Misery Whip"], self.TICKETMASTER["Misery Whip"])

        cache = json.loads(self.cache.read_text())
        self.assertEqual(sorted(cache), ["Beatrix", "Failure", "Francis of Delirium"])  # misses too
        self.assertEqual(cache["Beatrix"], {"checked": "2026-10-31"})

        services = Services()
        self.assertEqual(self.find(services, today=date(2027, 1, 28))[0], found)  # 89 days later: all from the cache
        self.assertEqual(services.requests, [])
        services = Services()
        self.find(services, names=["Beatrix"], today=date(2027, 1, 30))  # 91 days later: checked again
        self.assertEqual(services.requests, ["search Beatrix"])
        self.assertEqual(json.loads(self.cache.read_text())["Beatrix"], {"checked": "2027-01-30"})

    def test_new_mbid(self):
        self.cache.parent.mkdir()
        self.cache.write_text(json.dumps({"Failure": {"checked": "2026-10-30"}}))  # an earlier search's miss
        services = Services()
        self.assertIn("about", self.find(services, names=["Failure"])[0]["Failure"])
        self.assertEqual(services.requests[0], f"{MUSICBRAINZ}/{FAILURE}")

    def test_cap(self):
        with mock.patch.object(artists, "LOOKUPS", 1):
            services = Services()
            found, _ = self.find(services, names=["Francis of Delirium", "Failure"])
            self.assertEqual(services.requests, ["search Francis of Delirium", f"{MUSICBRAINZ}/{FRANCIS}"])
            self.assertEqual(found["Failure"], self.TICKETMASTER["Failure"])  # Ticketmaster's only
            self.assertNotIn("Failure", json.loads(self.cache.read_text()))  # waits for the next run
            services = Services()
            self.find(services, names=["Francis of Delirium", "Failure"])
            self.assertEqual(services.requests[0], f"{MUSICBRAINZ}/{FAILURE}")

    @mock.patch.object(artists, "BUSY_WAIT", 0)
    def test_errors(self):
        services = Services(fail={"search Francis of Delirium", WIKIDATA.format("Q2701586")})
        found, errors = self.find(services)
        self.assertEqual((len(errors["MusicBrainz"]), len(errors["Wikipedia"])), (1, 1))
        self.assertEqual(found["Failure"]["about_source"], f"https://musicbrainz.org/artist/{FAILURE}")
        self.assertEqual(sorted(json.loads(self.cache.read_text())), ["Beatrix"])  # failed ones are tried again
        with mock.patch.object(artists, "MAX_ERRORS", 1):
            services = Services(fail={"search Francis of Delirium"})
            self.find(services, names=["Francis of Delirium", "Failure"])
            self.assertEqual(services.requests, ["search Francis of Delirium"] * 2)  # asked twice; the rest wait

    def test_not_found(self):
        dead = [f"00000000-0000-0000-0000-00000000000{i}" for i in range(6)]  # stale Ticketmaster MusicBrainz ids
        self.TICKETMASTER = {f"Band {i}": {"mbid": mbid} for i, mbid in enumerate(dead)}
        names = [*self.TICKETMASTER, "Beatrix"]
        services = Services(missing={f"{MUSICBRAINZ}/{mbid}" for mbid in dead})
        found, errors = self.find(services, names=names)
        self.assertEqual(services.requests, [f"{MUSICBRAINZ}/{mbid}" for mbid in dead] + ["search Beatrix"])
        self.assertEqual(errors, {"MusicBrainz": [], "Wikipedia": []})  # not errors: they don't stop the others
        self.assertEqual(found["Band 0"], {"mbid": dead[0]})
        self.assertEqual(sorted(json.loads(self.cache.read_text())), sorted(names))  # cached as misses
        services = Services()
        self.find(services, names=names, today=date(2026, 11, 7))
        self.assertEqual(services.requests, [])  # not asked again before the recheck

        wiki = Services(missing={WIKIPEDIA + "Failure_%28band%29"})  # a missing Wikipedia page
        self.assertEqual(artists.look_up("Failure", FAILURE, Services(), wiki, errors)[1], True)
        self.assertEqual(errors, {"MusicBrainz": [], "Wikipedia": []})

    def test_prune(self):
        self.cache.parent.mkdir()
        self.cache.write_text(json.dumps({"Gone": {"checked": "2026-07-01"}, "Recent": {"checked": "2026-10-01"},
                                          "Beatrix": {"checked": "2026-07-01"}}))
        self.find(Services(), names=["Beatrix"])
        # Gone was last checked over 90 days ago and isn't playing; Beatrix is checked again.
        self.assertEqual(json.loads(self.cache.read_text()), {"Recent": {"checked": "2026-10-01"},
                                                              "Beatrix": {"checked": "2026-10-31"}})

    def test_run_survives(self):
        with mock.patch.object(run, "find_artists", side_effect=OSError("Disk full.")), \
                contextlib.redirect_stdout(io.StringIO()) as printed:
            self.assertEqual(run.artist_info(["Band"], {}, None), {})
        self.assertIn("::warning::Artist info could not be loaded (OSError: Disk full.)", printed.getvalue())


class RobotsExceptionTest(unittest.TestCase):
    def test_only_listed_prefixes(self):
        fetcher = Fetcher()
        for base in ("https://musicbrainz.org", "https://en.wikipedia.org", "https://www.wikidata.org",
                     "https://musicbrainz.org.evil.example"):
            fetcher.robots[base] = RobotFileParser()
            fetcher.robots[base].parse(["User-agent: *", "Disallow: /"])
        self.assertTrue(fetcher.allowed("https://musicbrainz.org/ws/2/artist?query=x&fmt=json"))
        self.assertTrue(fetcher.allowed("https://en.wikipedia.org/api/rest_v1/page/summary/Failure_%28band%29"))
        self.assertTrue(fetcher.allowed(WIKIDATA.format("Q2701586")))
        self.assertFalse(fetcher.allowed("https://musicbrainz.org/artist/" + FAILURE))
        self.assertFalse(fetcher.allowed("https://en.wikipedia.org/wiki/Failure_(band)"))
        self.assertFalse(fetcher.allowed("https://en.wikipedia.org/api/"))
        self.assertFalse(fetcher.allowed("https://www.wikidata.org/wiki/Special:Search"))
        self.assertFalse(fetcher.allowed("https://musicbrainz.org.evil.example/ws/2/artist"))


if __name__ == "__main__":
    unittest.main()
