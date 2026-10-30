"""Prototype additions for scraper/methods.py. Tested only against saved probe files."""

import html
import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

# ---------------------------------------------------------------- Live Nation (Next.js RSC)

_DECODER = json.JSONDecoder()
_PUSH = re.compile(r"self\.__next_f\.push\((\[.*\])\)\s*;?\s*$", re.S)


def rsc_text(page_html):
    """Join the React Server Component chunks a Next.js app-router page embeds in <script> tags."""
    soup = BeautifulSoup(page_html, "html.parser")
    parts = []
    for tag in soup.find_all("script"):
        m = _PUSH.match(tag.string or "")
        if not m:
            continue
        try:
            chunk = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if len(chunk) > 1 and isinstance(chunk[1], str):
            parts.append(chunk[1])
    return "".join(parts)


def rsc_events(page_html):
    """Return Live Nation event dicts from every "events":[...] array in the RSC payload, de-duplicated."""
    text = rsc_text(page_html)
    found, seen = [], set()
    for m in re.finditer(r'"events":\[', text):
        try:
            arr, _ = _DECODER.raw_decode(text, m.end() - 1)
        except ValueError:
            continue
        for e in arr:
            if not isinstance(e, dict) or "event_data_type" not in e:
                continue
            key = (e.get("event_data_type"), e.get("discovery_id") or e.get("id"))
            if key not in seen:
                seen.add(key)
                found.append(e)
    return found


_TIME = r"(\d{1,2}(?::\d\d)?\s*[ap]\.?\s*m\.?)"


def _clock(text):
    """'7PM' / '6:30 pm' -> '19:00' / '18:30'."""
    m = re.match(r"(\d{1,2})(?::(\d\d))?\s*([ap])", text.strip(), re.I)
    if not m:
        return None
    h, mins, ap = int(m.group(1)) % 12, int(m.group(2) or 0), m.group(3).lower()
    return f"{h + (12 if ap == 'p' else 0):02d}:{mins:02d}"


def _plain(value):
    """Strip tags and decode entities (twice, for double-encoded text)."""
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    text = html.unescape(html.unescape(text)).replace("\\n", " ").replace("\xa0", " ")
    return " ".join(text.split())


def livenation_to_event(e, page):
    info = _plain(e.get("important_info"))
    doors = re.search(r"Doors:?\s*" + _TIME, info, re.I)
    show = re.search(r"Show:?\s*" + _TIME, info, re.I)
    age = re.search(r"\b(all ages|21\s*\+|18\s*\+|16\s*\+)", f"{info} {e.get('name', '')}", re.I)
    date, time = e.get("start_date_local"), (e.get("start_time_local") or "")[:5]
    # Passes and multi-day bundles use 00:00:01 as a placeholder time: keep the date only.
    start = date if not time or time == "00:00" else f"{date}T{time}"
    artists = [a.get("name") for a in e.get("artists") or [] if a.get("name")]
    image = (e.get("image") or {}).get("url")
    return {
        "title": _plain(e.get("name")),
        "start": start,
        "url": urljoin(page, e["url"]) if e.get("url") else page,
        "image": image,
        "price": None,  # Live Nation sites don't publish prices in the page
        # extra fields
        "room": e.get("venue_room_name") or e.get("venue_name"),
        "headliner": artists[0] if artists else None,
        "support": artists[1:],
        "doors": _clock(doors.group(1)) if doors else None,
        "show": _clock(show.group(1)) if show else None,
        "age": re.sub(r"\s+\+", "+", age.group(1).lower()) if age else None,
        "status": e.get("status_code"),  # onsale / rescheduled / ... ; absent on "livenation" records
        "genre": e.get("genre"),
        "start_utc": e.get("start_datetime_utc"),
        "id": e.get("tm_id") or e.get("discovery_id") or e.get("id"),
    }


