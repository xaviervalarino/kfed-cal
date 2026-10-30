"""Fix for proto_methods.rsc_events: /shows pages put events in an SWRFallback {"data":[...],"filter":[venue_id, offset, limit,...]}."""
import re, sys
sys.path.insert(0, "/tmp/claude-0/-home-user-kfed-cal/1d4356bc-b777-5cf7-9b3c-17eb74dd9cb5/scratchpad/analysis/jsonld")
from proto_methods import rsc_text, _DECODER


def rsc_events(page_html):
    """Live Nation event dicts from every "events":[...] (homepage) or "data":[...] (/shows SWR fallback) array."""
    text = rsc_text(page_html)
    found, seen = [], set()
    for m in re.finditer(r'"(?:events|data)":\[', text):
        try:
            arr, _ = _DECODER.raw_decode(text, m.end() - 1)
        except ValueError:
            continue
        for e in arr:
            if not isinstance(e, dict) or "event_data_type" not in e:
                continue
            key = (e.get("event_data_type"), e.get("discovery_id") or e.get("id"))
            if key not in seen:
                seen.add(key)
                found.append(e)
    return found


def rsc_page_filter(page_html):
    """[venue_id, offset, limit, ...] of the /shows SWR list, or None. len(events) == limit means the list is capped."""
    m = re.search(r'"filter":(\[[^\]]*\])', rsc_text(page_html))
    return _DECODER.decode(m.group(1)) if m else None
