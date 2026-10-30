"""Scrape every venue in venues.json and write site/events.json and site/status.json (shapes in docs/DATA.md).
Run with `python -m scraper.run`."""

import json
import re
from datetime import datetime, time, timedelta, timezone
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit
from zoneinfo import ZoneInfo

from .fetch import Fetcher
from .methods import HAIKU, METHODS, describe, dollars, find_age
from .venues import load_venues

SITE = Path(__file__).resolve().parent.parent / "site"
OUTPUT = SITE / "events.json"
STATUS = SITE / "status.json"
# The status page's "source" column.
SOURCES = {"auto": "venue site", "dice_venue": "DICE", "monty_flyer": "flyer + Haiku",
           "permanent_records": "venue site", "tessera": "Tessera feed", "ticketmaster": "Ticketmaster",
           "tribe_events": "Events Calendar API"}
HAIKU_PRICE = {"input": 0.10, "output": 0.50}  # dollars per million tokens
# An event's fields in events.json, in this order.
FIELDS = ["venue", "title", "support", "details", "start", "doors", "price", "age", "status", "room", "url",
          "ticket_url", "image", "source_id"]
# A venue's fields in status.json, in this order.
ROW_FIELDS = ["name", "method", "source", "status", "events", "through", "with_time", "last_success", "note"]
STATUSES = {"sold_out", "cancelled", "postponed", "rescheduled"}
TRACKING = ("utm_", "fbclid", "gclid", "igshid", "mc_cid", "mc_eid")

STATUS_WORDS = {"soldout": "sold_out", "cancelled": "cancelled", "canceled": "cancelled", "postponed": "postponed",
                "rescheduled": "rescheduled"}
STATUS_PREFIX = re.compile(r"^(canceled|cancelled|postponed|rescheduled|sold out)\s*[:\-–—!]+\s*", re.I)
MOVED = re.compile(r"\(\s*moved (?:from|to) [^)]*\)|\bmoved from .+?(?:\s*[:\-–—]\s+|$)", re.I)
AGE_SUFFIX = re.compile(r"\s*[-–—(]?\s*(?:ages\s+)?(all ages|(?:18|21)\s*(?:\+|and over|& over|and up|& up))\s*\)?$", re.I)
PRESENTER = re.compile(r"^(.+?\bpresents?)\s*(?::|\s[-–—])\s*(.+)$", re.I)  # "PBW Presents: X", "X Presents - Y"
SUBTITLE = re.compile(r"\s+[-–—]\s+|(?<=\S)[-–—]\s+|:\s+")  # "Band - Tour", "Band- Tour", "Band: Tour"
WITH = re.compile(r"^(.+?)\s+(with\s+|w/\s*)(special guests?\s+)?(.+)$", re.I)
ACTS = re.compile(r",\s*|\s+[&+]\s+")


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
    if len(value) == 10 or start.time() == time(0, 0, 1):  # no time given, or the 00:00:01 placeholder
        return start.date().isoformat()
    if start.tzinfo:
        start = start.astimezone(tz)
    return start.strftime("%Y-%m-%dT%H:%M")


def clean(raw_events, venue_name, tz, today=None):
    """Tidy one venue's raw events: drop past, cancelled and duplicate events, split names into title, details
    and support, and normalize prices, times and links. Returns events with the fields in docs/DATA.md."""
    today = today or datetime.now(tz).date().isoformat()
    events, seen = [], set()
    for raw in raw_events:
        e = {k: v for k, v in raw.items() if v not in (None, "", [])}
        support = e.get("support") or []
        e["support"] = [support] if isinstance(support, str) else list(support)
        e["title"] = " ".join(unescape(e.get("title") or "").split())
        e["start"] = parse_start(e.get("start"), tz)
        e["venue"] = venue_name
        if not e["title"] or not e["start"] or e["start"][:10] < today:
            continue
        if re.match(r"moved to\b", e["title"], re.I):
            continue  # "MOVED TO THE BELASCO - ...": a pointer listed next to the real event
        split_name(e)
        if e.get("status") == "cancelled":
            continue  # the design has no style for cancelled shows
        e["support"] = tidy_support(e["support"], e["title"], e.get("details", ""))
        e["price"] = tidy_price(e["price"]) if e.get("price") else None
        for link in ("url", "ticket_url"):
            if isinstance(e.get(link), str):
                e[link] = tidy_url(e[link])
        if e.get("status") not in STATUSES:
            e["status"] = None
        if key(e.get("room")) == key(venue_name):
            e["room"] = None
        # Without a source id, the same show can be listed twice, once without its time.
        dedupe = e.get("source_id") or (e["start"][:10], key(e["title"]))
        if dedupe in seen:
            continue
        seen.add(dedupe)
        events.append({f: e[f] for f in FIELDS if e.get(f) not in (None, "", [])})
    return events


