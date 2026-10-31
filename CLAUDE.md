# kfed-cal

A free, static calendar of upcoming shows at 24 Los Angeles music venues ("KFED CAL"). A Python scraper runs
weekly on GitHub Actions and commits `site/events.json`, `site/status.json` and `scraper/cache/artists.json`.
The pages are a Svelte app in `web/`; the workflow builds it with the `site/` files copied in, and GitHub Pages
serves the build. Live: https://xaviervalarino.github.io/kfed-cal/

## Branches

- `build` is the working branch; `main` is what's deployed. A push to `main` redeploys the site, so merging to
  `main` publishes: ask before merging to `main` or opening a PR. Keep `main` a fast-forward of `build`.
- The weekly bot commits "Update events" to `main`. Fast-forward `build` to `origin/main` before pushing.
- The workflow runs the tests and `npm run check` before deploying; a failure there stops the deploy.

## Start here

- `README.md`: how the scraper and workflow work, adding a venue, the method table, scraping politely.
- `docs/PLAN.md`: what to build next, in order. Pick up from the first unticked box.
- `docs/DATA.md`: the contract between the scraper and the pages (`events.json`, `status.json`, artist fields).
- `docs/VENUES.md`: where each venue's events come from (Ticketmaster ids, DICE slugs, feeds, quirks).
- `docs/DESIGN.md`: the site design (tokens, type, screens). Mockups in `docs/reference/design/`.
- `docs/PROBE-FINDINGS.md`: evidence from the three probe rounds. `docs/reference/README.md` lists the
  prototype and probe code; it is not part of the running code.

## Layout

- `venues.json`: the venue list (JSON, chosen so it stays portable).
- `scraper/`: `venues.py` loads and validates the list; `fetch.py` is the polite HTTP client; `methods.py` holds
  one method per source platform; `artists.py` looks acts up (Ticketmaster, MusicBrainz, Wikipedia) and keeps
  the cache in `scraper/cache/artists.json`; `run.py` scrapes everything and writes the site data; `check.py`
  inspects a page to pick a method. Tests are `scraper/test_*.py`, fixtures in `scraper/fixtures/`.
- `site/`: the scraper's output, committed by the bot.
- `web/`: the site (Svelte 5, Vite, TypeScript). `index.html` is the calendar and `status.html` the scrape
  status; the code is in `web/src/`, one component per view or control in `web/src/lib/`. A show opens as a
  `#show=` dialog (`lib/ShowDetails.svelte`): the hash is the state. `web/fixtures/` holds sample data in the
  `site/` format for `npm run dev`.
- `.github/workflows/update.yml`: weekly scrape, commit, site build and Pages deploy.

## Commands

```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python -m scraper.venues          # validate venues.json
python -m unittest                # tests (no network)
python -m scraper.run             # scrape everything, write site/ and the artist cache
python -m scraper.check URL --find "a show name"   # what does this page offer?
npm --prefix web install          # site dependencies
npm --prefix web run dev          # the site with the sample data, at http://localhost:5173
npm --prefix web run dev:site     # the site with the scraper's latest site/ files
npm --prefix web run check        # type check
npm --prefix web run format       # format with Prettier
```

Keys for a local run go in the environment (or a `.env` you source; never commit it):
`TICKETMASTER_API_KEY`, `ANTHROPIC_API_KEY`. On GitHub they are repo secrets with the same names.

## Rules

- Be a polite scraper: honest User-Agent (`scraper/fetch.py`), respect robots.txt, delay between requests.
  Never fake the User-Agent, use a headless browser to dodge, or otherwise get past a bot challenge. If a site
  blocks us, use another source (usually Ticketmaster) or report it.
- One exception to robots.txt: documented public APIs that publish rules for apps, used under those rules.
  `ROBOTS_EXCEPTIONS` in `scraper/fetch.py` lists them: the MusicBrainz API (`/ws/2`: 1 request/second,
  User-Agent with a contact), the Wikipedia REST API (User-Agent with a contact and "bot"), and Wikidata's
  `Special:EntityData`, which its robots.txt allows but Python 3.13's parser refuses. List API prefixes only,
  never a site's pages.
- Never commit API keys or scraped pages that contain embedded tokens (GitHub push protection rejects them).
- Stack: Python 3.13, `httpx` + BeautifulSoup and `unittest` for the scraper; Svelte 5, Vite and TypeScript for the
  site, with scoped CSS and no CSS framework. Keep dependencies minimal.
- Cost: $0 except Claude Haiku for one flyer a week (~$0.001). Use model `claude-haiku-5-5`. MusicBrainz and
  Wikipedia are free.
- Scope: the calendar only. No user accounts, no user-submitted events or venue editing for now. No .ics yet.

## Working with the owner

- Explain what you're doing and why; the owner wants to understand how it works.
- Small, plain changes over clever ones. Match the existing code style and comment density.
- User-facing messages (warnings, errors, README) in short, plain, unambiguous sentences.
