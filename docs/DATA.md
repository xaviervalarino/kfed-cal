# Data files

The scraper (`scraper/run.py`) writes two files into `site/`, and the weekly workflow commits both. The pages are
a Svelte build from `web/`; the deploy copies both files into that build. This is the contract between the scraper
and the pages.

Rules for both files:

- Times are strings. Event times are venue-local (`America/Los_Angeles`) with no offset. Run times are UTC ISO
  8601 with an offset (`2026-11-04T10:21:07+00:00`).
- A field that is unknown is left out, never `null` or `""`.

`docs/reference/sample-events.json` uses the older prototype shape (offsets in `start`, `performers`,
`price_max`, nulls). Build against this file instead.

## `site/events.json`

```json
{
  "updated": "2026-11-04T10:21:07+00:00",
  "timezone": "America/Los_Angeles",
  "venues": [
    {"name": "The Echo", "website": "https://theecho.com/"},
    {"name": "Silverlake Lounge", "website": "http://thesilverlakelounge.com/"}
  ],
  "events": [
    {
      "venue": "The Echo",
      "title": "Francis of Delirium",
      "support": ["Beatrix"],
      "start": "2026-10-30T20:00",
      "doors": "19:00",
      "age": "All ages",
      "url": "https://www.ticketmaster.com/.../event/09006491C882C986",
      "ticket_url": "https://www.ticketmaster.com/.../event/09006491C882C986",
      "image": "https://s1.ticketm.net/dam/a/88a/..._TABLET_LANDSCAPE_LARGE_16_9.jpg",
      "source_id": "tm:vv1AaZk3oGkdFOiJk"
    },
    {
      "venue": "Zebulon",
      "title": "Kulture Klub",
      "details": "The '80s Dance Party",
      "support": ["special guest DJ Geneva Jacuzzi"],
      "start": "2026-10-30T22:00",
      "price": "free",
      "url": "https://dice.fm/event/...",
      "source_id": "dice:6a30e7a3a3a6de0001ce1ea8"
    }
  ]
}
```

- `updated`: when the last scrape finished. The masthead's "UPDATED WED OCT 28" line comes from this.
- `venues`: every venue in `venues.json`, in that order, including ones with no source. Use it for the venues
  filter.
- `events`: upcoming events only, sorted by `start`, then `venue`, then `title`.

Event fields:

| Field | Always there | Value |
|---|---|---|
| `venue` | yes | matches a `venues[].name` |
| `title` | yes | the headliner, or the event's name when there is no clear headliner |
| `start` | yes | `YYYY-MM-DDTHH:MM` with the show time, or `YYYY-MM-DD` when the source gives no show time |
| `url` | yes | the event's page |
| `support` | no | list of other acts, headliner excluded, e.g. `["Beatrix"]` |
| `details` | no | other text about the event: tour name, presenter, flyer text. E.g. `The Rising Skyline Tour`, `PBW Presents`, `3RD ANNUAL HALLOWEEN \| BANDS + DJs` |
| `doors` | no | `HH:MM`, venue-local. When the source gives only a doors time, it goes here and `start` is date-only |
| `price` | no | as a person would write it: `$27`, `$26.50`, `$16–19`, `free` |
| `age` | no | `All ages`, `18+` or `21+` |
| `status` | no | `sold_out`, `rescheduled` or `postponed`. Cancelled events are left out of the file |
| `room` | no | a second room at the venue, e.g. `Camille's at The Bellwether` |
| `ticket_url` | no | where to buy, when the source gives one |
| `image` | no | an image URL, usually 16:9 (DICE images are square) |
| `source_id` | no | the source's id, e.g. `tm:…`, `dice:…`. Unique within the file |

## `site/status.json`

```json
{
  "run": {
    "started": "2026-11-04T10:17:42+00:00",
    "finished": "2026-11-04T10:21:07+00:00",
    "next": "2026-11-11T10:17:00+00:00"
  },
  "totals": {"events": 812, "venues": 22},
  "haiku": {"model": "claude-haiku-5-5", "input_tokens": 2605, "output_tokens": 1543, "dollars": 0.001},
  "venues": [
    {
      "name": "The Echo",
      "method": "ticketmaster",
      "source": "Ticketmaster",
      "status": "ok",
      "events": 65,
      "through": "2027-04-18",
      "with_time": 1.0,
      "last_success": "2026-11-04T10:18:02+00:00"
    },
    {
      "name": "Zebulon",
      "method": "dice_venue",
      "source": "DICE",
      "status": "partial",
      "events": 30,
      "through": "2026-11-21",
      "with_time": 1.0,
      "last_success": "2026-11-04T10:19:40+00:00",
      "note": "DICE shows only the next 30 shows."
    },
    {
      "name": "Silverlake Lounge",
      "source": "none",
      "status": "no_source",
      "events": 0,
      "note": "No listings online yet."
    }
  ]
}
```

- `run.next`: the next scheduled run (Wednesdays 10:17 UTC).
- "Venues OK" and "needs a look" are counted from `venues[].status`. Needs a look = `kept` + `failed`: `partial`
  and `no_source` are known gaps, not this week's problems.
- `haiku`: tokens and cost for this run. All zeros when the Monty flyer was not read.
- `venues`: one entry per venue, in `venues.json` order.

Venue fields:

| Field | Always there | Value |
|---|---|---|
| `name` | yes | the venue's name |
| `method` | no | the scraper method; left out for a venue with no source |
| `source` | yes | a short label for the status table: `Ticketmaster`, `DICE`, `Tessera feed`, `Events Calendar API`, `flyer + Haiku`, `venue site`, `none` |
| `status` | yes | see below |
| `events` | yes | events in `events.json` for this venue |
| `through` | no | date of its last listed event, `YYYY-MM-DD` |
| `with_time` | no | share of its events that have a start time, `0` to `1` |
| `last_success` | no | when a run last scraped this venue without an error |
| `note` | no | one plain sentence: why it is partial, the error, or a known gap |

Status values and the chip each one gets (`DESIGN.md`):

| `status` | Meaning | Chip |
|---|---|---|
| `ok` | scraped this run | OK |
| `partial` | scraped this run, but the source lists only some of the venue's shows | PARTIAL |
| `kept` | this run failed or found 0 events; last run's events are still shown | KEPT LAST WEEK |
| `failed` | this run failed and there were no earlier events to keep | KEPT LAST WEEK chip style, text FAILED |
| `no_source` | no way to get this venue's listings yet | NO SOURCE |
