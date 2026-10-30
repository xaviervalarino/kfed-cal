"""Round 2b candidate methods. Each is (venue, fetcher) -> list of events with
title, start (local ISO), url, image, price, support, doors, age, status, room.
status is one of onsale / soldout / cancelled / rescheduled (None when unknown)."""

import html
import json
import re
from datetime import date, datetime, timedelta
from urllib.parse import quote, urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

LA = ZoneInfo("America/Los_Angeles")
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}


# ---------------------------------------------------------------- shared helpers

def _t(node):
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def _ev(title, start, url, image=None, price=None, support=None, doors=None, age=None, status=None, room=None):
    return dict(title=title, start=start, url=url, image=image, price=price,
                support=support or None, doors=doors, age=age, status=status, room=room)


def _hm(text):
    """'7:00 pm' / '7pm' / '8:00 PM' -> (19, 0)."""
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m", text or "", re.I)
    if not m:
        return None
    return int(m.group(1)) % 12 + (12 if m.group(3).lower() == "p" else 0), int(m.group(2) or 0)


def _iso(d, hm=None):
    """Date-only ISO when there is no time, so callers can tell 'unknown time' from midnight."""
    if not d:
        return None
    return datetime(d.year, d.month, d.day, *hm).isoformat() if hm else d.isoformat()


def _guess_date(mon, day, weekday=None, today=None):
    """Month/day without a year (upcoming listings): the first year that matches the weekday
    and is not more than a month in the past."""
    today = today or date.today()
    for y in (today.year, today.year + 1, today.year - 1):
        try:
            d = date(y, mon, day)
        except ValueError:
            continue
        if weekday and d.strftime("%a").lower() != weekday[:3].lower():
            continue
        if d >= today - timedelta(days=31):
            return d
    return None


def _age(text):
    m = re.search(r"\b(all ages|(?:1[68]|21)\s*\+|(?:1[68]|21) and (?:up|over))", text or "", re.I)
    return m.group(1) if m else None


def _status(*texts):
    s = " ".join(t for t in texts if t).lower()
    if "cancel" in s:
        return "cancelled"
    if "postpon" in s or "resched" in s or "moved" in s:
        return "rescheduled"
    if "sold" in s and "out" in s:
        return "soldout"
    return None


# ---------------------------------------------------------------- 1. Troubadour (Carbonhouse)

TROUBADOUR_AJAX = ("{base}/events/events_ajax/{offset}?category=0&venue=0&team=0&exclude="
                   "&per_page={per_page}&came_from_page=event-list-page")


def _troubadour_items(page_html, page, today=None):
    soup = BeautifulSoup(page_html, "html.parser")
    out = []
    for it in soup.select(".eventItem"):  # list cards; the month calendar uses .event_item
        a = it.select_one(".title a")
        m = re.search(r"([A-Za-z]{3})\w*\.?\s+([A-Za-z]{3})\w*\s+(\d{1,2})", _t(it.select_one(".date")))
        d = _guess_date(MONTHS[m.group(2).lower()], int(m.group(3)), m.group(1), today) if m else None
        tix = it.select_one("a.tickets")
        flag = (it.select_one("[data-ticket-text]") or {}).get("data-ticket-text", "")
        img = it.select_one(".thumb img")
        tagline = _t(it.select_one(".tagline"))
        out.append(_ev(
            title=_t(a),
            start=_iso(d),  # the list has no time; only the detail page does
            url=urljoin(page, a["href"]) if a else page,
            image=img.get("src") if img else None,
            price="Free" if "free" in flag else None,
            support=[s.strip() for s in tagline.split(",") if s.strip()] if tagline else None,
            age=_age(flag.replace("-", " ")),
            status=_status(flag, _t(tix), tix.get("data-text") if tix else "") or ("onsale" if tix else None),
        ))
    return soup, out


