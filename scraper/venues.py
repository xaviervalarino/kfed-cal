"""Load and check venues.json. Run `python -m scraper.venues` to check it."""

import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VENUES_FILE = Path(__file__).resolve().parent.parent / "venues.json"
# Each method, and what a venue using it must have ("params.x" is a key inside "params").
METHODS = {
    "auto": ["events_page"],
    "dice_venue": ["events_page"],
    "monty_flyer": ["events_page"],
    "permanent_records": ["events_page"],
    "tessera": ["events_page"],
    "ticketmaster": ["params.venue_ids"],
    "tribe_events": ["events_page"],
}
FIELDS = {"name", "website", "events_page", "method", "params", "partial", "notes"}


def load_venues(path=VENUES_FILE):
    """Return (timezone, venues). Exit with a readable list of problems if the file is bad."""
    try:
        data = json.loads(Path(path).read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"{path.name} is not valid JSON (line {e.lineno}, column {e.colno}): {e.msg}\n"
                 "Look for a missing comma between entries, or an extra comma after the last entry.")

    problems = []
    venues = data.get("venues", [])
    tz = data.get("timezone", "")

    if venues and not tz:
        problems.append('"timezone" is empty. Set it to your city\'s time zone, for example "America/Chicago".')
    elif tz:
        try:
            ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError):
            problems.append(f'"timezone" is "{tz}", which is not a known time zone. Use a name such as "America/Chicago".')

    seen = set()
    for i, v in enumerate(venues, 1):
        label = f'Venue #{i} ({v.get("name") or "no name"})'
        for field in ("name", "website"):
            if not v.get(field):
                problems.append(f'{label}: "{field}" is missing.')
        for field in set(v) - FIELDS:
            problems.append(f'{label}: unknown field "{field}". The allowed fields are: {", ".join(sorted(FIELDS))}.')
        for field in ("website", "events_page"):
            if v.get(field) and not v[field].startswith(("http://", "https://")):
                problems.append(f'{label}: "{field}" must start with http:// or https://.')
        if "params" in v and not isinstance(v["params"], dict):
            problems.append(f'{label}: "params" must be an object, like {{"venue_ids": ["..."]}}.')
        elif not isinstance(v.get("params", {}).get("venue_ids", []), list):
            problems.append(f'{label}: "venue_ids" must be a list, like ["KovZ917A967"], even for one id.')
        elif v.get("method") and v["method"] not in METHODS:
            problems.append(f'{label}: method "{v["method"]}" is not known. The known methods are: {", ".join(sorted(METHODS))}.')
        elif v.get("method"):
            for need in METHODS[v["method"]]:
                where = v.get("params", {}) if need.startswith("params.") else v
                if not where.get(need.removeprefix("params.")):
                    problems.append(f'{label}: method "{v["method"]}" needs "{need}".')
        if v.get("name") in seen:
            problems.append(f'{label}: another venue already has this name.')
        seen.add(v.get("name"))

    if problems:
        sys.exit(f"{path.name} has {len(problems)} problem(s):\n" + "\n".join(f"  - {p}" for p in problems))
    return tz, venues


if __name__ == "__main__":
    tz, venues = load_venues()
    scraped = sum(1 for v in venues if v.get("method"))
    print(f"venues.json OK: {len(venues)} venue(s), {scraped} with a method, timezone {tz or '(not set)'}")