def livenation(venue, fetcher):
    """Live Nation venue sites (theecho.com, thebelasco.com, wiltern.com, hollywoodpalladium.com ...)."""
    page = venue["events_page"]
    text = fetcher.get(page).text
    events = rsc_events(text)
    if not events:  # template changed: fall back to the page's JSON-LD
        return [to_event(e, page) for e in jsonld_events(text)]
    return [livenation_to_event(e, page) for e in events]


# ---------------------------------------------------------------- improved JSON-LD to_event

_STATUS = {"EventCancelled": "cancelled", "EventPostponed": "postponed", "EventRescheduled": "rescheduled",
           "EventMovedOnline": "online", "EventScheduled": None}


def _offers(data):
    offers = data.get("offers") or []
    offers = offers if isinstance(offers, list) else [offers]
    return [o for o in offers if isinstance(o, dict)]


def _num(v):
    try:
        return float(str(v).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def _names(value):
    value = value if isinstance(value, list) else [value] if value else []
    out = []
    for p in value:
        name = p.get("name") if isinstance(p, dict) else p
        if name:
            out.append(_plain(name))
    return out


def to_event(data, page):
    offers = _offers(data)
    prices = [p for o in offers for p in (_num(o.get("price")), _num(o.get("lowPrice")), _num(o.get("highPrice")))
              if p is not None and p > 0]  # price "0" on The Vermont means "unknown/RSVP", not free
    url = data.get("url") or next((o.get("url") for o in offers if o.get("url")), None)
    ticket = next((o.get("url") for o in offers if o.get("url")), None) or url
    avail = " ".join(str(o.get("availability", "")) for o in offers)
    status = str(data.get("eventStatus") or "").rsplit("/", 1)[-1]
    performers = _names(data.get("performer"))
    return {
        "title": _plain(data.get("name")),
        "start": data.get("startDate"),
        "url": urljoin(page, url) if isinstance(url, str) else page,
        "image": _image(data.get("image"), page),
        "price": f"{min(prices):g}" if prices else None,
        # extra fields
        "price_max": f"{max(prices):g}" if len(prices) > 1 and max(prices) != min(prices) else None,
        "ticket_url": urljoin(page, ticket) if isinstance(ticket, str) else None,
        "end": data.get("endDate"),
        "doors": data.get("doorTime"),
        "status": "soldout" if "SoldOut" in avail else _STATUS.get(status, status or None),
        "performers": performers,
        "room": _plain((data.get("location") or {}).get("name")) if isinstance(data.get("location"), dict) else None,
        "description": _plain(data.get("description"))[:500] or None,
    }


# unchanged helpers copied from methods.py so this file runs on its own
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
    if isinstance(data, list):
        for item in data:
            yield from _walk(item)
    elif isinstance(data, dict):
        types = data.get("@type", [])
        types = [types] if isinstance(types, str) else types
        if any(t.endswith("Event") or t == "Festival" for t in types):
            yield data
        else:
            for key in ("@graph", "itemListElement", "item"):
                if key in data:
                    yield from _walk(data[key])


def _image(value, page):
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, dict):
        value = value.get("url")
    return urljoin(page, value) if isinstance(value, str) else None


# ---------------------------------------------------------------- Greek: time + ticket link from the HTML cards

def greek_cards(page_html, page):
    """Simpleview 'asm-date-list' cards: adds time and Ticketmaster link that the JSON-LD lacks."""
    soup = BeautifulSoup(page_html, "html.parser")
    out = {}
    for card in soup.select("section.asm-date-list article, section.asm-hero-mosaic article"):
        link = card.find("a", href=re.compile(r"/event/"))
        if not link:
            continue
        text = " ".join(card.get_text(" ", strip=True).split())
        t = re.search(r"\b(\d{1,2}:\d\d\s*[AP]M)\b", text)
        tix = card.find("a", href=re.compile(r"ticketmaster\.com|axs\.com"))
        out[urljoin(page, link["href"])] = {"time": _clock(t.group(1)) if t else None,
                                             "ticket_url": tix["href"] if tix else None}
    return out
