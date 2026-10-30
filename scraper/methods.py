"""Ways to get events from a venue. Each method takes (venue, fetcher, report) and returns a list of raw
events: dicts with the fields in docs/DATA.md (title, start and url at least). `run.clean` tidies them.

`report` is a dict a method can add to for the status page: "partial" (why the list is incomplete),
"note" (anything else worth showing), "haiku" (tokens used). One method per source platform, not per venue."""

import base64
import html
import json
import os
import re
from datetime import date, datetime, timedelta
from urllib.parse import urljoin

import anthropic
from bs4 import BeautifulSoup

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]


def auto(venue, fetcher, report):
    """Read the schema.org Event data that many venue and ticketing sites embed in their pages."""
    page = venue["events_page"]
    events = jsonld_events(fetcher.get(page).text)
    return [to_event(e, page) for e in events]


def jsonld_events(page_html):
    soup = BeautifulSoup(page_html, "html.parser")
    found = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            found.extend(_walk(json.loads(tag.string or "", strict=False)))
        except json.JSONDecodeError:
            continue
    return found


def _walk(data):
    """Find Event objects, including ones nested in lists, @graph, ItemList, or a Place's events (DICE)."""
    if isinstance(data, list):
        for item in data:
            yield from _walk(item)
    elif isinstance(data, dict):
        types = data.get("@type", [])
        types = [types] if isinstance(types, str) else types
        if any(t.endswith("Event") or t == "Festival" for t in types):
            yield data
        else:
            for key in ("@graph", "itemListElement", "item", "event", "events"):
                if key in data:
                    yield from _walk(data[key])


def to_event(data, page):
    offers = data.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        offers = {}
    url = data.get("url") or offers.get("url")
    price = offers.get("price") or offers.get("lowPrice")
    return {
        "title": _text(data.get("name")),
        "start": data.get("startDate"),
        "url": urljoin(page, url) if isinstance(url, str) else page,
        "image": _image(data.get("image"), page),
        "price": str(price) if price not in (None, "") else None,
    }


def _text(value):
    return html.unescape(str(value)).strip() if value else ""


def _image(value, page):
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, dict):
        value = value.get("url")
    return urljoin(page, value) if isinstance(value, str) else None


# --- Ticketmaster Discovery API: most venues. Needs TICKETMASTER_API_KEY.
TICKETMASTER = "https://app.ticketmaster.com/discovery/v2/events.json"


def ticketmaster(venue, fetcher, report):
    """Every event Ticketmaster lists at the venue's Ticketmaster venue id(s)."""
    key = os.environ.get("TICKETMASTER_API_KEY")
    if not key:
        raise RuntimeError("TICKETMASTER_API_KEY is not set.")
    ids = venue["params"]["venue_ids"]
    events = []
    for venue_id in ids:
        page, pages = 0, 1
        while page < pages:
            params = {"venueId": venue_id, "size": 200, "sort": "date,asc", "page": page, "apikey": key}
            data = fetcher.get(TICKETMASTER, params=params).json()
            events += [tm_event(e, room=len(ids) > 1) for e in data.get("_embedded", {}).get("events", [])
                       if not e.get("test") and not _add_on(e)]
            pages = data.get("page", {}).get("totalPages", 0)
            page += 1
    return events


def tm_event(e, room=False):
    """One Discovery API event. `room` keeps Ticketmaster's venue name, for venues with more than one id."""
    when = e["dates"]["start"]
    day = when.get("localDate")  # missing while the date is TBA
    # pleaseNote often says "Doors: 7PM | Show: 8PM | All Ages"; localTime is sometimes the doors time.
    note = e.get("pleaseNote") or ""
    doors = clock((e.get("doorsTimes") or {}).get("localTime")) or _labelled("door", note)
    show = _labelled("show", note)
    time = show or clock(when.get("localTime"))
    if when.get("noSpecificTime") or when.get("timeTBA") or (not show and time == doors):
        time = None  # no time, or only a doors time: that one goes in doors, not in start
    wide = [i for i in e.get("images") or [] if i.get("ratio") == "16_9" and (i.get("width") or 0) <= 1200]
    lows = [p["min"] for p in e.get("priceRanges") or [] if p.get("min")]
    highs = [p["max"] for p in e.get("priceRanges") or [] if p.get("max")]
    code = e["dates"].get("status", {}).get("code")
    return {
        "title": e["name"],
        "support": [a["name"] for a in e.get("_embedded", {}).get("attractions", [])[1:]],  # headliner first
        "start": f"{day}T{time}" if day and time else day,
        "doors": doors,
        "price": dollars(min(lows), max(highs or lows)) if lows else None,
        "age": find_age((e.get("ageRestrictions") or {}).get("ageRuleDescription")) or find_age(note),
        "status": code if code in ("cancelled", "postponed", "rescheduled") else None,
        "room": e.get("_embedded", {}).get("venues", [{}])[0].get("name") if room else None,
        "url": e.get("url"),
        "ticket_url": e.get("url"),
        "image": max(wide, key=lambda i: i.get("width") or 0)["url"] if wide else None,  # largest up to 1200px
        "source_id": f"tm:{e['id']}",
    }


