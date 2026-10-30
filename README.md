# kfed-cal

A calendar of upcoming shows and events at local venues. A scraper collects each venue's listings into
`site/events.json` and GitHub Pages serves the calendar page in `site/`.

## How it works

1. `venues.json` lists the venues and how to scrape each one.
2. Early every Wednesday (Pacific time), GitHub Actions runs `python -m scraper.run`. It scrapes every venue, removes
   duplicates and past events, and commits the new `site/events.json`.
3. The workflow then publishes `site/` to GitHub Pages.

If a venue fails or suddenly returns 0 events, the scraper keeps that venue's previous events. It also shows
a warning on the workflow run, because the venue's website has probably changed.

To scrape right away, open the **Actions** tab, select **Update calendar**, and click **Run workflow**.

## Adding a venue

Add an entry to `venues.json`:

```json
{
  "timezone": "America/Chicago",
  "venues": [
    {
      "name": "The Blue Note",
      "website": "https://bluenote.example.com",
      "events_page": "https://bluenote.example.com/calendar",
      "method": "auto",
      "notes": "Anything worth remembering about this venue"
    }
  ]
}
```

- Each venue must have `name`, `events_page` and `method`. `website` and `notes` are optional.
- Put a comma between venues, but not after the last one.
- `timezone` is the city's time zone. The calendar shows event times in this time zone.

To check the file: `python -m scraper.venues`

### Which method?

Before adding a venue, check its events page:

```bash
python -m scraper.check https://bluenote.example.com/calendar --find "A show name you see on the page"
```

The check reports what the page offers. The table lists the methods from most preferred to least preferred:

| The check finds | Method |
| --- | --- |
| schema.org events | `auto` (works now) |
| Calendar/RSS feed links | a feed method (to add) |
| A JSON feed the page loads (browser dev tools, Network tab) | a JSON method (to add) |
| Embedded page data (`__NEXT_DATA__` etc.) | read the JSON from the page (to add) |
| A ticketing platform (Eventbrite, DICE, ...) | that platform's API (to add) |
| The show name is in the HTML | a custom HTML parser (to add) |
| Show name not found | headless Chrome or Lightpanda, with Playwright as the last resort (to add) |

The methods are in `scraper/methods.py`. We add a new method when a venue needs it.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scraper.run
python -m http.server -d site 8000   # then open http://localhost:8000
```

## Scraping politely

The scraper identifies itself in its User-Agent, follows each site's `robots.txt`, waits 2 seconds between
requests, and links every event back to its source.
