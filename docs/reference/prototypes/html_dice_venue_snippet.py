# Drop-in candidate for scraper/methods.py (tested offline with a fake fetcher below).
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

LA = ZoneInfo("America/Los_Angeles")


def dice_venue(venue, fetcher):
    """dice.fm/venue/<slug>: server-rendered Next.js page; upcoming events are in
    __NEXT_DATA__ props.pageProps.profile.sections[*].events. Plain request only:
    a headless browser gets a Cloudflare challenge on dice.fm."""
    page = venue["events_page"]
    soup = BeautifulSoup(fetcher.get(page).text, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        raise ValueError(f"{page}: no __NEXT_DATA__ (Cloudflare challenge?)")  # don't report 0 events
    profile = json.loads(tag.string)["props"]["pageProps"]["profile"]
    events, seen = [], set()
    for section in profile.get("sections") or []:
        for e in section.get("events") or []:
            if e["id"] in seen:
                continue
            seen.add(e["id"])
            price = e.get("price") or {}
            cents = price.get("amount") if price.get("amount") is not None else price.get("amount_from")
            start = e["dates"]["event_start_date"]
            events.append({
                "title": e["name"].strip(),
                "start": datetime.fromisoformat(start).astimezone(LA).isoformat(),
                "url": f"https://dice.fm/event/{e['id']}",
                "image": (e.get("images") or {}).get("square"),
                "price": f"{cents / 100:.2f}" if cents is not None else None,
                "sold_out": e.get("status") == "sold-out",
            })
    return events


if __name__ == "__main__":
    import sys
    class R:  # fake fetcher response
        def __init__(self, t): self.text = t
    class F:
        def __init__(self, path): self.path = path
        def get(self, url): return R(open(self.path, encoding="utf-8").read())
    for p in sys.argv[1:]:
        try:
            ev = dice_venue({"events_page": "https://dice.fm/venue/x"}, F(p))
            print(p.split("/")[-2], len(ev), ev[:1])
        except ValueError as e:
            print(p.split("/")[-2], "ERROR", e)
