"""Ways to get events from a venue. Each method takes (venue, fetcher) and returns raw events:
dicts with title, start, url, image, price. New methods get added here as venues need them."""

import html
import json
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def auto(venue, fetcher):
    """Read the schema.org Event data that many venue and ticketing sites embed in their pages."""
    page = venue["events_page"]
    events = jsonld_events(fetcher.get(page).text)
    return [to_event(e, page) for e in events]


METHODS = {"auto": auto}


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
