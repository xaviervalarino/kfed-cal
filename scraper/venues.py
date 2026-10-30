"""Load and check venues.json. Run `python -m scraper.venues` to check it."""

import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VENUES_FILE = Path(__file__).resolve().parent.parent / "venues.json"
METHODS = {"auto"}
FIELDS = {"name", "website", "events_page", "method", "notes"}


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
        for field in ("name", "events_page", "method"):
            if not v.get(field):
                problems.append(f'{label}: "{field}" is missing.')
        for field in set(v) - FIELDS:
            problems.append(f'{label}: unknown field "{field}". The allowed fields are: {", ".join(sorted(FIELDS))}.')
        for field in ("website", "events_page"):
            if v.get(field) and not v[field].startswith(("http://", "https://")):
                problems.append(f'{label}: "{field}" must start with http:// or https://.')
        if v.get("method") and v["method"] not in METHODS:
            problems.append(f'{label}: method "{v["method"]}" is not known. The known methods are: {", ".join(sorted(METHODS))}.')
        if v.get("name") in seen:
            problems.append(f'{label}: another venue already has this name.')
        seen.add(v.get("name"))

    if problems:
        sys.exit(f"{path.name} has {len(problems)} problem(s):\n" + "\n".join(f"  - {p}" for p in problems))
    return tz, venues


if __name__ == "__main__":
    tz, venues = load_venues()
    print(f"venues.json OK: {len(venues)} venue(s), timezone {tz or '(not set)'}")
