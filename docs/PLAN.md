# Build plan

State on Oct 30 2026: `main` has a working skeleton (venue list loader, polite fetcher, JSON-LD `auto` method,
runner that keeps last good events, a plain calendar page, monthly workflow, GitHub Pages live at
https://xaviervalarino.github.io/kfed-cal/, currently empty). Probing and design are done. The steps below turn
it into the real site. Do them in order; each ends with tests passing (`python -m unittest`).

How to use this checklist: tick a box (`- [x]`) in the same commit that does the work. Pick up from the first
unticked box. If you leave something half done, leave the box unticked and add a short note under it.

## 1. Housekeeping

- [x] `requirements.txt`: add `brotli` (some servers send br-compressed pages) and `anthropic` (Monty flyer).
  Pin versions like the existing lines.
- [x] `.gitignore`: add `.env`.
- [x] `venues.json`: set `"timezone": "America/Los_Angeles"`.
- [x] `.github/workflows/update.yml`:
  - cron to weekly, early Wednesday Pacific: `"17 10 * * 3"` (10:17 UTC = 3:17 AM PDT / 2:17 AM PST).
  - give the "Scrape venues" step `env: TICKETMASTER_API_KEY: ${{ secrets.TICKETMASTER_API_KEY }}` and
    `ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}` (both secrets already exist in the repo).
  - commit `site/status.json` along with `site/events.json`.
- [x] README: monthly → weekly. (The method table moved to step 3.)

## 2. Venue entries and event schema

- [x] `venues.json` entries gain method parameters. Suggested: one optional `params` object per venue, e.g.
  `{"method": "ticketmaster", "params": {"venue_ids": ["KovZ917AiI3", "KovZ917AReX"]}}`,
  `{"method": "dice_venue", "params": {"slug": "zebulon-y8bv"}}`. Update `scraper/venues.py` (`FIELDS`,
  `METHODS`, validation) to match.
  Done as: `params` for values that aren't a URL; methods that read one URL take it from `events_page` (DICE
  uses its `https://dice.fm/venue/<slug>` page). `venues.py` lists what each method needs.
- [x] Fill in all 21 venues from `VENUES.md` (Silverlake Lounge with no method can be left out of the scrape but
  listed for the status page; pick a clean way).
  There are 22. A venue without `method` is not scraped and shows as "no source" on the status page.
