"""What is known about the acts in the events: links, a photo and a sentence or two (`artists` in docs/DATA.md).

Sources, in order: the event's Ticketmaster attractions, then MusicBrainz for names Ticketmaster gave no links or a
MusicBrainz id for, then the English Wikipedia summary for acts MusicBrainz links to Wikidata. MusicBrainz and Wikipedia lookups are
cached in scraper/cache/artists.json, misses too."""

import json
import re
import time
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote, urlsplit

import httpx

CACHE = Path(__file__).resolve().parent / "cache" / "artists.json"
MUSICBRAINZ = "https://musicbrainz.org/ws/2/artist"
WIKIDATA = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"
WIKIPEDIA = "https://en.wikipedia.org/api/rest_v1/page/summary/"
RECHECK = timedelta(days=90)
# shortcut: a first run with ~1,200 new names takes two weeks to fill the cache. Raise it if new acts outpace 600 a week.
LOOKUPS = 600
# After this many failed lookups in a row the service is likely down: the rest wait for the next run. MusicBrainz
# answers a scattered 503 now and then from shared CI addresses, so single failures don't count toward it.
MAX_ERRORS = 5
MIN_SCORE = 95
BUSY_WAIT = 5  # seconds to wait before asking MusicBrainz again after a 503

# Link kinds, in the order pages show them, and the hosts that make a link that kind.
KINDS = ["spotify", "bandcamp", "qobuz", "apple_music", "soundcloud", "youtube", "homepage", "instagram"]
HOSTS = {"spotify.com": "spotify", "bandcamp.com": "bandcamp", "qobuz.com": "qobuz", "music.apple.com": "apple_music",
         "itunes.apple.com": "apple_music", "soundcloud.com": "soundcloud", "youtube.com": "youtube",
         "youtu.be": "youtube", "instagram.com": "instagram"}
# Known services the pages don't show. A link to one of them is never the act's homepage.
OTHER_HOSTS = ("facebook.com", "twitter.com", "x.com", "tiktok.com", "wikipedia.org", "wikidata.org",
               "musicbrainz.org", "last.fm", "discogs.com")
MBID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
QID = re.compile(r"^Q\d+$")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“‘])")
ABBREVIATION = re.compile(r"\b(?:St|Dr|Mr|Mrs|Ms|Jr|Sr|vs|No|Mt|Ft)\.$")  # "St. Louis" is one sentence


def link_kind(url, homepage=False):
    """The link's kind by its host, whatever the source labelled it. Another site is the homepage only when the
    source says it is one (`homepage`)."""
    host = (urlsplit(url).hostname or "").lower()
    kind = next((kind for domain, kind in HOSTS.items() if on_domain(host, domain)), None)
    if not kind and homepage and not any(on_domain(host, domain) for domain in OTHER_HOSTS):
        kind = "homepage"
    return kind


def on_domain(host, domain):
    return host == domain or host.endswith("." + domain)


def add_link(links, url, homepage=False):
    """Add url to links under its kind, unless that kind already has one."""
    kind = link_kind(url, homepage) if isinstance(url, str) and url.startswith("http") else None
    if kind:
        links.setdefault(kind, url)


def tm_artist(attraction):
    """One Ticketmaster attraction: its links (keys are sometimes wrong, so links go by host), its MusicBrainz id
    and its widest image up to 1200px wide (the widest one when all are larger)."""
    links, mbid = {}, None
    for label, entries in (attraction.get("externalLinks") or {}).items():
        for entry in entries or []:
            if label == "musicbrainz":
                mbid = mbid or entry.get("id")
            else:
                add_link(links, entry.get("url"), homepage=label == "homepage")
    images = [i for i in attraction.get("images") or [] if i.get("url")]
    small = [i for i in images if (i.get("width") or 0) <= 1200]
    image = max(small or images, key=lambda i: i.get("width") or 0)["url"] if images else None
    return drop_empty({"image": image, "links": links, "mbid": mbid if mbid and MBID.match(mbid) else None})


def fold(name):
    """A name without case, accents or extra spaces, for comparing names."""
    letters = unicodedata.normalize("NFKD", name or "")
    return " ".join("".join(c for c in letters if not unicodedata.combining(c)).casefold().split())


def mb_search(name, mb):
    """The MusicBrainz id for name, or None. Only an exact name (case and accents aside) that no other result
    shares, with a score of 95 or more: "Beatrix" finds Beatrix Potter first, and several bands are called
    "Failure"."""
    phrase = name.replace("\\", "\\\\").replace('"', '\\"')
    found = mb_get(mb, MUSICBRAINZ, {"query": f'artist:"{phrase}"', "fmt": "json", "limit": 5})
    same = [a for a in found.get("artists") or [] if fold(a.get("name")) == fold(name)]
    return same[0]["id"] if len(same) == 1 and (same[0].get("score") or 0) >= MIN_SCORE else None


def mb_get(mb, url, params):
    """MusicBrainz answers 503 when it is busy or the rate is exceeded, even at 1 request a second: wait, then
    try once more."""
    try:
        return mb.get(url, params=params).json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 503:
            raise
    time.sleep(BUSY_WAIT)
    return mb.get(url, params=params).json()


