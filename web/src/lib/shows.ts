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
  if (show.doors) return `DOORS ${clockTime(show.doors)}`;
  return "TBA";
}

/** The line under the band name: details, then the support acts. */
export const supportLine = (show: Show) =>
  [show.details, show.support?.length && `w/ ${show.support.join(", ")}`]
    .filter(Boolean)
    .join(" · ");

/** "no shows", "1 show", "7 shows" */
export const showCount = (count: number) =>
  count === 0 ? "no shows" : `${count} ${count === 1 ? "show" : "shows"}`;

export const STATUS_LABELS = {
  sold_out: "SOLD OUT",
  rescheduled: "RESCHEDULED",
  postponed: "POSTPONED",
} as const;
