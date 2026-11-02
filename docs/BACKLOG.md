# Backlog

Nothing here is scheduled. The build checklist that got the site live is in git history (`docs/PLAN.md`, removed
Nov 2 2026).

## Venues

- Silverlake Lounge: no source. The owner will forward the venue's mailing-list email; a method can read that.
- Fallback methods, built only if Ticketmaster falls short for a venue: `aeg` (Fonda, Roxy) and `hollywood_bowl`.
  Sources and quirks are in `VENUES.md`; prototypes in `reference/prototypes/` (`axs_methods_snippet.py`,
  `round2b_methods_round2b.py`).

## Artist info

- Spotify Web API for exact profile links and photos. Not now: development-mode apps need the app owner to have
  Spotify Premium (https://developer.spotify.com/documentation/web-api/concepts/quota-modes), which breaks the $0
  rule, and the developer terms limit storing Spotify content (https://developer.spotify.com/terms, IV.3). Acts
  without a Spotify link get a SEARCH SPOTIFY button instead.
- If `events.json` grows a lot (more venues), move `artists` into its own `site/artists.json` and load it after
  the calendar shows. On Nov 2 2026 `events.json` was 966 KB, 197 KB gzipped.

## Workflow

- The scrape commits to `main` at the end of its run. A push to `main` during a run makes that commit fail
  ("rejected, fetch first") and the run's data is lost; run the workflow again. A `git pull --rebase` before the
  bot's `git push` in `update.yml` would prevent it.