def _add_on(e):
    """Seat upgrades and merch ("Upgrade: Premium Viewing Deck") are listed as events too."""
    kind = ((e.get("classifications") or [{}])[0].get("type") or {}).get("name")
    return kind in ("Upsell", "Merchandise")


def _labelled(label, text):
    """The time after "Show:" or "Doors:" in a line like "Doors: 7PM | Show: 8PM"."""
    m = re.search(rf"\b{label}s?:\s*([^|]+)", text, re.I)
    return clock(m.group(1)) if m else None


# --- DICE venue pages: Zebulon, the Paramount, the Glass House.
def dice_venue(venue, fetcher, report):
    """A dice.fm/venue/<slug> page. Its __NEXT_DATA__ script holds the venue's next events.
    Plain request only: DICE shows headless browsers a bot challenge."""
    soup = BeautifulSoup(fetcher.get(venue["events_page"]).text, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        raise ValueError("The DICE page has no event data. DICE may have changed the page.")
    sections = (json.loads(tag.string)["props"]["pageProps"].get("profile") or {}).get("sections") or []
    events = [dice_event(e) for section in sections for e in section.get("events") or []]
    if any(section.get("load_more") for section in sections):  # a "load more" button the scraper does not press
        report["partial"] = f"DICE shows only the next {len(events)} shows."
    return events


def dice_event(e):
    # DICE writes the lineup into the name: "The Tubs, Touch Girl Apple Blossom". After a colon, commas belong
    # to the tour name instead ("Bodysnatcher: Hell Is Here, Hell Is Home Tour").
    name = (e.get("name") or "").strip()
    parts = [name] if ": " in name else [part.strip() for part in name.split(", ") if part.strip()]
    title, *support = parts or [""]
    price = e.get("price") or {}
    if price.get("amount") == 0:
        cost = "free"
    elif price.get("amount"):
        cost = dollars(price["amount"] / 100)
    elif price.get("amount_from"):
        cost = "from " + dollars(price["amount_from"] / 100)
    else:
        cost = None
    return {
        "title": title,
        "support": support,
        "start": (e.get("dates") or {}).get("event_start_date"),
        "price": cost,
        "status": (e.get("status") or "").replace("-", "_"),  # "on-sale", "sold-out", ...: clean keeps the known ones
        "url": f"https://dice.fm/event/{e['id']}",
        "image": (e.get("images") or {}).get("square"),
        "source_id": f"dice:{e['id']}",
    }


# --- Tessera ticketing: Lodge Room.
TESSERA_SHOW = re.compile(r"eventObjects\.push\((\{.*?\})\);", re.S)


def tessera(venue, fetcher, report):
    """The venue's page lists each show in an `eventObjects.push({...});` call. The Tessera ticket API
    (params.api) adds prices and sold-out flags. It needs a visitor session, started as the venue's own page
    does: a POST with no body, then the session id in a SessionId header."""
    page = venue["events_page"]
    shows = [json.loads(raw) for raw in TESSERA_SHOW.findall(fetcher.get(page).text)]
    if shows:
        api, ids = venue["params"]["api"], ",".join(str(s["id"]) for s in shows)
        try:
            start = fetcher.post(f"{api}/authorization/session", headers={"Content-Type": "application/json"})
            session = start.json()["sessionId"]
            found = fetcher.get(f"{api}/products", params={"ids": ids}, headers={"SessionId": session}).json()
            products = {str(p.get("frontendId")): p for p in found}
            return [tessera_event(s, products.get(str(s["id"]), {}), page) for s in shows]
        except Exception as e:  # any surprise in the price data: the listing is still good without prices
            report["note"] = f"Prices could not be loaded ({describe(e)})."
    return [tessera_event(s, {}, page) for s in shows]


def tessera_event(show, product, page):
    tiers = product.get("campaigns") or []
    prices = [c["price"] for c in tiers if c.get("price") is not None]
    sold_out = product.get("isSoldOut") or (tiers and all(c.get("isSoldOut") for c in tiers))
    return {
        "title": html.unescape(" / ".join(show.get("mainArtist") or [])),
        "support": [html.unescape(a) for a in show.get("additionalArtists") or []],
        "start": datetime.strptime(show["eventDate"].upper(), "%m/%d/%Y %I:%M %p").isoformat(),
        "doors": clock(show.get("doors")),
        "price": dollars(min(prices), max(prices)) if prices else None,
        "status": "sold_out" if sold_out else None,
        "url": show.get("link") or page,
        "image": show.get("image"),
        "source_id": f"tessera:{show['id']}",
    }


# --- The Events Calendar (WordPress "tribe" plugin) REST API: The Vermont.
def tribe_events(venue, fetcher, report):
    """events_page is the plugin's REST URL, e.g. https://site/wp-json/tribe/events/v1/events?per_page=50.
    It lists upcoming events only and pages with next_rest_url."""
    url, events = venue["events_page"], []
    for _ in range(20):  # 20 pages of 50 is far more than any venue lists
        data = fetcher.get(url).json()
        events += [tribe_event(e) for e in data.get("events") or []
                   if e.get("status", "publish") == "publish" and not e.get("hide_from_listings")]
        url = html.unescape(data.get("next_rest_url") or "")
        if not url:
            break
    return events


def tribe_event(e):
    fields = e.get("custom_fields")
    fields = fields.values() if isinstance(fields, dict) else []  # an empty list when there are none
    performer = next((f.get("value") for f in fields if (f.get("label") or "").lower() == "performer"), "")
    image = e.get("image")
    return {
        "title": _plain(e.get("title")),
        "support": _plain(performer).split(", ") if performer else [],
        "start": e["start_date"][:10] if e.get("all_day") else e["start_date"],
        "price": _plain(e.get("cost")) or None,
        "age": find_age(_plain(e.get("description"))),
        "url": e.get("url"),
        "ticket_url": _plain(e.get("website")) or None,
        "image": image.get("url") if isinstance(image, dict) else None,
        "source_id": f"tribe:{e['id']}",
    }


def _plain(value):
    """Text from a value that may hold HTML tags and (double-)escaped entities."""
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return " ".join(html.unescape(html.unescape(text)).split())


# --- Permanent Records Roadhouse: a hand-made HTML table.
PR_DATE = re.compile(r"(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*-\s*(.+))?", re.I)


def permanent_records(venue, fetcher, report):
    page = venue["events_page"]
    return permanent_records_events(fetcher.get(page).text, page, date.today())


def permanent_records_events(page_html, page, today):
    """Each show is a table row: image | "Friday, October 30th - 6PM" and one act per line | price and
    ticket link. Dates have no year: take the next one from `today`."""
    events = []
    for row in BeautifulSoup(page_html, "html.parser").find_all("tr"):
        cells = row.find_all("td", recursive=False)
        italic = cells[1].find("i") if len(cells) == 3 else None
        date_lines = italic.get_text("\n", strip=True).splitlines() if italic else []
        m = PR_DATE.search(" ".join(date_lines))
        if not m:
            continue
        lines = [line for line in cells[1].get_text("\n", strip=True).splitlines() if line not in date_lines]
        if not lines or lines[0].lower().startswith("details coming soon") or "closed for" in " ".join(lines).lower():
            continue  # a placeholder or a closed night, not a show
        if lines[0].endswith((":", "...")) and len(lines) > 1:  # "Stepping Stone Presents:" / "An Evening with..."
            lines[:2] = [f"{lines[0]} {lines[1]}"]
        try:
            day = date(today.year, MONTHS.index(m.group(1).lower()) + 1, int(m.group(2)))
        except ValueError:  # shortcut: skips a typo like "February 30th", and Feb 29 listed in the year before
            continue
        if day < today - timedelta(days=60):  # a January show listed in December
            day = day.replace(year=today.year + 1)
        time = clock(m.group(3))
        price = []  # "$15 ADVANCE" / "$20 DOS" are two prices; "$5 PER" / "PLAYER" is one that wrapped
        for line in cells[2].get_text("\n", strip=True).splitlines():
            if line.lower().startswith(("buy tickets", "rsvp")):
                continue
            if price and not line.startswith("$"):
                price[-1] += f" {line}"
            else:
                price.append(line)
        link = cells[2].find("a", href=True)
        image = cells[0].find("img", src=True)
        events.append({
            "title": lines[0],
            "support": lines[1:],
            "start": f"{day.isoformat()}T{time}" if time else day.isoformat(),
            "price": " / ".join(price) if price else None,
            "url": link["href"] if link else page,
            "ticket_url": link["href"] if link else None,
            "image": urljoin(page, image["src"]) if image else None,
        })
    return events


# --- Monty Bar: a weekly flyer image read by Claude Haiku. Needs ANTHROPIC_API_KEY.
HAIKU = "claude-haiku-5-5"
MONTY_FLYER = re.compile(r"https://montybar\.com/wp-content/uploads/[\w/]+/MONTY-weekly-[\d-]+?(?:-\d+x\d+)?\.(?:png|jpe?g)")
MONTY_PROMPT = """This is the weekly events flyer for Monty Bar, a bar in Los Angeles. Today is {today}.
List every event on the flyer, one entry per event. Use the year of the week shown on the flyer.
Copy text exactly as written. Do not guess: if a day has no event, leave it out.
Keep all text that belongs to an event (support acts, DJs, "performing live", prices, ages) in its details.
Put any text you cannot tie to one event in unplaced_text."""
MONTY_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "description": "Start time as HH:MM (24-hour), or empty if not shown"},
                    "title": {"type": "string", "description": "Main event or act name, as written"},
                    "details": {"type": "string", "description": "All other text for this event, verbatim"},
                    "price": {"type": "string", "description": "The price as written, or empty if not shown"},
                },
                "required": ["date", "time", "title", "details", "price"],
                "additionalProperties": False,
            },
        },
        "unplaced_text": {"type": "string", "description": "Flyer text not tied to a specific day, verbatim"},
    },
    "required": ["events", "unplaced_text"],
    "additionalProperties": False,
}


