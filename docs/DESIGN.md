# Site design

Final screens: https://claude.ai/artifact/7uqtb19jfKxT1dMXcAHR98 (private to the owner).
The same boards are saved in `reference/design/*.dc.html`. They are mockup files: plain HTML with inline
styles, plus a small `renderVals()` script at the bottom holding the sample data. Read them for exact values.
Earlier explorations (rejected looks): https://claude.ai/artifact/SP6vNLUH3DQFoDSpBdDzxo.

## Feel

A cheap xerox / metal-zine flyer, but tidy and easy to scan. Black page, few colors, one loud masthead.
Rejected along the way: grain or dotted backgrounds, dashed underlines, many fonts per row, sticker blocks
behind the logo, cyan or slime green as UI colors, decorative rules or taglines around the logo.

## Color tokens

| Token | Hex | Use |
|---|---|---|
| ground | `#0b0b0b` | page background |
| bone | `#ece6d6` | masthead letters, band names, primary buttons (Get tickets), day-header rule, search underline |
| red | `#ff3b3b` | show times, masthead misprint, SOLD OUT chip |
| pink | `#f4cdd5` | venue names, small caps labels (day of week, "UPDATED …"), counts |
| dusty | `#b98e98` | support lines, prices, button outlines, **selected state** (fill, with black text; the picked day in month view and the phone week strip uses bone instead) |
| rule | `#34302c` | hairlines between rows and around the control rail |
| dim | `#817c74` | empty days in the month grid (4.75:1 on the ground) |
| dark red | `#8f1d1d` | in reserve, unused for now |

All text colors pass 4.5:1 on the ground.

## Type (Google Fonts)

| Font | Use |
|---|---|
| Creepster | masthead "KFED CAL" only |
| Pirata One | dates only: day numbers, "Oct 30", "Nov 2–8", "November" (month view title), section titles |
| Barlow Condensed 600/700 | band names, in their real case (not forced uppercase) |
| Courier Prime 400/700 | everything else: times, venues, support, buttons, labels |

Pirata One sizes: 40px day headers (list and month; the phone sticker too), 36px titles (pager title, filter
sheet), 40px "Scrape status". Ranges use an en dash: unspaced inside a month ("Nov 2–8"), spaced across months
("Oct 26 – Nov 1"). Scraped text is typeset when the events load: curly quotes and apostrophes, and an en dash
for " - ". A no-break space before each "·" and after "w/" and "DOORS" keeps them with the word they follow.
Empty and error messages share one style: Courier 14px, dusty, 1.4 line height.

## Masthead

`KFED CAL`, Creepster, bone, centered, 120px desktop / 64px phone, `text-shadow: 3px 2px 0 #ff3b3b`
(a tight red misprint down-right; 2px 2px on phone). It links to the calendar.
Under it: `UPDATED WED OCT 28` (Courier 700, 12px, 0.2em tracking, pink, underlined), linking to the status page.
The update time is when the last scrape finished.

## Controls

A rail between two `rule` hairlines. Buttons: Courier 700, 14px caps, 0.1em tracking, 44px tall, 1px `dusty`
outline, bone text. Selected: `dusty` fill, black text. Groups: date picks (TONIGHT / WEEKEND / NEXT 7 DAYS),
VENUES ▾ (multi-select, remembered in localStorage), search (bone 2px underline), LIST / WEEK / MONTH
segmented switch. Week and month views put ‹ PREV · title · NEXT › on the left instead of the date picks.
Phone: TONIGHT / WEEKEND / 7 DAYS / FILTER; FILTER opens a bottom sheet (search, when, venues, hide sold out,
"SEE N SHOWS").

## Views

- **List** (default): day header = Pirata date + pink caps label ("FRIDAY · TONIGHT"), 2px bone rule. Rows: time
  (red, bold) · band (Barlow 700) with support line (dusty) · venue (pink caps) · price (dusty) or SOLD OUT chip.
  Phone day header: the date is a bone sticker (ground text, 2px 8px padding, no rotation) with the short
  label ("FRI · TONIGHT") on the right. The mockups in `reference/design/` predate it.
  Phone row: line 1 = time · venue · price, line 2 = band, line 3 = support.
- **Week**: 7 ruled columns; header = pink day-of-week + Pirata numeral; rows stacked (time · venue, band, support).
  Phone: strip of 7 day buttons (dow, numeral, count; the picked day bone-filled with ground text) + that day's
  list.
- **Month**: grid, Sunday first; cell = Pirata numeral, pink show count, top two bands; days with 5+ shows get a
  bone top rule, empty days dimmed; picked day bone-filled with ground text. Side panel (desktop) or list below
  (phone) shows the picked day.
- **Show open** (phone tap / desktop click on the band name): a dialog, full screen on phones and a 560px panel on
  desktop. Image (if any), tickets line, doors and ages when the source has them, GET TICKETS ↗ (bone fill: the
  ticket link, else the event page) and VENUE (outline) buttons, plus EVENT PAGE ↗ when that is a third page.
  Then one section per act: name, `about` with a "From Wikipedia" / "From MusicBrainz" credit, its photo when it
  differs from the top image, and outline link buttons (SPOTIFY … INSTAGRAM, then SEARCH QOBUZ when there's no
  Qobuz link). The URL hash `#show=<source_id>` (or venue|start|title when there's no id) holds the open show, so
  Back closes it and the link can be shared.
- **Sold out**: red chip, band name dims to dusty.

## Status page (`/status.html`)

Same masthead and update line. "Scrape status" heading with run time and next run. Tiles: total shows, venues OK,
needs a look, Haiku cost this run. Table per venue: venue, source, status chip, shows, listings run through,
% with a start time, notes. Status chips: OK (bone outline), PARTIAL (dusty fill: capped or incomplete source),
KEPT LAST WEEK (red fill: this run failed, previous events kept), NO SOURCE (dashed). Not linked from anywhere
except the update line (and an optional footer link).
