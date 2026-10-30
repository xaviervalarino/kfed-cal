// Event times are Los Angeles wall-clock strings ("2026-10-30T19:00"). Keep them as strings:
// a Date built from one would shift into the visitor's own time zone.

const TIME_ZONE = "America/Los_Angeles";

// The fixtures are a snapshot of this day, so `npm run dev` shows them as upcoming.
const FIXTURES_DAY = "2026-10-30";

/** The parts of a moment's Los Angeles date and time, by type: `{ weekday: "Wed", hour: "3", … }`. */
export const partsInLA = (date: Date, options: Intl.DateTimeFormatOptions) =>
  Object.fromEntries(
    new Intl.DateTimeFormat("en-US", { timeZone: TIME_ZONE, ...options })
      .formatToParts(date)
      .map((part) => [part.type, part.value]),
  );

/** Today as "YYYY-MM-DD" in Los Angeles. */
export function todayInLA(): string {
  if (import.meta.env?.MODE === "fixtures") return FIXTURES_DAY;
  const { year, month, day } = partsInLA(new Date(), {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  return `${year}-${month}-${day}`;
}

/** The "YYYY-MM-DD" part of a start time. */
export const dayOf = (start: string) => start.slice(0, 10);

// Day math runs on midnight UTC: a date-only string parses that way, and UTC has no DST shifts.
export function addDays(day: string, days: number): string {
  const date = new Date(day);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

/** 0 for Sunday through 6 for Saturday. */
export const dayOfWeek = (day: string) => new Date(day).getUTCDay();

/** The Monday on or before a day. Weeks run Monday to Sunday so a weekend stays in one week. */
export const weekStart = (day: string) =>
  addDays(day, -((dayOfWeek(day) + 6) % 7));

/** The first of a day's month: "2026-11-01". */
export const monthStart = (day: string) => `${day.slice(0, 8)}01`;

/** The first of the month `months` away from the first of a month. */
export function addMonths(first: string, months: number): string {
  const date = new Date(first);
  date.setUTCMonth(date.getUTCMonth() + months);
  return date.toISOString().slice(0, 10);
}

/** Every day of the month that starts on `first`. */
export function monthDays(first: string): string[] {
  const next = addMonths(first, 1);
  const days: string[] = [];
  for (let day = first; day < next; day = addDays(day, 1)) days.push(day);
  return days;
}

/**
 * A formatter for "YYYY-MM-DD" days. A date-only string parses as midnight UTC, so formatting in
 * UTC gives back the same calendar day in any visitor's zone. Make each one once: creating a
 * formatter costs about as much as 100 format calls.
 */
export function dayFormat(options: Intl.DateTimeFormatOptions) {
  const format = new Intl.DateTimeFormat("en-US", {
    timeZone: "UTC",
    ...options,
  });
  return (day: string) => format.format(new Date(day));
}

/** "October 30" */
export const monthAndDay = dayFormat({ month: "long", day: "numeric" });

/** "November" */
export const monthName = dayFormat({ month: "long" });

const longWeekday = dayFormat({ weekday: "long" });
const shortWeekday = dayFormat({ weekday: "short" });

/** "Friday", or "Fri" with `short`. */
export const weekday = (day: string, short = false) =>
  short ? shortWeekday(day) : longWeekday(day);

/** "19:00" → "7PM", "18:30" → "6:30PM" */
export function clockTime(hhmm: string): string {
  const [hh, mm] = hhmm.split(":");
  const hour = Number(hh);
  return `${hour % 12 || 12}${mm === "00" ? "" : ":" + mm}${hour < 12 ? "AM" : "PM"}`;
}

/** A UTC run time as the Los Angeles date: "WED OCT 28". */
export function updatedLabel(iso: string): string {
  const parts = partsInLA(new Date(iso), {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  return `${parts.weekday} ${parts.month} ${parts.day}`.toUpperCase();
}