def troubadour(venue, fetcher, today=None, max_pages=20):
    """/events server-renders the first 12 cards; button#loadMoreEvents then GETs
    /events/events_ajax/<offset>?...&per_page=12 (an HTML fragment of more .eventItem cards)."""
    page = venue["events_page"]
    base = re.match(r"https?://[^/]+", page).group(0)
    soup, events = _troubadour_items(fetcher.get(page).text, page, today)
    btn = soup.select_one("#loadMoreEvents")
    offset = int(btn.get("data-offset", 12)) if btn else 12
    step = int(btn.get("data-increment", 12)) if btn else 12
    seen = {e["url"] for e in events}
    for _ in range(max_pages if btn else 0):
        _, more = _troubadour_items(fetcher.get(TROUBADOUR_AJAX.format(base=base, offset=offset, per_page=step)).text, page, today)
        more = [e for e in more if e["url"] not in seen]
        if not more:
            break
        seen.update(e["url"] for e in more)
        events += more
        offset += step
    return events


# ---------------------------------------------------------------- 2. El Cid (Squarespace page + DICE event-list widget)

DICE_WIDGET = re.compile(r"DiceEventListWidget\.create\((\{.*?\})\);", re.S)
DICE_API = "https://partners-endpoint.dice.fm/api/v2/events"


def dice_widget_config(page_html):
    m = DICE_WIDGET.search(page_html)
    return json.loads(m.group(1)) if m else None


def dice_widget_url(cfg, page_size=100):
    q = [f"page[size]={page_size}", "types=linkout,event"]
    q += [f"filter[venues][]={quote(v)}" for v in cfg.get("venues") or []]
    q += [f"filter[promoters][]={quote(p)}" for p in cfg.get("promoters") or []]
    return DICE_API + "?" + "&".join(q)


def _dice_local(iso, tz):
    if not iso:
        return None
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ZoneInfo(tz or "America/Los_Angeles")).replace(tzinfo=None).isoformat()


def dice_widget_events(payload):
    """ASSUMED shape of the partners API (no response captured yet):
    {"data": [{name, date, timezone, url, event_images{landscape,square}, ticket_types[{price{total}}],
    status, sold_out, age_limit, lineup[{details, time}], venue}], "links": {"next": ...}}"""
    out = []
    for e in payload.get("data") or []:
        imgs = e.get("event_images") or {}
        totals = [t["price"]["total"] for t in e.get("ticket_types") or [] if (t.get("price") or {}).get("total")]
        doors = next((x.get("time") for x in e.get("lineup") or [] if "door" in (x.get("details") or "").lower()), None)
        out.append(_ev(
            title=(e.get("name") or "").strip(),
            start=_dice_local(e.get("date"), e.get("timezone")),
            url=e.get("url"),
            image=imgs.get("landscape") or imgs.get("square"),
            price=f"${min(totals) / 100:.2f}" if totals else None,
            doors=doors,
            age=e.get("age_limit"),
            status="soldout" if e.get("sold_out") else _status(e.get("status")) or "onsale",
            room=e.get("venue"),
        ))
    return out


def el_cid(venue, fetcher, max_pages=10):
    """The /events page is an empty Squarespace page holding a DICE widget (venues: ["El Cid"]).
    The widget's public apiKey goes in an x-api-key header, so this bypasses Fetcher.get:
    give Fetcher.get a headers argument instead of calling fetcher.client directly."""
    cfg = dice_widget_config(fetcher.get(venue["events_page"]).text)
    if not cfg:
        return []
    url, events = dice_widget_url(cfg), []
    for _ in range(max_pages):
        if not fetcher.allowed(url):
            break
        r = fetcher.client.get(url, headers={"x-api-key": cfg["apiKey"]})
        r.raise_for_status()
        payload = r.json()
        events += dice_widget_events(payload)
        url = (payload.get("links") or {}).get("next")
        if not url:
            break
    return events


# ---------------------------------------------------------------- 3. Greek Theatre (Simpleview)

GREEK_FIELDS = ["recid", "title", "url", "date", "startTime", "startDate", "endDate", "media_raw",
                "linkUrl", "custom.subtitle", "custom.calendarname", "udfs_object"]


def greek_query_url(base, token, start, limit=100, skip=0):
    """The same query the asm_list widget on /events-tickets/ sends (calendarid 1, 5-year window)."""
    end = start + timedelta(days=5 * 365)
    flt = {"active": True, "calendarid": {"$in": ["1"]},
           "date_range": {"start": {"$date": f"{start.isoformat()}T07:00:00.000Z"},
                          "end": {"$date": f"{end.isoformat()}T07:00:00.000Z"}}}
    opts = {"limit": limit, "skip": skip, "count": True, "castDocs": False,
            "fields": {f: 1 for f in GREEK_FIELDS}, "sort": {"date": 1, "startTime": 1, "rank": 1, "title_sort": 1}}
    return (f"{base}/includes/rest_v2/plugins_events_events_by_date/find/?json="
            + quote(json.dumps({"filter": flt, "options": opts}, separators=(",", ":")))
            + "&token=" + quote(token))


