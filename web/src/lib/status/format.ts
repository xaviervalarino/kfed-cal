// Formatting for the status page. Run times are UTC ISO strings; the page shows Los Angeles time.
import { dayFormat, partsInLA } from "../dates";
import { dotJoin } from "../shows";
import type { VenueReport } from "../types";

/** "WED", the Los Angeles weekday of a run time. */
export const weekdayLabel = (iso: string) =>
  partsInLA(new Date(iso), { weekday: "short" }).weekday.toUpperCase();

/** "WED, 3:21AM PT". "PT" stays fixed so the label reads the same in summer and winter. */
export function runLabel(iso: string): string {
  const { weekday, hour, minute, dayPeriod } = partsInLA(new Date(iso), {
    weekday: "short",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  return `${weekday}, ${hour}:${minute}${dayPeriod} PT`.toUpperCase();
}

/** "2027-04-18" → "Apr 2027" */
export const monthAndYear = dayFormat({ month: "short", year: "numeric" });

/** 1 → "100%", 0.456 → "46%" */
export const percent = (share: number) => `${Math.round(share * 100)}%`;

/** The phone layout's second line: "Ticketmaster · 36 shows · through Nov 2026 · 100% with a time". Missing parts are skipped. */
export function venueDetails(venue: VenueReport): string {
  return dotJoin([
    venue.source,
    `${venue.events} ${venue.events === 1 ? "show" : "shows"}`,
    venue.through && `through ${monthAndYear(venue.through)}`,
    venue.with_time !== undefined && `${percent(venue.with_time)} with a time`,
  ]);
}