- [x] Event fields (methods return dicts; `run.clean` normalizes): `title` (headliner), `support` (list of names
  or a string), `start` (venue-local `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM`), `doors`, `url` (event page),
  `ticket_url`, `image`, `price` (string as shown, e.g. "$27", "$5–10", "free"; omit when unknown), `age`,
  `status` (`sold_out` / `cancelled` / `rescheduled` / `postponed`), `room` (Echo vs Echoplex, Camille's),
  `source_id` (e.g. `tm:<id>`), `venue`.
  Plus `details` (tour name, presenter, flyer text). The contract with the site is `docs/DATA.md`.
- [x] Cleanup rules in `run.clean`: listed at the end of `VENUES.md`. Drop cancelled events or keep them flagged
  (decide; the design has no cancelled style yet, so dropping is simplest).
  Cancelled events are dropped.

## 3. Methods (`scraper/methods.py`)

Port from `docs/reference/prototypes/` and register each in `METHODS` (and in `venues.py`):

- [x] `ticketmaster`: from `reference/probe_ticketmaster.py` (client). 13 venues, El Cid partial.
- [x] `dice_venue`: from `html_dice_venue_snippet.py`, `html_dice_method.py`. Zebulon, Paramount, Glass House.
- [x] `tessera`: from `feeds_methods_proposed.py` (`tessera`), `feeds_venue_extractors.py` (`lodge_room`).
  Lodge Room.
  Since Oct 30 2026 the ticket API wants a visitor session: the method starts one the way the venue's page does
  (a POST with no body) and sends its id in a `SessionId` header.
- [x] `tribe_events`: from `round2a_tribe_events.py`. The Vermont.
- [x] `monty_flyer`: from `reference/probe_monty_flyer.py`. Monty Bar.
- [x] `permanent_records`: no prototype; write it (text like "November 1st - 6PM"). Permanent Records Roadhouse.
- `aeg`, `hollywood_bowl`, `livenation`: from `axs_methods_snippet.py`, `round2b_methods_round2b.py`,
  `jsonld_proto_methods.py`. Fallbacks only; build one only if TM falls short.

Also:
- [x] `auto`: `_walk` must descend into `event` / `events` keys (DICE nests events in `Place.event`).
- [x] `Fetcher`: detect bot-challenge pages (Cloudflare "Just a moment...", 403 + challenge markup) and raise a
  clear error. Never retry with a fake User-Agent or a browser to get past one.
- [x] A method that needs a key raises a clear error when the env var is missing (the runner then keeps last
  week's events for that venue and the status page shows it).
- [x] README: method table lists the real methods.

## 4. Runner and status

- [x] Cross-venue dedupe on `source_id`.
- [x] Write `site/status.json` every run: run start/end, next run, totals, Haiku tokens and cost, and per venue:
  method, ok / partial / kept-last-week / no-source, event count, last event date, share with a start time, last
  successful run, error text. Keep `last_success` from the previous status.json.
- [x] Keep the `::warning::` lines for the Actions summary.

## 5. Tests

- [x] Small, hand-trimmed fixtures in `scraper/fixtures/` (a few events per source). Make them from the saved
  pages on the `probe` branch (`probe/out/`, or commit 63961a7 for round 2) or from a fresh local fetch. Redact
  tokens (Mapbox `pk.eyJ…`, Google `AIza…`): GitHub push protection rejects commits that contain them.
- [x] One test per method: fixture in, expected events out. Test `clean` rules and status.json shape.
- [x] No network in tests. Mock `anthropic` for `monty_flyer`.

## 6. Site (`web/`)

Per `DESIGN.md` (reference markup in `docs/reference/design/`). A Svelte 5 + Vite + TypeScript app in `web/` that
reads `events.json` and `status.json` (contract: `DATA.md`). The workflow builds it and deploys the build. Must
work at 390px wide.

- [x] App shell: calendar and status pages, design tokens, self-hosted fonts, masthead with the update line.
- [x] List view.
- [x] Status page: reads `status.json`.
- [x] Deploy: the workflow builds `web/` and uploads `web/dist`.
- [x] Week and month views.
- [x] Filters: date picks, venues multi-select saved in localStorage, search, hide sold out; the phone filter
  sheet. Phones switch views from a second bar row (LIST / WEEK / MONTH and FILTER), which the mockups left out.
- [x] Open a show: tap on phones, click on desktop. A `#show=` dialog with tickets, venue, and per-act info and
  links (`DESIGN.md`, "Show open").
- [x] Artist info in `events.json` (`DATA.md`, "Artist fields"): Ticketmaster attraction links and photos,
  MusicBrainz links, Wikipedia summaries, cached in `scraper/cache/artists.json`. A Qobuz search link stands in
  when there is no Qobuz profile link (Qobuz has no public API).
- [x] More venues: The Moroccan Lounge (Ticketmaster), Gold-Diggers (DICE).
- [ ] Shows with no event page (Monty Bar's flyer, most Permanent Records nights: their `url` is the venue's
  homepage): the details view already hides EVENT PAGE there. Still to do: say where the listing comes from
  (Monty Bar: "From the bar's weekly flyer").

## 7. Ship

- [ ] Run the scraper locally against the real sites (`python -m scraper.run`), check `site/status.json`, and view
  the site with that data (`npm --prefix web run dev:site`).
- [x] Push, run the workflow by hand once (Actions → Update calendar → Run workflow), check the live site.
- [ ] Then delete the `probe` branch (owner confirms first). It holds copies of venue pages; `main` never had them.

## Open items (not blocking)

- El Cid: TM has 3 events; the DICE widget on their site may give the full list.
- Silverlake Lounge: no source; owner will forward the venue's mailing-list email.
- Belasco's Universe-ticketed nights are not on TM (minor).
- Footer "SCRAPE STATUS →" link: owner hasn't decided whether to keep it alongside the update-time link.
