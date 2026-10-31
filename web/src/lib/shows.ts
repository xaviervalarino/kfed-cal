import { clockTime, dayOf } from "./dates";
import type { Show } from "./types";

export interface Day {
  day: string;
  shows: Show[];
}

/** Groups shows by date. Expects them sorted by start, as events.json is. */
export function groupByDay(shows: Show[]): Day[] {
  const days: Day[] = [];
  for (const show of shows) {
    const day = dayOf(show.start);
    const last = days.at(-1);
    if (last?.day === day) last.shows.push(show);
    else days.push({ day, shows: [show] });
  }
  return days;
}

/** The red time in a row: the show time, else the doors time, else TBA. */
export function timeLabel(show: Show): string {
  if (show.start.length > 10) return clockTime(show.start.slice(11));
  if (show.doors) return `DOORS\u00A0${clockTime(show.doors)}`;
  return "TBA";
}

/** Joins parts with a dot. The no-break space keeps the dot from starting a wrapped line. */
export const dotJoin = (parts: unknown[]) =>
  parts.filter(Boolean).join("\u00A0· ");

/** The line under the band name: details, then the support acts. */
export const supportLine = (show: Show) =>
  dotJoin([
    show.details,
    show.support?.length && `w/\u00A0${show.support.join(", ")}`,
  ]);

/** Curly quotes and apostrophes, and an en dash for " - ", in scraped text. */
export const typeset = (text: string) =>
  text
    .replace(/'/g, "’")
    .replace(/"(?=\S)/g, "“")
    .replace(/"/g, "”")
    .replace(/ - /g, " – ");

/** A show with its scraped text typeset. */
export const typesetShow = (show: Show): Show => ({
  ...show,
  title: typeset(show.title),
  details: show.details && typeset(show.details),
  support: show.support?.map(typeset),
});

/** "no shows", "1 show", "7 shows" */
export const showCount = (count: number) =>
  count === 0 ? "no shows" : `${count} ${count === 1 ? "show" : "shows"}`;

export const STATUS_LABELS = {
  sold_out: "SOLD OUT",
  rescheduled: "RESCHEDULED",
  postponed: "POSTPONED",
} as const;
