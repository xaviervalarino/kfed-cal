"""Offline extractors for bellwether, teragram, regent, lodge-room, paramount (+ notes for el-cid, permanent-records).

Each extractor returns normalized events: title, start (ISO local, no tz), url, image, price,
plus an "extra" dict with the other fields used for the availability matrix.
"""

import html as htmlmod
import json
import re
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def _t(node):
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def _time(text):
    """'7:00 pm' / '7:00pm' / 'Show: 8:00 pm' -> (19, 0) or None."""
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m", text or "", re.I)
    if not m:
        return None
    h, mi = int(m.group(1)) % 12, int(m.group(2) or 0)
    return (h + (12 if m.group(3).lower() == "p" else 0), mi)


def _iso(d, hm):
    return datetime(d.year, d.month, d.day, *(hm or (0, 0))).isoformat() if d else None


def _event(title, start, url, image, price=None, **extra):
    return {"title": title, "start": start, "url": url, "image": image, "price": price,
            "extra": {k: v for k, v in extra.items()}}


# ---------------------------------------------------------------- Bellwether (APE Concerts WP theme)

def bellwether(page_html, page_url="https://thebellwetherla.com/"):
    """Server-rendered list: div.upcoming-events-list > div.detail-information (one per event).
    The li.carousel.item blocks at the top are a featured slider (duplicates) and are skipped."""
    soup = BeautifulSoup(page_html, "html.parser")
    out = []
    for item in soup.select(".upcoming-events-list .detail-information"):
        title = _t(item.select_one(".show-title"))
        ds = item.select_one(".date-show[content]")  # content="October 31, 2026 8:00pm" (show time)
        start = None
        if ds:
            m = re.match(r"\s*([A-Za-z]+ \d{1,2}, \d{4})\s*(.*)", ds["content"])
            if m:
                d = datetime.strptime(m.group(1), "%B %d, %Y").date()
                start = _iso(d, _time(m.group(2)))
        more = item.select_one("a.more-info") or item.select_one(".entry a")
        buy = item.select_one(".event-data a.button:not(.more-info)")
        img = item.select_one("img.wp-post-image")
        topline = _t(item.select_one(".topline"))
        buy_text = _t(buy).lower()
        status = "cancelled" if ("cancel" in topline.lower() or "cancel" in buy_text) else (
            "sold_out" if buy and "soldout" in (buy.get("class") or []) else "onsale")
        out.append(_event(
            title, start,
            urljoin(page_url, more["href"]) if more else page_url,
            img["src"] if img else None,
            None,
            headliner=title,
            support=_t(item.select_one(".support")) or None,
            tagline=topline or None,
            doors=_t(item.select_one(".event__doors-open")).rstrip(" |") or None,
            show_time=_t(item.select_one(".event__start-time")).replace("Show:", "").strip() or None,
            ticket_url=buy["href"] if buy and buy.get("href") else None,
            status=status,
        ))
    return out


# ------------------------------------------------- Teragram + Regent (TicketWeb "event-discovery" WP plugin)

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _tw_date(text, ref):
    """'30 Oct, 2026' (Regent), 'Fri, October 30' (Teragram: no year -> infer from weekday/ref date)."""
    text = text.strip()
    m = re.search(r"(\d{1,2}) ([A-Za-z]{3})[a-z]*,? (\d{4})", text)
    if m:
        return date(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)))
    m = re.search(r"(?:([A-Za-z]{3})[a-z]*, )?([A-Za-z]{3})[a-z]* (\d{1,2})(?:,? (\d{4}))?", text)
    if not m:
        return None
    mon, day = _MONTHS[m.group(2).lower()], int(m.group(3))
    if m.group(4):
        return date(int(m.group(4)), mon, day)
    wd = m.group(1).lower() if m.group(1) else None
    for y in (ref.year, ref.year + 1, ref.year - 1):
        try:
            d = date(y, mon, day)
        except ValueError:
            continue
        if wd and d.strftime("%a").lower() != wd:
            continue
        if (d - ref).days >= -31:  # listings are upcoming; allow a little slack
            return d
    return None


def _age(text):
    m = re.search(r"\b(all ages|(1[68]|21)\s*\+|(1[68]|21) and (up|over))", text or "", re.I)
    return m.group(0) if m else None