def split_name(e):
    """Pull what isn't the act's name out of an event's title, the way the design shows it:
    "CANCELED - X" sets the status; "PBW Presents: X - Some Tour" becomes title "X" with details
    "PBW Presents · Some Tour"; "X with Y" becomes title "X" with support "Y", but only after "w/" or
    "special guest", or when Y is already a known support act ("An Evening with River Shook" stays whole)."""
    title, details = e["title"], []
    m = STATUS_PREFIX.match(title)
    if m:
        e["status"] = STATUS_WORDS[key(m.group(1))]
        title = title[m.end():]
    if MOVED.search(title):
        if e.get("status") not in STATUSES:  # a source's "on_sale" doesn't count
            e["status"] = "rescheduled"
        title = MOVED.sub(" ", title).strip(" -–—:")
    m = AGE_SUFFIX.search(title)
    if m and m.start() > 0:  # "Ninajirachi (18 and Over)", "Takuya Nakamura - Ages 18+"
        e["age"] = e.get("age") or find_age(m.group(1))
        title = title[:m.start()]
    m = PRESENTER.match(title)
    if m:
        details.append(m.group(1))
        title = m.group(2)
    title = re.sub(r"(special guests?)\s*:", r"\1", title, flags=re.I)  # "w/Special Guest: X" isn't a subtitle
    parts = SUBTITLE.split(title, maxsplit=1)
    if len(parts) == 2 and all(p.strip() for p in parts):
        title, rest = parts
        if key(rest) in STATUS_WORDS:  # "Qendresa - SOLD OUT"
            e["status"] = STATUS_WORDS[key(rest)]
        else:
            details.append(rest)
    m = WITH.match(title)
    if m:
        known = {key(s) for s in e["support"]}
        acts = [m.group(4)] if key(m.group(4)) in known else ACTS.split(m.group(4))
        if m.group(2).lower().startswith("w/") or m.group(3) or all(key(a) in known for a in acts):
            title = m.group(1)
            e["support"] = acts + e["support"]
    e["title"] = title.strip()
    e["details"] = " · ".join(details + ([e["details"]] if e.get("details") else []))


def tidy_support(names, title, details):
    """Support acts without the ones already named in the title or details, junk like "etc", or repeats."""
    named = words(f"{title} {details}")
    out, seen = [], set()
    for name in names:
        name = re.sub(r"^(?:special guests?:?|with|w/|feat\.?|ft\.?)\s+", "", " ".join(str(name).split()), flags=re.I)
        name = re.sub(r"\s*[&+]\s*more\W*$|\s+and\s+more\W*$", "", name, flags=re.I).strip(" ,+&")
        k = key(name)
        if k and k not in ("etc", "more") and k not in seen and words(name) not in named:
            seen.add(k)
            out.append(name)
    return out


def tidy_price(price):
    price = " ".join(str(price).split())
    if price.lower().rstrip("!") == "free":
        return "free"
    if re.fullmatch(r"\$?0+(\.0+)?|\$", price):
        return None  # "$0" means the source has no price, not a free show
    if re.fullmatch(r"\d+(\.\d+)?", price):
        return dollars(float(price))
    return price


def tidy_url(url):
    """Drop tracking parameters (utm_*, fbclid, ...) from a link."""
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    kept = [(k, v) for k, v in query if not k.lower().startswith(TRACKING)]
    return url if len(kept) == len(query) else parts._replace(query=urlencode(kept)).geturl()


def key(text):
    """Text reduced to lowercase letters and digits, for comparing names."""
    return re.sub(r"[\W_]", "", (text or "").casefold())


def words(text):
    """"The F16's" -> " the f16s ": lowercase words between spaces, to find a name as whole words in a title."""
    found = re.findall(r"\w+", re.sub(r"['’]", "", text.casefold()))
    return " " + " ".join(found) + " "