def greek_rest_events(payload, base):
    """Response {"docs": {"count": N, "docs": [...]}} (shape from the page's own JS)."""
    out = []
    for d in (payload.get("docs") or {}).get("docs") or []:
        day = date.fromisoformat(d["date"][:10]) if d.get("date") else None
        hm = tuple(int(x) for x in d["startTime"].split(":")[:2]) if d.get("startTime") else None
        title = d.get("title") or ""
        out.append(_ev(title=title, start=_iso(day, hm), url=urljoin(base, d.get("url") or ""),
                       image=((d.get("media_raw") or [{}])[0]).get("mediaurl"),
                       support=[d["custom"]["subtitle"]] if (d.get("custom") or {}).get("subtitle") else None,
                       status=_status(title) or "onsale", room="The Greek Theatre")
                   | {"tickets": d.get("linkUrl")})
    return out


def greek_home_events(page_html, base="https://www.lagreektheatre.com/", today=None):
    """Fallback, tested: the homepage server-renders an event slider (time + Ticketmaster link)
    plus a schema.org ItemList (full date with year, description with seating/age)."""
    soup = BeautifulSoup(page_html, "html.parser")
    ld = {}
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "", strict=False)
        except json.JSONDecodeError:
            continue
        for g in data.get("@graph", []) if isinstance(data, dict) else []:
            for it in g.get("itemListElement", []) if g.get("@type") == "ItemList" else []:
                if it.get("item", {}).get("startDate"):
                    ld[it["item"]["url"]] = it["item"]
    out, seen = [], set()
    for art in soup.select("article.slide[data-recid]"):
        a, month = art.select_one(".slide-title a"), art.select_one(".date-month")
        if not a or not month or art["data-recid"] in seen:  # each slide appears twice; the date-less copy is skipped
            continue
        seen.add(art["data-recid"])
        url = urljoin(base, a["href"])
        meta = ld.get(url, {})
        day = (date.fromisoformat(meta["startDate"][:10]) if meta.get("startDate")
               else _guess_date(MONTHS[_t(month)[:3].lower()], int(_t(art.select_one(".date-day"))), today=today))
        tm = next((x["href"] for x in art.select("a[href*='ticketmaster.com']")), None)
        title = _t(a)
        img = (meta.get("image") or {}).get("url") if isinstance(meta.get("image"), dict) else None
        out.append(_ev(title=title, start=_iso(day, _hm(_t(art.select_one(".date-details")))), url=url, image=img,
                       age=_age(meta.get("description")), status=_status(title) or "onsale", room="The Greek Theatre")
                   | {"tickets": tm})
    return out


def greek(venue, fetcher):
    """Primary: Simpleview REST v2 with the site's public token (UNTESTED: the token endpoint
    /plugins/core/get_simple_token/ is the usual Simpleview one but was not seen in the probe).
    Fallback: the homepage slider (tested, a featured subset)."""
    base = "https://www.lagreektheatre.com"
    try:
        token = fetcher.get(base + "/plugins/core/get_simple_token/").text.strip()
        events, skip = [], 0
        while True:
            payload = fetcher.get(greek_query_url(base, token, date.today(), skip=skip)).json()
            batch = greek_rest_events(payload, base)
            events += batch
            skip += len(batch)
            if not batch or skip >= payload["docs"].get("count", 0):
                return events
    except Exception:
        return greek_home_events(fetcher.get(base + "/").text, base + "/")


# ---------------------------------------------------------------- 4. Hollywood Bowl (JSON feed)

