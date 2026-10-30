# Build plan

State on Oct 30 2026: `main` has a working skeleton (venue list loader, polite fetcher, JSON-LD `auto` method,
runner that keeps last good events, a plain calendar page, monthly workflow, GitHub Pages live at
https://xaviervalarino.github.io/kfed-cal/, currently empty). Probing and design are done. The steps below turn
it into the real site. Do them in order; each ends with tests passing (`python -m unittest`).

## 1. Housekeeping (done)

- `requirements.txt`: add `brotli` (some servers send br-compressed pages) and `anthropic` (Monty flyer).
  Pin versions like the existing lines.
- `.gitignore`: add `.env`.
- `venues.json`: set `"timezone": "America/Los_Angeles"`.
- `.github/workflows/update.yml`:
  - cron to weekly, early Wednesday Pacific: `"17 10 * * 3"` (10:17 UTC = 3:17 AM PDT / 2:17 AM PST).
  - give the "Scrape venues" step `env: TICKETMASTER_API_KEY: ${{ secrets.TICKETMASTER_API_KEY }}` and
    `ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}` (both secrets already exist in the repo).
  - commit `site/status.json` along with `site/events.json`.
- README: monthly → weekly (done); method table gets the real methods (still to do, after step 3).

## 2. Venue entries and event schema

- `venues.json` entries gain method parameters. Suggested: one optional `params` object per venue, e.g.
  `{"method": "ticketmaster", "params": {"venue_ids": ["KovZ917AiI3", "KovZ917AReX"]}}`,
  `{"method": "dice_venue", "params": {"slug": "zebulon-y8bv"}}`. Update `scraper/venues.py` (`FIELDS`,
  `METHODS`, validation) to match. Fill in all 21 venues from `VENUES.md` (Silverlake Lounge with no method can
  be left out of the scrape but listed for the status page; pick a clean way).
- Event fields (methods return dicts; `run.clean` normalizes): `title` (headliner), `support` (list of names or a
  string), `start` (venue-local `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM`), `doors`, `url` (event page), `ticket_url`,
  `image`, `price` (string as shown, e.g. "$27", "$5–10", "free"; omit when unknown), `age`, `status`
  (`sold_out` / `cancelled` / `rescheduled` / `postponed`), `room` (Echo vs Echoplex, Camille's), `source_id`
  (e.g. `tm:<id>`), `venue`.
- Cleanup rules in `run.clean`: listed at the end of `VENUES.md`. Drop cancelled events or keep them flagged
  (decide; the design has no cancelled style yet, so dropping is simplest).

## 3. Methods (`scraper/methods.py`)

Port from `docs/reference/prototypes/` and register each in `METHODS` (and in `venues.py`):

| Method | Prototype | Venues |
|---|---|---|
| `ticketmaster` | `reference/probe_ticketmaster.py` (client) | 13 venues, El Cid partial |
| `dice_venue` | `html_dice_venue_snippet.py`, `html_dice_method.py` | Zebulon, Paramount, Glass House |
| `tessera` | `feeds_methods_proposed.py` (`tessera`), `feeds_venue_extractors.py` (`lodge_room`) | Lodge Room |
| `tribe_events` | `round2a_tribe_events.py` | The Vermont |
| `monty_flyer` | `reference/probe_monty_flyer.py` | Monty Bar |
| `permanent_records` | none yet: write it (text like "November 1st - 6PM") | Permanent Records Roadhouse |
| `aeg`, `hollywood_bowl`, `livenation` | `axs_methods_snippet.py`, `round2b_methods_round2b.py`, `jsonld_proto_methods.py` | fallbacks only; build if TM falls short |

Also:
- `auto`: `_walk` must descend into `event` / `events` keys (DICE nests events in `Place.event`).
- `Fetcher`: detect bot-challenge pages (Cloudflare "Just a moment...", 403 + challenge markup) and raise a clear
  error. Never retry with a fake User-Agent or a browser to get past one.
- A method that needs a key raises a clear error when the env var is missing (the runner then keeps last week's
  events for that venue and the status page shows it).

## 4. Runner and status

- Cross-venue dedupe on `source_id`.
- Write `site/status.json` every run: run start/end, next run, totals, Haiku tokens and cost, and per venue:
  method, ok / partial / kept-last-week / no-source, event count, last event date, share with a start time, last
  successful run, error text. Keep `last_success` from the previous status.json.
- Keep the `::warning::` lines for the Actions summary.

## 5. Tests

- Small, hand-trimmed fixtures in `scraper/fixtures/` (a few events per source). Make them from the saved pages
  on the `probe` branch (`probe/out/`, or commit 63961a7 for round 2) or from a fresh local fetch. Redact tokens
  (Mapbox `pk.eyJ…`, Google `AIza…`): GitHub push protection rejects commits that contain them.
- One test per method: fixture in, expected events out. Test `clean` rules and status.json shape.
- No network in tests. Mock `anthropic` for `monty_flyer`.

## 6. Site (`site/`)

Rebuild `site/index.html` and add `site/status.html` per `DESIGN.md` (reference markup in
`docs/reference/design/`). Keep it dependency-free: one HTML file each, inline CSS and vanilla JS, Google Fonts
link. Reads `events.json` / `status.json`. List / week / month views, filters (date picks, venues multi-select
saved in localStorage, search, hide sold out), tap to expand on phones. Must work at 390px wide.

## 7. Ship

- Run the scraper locally against the real sites (`python -m scraper.run`), check `site/status.json`, open
  `site/index.html` with a local server (`python -m http.server -d site`).
- Push, run the workflow by hand once (Actions → Update calendar → Run workflow), check the live site.
- Then delete the `probe` branch (owner confirms first). It holds copies of venue pages; `main` never had them.

## Open items (not blocking)

- El Cid: TM has 3 events; the DICE widget on their site may give the full list.
- Silverlake Lounge: no source; owner will forward the venue's mailing-list email.
- Belasco's Universe-ticketed nights are not on TM (minor).
- Footer "SCRAPE STATUS →" link: owner hasn't decided whether to keep it alongside the update-time link.