def ticketweb_plugin(page_html, page_url, ref=None):
    """div.tw-plugin-upcoming-event-list > div.tw-section. Two theme layouts seen:
    Teragram: .tw-event-date 'Fri, October 30' (no year), time labelled 'Doors:', .tw-attractions, .tw-age-restriction
    Regent:   '.event-date-time .tw-event-date' '30 Oct, 2026', unlabelled time, age only inside the title.
    Paginated: /page/2/, /page/3/ ... (a.page-numbers inside .tm-paginate)."""
    ref = ref or date.today()
    soup = BeautifulSoup(page_html, "html.parser")
    out = []
    for sec in soup.select(".tw-plugin-upcoming-event-list .tw-section"):
        name_el = sec.select_one(".tw-name")
        title = _t(name_el)
        dates = [_t(x) for x in sec.select(".tw-event-date")]
        d = None
        for txt in sorted(dates, key=len, reverse=True):  # prefer the most complete text
            d = _tw_date(txt, ref)
            if d:
                break
        time_label = _t(sec.select_one(".tw-event-time-complete"))
        hm = _time(_t(sec.select_one(".tw-event-time")))
        more = sec.select_one("a.tw-more-info-btn")
        buy = sec.select_one("a.tw-buy-tix-btn")
        img = sec.select_one("img.event-img")
        classes = " ".join(buy.get("class", [])) if buy else ""
        status = ("moved" if "moved" in classes else "sold_out" if "sold" in classes
                  else "cancelled" if "cancel" in classes else "onsale")
        age_el = sec.select_one(".tw-age-restriction")
        support = [_t(s) for s in sec.select(".tw-attractions span")]
        out.append(_event(
            title, _iso(d, hm),
            urljoin(page_url, more["href"]) if more else page_url,
            img["src"] if img else None,
            None,
            headliner=None,  # title is a free-text event name, not a clean headliner
            support=support or None,
            time_is_doors="doors" in time_label.lower(),
            doors=_t(sec.select_one(".tw-event-time")) if "doors" in time_label.lower() else None,
            age=_t(age_el) if age_el else _age(title),
            ticket_url=buy["href"] if buy else None,
            status=status,
        ))
    return out


def ticketweb_next_pages(page_html):
    soup = BeautifulSoup(page_html, "html.parser")
    return sorted({a["href"] for a in soup.select(".tm-paginate a.page-numbers[href]")})


# ---------------------------------------------------------------- Lodge Room (Tessera ticketing)

_PUSH = re.compile(r"eventObjects\.push\((\{.*?\})\);", re.S)


def lodge_room(page_html, products=None):
    """Plain HTML carries one `eventObjects.push({...});` per show (valid JSON object literals).
    Optional enrichment: tickets.lodgeroomhlp.com/api/v1/products?ids=<comma ids> (price, sold out)."""
    by_id = {str(p.get("frontendId")): p for p in (products or [])}
    out = []
    for raw in _PUSH.findall(page_html):
        o = json.loads(raw)
        title = htmlmod.unescape(" / ".join(o.get("mainArtist") or []))
        start = datetime.strptime(o["eventDate"].upper(), "%m/%d/%Y %I:%M %p").isoformat()
        p = by_id.get(str(o["id"]))
        price = sold_out = None
        if p:
            prices = [c["price"] for c in p.get("campaigns", []) if c.get("price") is not None]
            price = f"${min(prices):g}" + (f"-${max(prices):g}" if prices and max(prices) != min(prices) else "") if prices else None
            sold_out = bool(p.get("isSoldOut")) or all(c.get("isSoldOut") for c in p.get("campaigns", []) or [{}])
        out.append(_event(
            title, start, o.get("link"), o.get("image"), price,
            headliner=title,
            support=[htmlmod.unescape(a) for a in o.get("additionalArtists") or []] or None,
            doors=o.get("doors") or None,
            description=o.get("additionalInformation") or None,
            tags=o.get("tags") or None,
            ticket_url=o.get("link"),  # purchase is an overlay on the show page
            status="sold_out" if sold_out else ("onsale" if p else None),
            tessera_id=o["id"],
        ))
    return out


def lodge_room_products_url(page_html):
    ids = [str(json.loads(r)["id"]) for r in _PUSH.findall(page_html)]
    return "https://tickets.lodgeroomhlp.com/api/v1/products?ids=" + "%2C".join(ids)


# ---------------------------------------------------------------- DICE event-list widget (Paramount, also Glass House, Zebulon)

def dice_widget_config(page_html):
    m = re.search(r"DiceEventListWidget\.create\((\{.*?\})\);", page_html, re.S)
    return json.loads(m.group(1)) if m else None


def dice_events(payload):
    """UNTESTED against real data (no DICE response was captured). Shape assumed from the
    partners API the widget uses: {"data": [ {name, date, timezone, url, images, price, ...} ], "links": {"next"}}."""
    out = []
    for e in payload.get("data", []):
        start = (e.get("date") or "")[:19] or None  # API returns UTC 'Z'; convert with e["timezone"] in prod
        imgs = e.get("event_images") or {}
        image = imgs.get("landscape") or imgs.get("square") or ((e.get("images") or [None])[0])
        tt = [t.get("price", {}).get("total") for t in e.get("ticket_types") or [] if t.get("price")]
        price = e.get("price") or (min(tt) / 100 if tt else None)
        out.append(_event(e.get("name"), start, e.get("url"), image, str(price) if price else None,
                          age=e.get("age_limit"), sold_out=e.get("sold_out"), status=e.get("status"),
                          genre=e.get("genre_tags"), description=e.get("description")))
    return out
