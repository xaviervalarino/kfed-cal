# Reference material (not part of the running code)

- `prototypes/`: scraping methods written and tested offline against saved venue pages during the probes.
  Port them into `scraper/methods.py`; don't import them from here.
- `probe_ticketmaster.py`, `probe_monty_flyer.py`: the probe scripts that looked up Ticketmaster venue ids and
  read Monty's flyer with Claude Haiku. They were run from `probe/` on the `probe` branch, so their import paths
  won't work from here as-is.
- `design/`: the final mockup boards (`*.dc.html`, inline styles + sample data in the script at the bottom) and
  the canvas layout. See `../DESIGN.md`.
- `sample-events.json`: 104 real events from the Echo, Belasco, Wiltern, Zebulon and the Paramount
  (Oct 30 – Nov 30 2026), in the prototype methods' output shape. Handy for building the UI before the scraper
  is done.
