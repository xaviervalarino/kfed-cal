# kfed-cal

A calendar of upcoming shows and events at local venues. A scraper collects each venue's listings into
`site/events.json` and GitHub Pages serves the calendar page in `site/`.

## How it works

1. `venues.json` lists the venues and how to scrape each one.
2. Early every Wednesday (Pacific time), GitHub Actions runs `python -m scraper.run`. It scrapes every venue, removes
   duplicates and past events, and commits the new `site/events.json` and `site/status.json` (how each venue's
   scrape went). `docs/DATA.md` describes both files.

   It also collects artist info (links, a photo, a sentence or two) from Ticketmaster, MusicBrainz and Wikipedia.
   MusicBrainz and Wikipedia answers are cached in `scraper/cache/artists.json` for 90 days, which the workflow
   commits too. A run looks up at most 600 new names, so the cache fills over the first few weekly runs.
3. The workflow then publishes `site/` to GitHub Pages.

If a venue fails or suddenly returns 0 events, the scraper keeps that venue's previous events. It also shows
a warning on the workflow run, because the venue's website has probably changed.

To scrape right away, open the **Actions** tab, select **Update calendar**, and click **Run workflow**.

## Adding a venue

Add an entry to `venues.json`:

```json
{
  "timezone": "America/Los_Angeles",
  "venues": [
    {
      "name": "The Echo",
      "website": "https://theecho.com/",
      "method": "ticketmaster",
      "params": {"venue_ids": ["KovZ917A967"]}
    },
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

- Each venue must have `name` and `website`. The method decides what else it needs (table below).
- Leave out `method` for a venue with no source yet. The status page lists it as "no source" with its `notes`.
- `partial`: one sentence on why the source lists only some of the venue's shows. The status page shows it.
- Put a comma between venues, but not after the last one.
- `timezone` is the city's time zone. The calendar shows event times in this time zone.

To check the file: `python -m scraper.venues`

### Methods

The methods are in `scraper/methods.py`, one per source platform. `docs/VENUES.md` says which venue uses which.

| Method | Reads | The venue needs |
| --- | --- | --- |
| `ticketmaster` | the Ticketmaster Discovery API (needs `TICKETMASTER_API_KEY`) | `params.venue_ids`: one or more Ticketmaster venue ids |
| `dice_venue` | a DICE venue page | `events_page`: `https://dice.fm/venue/<slug>` |
| `tessera` | a venue site ticketed by Tessera (Lodge Room) | `events_page`, and `params.api`: its ticket API, for prices |
| `tribe_events` | the API of a WordPress site running The Events Calendar | `events_page`: its `/wp-json/tribe/events/v1/events?per_page=50` address |
| `auto` | schema.org events embedded in a page | `events_page` |
| `permanent_records` | Permanent Records Roadhouse's show table | `events_page` |
| `monty_flyer` | Monty Bar's weekly flyer image, read by Claude Haiku (needs `ANTHROPIC_API_KEY`) | `events_page` |

### Which method?

First look the venue up on Ticketmaster: it has full listings for most large rooms. Otherwise check its events page:

```bash
python -m scraper.check https://bluenote.example.com/calendar --find "A show name you see on the page"
```

| The check finds | Method |
| --- | --- |
| schema.org events | `auto` |
| DICE (or a DICE widget) | `dice_venue` with the venue's DICE page |
| `/wp-json/tribe/` links | `tribe_events` |
| Calendar/RSS feed links, a JSON feed, or embedded page data (`__NEXT_DATA__` etc.) | a new method that reads it |
| The show name is in the HTML | a small HTML parser, like `permanent_records` |
| Show name not found | JavaScript loads the listings. Look for another source first |

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scraper.run
npm --prefix web install
npm --prefix web run dev:site   # the site with that data, at http://localhost:5173
```

`python -m unittest` runs the tests (no network). The Ticketmaster and Monty Bar methods read `TICKETMASTER_API_KEY`
and `ANTHROPIC_API_KEY` from the environment. Without them, those venues fail and keep their last events.

## Scraping politely

The scraper identifies itself in its User-Agent, follows each site's `robots.txt`, waits 2 seconds between
requests, and links every event back to its source.

One exception: the MusicBrainz and Wikipedia APIs. Their `robots.txt` files disallow them for crawlers, but they
publish rules for apps, and the scraper follows those instead: one MusicBrainz request a second at most, and a
User-Agent with a contact address and the word "bot". `ROBOTS_EXCEPTIONS` in `scraper/fetch.py` lists them.
It also lists Wikidata's entity data (`/wiki/Special:EntityData/`), which Wikidata's `robots.txt` allows but Python
3.13's `robots.txt` parser refuses.
