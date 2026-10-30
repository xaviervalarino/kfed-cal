"""Candidate scraper methods for DICE venue pages and DICE-widget venue sites.
Tested offline against probe/out/*/plain.html. Usage: python -I dice_method.py <plain.html> [...]"""

import json
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

LA = ZoneInfo("America/Los_Angeles")
DICE_EVENT = "https://dice.fm/event/{id}"


def _la(iso):
    """DICE dates carry an offset (e.g. -08:00); normalize to America/Los_Angeles wall time."""
    if not iso:
        return None
    return datetime.fromisoformat(iso).astimezone(LA).isoformat()


def _dice_price(price):
    """price.amount (single tier) or price.amount_from (several tiers) are integer cents."""
    price = price or {}
    cents = price.get("amount")
    prefix = ""
    if cents is None:
        cents, prefix = price.get("amount_from"), "from "
    if cents is None:
        return None
    sym = "$" if price.get("currency", "USD") == "USD" else price.get("currency") + " "
    return f"{prefix}{sym}{cents / 100:.2f}"


def dice_next_events(page_html):
    """Events from a dice.fm/venue/<slug> page: __NEXT_DATA__ -> props.pageProps.profile.sections[*].events."""
    soup = BeautifulSoup(page_html, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return None  # e.g. Cloudflare "Just a moment..." challenge page
    profile = json.loads(tag.string)["props"]["pageProps"].get("profile") or {}
    events, seen = [], set()
    for section in profile.get("sections") or []:
        raw = section.get("events") or [i.get("event") for i in section.get("items") or [] if i.get("type") == "event"]
        for e in raw:
            if not e or e["id"] in seen:
                continue
            seen.add(e["id"])
            dates = e.get("dates") or {}
            events.append({
                "title": (e.get("name") or "").strip(),
                "start": _la(dates.get("event_start_date")),
                "url": DICE_EVENT.format(id=e["id"]),
                "image": (e.get("images") or {}).get("square"),
                "price": _dice_price(e.get("price")),
                # extras the current event shape does not carry yet
                "end": _la(dates.get("event_end_date")),
                "status": e.get("status"),  # on-sale | sold-out | ...
                "sold_out": e.get("status") == "sold-out",
            })
    return events


def dice_jsonld_events(page_html):
    """Fallback: the schema.org Place JSON-LD on the same page has an `event` array
    (no sold-out info: eventStatus is always EventScheduled and offers has no availability)."""
    soup = BeautifulSoup(page_html, "html.parser")
    out = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "", strict=False)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "Place":
            for e in data.get("event") or []:
                offers = e.get("offers") or {}
                low = offers.get("lowPrice")
                out.append({
                    "title": e.get("name", "").strip(),
                    "start": _la(e.get("startDate")),
                    "url": e.get("url"),
                    "image": (e.get("image") or [None])[0],
                    "price": f"${low}" if low else None,
                })
    return out


WIDGET = re.compile(r"DiceEventListWidget\.create\((\{.*?\})\)\s*;?", re.S)


def dice_widget_config(page_html):
    """On venue sites: the DICE event-list widget config (partnerId, venues/promoters filters).
    Use it to detect DICE venues and route them to a DICE method. Do not log the apiKey."""
    m = WIDGET.search(page_html)
    if not m:
        return None
    cfg = json.loads(m.group(1))
    return {k: cfg.get(k) for k in ("partnerId", "venues", "promoters", "hidePostponed", "hideCancelled")}


if __name__ == "__main__":
    for path in sys.argv[1:]:
        html = open(path, encoding="utf-8").read()
        print("=====", path)
        print("widget:", dice_widget_config(html))
        nxt = dice_next_events(html)
        if nxt is None:
            continue
        ld = dice_jsonld_events(html)
        print(f"__NEXT_DATA__ events: {len(nxt)}  JSON-LD events: {len(ld)}")
        if nxt:
            print("range:", nxt[0]["start"], "->", max(e["start"] for e in nxt))
            print("sold out:", [e["title"] for e in nxt if e["sold_out"]])
            print("statuses:", sorted({e["status"] for e in nxt}))
            # cross-check the two sources agree on title/start/url
            mism = [(a["title"], b["title"]) for a, b in zip(nxt, ld) if (a["title"], a["start"], a["url"]) != (b["title"], b["start"], b["url"])]
            print("NEXT vs JSON-LD mismatches:", mism[:3], "count", len(mism))
            for e in nxt[:3]:
                print(json.dumps(e, ensure_ascii=False))
