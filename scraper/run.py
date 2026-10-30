"""Scrape every venue in venues.json and write site/events.json. Run with `python -m scraper.run`."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .fetch import Fetcher
from .methods import METHODS
from .venues import load_venues

OUTPUT = Path(__file__).resolve().parent.parent / "site" / "events.json"


def warn(message):
    # The ::warning:: prefix makes GitHub Actions show it on the run's summary page.
    print(f"::warning::{message}")


def parse_start(value, tz):
    """Return the event's start as venue-local "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM", or None."""
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    try:
        start = datetime.fromisoformat(value)
    except ValueError:
        return None
    if len(value) == 10:  # date only, no time given
        return start.date().isoformat()
    if start.tzinfo:
        start = start.astimezone(tz)
    return start.strftime("%Y-%m-%dT%H:%M")


def clean(raw_events, venue_name, tz):
    today = datetime.now(tz).date().isoformat()
    events, seen = [], set()
    for e in raw_events:
        start = parse_start(e.get("start"), tz)
        if not e.get("title") or not start or start[:10] < today:
            continue
        key = (start[:10], re.sub(r"[^a-z0-9]", "", e["title"].lower()))
        if key in seen:
            continue
        seen.add(key)
        events.append({**e, "start": start, "venue": venue_name})
    return events


def main():
    tz_name, venues = load_venues()
    tz = ZoneInfo(tz_name) if tz_name else timezone.utc
    today = datetime.now(tz).date().isoformat()

    previous = {}
    if OUTPUT.exists():
        for e in json.loads(OUTPUT.read_text()).get("events", []):
            if e["start"][:10] >= today:
                previous.setdefault(e["venue"], []).append(e)

    fetcher = Fetcher()
    all_events = []
    for venue in venues:
        name = venue["name"]
        try:
            events = clean(METHODS[venue["method"]](venue, fetcher), name, tz)
        except Exception as e:  # one broken venue shouldn't stop the rest
            events = []
            warn(f"{name}: scrape failed ({type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''})")
        if not events and previous.get(name):
            warn(f"{name}: found 0 events. The last run found {len(previous[name])}. "
                 "The scraper keeps the old events. The venue's website may have changed.")
            events = previous[name]
        print(f"{name}: {len(events)} events")
        all_events.extend(events)

    all_events.sort(key=lambda e: (e["start"], e["venue"], e["title"]))
    OUTPUT.write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "venues": [{"name": v["name"], "website": v.get("website") or v["events_page"]} for v in venues],
        "events": all_events,
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(all_events)} events to site/events.json")


if __name__ == "__main__":
    main()
