"""Proposed addition to scraper/methods.py: The Events Calendar (WordPress "tribe") REST API."""
import html
import re
from datetime import datetime
from zoneinfo import ZoneInfo


def tribe_events(venue, fetcher):
    """WordPress sites running The Events Calendar (e.g. vermonthollywood.com).
    venue["feed"] defaults to <events_page origin>/wp-json/tribe/events/v1/events?per_page=50.
    The API returns upcoming events only (default start_date = today) and pages via next_rest_url."""
    url = venue.get("feed") or re.match(r"https?://[^/]+", venue["events_page"]).group() + \
        "/wp-json/tribe/events/v1/events?per_page=50"
    events, seen = [], set()
    for _ in range(20):  # safety cap: 20 pages x 50 = 1000 events
        data = fetcher.get(url).json()
        for e in data.get("events") or []:
            if e.get("id") in seen or e.get("status", "publish") != "publish" or e.get("hide_from_listings"):
                continue
            seen.add(e.get("id"))
            events.append(_tribe_event(e))
        url = data.get("next_rest_url")
        if not url:
            break
    total = data.get("total")
    if total is not None and int(total) != len(seen):
        print(f"::warning::{venue.get('name')}: tribe API listed {len(seen)} of {total} events")
    return events


def _tribe_event(e):
    tz = ZoneInfo(e.get("timezone") or "America/Los_Angeles")
    start = datetime.strptime(e["start_date"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
    end = datetime.strptime(e["end_date"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz) if e.get("end_date") else None
    values = [v for v in (e.get("cost_details") or {}).get("values") or [] if _float(v) is not None]
    cost = _plain(e.get("cost"))
    price = cost or None  # "$16.50", "Free", "$20 - $35" as the site writes it
    if not price and values:
        price = "$" + "-$".join(sorted(set(values), key=float))
    venue = e.get("venue") if isinstance(e.get("venue"), dict) else {}
    performer = ((e.get("custom_fields") or {}).get("_ecp_custom_2") or {}).get("value")  # Vermont-specific label
    return {
        "title": _plain(e.get("title")),
        "start": start.date().isoformat() if e.get("all_day") else start.isoformat(),
        "url": e.get("url"),
        "image": (e.get("image") or {}).get("url") if isinstance(e.get("image"), dict) else None,
        "price": price,
        # extra fields
        "end": end.isoformat() if end else None,
        "ticket_url": e.get("website") or None,
        "room": _plain(venue.get("venue")) or None,
        "organizer": [_plain(o.get("organizer")) for o in e.get("organizer") or [] if o.get("organizer")],
        "categories": [c.get("name") for c in e.get("categories") or []],
        "tags": [t.get("name") for t in e.get("tags") or []],
        "performers": _plain(performer) or None,
        "description": _plain(e.get("description"))[:500] or None,
        "id": e.get("id"),
    }


def _float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _plain(value):
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return " ".join(html.unescape(html.unescape(text)).split())
