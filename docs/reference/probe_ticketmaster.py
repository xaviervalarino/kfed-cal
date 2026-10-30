"""Exploration only: look up our venues in the Ticketmaster Discovery API and save their upcoming events.

Writes probe/out/ticketmaster/. Skips quietly when TICKETMASTER_API_KEY is not set.
"""

import json
import os
import time
from pathlib import Path

import httpx

KEY = os.environ.get("TICKETMASTER_API_KEY")
API = "https://app.ticketmaster.com/discovery/v2"
OUT = Path(__file__).resolve().parent / "out" / "ticketmaster"
KEYWORDS = ["Bellwether", "Teragram Ballroom", "Regent Theater", "The Echo", "Echoplex", "Belasco", "Wiltern",
            "Hollywood Palladium", "Greek Theatre", "Fonda Theatre", "Roxy Theatre", "Troubadour", "Lodge Room",
            "El Cid", "Vermont Hollywood", "Hollywood Bowl", "Glass House", "Zebulon", "Paramount",
            "Permanent Records", "Monty", "Silverlake Lounge"]
LA_AREA = {"Los Angeles", "West Hollywood", "Hollywood", "Pomona"}


def get(client, path, **params):
    time.sleep(0.3)  # the API allows about 5 requests per second
    r = client.get(f"{API}/{path}", params={"apikey": KEY, **params})
    return r.status_code, r.json() if "json" in r.headers.get("content-type", "") else {"text": r.text[:500]}


def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2).replace(KEY, "[REDACTED]"))


def main():
    if not KEY:
        print("TICKETMASTER_API_KEY is not set: skipping the Ticketmaster probe")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    summary, done = {}, set()
    with httpx.Client(timeout=30) as client:
        for keyword in KEYWORDS:
            status, data = get(client, "venues.json", keyword=keyword, stateCode="CA", size=20)
            venues = data.get("_embedded", {}).get("venues", [])
            summary[keyword] = rows = []
            for v in venues:
                city = (v.get("city") or {}).get("name")
                row = {"id": v["id"], "name": v.get("name"), "city": city,
                       "upcoming": (v.get("upcomingEvents") or {}).get("_total")}
                rows.append(row)
                if city in LA_AREA and row["upcoming"] and v["id"] not in done:
                    done.add(v["id"])
                    s, events = get(client, "events.json", venueId=v["id"], size=200, sort="date,asc")
                    save(f"events-{v['id']}.json", events)
                    row["events_saved"] = len(events.get("_embedded", {}).get("events", []))
                    row["events_total"] = events.get("page", {}).get("totalElements")
            print(f"{keyword}: HTTP {status}, " + "; ".join(
                f"{r['name']} ({r['city']}) id={r['id']} upcoming={r['upcoming']}" for r in rows) or "no venues", flush=True)
    save("summary.json", summary)


if __name__ == "__main__":
    main()
