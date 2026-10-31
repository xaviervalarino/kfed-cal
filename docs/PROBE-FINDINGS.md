# Venue probe findings (rounds 1–3, Oct 30 2026)

Exploration notes for turning the probes into scraper methods. Prototype code (tested offline against the
saved pages) is in `docs/reference/prototypes/`. The saved pages were on the `probe` branch, deleted Oct 31 2026
once the methods were built; fetch a page fresh to look at it again.

## Per venue

| Venue | Method (prototype) | Source | Coverage | Notes |
|---|---|---|---|---|
| Echo / Echoplex | ticketmaster (planned) | TM Discovery API | full | `/shows` (Next.js payload, `livenation`) caps at 36 ≈ 4 weeks; room in `venue_room_name` |
| Belasco | livenation or ticketmaster | `https://www.thebelasco.com/shows` | 35 = complete | 3 Universe-ticketed events (Confessional) not on TM |
| Wiltern | ticketmaster (planned) | TM API | full | `/shows` capped at 36 ≈ 7 weeks |
| Palladium | ticketmaster (planned) | TM API | full | `/shows` capped at 36 ≈ 4.5 months |
| Bellwether, Teragram, Regent | ticketmaster (planned) | TM API | full | sites behind Cloudflare managed challenge (403 to plain requests); browser passes. HTML methods `ape_html`, `ticketweb_plugin` exist as fallback |
| Greek | ticketmaster (planned) | TM API | full | Akamai blocks headless browsers; `/events-tickets/` loads via Simpleview REST with a token (unverified) |
| Fonda, Roxy | `aeg` | `aegwebprod.blob.core.windows.net/json/events/{18,81}/events.json` | full (46 / 53) | no prices ("$0"); drop statusId 2 (cancelled) and "TBD" dates; has doors, age, AXS link |
| Lodge Room | `tessera` | `eventObjects.push({...})` in homepage + `tickets.lodgeroomhlp.com/api/v1/products?ids=` | full (71), prices | WP `/wp-json/wp/v2/shows` is worse (sorted by post date, no prices) |
| Vermont | `tribe_events` | `/wp-json/tribe/events/v1/events?per_page=50` | full (11), prices | site + iCal behind Cloudflare; the REST API is not |
| Hollywood Bowl | `hollywood_bowl` (round2b) | `https://www.hollywoodbowl.com/events/feed` JSON | full (14) | feed mixes LA Phil venues; keep `venue.class == "hb"` |
| Troubadour | `troubadour` (round2b) | `/events` + `/events/events_ajax/{offset}?...&per_page=12` | full, dates only | needs `brotli` installed (server sends br); no times |
| Glass House, Paramount, Zebulon | `dice_venue` | `dice.fm/venue/<slug>` `__NEXT_DATA__` | Zebulon capped at 30 (~3 weeks, load_more) | plain request only: dice.fm shows headless browsers a Cloudflare challenge. Slugs: the-glass-house-d5gq, the-paramount-7lwp, zebulon-y8bv |
| El Cid, Permanent Records | `dice_venue` | DICE venue page | — | slug unknown: get it from any event page's `venues[0].perm_name` |
| Monty | flyer + Claude Haiku (planned) | weekly flyer image on montybar.com | current week | weekly schedule needed; keep ambiguous flyer text (e.g. "Performing live") with the event, don't drop it |
| Silverlake Lounge | — | — | — | DICE page empty, site has no events, Instagram image posts only. Waiting on the venue's mailing-list email (user subscribing); Meta Business Discovery API is the fallback idea |

## Field availability (drives the UI)

- Always: title, date, link, image. Nearly always: start time (Bowl, Troubadour lack it).
- Common: support acts, doors, age, status (sold out / cancelled / rescheduled), room.
- Rare: price (DICE, Lodge Room, Vermont only). Genre: Live Nation only. Description: rare.

## Scraping lessons

1. Prefer plain requests; headless browsers are blocked outright by DICE (Cloudflare) and the Greek (Akamai).
2. Homepages are capped or curated: target full listings and follow pagination.
3. One method per platform, not per venue.
4. Detect challenge pages and raise, so a block keeps last run's events instead of reporting 0.
5. Event fields to add: support, doors, age, status, room, ticket_url.
6. Cleanup: "$0" = unknown price; strip "Rescheduled:" / "Moved From X" into status; 00:00:01 passes = date-only;
   drop utm/fbclid; cross-venue dedupe on Ticketmaster id.
7. `auto` (`_walk`) misses JSON-LD nested in `Place.event`: add "event"/"events" to the walked keys.
8. Probe pitfalls: GitHub push protection rejects pages containing embedded API tokens (redact before commit);
   `ubuntu-latest` is Ubuntu 26.

## Round 3 results

- Ticketmaster Discovery API: complete listings (every event, 6–18 months ahead) for 16 venues. Venue ids:
  Echo KovZ917A967 (65), Echoplex KovZpa6OCe (32), Belasco KovZpZAJvttA (34), Wiltern KovZpZAEAl6A (89),
  Palladium KovZpZAEAlaA (45), Bellwether KovZ917AiI3 (36) + Camille's KovZ917AReX (4), Teragram KovZpZAEvnFA (44),
  Regent KovZpZAJ6daA (88), Greek KovZpa2Hxe (9), Fonda KovZpZAFAkIA (43), Roxy KovZpZAFAIFA (47),
  Troubadour KovZpa4eIe (48), Hollywood Bowl KovZpZAFFvJA (12). Partial only: El Cid KovZ917ASUM (3),
  Vermont KovZ917At7I (1), Lodge Room KovZpZAFEA1A (2). Not on TM: Zebulon, Glass House, Paramount, Permanent
  Records, Monty, Silverlake Lounge (id exists, 0 events).
- Monty flyer + Claude Haiku 5.5: all 5 nights read correctly (date, time, title, support, price; "Performing
  live" text kept in details). 2605 input + 1543 output tokens = $0.001 per flyer (~5¢/year weekly).
- Permanent Records Roadhouse: http://roadhouse.permanentrecordsla.com/ (https has a self-signed certificate) lists
  shows as "November 1st - 6PM" text: needs an HTML method.
- Troubadour: brotli fixed `/events`; `events_ajax` returns 403 without a Referer header. Use Ticketmaster instead.
- DICE event pages for El Cid / Permanent Records: those events are past, so no venue slug in the page. El Cid can
  use TM (partial) or its own site; find the DICE slug from a current event if needed.
- Zebulon homepage widget: no JSON requests captured even with scrolling. Keep `dice_venue` (30 events ≈ 3 weeks).

## Pending

- Schedule weekly (Wednesday early), build methods from prototypes, extend event schema, update site UI.

## Decisions

- Scope: the calendar only. No user editing of venues or events for now.
- JamBase: rejected. Its only free option is a 14-day evaluation trial that forbids production use and stored data.
- Schedule: weekly (early Wednesday, so Monty's Wed–Sun flyer is current).

## Site design

Superseded: see docs/DESIGN.md.