def bowl_feed_events(rows, venue_class="hb"):
    """/events/feed is one JSON list for LA Phil's three sites (WDCH, Ford, Bowl): filter by venue.class."""
    out = []
    for r in rows:
        if (r.get("venue") or {}).get("class") != venue_class or r.get("hide_from_calendar") or r.get("is_past"):
            continue
        start = r.get("start_time") or ""
        sup = html.unescape(re.sub(r"<[^>]+>", ", ", r.get("supporting_artists") or "")).strip(" ,")
        flag = r.get("calendar_flag")
        out.append(_ev(
            title=html.unescape((r.get("program") or {}).get("name") or ""),
            start=start[:10] if r.get("hide_time") else start[:19],  # already local wall time (-07:00/-08:00)
            url=r.get("absolute_url"),
            image=(r.get("calendar_image") or {}).get("url"),
            price="Free" if r.get("is_free") else None,
            support=[s.strip() for s in re.split(r"\s*,\s*", sup) if s.strip()] or None,  # sometimes a subtitle
            status=(_status(json.dumps(flag)) if flag else None) or "onsale",
            room=(r.get("venue") or {}).get("name"),
        ) | {"tickets": r.get("buy_url")})
    return out


def hollywood_bowl(venue, fetcher):
    return bowl_feed_events(fetcher.get("https://www.hollywoodbowl.com/events/feed").json())


# ---------------------------------------------------------------- 6. Teragram + Regent (TicketWeb WP plugin)

def _tw_date(texts, today=None):
    for text in sorted(texts, key=len, reverse=True):
        m = re.search(r"(\d{1,2}) ([A-Za-z]{3})\w*,? (\d{4})", text)  # Regent: '30 Oct, 2026'
        if m:
            return date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))
        m = re.search(r"(?:([A-Za-z]{3})\w*, )?([A-Za-z]{3})\w* (\d{1,2})", text)  # Teragram: 'Sat, December 5'
        if m and m.group(2).lower() in MONTHS:
            return _guess_date(MONTHS[m.group(2).lower()], int(m.group(3)), m.group(1), today)
    return None


def ticketweb_plugin_events(page_html, page, today=None):
    soup = BeautifulSoup(page_html, "html.parser")
    out = []
    for sec in soup.select(".tw-plugin-upcoming-event-list .tw-section"):
        d = _tw_date([_t(x) for x in sec.select(".tw-event-date")], today)
        t_label, t_val = _t(sec.select_one(".tw-event-time-complete")), _t(sec.select_one(".tw-event-time"))
        prefix = _t(sec.select_one(".tw-prefix"))
        if "door" in t_label.lower():  # Teragram labels its only time "Doors:"
            start, doors = _iso(d, _hm(t_val)), t_val
        else:  # Regent: show time, doors in .tw-prefix ('Doors: 6:00pm', sometimes 'X Presents:')
            start, doors = _iso(d, _hm(t_val)), (prefix.split(":", 1)[1].strip() if prefix.lower().startswith("doors") else None)
        buy, more = sec.select_one("a.tw-buy-tix-btn"), sec.select_one("a.tw-more-info-btn")
        cls = " ".join(buy.get("class", [])) if buy else ""
        title = _t(sec.select_one(".tw-name"))
        img = sec.select_one("img.event-img")
        age_el = sec.select_one(".tw-age-restriction")
        out.append(_ev(
            title=title, start=start, url=urljoin(page, more["href"]) if more else page,
            image=img.get("src") if img else None,
            price="Free" if "free" in cls else None,
            support=[_t(s) for s in sec.select(".tw-attractions span")] or None,
            doors=doors, age=_age(_t(age_el)) or _age(title),
            status=_status(cls.replace("tw_", " "), _t(buy)) or ("onsale" if buy else None),
            room=_t(sec.select_one(".tw-venue-name")) or None,
        ) | {"tickets": buy.get("href") if buy else None})
    return out


def ticketweb_plugin(venue, fetcher, max_pages=10):
    """Needs a page that passes Cloudflare (plain requests get a 403 challenge).
    Teragram paginates /page/N/; Regent's /events/ lists everything on one page."""
    page, events, seen_pages = venue["events_page"], [], set()
    queue = [page]
    while queue and len(seen_pages) < max_pages:
        url = queue.pop(0)
        seen_pages.add(url.rstrip("/"))
        h = fetcher.get(url).text
        events += ticketweb_plugin_events(h, url)
        soup = BeautifulSoup(h, "html.parser")
        nxt = soup.select_one(".tm-paginate a.next[href]")
        if nxt and nxt["href"].rstrip("/") not in seen_pages:
            queue.append(urljoin(url, nxt["href"]))
    return events
