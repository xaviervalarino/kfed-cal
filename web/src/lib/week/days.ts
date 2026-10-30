import { addDays } from "../dates";
import { groupByDay } from "../shows";
import type { Show } from "../types";

export interface WeekDay {
  day: string;
  /** Before today. */
  past: boolean;
  shows: Show[];
}

/** The seven days from `start` (a Monday), each with its shows. */
export function weekDays(
  shows: Show[],
  start: string,
  today: string,
): WeekDay[] {
  const byDay = new Map(groupByDay(shows).map((d) => [d.day, d.shows]));
  return Array.from({ length: 7 }, (_, i) => {
    const day = addDays(start, i);
    return { day, past: day < today, shows: byDay.get(day) ?? [] };
  });
}
