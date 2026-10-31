// The calendar page's state: which view is showing, the filters, and the week or month on screen.
import {
  addDays,
  addMonths,
  dayOf,
  dayOfWeek,
  monthAndDay,
  monthName,
  monthStart,
  todayInLA,
  weekStart,
} from "./dates";
import type { Show, Venue } from "./types";

export type View = "list" | "week" | "month";
export type DatePick = "tonight" | "weekend" | "week";

/** The date picks, with a full label for desktops and a short one for phones. */
export const PICKS: { pick: DatePick; label: string; short: string }[] = [
  { pick: "tonight", label: "TONIGHT", short: "TONIGHT" },
  { pick: "weekend", label: "WEEKEND", short: "WEEKEND" },
  { pick: "week", label: "NEXT 7 DAYS", short: "7 DAYS" },
];

const HIDDEN_VENUES_KEY = "kfed-cal:hidden-venues";

/** The first and last day a date pick covers. */
export function pickRange(pick: DatePick, today: string): [string, string] {
  if (pick === "tonight") return [today, today];
  if (pick === "week") return [today, addDays(today, 6)];
  // Weekend: Friday to Sunday, or what's left of it from Friday on.
  const dow = dayOfWeek(today);
  const sunday = dow === 0 ? today : addDays(today, 7 - dow);
  const first = dow >= 1 && dow <= 4 ? addDays(today, 5 - dow) : today;
  return [first, sunday];
}

// Letters that NFD does not split into a base letter and an accent.
const LOOKALIKES: Record<string, string> = {
  ð: "d",
  đ: "d",
  ø: "o",
  æ: "ae",
  œ: "oe",
  ß: "ss",
  ł: "l",
  þ: "th",
  ı: "i",
};

// Lowercase without accents, so "dadi" finds "Daði Freyr" and "mo" finds "Mø". Curly quotes
// become straight ones, so a typed apostrophe finds the typeset one.
const fold = (text: string) =>
  text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/[’‘]/g, "'")
    .replace(/[“”]/g, '"')
    .toLowerCase()
    .replace(/[ðđøæœßłþı]/g, (letter) => LOOKALIKES[letter]);

// Storage can be missing or blocked (private windows); the filter then lasts for the visit only.
function readHiddenVenues(): string[] {
  try {
    const saved = JSON.parse(localStorage.getItem(HIDDEN_VENUES_KEY) ?? "[]");
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

export class Calendar {
  shows = $state.raw<Show[]>([]);
  venues = $state.raw<Venue[]>([]);
  view = $state<View>("list");
  /** Filters the list view only. */
  pick = $state<DatePick>();
  search = $state("");
  /** Venues the visitor turned off. Stored as hidden, so a venue added later shows by default. */
  hiddenVenues = $state.raw<string[]>(readHiddenVenues());
  hideSoldOut = $state(false);
  today = $state(todayInLA());
  /** The first day of the week (a Monday) or month on screen in week and month view. */
  anchor = $state("");

  /** Venues turned on, counted from `venues` so a saved name of a venue that left the list doesn't count. */
  shownVenues = $derived(
    this.venues.filter((venue) => !this.hiddenVenues.includes(venue.name))
      .length,
  );

  /** Shows that pass the venue, search and sold-out filters. */
  matching = $derived.by(() => {
    const query = fold(this.search.trim());
    const hidden = new Set(this.hiddenVenues);
    return this.shows.filter(
      (show) =>
        !hidden.has(show.venue) &&
        !(this.hideSoldOut && show.status === "sold_out") &&
        (!query ||
          fold(
            [show.title, show.details, ...(show.support ?? [])].join(" "),
          ).includes(query)),
    );
  });

  /** The first and last day on screen. It never starts before today: events.json can be a week old. */
  range = $derived.by((): [string, string] => {
    if (this.view === "list")
      return this.pick
        ? pickRange(this.pick, this.today)
        : [this.today, "9999-12-31"];
    const last =
      this.view === "week"
        ? addDays(this.anchor, 6)
        : addDays(addMonths(this.anchor, 1), -1);
    return [this.anchor > this.today ? this.anchor : this.today, last];
  });

  /** The shows the current view lists. */
  visible = $derived.by(() => {
    const [first, last] = this.range;
    return this.matching.filter((show) => {
      const day = dayOf(show.start);
      return day >= first && day <= last;
    });
  });

  /** Whether a filter narrows what's shown, so an empty view can say so. */
  filtered = $derived(
    this.search.trim() !== "" ||
      this.hideSoldOut ||
      this.shownVenues < this.venues.length ||
      (this.view === "list" && this.pick !== undefined),
  );

  /** The pager title: "Nov 2–8", "Oct 26 – Nov 1", "November", "January 2027". */
  title = $derived.by(() => {
    const thisYear = this.today.slice(0, 4);
    if (this.view === "week") {
      const last = addDays(this.anchor, 6);
      const sameMonth = this.anchor.slice(0, 7) === last.slice(0, 7);
      const span = sameMonth
        ? `${monthAndDay(this.anchor)}–${Number(last.slice(8))}`
        : `${monthAndDay(this.anchor)} – ${monthAndDay(last)}`;
      const year = last.slice(0, 4);
      return year === thisYear ? span : `${span}, ${year}`;
    }
    const year = this.anchor.slice(0, 4);
    return year === thisYear
      ? monthName(this.anchor)
      : `${monthName(this.anchor)} ${year}`;
  });

  /** Paging stops at the week or month holding today; earlier ones have no shows. */
  canGoBack = $derived(this.anchor > this.#periodStart(this.today));

  /** The Monday or the first of the month on or before a day, for the view on screen. */
  #periodStart(day: string) {
    return this.view === "week" ? weekStart(day) : monthStart(day);
  }

  setView(view: View) {
    this.view = view;
    if (view !== "list") this.anchor = this.#periodStart(this.today);
  }

  /** Moves week or month view one week or month forward (1) or back (-1). */
  step(direction: 1 | -1) {
    this.anchor =
      this.view === "week"
        ? addDays(this.anchor, 7 * direction)
        : addMonths(this.anchor, direction);
  }

  /** For a tab left open past midnight: moves to the new day, and up from a week or month that has passed. */
  refreshToday() {
    this.today = todayInLA();
    if (this.view !== "list" && this.anchor < this.#periodStart(this.today))
      this.setView(this.view);
  }

  /** Date picks apply to the list, so they read as picked only there. */
  isPicked(pick: DatePick) {
    return this.view === "list" && this.pick === pick;
  }

  /** Picks a date range and switches to the list, or clears the pick when it's already picked. */
  togglePick(pick: DatePick) {
    if (this.isPicked(pick)) {
      this.pick = undefined;
      return;
    }
    this.pick = pick;
    this.setView("list");
  }

  toggleVenue(name: string) {
    this.setHiddenVenues(
      this.hiddenVenues.includes(name)
        ? this.hiddenVenues.filter((n) => n !== name)
        : [...this.hiddenVenues, name],
    );
  }

  showAllVenues() {
    this.setHiddenVenues([]);
  }

  hideAllVenues() {
    this.setHiddenVenues(this.venues.map((venue) => venue.name));
  }

  setHiddenVenues(names: string[]) {
    this.hiddenVenues = names;
    try {
      localStorage.setItem(HIDDEN_VENUES_KEY, JSON.stringify(names));
    } catch {
      // Not saved; see readHiddenVenues.
    }
  }
}
