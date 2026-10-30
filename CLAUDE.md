# kfed-cal

A free, static calendar of upcoming shows at ~21 Los Angeles music venues ("KFED CAL"). A Python scraper runs
weekly on GitHub Actions, writes `site/events.json` (and soon `site/status.json`), and GitHub Pages serves
`site/`. Live: https://xaviervalarino.github.io/kfed-cal/

## Start here

- `docs/PLAN.md`: what to build next, in order. Pick up from the first unfinished step.
- `docs/VENUES.md`: where each venue's events come from (Ticketmaster ids, DICE slugs, feeds, quirks).
- `docs/DESIGN.md`: the final site design (tokens, type, screens). Mockups in `docs/reference/design/`.
- `docs/PROBE-FINDINGS.md`: evidence from the three probe rounds.
- `docs/reference/`: prototype code for each scraping method, the probe scripts for Ticketmaster and Monty's
  flyer, and `sample-events.json` (real events from 5 venues, Oct 30 2026) for building the UI.

## Layout

- `venues.json`: the venue list (JSON, chosen so it stays portable).
- `scraper/venues.py` loads and validates it; `fetch.py` is the polite HTTP client; `methods.py` holds one
  method per source platform; `run.py` scrapes everything and writes the site data; `check.py` inspects a page
  to pick a method.
- `site/index.html`: the calendar (single file, vanilla JS). `site/events.json`: generated, committed by the bot.
- `.github/workflows/update.yml`: scheduled scrape + Pages deploy.

## Commands

```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python -m scraper.venues          # validate venues.json
python -m unittest                # tests (no network)
python -m scraper.run             # scrape everything, write site/events.json
python -m scraper.check URL --find "a show name"   # what does this page offer?
python -m http.server -d site     # view the site at http://localhost:8000
```

Keys for a local run go in the environment (or a `.env` you source; never commit it):
`TICKETMASTER_API_KEY`, `ANTHROPIC_API_KEY`. On GitHub they are repo secrets with the same names.

## Rules

- Be a polite scraper: honest User-Agent (`scraper/fetch.py`), respect robots.txt, delay between requests.
  Never fake the User-Agent, use a headless browser to dodge, or otherwise get past a bot challenge. If a site
  blocks us, use another source (usually Ticketmaster) or report it.
- Never commit API keys or scraped pages that contain embedded tokens (GitHub push protection rejects them).
- Stack: Python 3.13, `httpx` + BeautifulSoup, `unittest`. Keep dependencies minimal; no frameworks for the site.
- Cost: $0 except Claude Haiku for one flyer a week (~$0.001). Use model `claude-haiku-5-5`.
- Scope: the calendar only. No user accounts, no user-submitted events or venue editing for now. No .ics yet.

## Working with the owner

- Explain what you're doing and why; the owner wants to understand how it works.
- Small, plain changes over clever ones. Match the existing code style and comment density.
- User-facing messages (warnings, errors, README) in short, plain, unambiguous sentences.
- Work on a branch. Ask before merging to `main` or opening a PR.