def monty_flyer(venue, fetcher, report):
    """The flyer covers Wednesday to Sunday of the current week, so the scrape runs on Wednesdays."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")
    page = venue["events_page"]
    found = MONTY_FLYER.findall(fetcher.get(page).text)
    if not found:
        raise ValueError("Found no weekly flyer image on the page.")
    flyer = re.sub(r"-\d+x\d+(?=\.\w+$)", "", found[0])  # the full-size image, not a thumbnail
    image = fetcher.get(flyer)
    response = anthropic.Anthropic().messages.create(
        model=HAIKU,
        max_tokens=16000,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
                                         "media_type": image.headers.get("content-type", "image/png").split(";")[0],
                                         "data": base64.standard_b64encode(image.content).decode()}},
            {"type": "text", "text": MONTY_PROMPT.format(today=date.today())},
        ]}],
        output_config={"format": {"type": "json_schema", "schema": MONTY_SCHEMA}},
    )
    report["haiku"] = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
    if response.stop_reason != "end_turn":
        raise ValueError(f"Claude Haiku did not finish reading the flyer (stop reason: {response.stop_reason}).")
    shows = json.loads(next(b.text for b in response.content if b.type == "text"))["events"]
    if shows and max(s["date"] for s in shows) < date.today().isoformat():
        raise ValueError("The flyer on the site is for a past week. This week's flyer may not be up yet.")
    return [{
        "title": s["title"],
        "details": s["details"],
        "start": f"{s['date']}T{clock(s['time'])}" if clock(s["time"]) else s["date"],
        "price": s["price"],
        "url": page,
        "image": flyer,
    } for s in shows]


METHODS = {
    "auto": auto,
    "dice_venue": dice_venue,
    "monty_flyer": monty_flyer,
    "permanent_records": permanent_records,
    "tessera": tessera,
    "ticketmaster": ticketmaster,
    "tribe_events": tribe_events,
}


# --- Small helpers shared by the methods and run.py.
def describe(error):
    """"KeyError: 'sessionId'": an exception's type and the first line of its message, for status notes."""
    message = str(error).splitlines()[0] if str(error).strip() else "no details"
    return f"{type(error).__name__}: {message}"


def clock(text):
    """"7PM", "7:30 pm", "19:00:00" -> "19:00"; a range "12-8PM" -> its start, "12:00". None when there is no time."""
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?(?::\d{2})?\s*(?:[-–]\s*\d{1,2}(?::\d{2})?\s*)?([ap])\.?m\b", text or "", re.I)
    if m:
        hour = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "p" else 0)
        return f"{hour:02d}:{int(m.group(2) or 0):02d}"
    m = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", text or "")
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else None


def find_age(text):
    """"All Ages", "18 & Over", "21+ ONLY" -> "All ages", "18+", "21+". None when the text has no age."""
    text = (text or "").lower()
    if "all ages" in text:
        return "All ages"
    m = re.search(r"\b(18|21)\s*(\+|& over|and over|& up|and up)", text)
    return f"{m.group(1)}+" if m else None


def dollars(low, high=None):
    """16, 19 -> "$16–19". 26.5 -> "$26.50"."""
    def amount(x):
        return f"{x:.2f}".removesuffix(".00")
    return f"${amount(low)}" if high is None or high == low else f"${amount(low)}–{amount(high)}"
