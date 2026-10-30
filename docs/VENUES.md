# Venues: where each one's events come from

The plan per venue, settled by three probe rounds (details and evidence: `PROBE-FINDINGS.md`).
Prototype code for each method is in `reference/prototypes/` (tested offline against saved pages, not wired in).

All times are venue-local, `America/Los_Angeles`.

## Ticketmaster Discovery API (method `ticketmaster`)

One method covers most rooms. `GET https://app.ticketmaster.com/discovery/v2/events.json?venueId=<id>&size=200&sort=date,asc&apikey=$TICKETMASTER_API_KEY`
(page with `page=N` while `page.totalPages` says more; the API allows about 5 requests/second and 5000/day).
Reference client: `reference/probe_ticketmaster.py`.

| Venue | TM venue id(s) | Upcoming (Oct 30) | Notes |
|---|---|---|---|
| The Echo | KovZ917A967 | 65 | through Apr 2027 |
| Echoplex | KovZpa6OCe | 32 | |
| The Belasco | KovZpZAJvttA | 34 | 3 Universe-ticketed nights are not on TM (their `/shows` page has them) |
| The Wiltern | KovZpZAEAl6A | 89 | |
| Hollywood Palladium | KovZpZAEAlaA | 45 | city is "Hollywood" |
| The Bellwether | KovZ917AiI3 + KovZ917AReX | 36 + 4 | second id is Camille's (bar room); include both |
| Teragram Ballroom | KovZpZAEvnFA | 44 | |
| The Regent | KovZpZAJ6daA | 88 | |
| Greek Theatre | KovZpa2Hxe | 9 | not the Berkeley one (KovZpZAFadlA) |
| The Fonda | KovZpZAFAkIA | 43 | AEG feed also works (see below); pick TM |
| The Roxy | KovZpZAFAIFA | 47 | same |
| Troubadour | KovZpa4eIe | 48 | own site has dates only, no times |
| Hollywood Bowl | KovZpZAFFvJA | 12 | or the Bowl's own feed (below); compare when building |

Useful TM fields: `name`, `dates.start.localDate/localTime`, `dates.status.code` (onsale / offsale / cancelled /
rescheduled / postponed), `url`, `images` (pick the widest 16_9), `priceRanges` (often missing),
`_embedded.attractions` (headliner first, then support), `classifications` (segment Music vs Arts & Theatre etc.).
TM lists separate events for multi-day passes (e.g. "And Always Forever 2026 - 2-DAY PASS"): keep them separate.

## Other sources

| Venue | Method | Source | Notes |
|---|---|---|---|
| Zebulon | `dice_venue` | `https://dice.fm/venue/zebulon-y8bv` → `__NEXT_DATA__` | capped at 30 events (~3 weeks); prices included. Plain request only: dice.fm shows headless browsers a Cloudflare challenge |
| The Paramount | `dice_venue` | `https://dice.fm/venue/the-paramount-7lwp` | |
| Glass House (Pomona) | `dice_venue` | `https://dice.fm/venue/the-glass-house-d5gq` | TM has the venue but 0 events |
| Lodge Room | `tessera` | `eventObjects.push({...})` on the homepage + prices from `tickets.lodgeroomhlp.com/api/v1/products?ids=...` | 71 events with prices. TM has only 2 |
| The Vermont | `tribe_events` | `https://www.vermonthollywood.com/wp-json/tribe/events/v1/events?per_page=50` | 11 events, prices. Site + iCal are behind Cloudflare; this REST path is not |
| Hollywood Bowl (alt) | `hollywood_bowl` | `https://www.hollywoodbowl.com/events/feed` (JSON) | feed mixes LA Phil venues: keep `venue.class == "hb"`; dates only |
| Fonda / Roxy (alt) | `aeg` | `https://aegwebprod.blob.core.windows.net/json/events/18/events.json` (Fonda), `/81/` (Roxy) | prices always "$0" = unknown; drop `statusId == 2` (cancelled) and "TBD" dates |
| El Cid | `ticketmaster` (partial) + TBD | TM KovZ917ASUM has only 3 | `elcidsunset.com/events` (Squarespace) embeds the DICE event-list widget: get its config (prototype `dice_widget_config`) and use that DICE venue/promoter. `?format=json` is disallowed by robots.txt |
| Permanent Records Roadhouse | new HTML method | `http://roadhouse.permanentrecordsla.com/` (http: the https cert is self-signed) | lists shows as text like "November 1st - 6PM"; needs a small parser |
| Monty Bar | `monty_flyer` | weekly flyer image on `https://montybar.com/` (`wp-content/uploads/.../MONTY-weekly-YYYY-NN.png`, strip `-WxH` for full size) read by Claude Haiku 5.5 with a JSON schema | reference: `reference/probe_monty_flyer.py`. 5/5 nights correct, ~$0.001 per run. Keep ambiguous text (e.g. "Performing live: …") in the event's details, never drop it. Flyer covers Wed–Sun, hence the Wednesday schedule |
| Silverlake Lounge | none yet | — | DICE page empty, no site listings, Instagram image posts only. Waiting on the venue's mailing-list email (owner is subscribing). Show it on the status page as "no source" |

## Rules that came out of probing

1. Plain HTTP first (`httpx`), honest User-Agent, respect robots.txt, 2 s between requests to the same host.
   Never fake the User-Agent or try to get past a bot challenge. Playwright only if a venue truly needs it
   (none does today).
2. Detect challenge pages (Cloudflare "Just a moment...", 403 with challenge HTML, Akamai) and raise, so the run
   keeps last week's events for that venue instead of reporting 0.
3. Homepages are curated and capped; use full listings and follow pagination.
4. One method per platform, not per venue (`ticketmaster`, `dice_venue`, `aeg`, `tessera`, `tribe_events`, ...).
5. `brotli` must be installed or httpx can't decode some servers' responses (Troubadour sends `br`).
6. `auto` (JSON-LD) must also walk `event` / `events` keys: DICE nests events in `Place.event`.
7. Cleanup: "$0" = unknown price; "Rescheduled:" / "Moved From X" prefixes become a status; a 00:00:01 start means
   date-only; strip utm / fbclid params; dedupe across venues on the TM event id.
