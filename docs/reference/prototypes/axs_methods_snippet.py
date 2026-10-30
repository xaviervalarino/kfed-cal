"""Proposed additions to scraper/methods.py (tested offline by test_snippet.py)."""
import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def aeg(venue, fetcher):
    """AEG/Goldenvoice venue sites (Fonda, Roxy): the homepage names a static JSON file on Azure Blob storage
    (<div class="js-axs-events-section" data-file=".../json/events/<id>/events.json">) that holds the whole calendar.
    Set venue["feed"] to skip the homepage lookup."""
    page = venue["events_page"]
    feed = venue.get("feed")
    if not feed:
        soup = BeautifulSoup(fetcher.get(page).text, "html.parser")
        files = [d["data-file"] for d in soup.select(".js-axs-events-section[data-file]") if "/json/events/" in d["data-file"]]
        if not files:
            raise ValueError("no AEG events feed found on the page")
        feed = files[0]
    data = fetcher.get(feed).json()
    events = data.get("events", [])
    total = (data.get("meta") or {}).get("total")
    if total is not None and int(total) != len(events):
        print(f"::warning::{venue['name']}: AEG feed has {len(events)} of {total} events")
    return [e for e in (_aeg_event(x, page) for x in events) if e]


def _aeg_event(e, page):
    ticketing = e.get("ticketing") or {}
    start = e.get("eventDateTime") or ""
    if ticketing.get("statusId") == 2 or not re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d", start):  # cancelled, or "TBD"
        return None
    title = e.get("title") or {}
    low, high = _dollars(e.get("ticketPriceLow")), _dollars(e.get("ticketPriceHigh"))
    price = (f"${low:g}" + (f"-${high:g}" if high and high != low else "")) if low else None
    return {
        "title": _text(title.get("eventTitleText") or title.get("headlinersText")),
        "start": start[:16],  # venue-local time, e.g. "2026-10-30T21:00"
        "url": urljoin(page, f"/events/detail?event_id={e['eventId']}"),
        "image": _aeg_image(e),
        "price": price,
    }


def _dollars(value):
    m = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(m.group()) if m and float(m.group()) > 0 else None  # the feed writes "$0" when no price is set


def _aeg_image(e):
    for media in (e.get("media"), e.get("relatedMedia")):  # relatedMedia falls back to the artist's photos
        if isinstance(media, dict):
            for key in ("86", "17", "18"):  # 1200x628, 678x399, 564x564
                name = (media.get(key) or {}).get("file_name")
                if name and "/defaults/" not in name:
                    return name
    return None


_MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}


def hollywood_bowl(venue, fetcher):
    """Hollywood Bowl homepage "Upcoming Events" cards. One card per program; dates only, no times or prices.
    A multi-night run ("Oct 21 - 31, 2026") becomes one event on its first night not yet past."""
    page = venue["events_page"]
    soup = BeautifulSoup(fetcher.get(page).text, "html.parser")
    today = date.today()
    events = []
    for card in soup.select(".gallery-calendar li.gallery-item"):
        link, name, when = card.select_one("a[title]"), card.select_one(".gallery-card__title"), card.select_one("time")
        if not (link and name and when):
            continue
        dates = _bowl_dates(when.get_text(" ", strip=True))
        if not dates:
            continue
        first, last = dates
        start = max(first, min(today, last))
        img = card.select_one("img")
        events.append({
            "title": " / ".join(s.strip() for s in name.get_text("\n").split("\n") if s.strip()),
            "start": start.isoformat(),
            "url": urljoin(page, link["href"]),
            "image": urljoin(page, img["src"]) if img and img.get("src") else None,
            "price": None,
        })
    return events


def _bowl_dates(text):
    """'Oct 21 – 31, 2026', 'Oct 29, 2026 – Nov 01, 2026', 'June 06, 2027' -> (first, last)."""
    years = re.findall(r"\d{4}", text)
    if not years:
        return None
    found, month = [], None
    for part in re.split(r"\s*[–—-]\s*", text):
        m = re.match(r"([A-Za-z]+)\.? (\d{1,2})(?:, (\d{4}))?", part)
        if m and m.group(1)[:3].lower() in _MONTHS:
            month, day, year = _MONTHS[m.group(1)[:3].lower()], int(m.group(2)), m.group(3)
        elif month and re.match(r"\d{1,2}\b", part):
            day, year = int(re.match(r"\d{1,2}", part).group()), None
        else:
            continue
        found.append(date(int(year or years[-1]), month, day))
    return (found[0], found[-1]) if found else None


def _text(value):  # same as methods._text
    import html
    return html.unescape(str(value)).strip() if value else ""
