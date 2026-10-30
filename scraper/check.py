"""Check a venue's events page to see which scraping method it needs.

    python -m scraper.check https://venue.example.com/calendar
    python -m scraper.check https://venue.example.com/calendar --find "Some Band"

--find takes a show name that you can see in your browser. If the downloaded page does not
contain that name, JavaScript probably loads the listings.
"""

import argparse
import re

from bs4 import BeautifulSoup

from .fetch import Fetcher
from .methods import jsonld_events, to_event

EMBEDDED_DATA = ["__NEXT_DATA__", "__NUXT__", "__INITIAL_STATE__", "__APOLLO_STATE__", "__PRELOADED_STATE__"]
TICKETING = ["eventbrite", "dice.fm", "ticketmaster", "livenation", "axs.com", "ticketweb", "etix",
             "seetickets", "tixr", "showclix", "prekindle", "holdmyticket", "songkick", "bandsintown",
             "venuepilot", "ticketfly", "ticketleap", "universe.com", "eventim", "opendate"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url")
    parser.add_argument("--find", help="a show name you can see on the page in your browser")
    args = parser.parse_args()

    fetcher = Fetcher()
    if not fetcher.allowed(args.url):
        print("robots.txt does NOT allow scraping this page.")
        return
    response = fetcher.get(args.url)
    page = response.text
    soup = BeautifulSoup(page, "html.parser")
    print(f"Fetched {response.url} ({response.status_code}, {len(page):,} bytes, "
          f"{len(soup.find_all('script'))} scripts)")

    events = jsonld_events(page)
    print(f"\nschema.org events: {len(events)}" + ("  -> method \"auto\" should work" if events else ""))
    for e in events[:5]:
        e = to_event(e, args.url)
        print(f"  {e['start']}  {e['title']}")

    feeds = {a["href"] for a in soup.find_all(["a", "link"], href=True)
             if re.search(r"\.ics\b|ical|webcal:|/feed/?$|\.rss\b", a["href"], re.I)
             or a.get("type") in ("text/calendar", "application/rss+xml")}
    print(f"\nCalendar/RSS feed links: {len(feeds)}")
    for href in sorted(feeds)[:10]:
        print(f"  {href}")

    embedded = [name for name in EMBEDDED_DATA if name in page]
    print(f"\nEmbedded page data: {', '.join(embedded) or 'none'}")

    lowered = page.lower()
    platforms = [name for name in TICKETING if name in lowered]
    print(f"Ticketing platforms mentioned: {', '.join(platforms) or 'none'}")

    if args.find:
        visible = args.find.lower() in lowered
        print(f'\n"{args.find}" in the downloaded page: {"YES" if visible else "NO"}')
        if not visible:
            print("  JavaScript probably loads the listings. Look for a JSON feed in the Network tab\n"
                  "  of the browser's dev tools. If you find no feed, use a headless browser.")


if __name__ == "__main__":
    main()