def scrape(venue, fetcher, tz, today, previous):
    """Run one venue's method. Returns (events, status row, the method's report)."""
    name, method, report = venue["name"], venue.get("method"), {}
    row = {"name": name, "method": method, "source": SOURCES.get(method, "none")}
    if not method:
        return [], {**row, "status": "no_source", "note": venue.get("notes")}, report
    try:
        events, error = clean(METHODS[method](venue, fetcher, report), name, tz, today), None
    except Exception as e:  # one broken venue shouldn't stop the rest
        events, error = [], describe(e)
    if events:
        partial = report.get("partial") or venue.get("partial")
        return events, {**row, "status": "partial" if partial else "ok", "note": partial or report.get("note")}, report
    if previous:
        if error:
            warn(f"{name}: scrape failed ({error}). The scraper keeps the last run's events.")
        else:
            warn(f"{name}: found 0 events. The last run found {len(previous)}. "
                 "The scraper keeps the old events. The venue's website may have changed.")
        note = error or f"Found 0 events. The last run found {len(previous)}."
        return previous, {**row, "status": "kept", "note": note}, report
    if error:
        warn(f"{name}: scrape failed ({error}).")
        return [], {**row, "status": "failed", "note": error}, report
    return [], {**row, "status": "ok", "note": report.get("note")}, report


def next_run(after):
    """The next scheduled run: Wednesdays 10:17 UTC (the cron in .github/workflows/update.yml)."""
    run = after.replace(hour=10, minute=17, second=0, microsecond=0) + timedelta(days=(2 - after.weekday()) % 7)
    return run if run > after else run + timedelta(days=7)


def read_json(path):
    return json.loads(path.read_text()) if path.exists() else {}


def iso(moment):
    return moment.isoformat(timespec="seconds")


def main():
    started = datetime.now(timezone.utc)
    tz_name, venues = load_venues()
    tz = ZoneInfo(tz_name) if tz_name else timezone.utc
    today = datetime.now(tz).date().isoformat()

    previous = {}
    for e in read_json(OUTPUT).get("events", []):
        if e["start"][:10] >= today:
            previous.setdefault(e["venue"], []).append(e)
    last_success = {v["name"]: v.get("last_success") for v in read_json(STATUS).get("venues", [])}

    fetcher = Fetcher()
    all_events, rows, ids, haiku = [], [], set(), {"input_tokens": 0, "output_tokens": 0}
    for venue in venues:
        name = venue["name"]
        events, row, report = scrape(venue, fetcher, tz, today, previous.get(name, []))
        for k in haiku:
            haiku[k] += report.get("haiku", {}).get(k, 0)
        # The same Ticketmaster event can be listed at two venues: keep the first.
        events = [e for e in events if e.get("source_id") not in ids]
        ids.update(e["source_id"] for e in events if e.get("source_id"))
        row["events"] = len(events)
        if events:
            row["through"] = max(e["start"][:10] for e in events)
            row["with_time"] = round(sum("T" in e["start"] for e in events) / len(events), 2)
        succeeded = row["status"] in ("ok", "partial")
        row["last_success"] = iso(datetime.now(timezone.utc)) if succeeded else last_success.get(name)
        rows.append({k: row[k] for k in ROW_FIELDS if row.get(k) is not None})
        print(f"{name}: {row['status']}, {len(events)} events")
        all_events.extend(events)

    all_events.sort(key=lambda e: (e["start"], e["venue"], e["title"]))
    finished = datetime.now(timezone.utc)
    OUTPUT.write_text(json.dumps({
        "updated": iso(finished),
        "timezone": tz_name,
        "venues": [{"name": v["name"], "website": v["website"]} for v in venues],
        "events": all_events,
    }, indent=2, ensure_ascii=False) + "\n")
    cost = (haiku["input_tokens"] * HAIKU_PRICE["input"] + haiku["output_tokens"] * HAIKU_PRICE["output"]) / 1e6
    STATUS.write_text(json.dumps({
        "run": {"started": iso(started), "finished": iso(finished), "next": iso(next_run(finished))},
        "totals": {"events": len(all_events), "venues": len(venues)},
        "haiku": {"model": HAIKU, **haiku, "dollars": round(cost, 5)},
        "venues": rows,
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(all_events)} events to site/events.json and the run's status to site/status.json")


if __name__ == "__main__":
    main()