def mb_artist(mbid, mb):
    """Links, a short `about` and the Wikidata id from the act's MusicBrainz url relations."""
    data = mb_get(mb, f"{MUSICBRAINZ}/{mbid}", {"inc": "url-rels", "fmt": "json"})
    links, wikidata = {}, None
    for relation in data.get("relations") or []:
        url = (relation.get("url") or {}).get("resource")
        if relation.get("ended") or not url:
            continue  # a link the act no longer uses
        if relation.get("type") == "wikidata":
            wikidata = url.rstrip("/").rsplit("/", 1)[-1]
        else:
            add_link(links, url, homepage=relation.get("type") == "official homepage")
    about = mb_about(data)
    return drop_empty({"about": about, "about_source": f"https://musicbrainz.org/artist/{mbid}" if about else None,
                       "links": links, "mbid": mbid, "wikidata": wikidata if wikidata and QID.match(wikidata) else None})


def mb_about(data):
    """ "Group from Los Angeles, formed 2019." from the act's type, area and start year. None when all are unknown."""
    kind = data.get("type") if data.get("type") in ("Person", "Group", "Orchestra", "Choir") else None
    area = (data.get("area") or {}).get("name")
    year = ((data.get("life-span") or {}).get("begin") or "")[:4]
    text = " ".join(filter(None, [kind, f"from {area}" if area else None]))
    if year:
        text = ", ".join(filter(None, [text, f"{'born' if kind == 'Person' else 'formed'} {year}"]))
    return f"{text[0].upper()}{text[1:]}." if text else None


def wikipedia(wikidata, wiki):
    """`about` and `about_source` from the English Wikipedia article that Wikidata item links to, or {}."""
    entities = wiki.get(WIKIDATA.format(wikidata)).json().get("entities") or {}
    item = next(iter(entities.values()), {})  # keyed by the item's current id, which differs after a merge
    title = ((item.get("sitelinks") or {}).get("enwiki") or {}).get("title")
    if not title:
        return {}
    page = wiki.get(WIKIPEDIA + quote(title.replace(" ", "_"), safe="")).json()
    source = ((page.get("content_urls") or {}).get("desktop") or {}).get("page")
    if page.get("type") == "disambiguation" or not page.get("extract") or not source:
        return {}
    return {"about": first_sentences(page["extract"]), "about_source": source}


def first_sentences(text, limit=300):
    """The text's first sentence, and the second too when both fit in `limit` characters."""
    sentences = []
    for piece in SENTENCE_END.split(" ".join(text.split())):
        if sentences and ABBREVIATION.search(sentences[-1]):
            sentences[-1] += " " + piece
        else:
            sentences.append(piece)
    if len(sentences) > 1 and len(sentences[0]) + len(sentences[1]) < limit:
        return f"{sentences[0]} {sentences[1]}"
    return sentences[0]


def look_up(name, mbid, mb, wiki, errors):
    """MusicBrainz, then Wikipedia, for one act. Returns (what was found, whether every step worked). A step that
    answers 404 or is refused worked: it found nothing, and asking again before the recheck gets the same answer."""
    try:
        mbid = mbid or mb_search(name, mb)
        found = mb_artist(mbid, mb) if mbid else {}
    except Exception as e:  # one failed lookup doesn't stop the others
        if not permanent(e):
            errors["MusicBrainz"].append(e)
            return {}, False
        found = drop_empty({"mbid": mbid})  # cached with the dead id, so the next run doesn't ask again
    wikidata = found.pop("wikidata", None)
    if wikidata:
        try:
            found.update(wikipedia(wikidata, wiki))
        except Exception as e:
            if not permanent(e):
                errors["Wikipedia"].append(e)
                return found, False
    return found, True


def permanent(e):
    """True for a 404 (a stale MusicBrainz id, a missing page) or a refusal (robots.txt, a bot challenge)."""
    return isinstance(e, PermissionError) or (isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 404)


def find_artists(names, ticketmaster, mb, wiki, today=None, cache_path=CACHE):
    """Artist info for each name in `names` that something is known about. `ticketmaster` maps a name to what
    its attraction gave (`tm_artist`). `mb` fetches from MusicBrainz, `wiki` from Wikidata and Wikipedia.
    Returns (artists, the errors of failed lookups by source)."""
    today = today or date.today()
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    stale = (today - RECHECK).isoformat()
    errors = {"MusicBrainz": [], "Wikipedia": []}
    artists, looked_up, waiting, failing = {}, 0, 0, 0
    names = dict.fromkeys(names)
    for name in names:
        tm, found = ticketmaster.get(name, {}), {}
        if tm.get("mbid") or not tm.get("links"):
            entry = cache.get(name)
            if entry and entry["checked"] >= stale and tm.get("mbid") in (None, entry.get("mbid")):
                found = entry
            elif looked_up >= LOOKUPS or failing >= MAX_ERRORS:
                waiting += 1
            else:
                looked_up += 1
                found, complete = look_up(name, tm.get("mbid"), mb, wiki, errors)
                failing = 0 if complete else failing + 1
                if complete:
                    cache[name] = {"checked": today.isoformat(), **found}
        links = {**found.get("links", {}), **tm.get("links", {})}  # Ticketmaster's win
        info = drop_empty({
            "about": found.get("about"),
            "about_source": found.get("about_source"),
            "image": tm.get("image"),
            "links": {kind: links[kind] for kind in KINDS if kind in links},
            "mbid": tm.get("mbid") or found.get("mbid"),
        })
        if info:
            artists[name] = info
    # Acts that left the calendar stay until their entry is due for a recheck.
    cache = {name: entry for name, entry in cache.items() if name in names or entry["checked"] >= stale}
    cache_path.parent.mkdir(exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"Artists: info for {len(artists)} of {len(names)} names, {looked_up} looked up, "
          f"{waiting} waiting for the next run")
    return artists, errors


def drop_empty(fields):
    return {k: v for k, v in fields.items() if v not in (None, "", [], {})}
