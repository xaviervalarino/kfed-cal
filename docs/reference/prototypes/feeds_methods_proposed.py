"""Proposed scraper methods, same signature as scraper/methods.py: method(venue, fetcher) -> list of
{title, start, url, image, price}. Tested offline with a fake fetcher (see test block at the bottom)."""

import html as htmlmod
import json
import re
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

_TIME = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m", re.I)
_MON = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}


def _hm(text):
    m = _TIME.search(text or "")
    return ((int(m.group(1)) % 12) + (12 if m.group(3).lower() == "p" else 0), int(m.group(2) or 0)) if m else (0, 0)


def _txt(node):
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


# --- Lodge Room: Tessera ticketing. Plain request is enough.
_PUSH = re.compile(r"eventObjects\.push\((\{.*?\})\);", re.S)


def tessera(venue, fetcher):
    page = venue["events_page"]
    objs = [json.loads(raw) for raw in _PUSH.findall(fetcher.get(page).text)]
    prices = {}
    api = venue.get("tessera_api")  # e.g. "https://tickets.lodgeroomhlp.com/api/v1"
    if api and objs:
        try:
            ids = ",".join(str(o["id"]) for o in objs)
            for p in fetcher.get(f"{api}/products?ids={ids}").json():
                ps = [c["price"] for c in p.get("campaigns") or [] if c.get("price") is not None]
                if ps:
                    prices[str(p["frontendId"])] = f"${min(ps):g}"
        except Exception:
            pass  # price is optional; the listing itself came from the page
    return [{
        "title": htmlmod.unescape(" / ".join(o.get("mainArtist") or [])),
        "start": datetime.strptime(o["eventDate"].upper(), "%m/%d/%Y %I:%M %p").isoformat(),
        "url": o.get("link") or page,
        "image": o.get("image") or None,
        "price": prices.get(str(o["id"])),
    } for o in objs]


# --- Teragram, Regent: TicketWeb "event-discovery" WordPress plugin. Behind a Cloudflare managed
# challenge: needs a fetcher that runs a real browser. Follows /page/N/ pagination.
def _tw_date(texts, today):
    for t in sorted(texts, key=len, reverse=True):
        m = re.search(r"(\d{1,2}) ([A-Za-z]{3})[a-z]*,? (\d{4})", t)  # "30 Oct, 2026"
        if m:
            return date(int(m.group(3)), _MON[m.group(2).lower()], int(m.group(1)))
        m = re.search(r"([A-Za-z]{3})[a-z]*,? ([A-Za-z]{3})[a-z]* (\d{1,2})", t)  # "Fri, October 30"
        if m:
            for y in (today.year, today.year + 1):
                try:
                    d = date(y, _MON[m.group(2).lower()], int(m.group(3)))
                except ValueError:
                    continue
                if d.strftime("%a").lower() == m.group(1).lower() and (d - today).days > -31:
                    return d
    return None


def ticketweb_plugin(venue, fetcher, max_pages=10):
    page, today, seen, events = venue["events_page"], date.today(), set(), []
    queue = [page]
    while queue and len(seen) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        soup = BeautifulSoup(fetcher.get(url).text, "html.parser")
        for sec in soup.select(".tw-plugin-upcoming-event-list .tw-section"):
            buy = sec.select_one("a.tw-buy-tix-btn")
            if buy and "moved" in " ".join(buy.get("class", [])):
                continue  # "this event has moved" (to another venue)
            d = _tw_date([_txt(x) for x in sec.select(".tw-event-date")], today)
            more, img = sec.select_one("a.tw-more-info-btn"), sec.select_one("img.event-img")
            events.append({
                "title": _txt(sec.select_one(".tw-name")),
                "start": datetime(d.year, d.month, d.day, *_hm(_txt(sec.select_one(".tw-event-time")))).isoformat() if d else None,
                "url": urljoin(url, more["href"]) if more else url,
                "image": img["src"] if img else None,
                "price": None,
            })
        queue += [a["href"] for a in soup.select(".tm-paginate a.page-numbers[href]") if a["href"] not in seen]
    return events


# --- Bellwether: APE Concerts WordPress theme. Behind a Cloudflare managed challenge (browser fetcher).
def ape_html(venue, fetcher):
    page = venue["events_page"]
    soup = BeautifulSoup(fetcher.get(page).text, "html.parser")
    out = []
    for it in soup.select(".upcoming-events-list .detail-information"):
        ds = it.select_one(".date-show[content]")  # "October 31, 2026 8:00pm"
        m = re.match(r"\s*([A-Za-z]+ \d{1,2}, \d{4})(.*)", ds["content"]) if ds else None
        d = datetime.strptime(m.group(1), "%B %d, %Y") if m else None
        more, img = it.select_one("a.more-info") or it.select_one(".entry a"), it.select_one("img.wp-post-image")
        out.append({
            "title": _txt(it.select_one(".show-title")),
            "start": d.replace(hour=_hm(m.group(2))[0], minute=_hm(m.group(2))[1]).isoformat() if d else None,
            "url": urljoin(page, more["href"]) if more else page,
            "image": img["src"] if img else None,
            "price": None,
        })
    return out


if __name__ == "__main__":
    import sys
    from pathlib import Path

    OUT = Path(sys.argv[1])

    class Resp:
        def __init__(self, text):
            self.text = text

        def json(self):
            return json.loads(self.text)

    class FakeFetcher:
        def __init__(self, mapping):
            self.mapping = mapping

        def get(self, url):
            if url.startswith("https://tickets.lodgeroomhlp.com/api/v1/products"):
                return Resp((OUT / "lodge-room/feeds/3.json").read_text())
            if url not in self.mapping:
                raise FileNotFoundError(url)  # pagination pages were not saved
            return Resp((OUT / self.mapping[url]).read_text())

    class Lenient(FakeFetcher):
        def get(self, url):
            try:
                return super().get(url)
            except FileNotFoundError:
                return Resp("<html></html>")

    cases = [
        (tessera, {"events_page": "https://www.lodgeroomhlp.com/", "tessera_api": "https://tickets.lodgeroomhlp.com/api/v1"},
         {"https://www.lodgeroomhlp.com/": "lodge-room/plain.html"}),
        (ticketweb_plugin, {"events_page": "https://teragramballroom.com/"}, {"https://teragramballroom.com/": "teragram/rendered.html"}),
        (ticketweb_plugin, {"events_page": "https://regentdtla.com/"}, {"https://regentdtla.com/": "regent/rendered.html"}),
        (ape_html, {"events_page": "https://thebellwetherla.com/"}, {"https://thebellwetherla.com/": "bellwether/rendered.html"}),
    ]
    for fn, venue, mapping in cases:
        evs = fn(venue, Lenient(mapping))
        assert evs and all(e["title"] and e["start"] and e["url"] for e in evs), fn.__name__
        print(fn.__name__, venue["events_page"], len(evs), "events; first:", json.dumps(evs[0], ensure_ascii=False))
