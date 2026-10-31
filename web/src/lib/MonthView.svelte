<script lang="ts">
  import { untrack } from "svelte";
  import { dayOfWeek, monthAndDay, monthDays, weekday } from "./dates";
  import ShowCard from "./ShowCard.svelte";
  import { groupByDay, showCount } from "./shows";
  import type { Show } from "./types";

  let {
    shows,
    start,
    today,
  }: {
    /** The month's shows that pass the filters, from today on. */
    shows: Show[];
    /** The first of the month, "YYYY-MM-01". */
    start: string;
    today: string;
  } = $props();

  const WEEKDAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
  // The phone bar is full at this many shows.
  const FULL_BAR = 7;

  const showsByDay = $derived(
    new Map(groupByDay(shows).map((group) => [group.day, group.shows])),
  );
  const days = $derived(monthDays(start));

  // Today if it's in the month, else the first day with shows, else the 1st. A new month resets it;
  // the shows are read untracked, so a filter change doesn't move a picked day.
  let picked = $derived(
    today.startsWith(start.slice(0, 7))
      ? today
      : (untrack(() => showsByDay)
          .keys()
          .next().value ?? start),
  );
  const pickedShows = $derived(showsByDay.get(picked) ?? []);
</script>

<div class="month">
  <div class="calendar">
    <div class="weekdays" aria-hidden="true">
      {#each WEEKDAYS as name (name)}
        <span
          ><span class="long">{name}</span><span class="short">{name[0]}</span
          ></span
        >
      {/each}
    </div>
    <div class="grid">
      {#each days as day, index (day)}
        <!-- Days before today are dimmed and can't be picked. -->
        {@const past = day < today}
        {@const list = showsByDay.get(day) ?? []}
        <button
          class="cell"
          class:busy={list.length >= 5}
          class:empty={list.length === 0}
          style:grid-column-start={index === 0 ? dayOfWeek(day) + 1 : undefined}
          aria-pressed={day === picked}
          aria-current={day === today ? "date" : undefined}
          aria-label={past
            ? monthAndDay(day)
            : `${monthAndDay(day)}, ${showCount(list.length)}`}
          disabled={past}
          onclick={() => (picked = day)}
        >
          <span class="head">
            <span class="number">{Number(day.slice(8))}</span>
            {#if list.length}
              <span class="count">{showCount(list.length)}</span>
            {/if}
          </span>
          {#if list.length}
            <span class="bands"
              >{list
                .slice(0, 2)
                .map((show) => show.title)
                .join(" · ")}</span
            >
            <span
              class="bar"
              style:width="{Math.min(list.length / FULL_BAR, 1) * 80}%"
            ></span>
          {/if}
        </button>
      {/each}
    </div>
  </div>

  <section class="day">
    <h3>
      <span class="date">{monthAndDay(picked)}</span>
      <span class="label">
        {weekday(picked, true)}<span class="phone-only"
          >{" · "}{showCount(pickedShows.length)}</span
        >
      </span>
    </h3>
    {#if pickedShows.length}
      <ul>
        {#each pickedShows as show (show)}
          <ShowCard {show} />
        {/each}
      </ul>
    {:else}
      <p class="none">No shows on {monthAndDay(picked)}.</p>
    {/if}
  </section>
</div>

<style>
  .month {
    display: flex;
    gap: 32px;
  }

  .calendar {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .weekdays,
  .grid {
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    gap: 4px;
  }

  .grid {
    grid-auto-rows: 116px;
  }

  .weekdays {
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.2em;
    color: var(--color-pink);
  }

  .weekdays > span {
    padding: 0 8px 4px;
  }

  .short {
    display: none;
  }

  .cell {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 4px;
    padding: 8px;
    border: 0;
    /* A quiet rule on every day, a bone one on busy days. */
    border-top: 2px solid var(--color-rule);
    background: transparent;
    color: var(--color-bone);
    font-family: var(--font-text);
    text-align: left;
    cursor: pointer;
  }

  .cell.busy {
    border-top-color: var(--color-bone);
  }

  .cell.empty {
    color: var(--color-dim);
  }

  .cell:disabled {
    cursor: default;
  }

  .cell:not(:disabled, [aria-pressed="true"]):hover {
    background: var(--color-panel);
  }

  .cell:focus-visible {
    outline: 2px solid var(--color-bone);
    outline-offset: 2px;
  }

  /* The border stays, in the fill color, so the day's text doesn't move when it's picked. */
  .cell[aria-pressed="true"] {
    border-top-color: var(--color-bone);
    background: var(--color-bone);
    color: var(--color-ground);
  }

  /* The count drops under the number when the cell is too narrow for both. */
  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    column-gap: 4px;
  }

  .number {
    font-family: var(--font-date);
    font-size: 30px;
    line-height: 1;
  }

  .count {
    margin-left: auto;
    font-size: 12px;
    color: var(--color-pink);
  }

  .cell[aria-pressed="true"] .count {
    color: var(--color-ground);
  }

  .bands {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
    line-clamp: 3;
    overflow: hidden;
    overflow-wrap: anywhere;
    font-family: var(--font-band);
    font-weight: 600;
    font-size: 15px;
    line-height: 1.15;
  }

  .bar {
    display: none;
    height: 3px;
    background: var(--color-dusty);
  }

  .cell[aria-pressed="true"] .bar {
    background: var(--color-ground);
  }

  .day {
    flex-shrink: 0;
    width: 320px;
  }

  h3 {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin: 0;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--color-bone);
    font-weight: 400;
  }

  .date {
    font-family: var(--font-date);
    font-size: 40px;
    line-height: 1;
  }

  .label {
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--color-pink);
  }

  .phone-only {
    display: none;
  }

  ul {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .none {
    margin: 16px 0 0;
    font-size: 14px;
    line-height: 1.4;
    color: var(--color-dusty);
  }

  /* Beside the grid the cells get too narrow for their count, so the day goes below it. */
  @media (max-width: 1100px) {
    .month {
      flex-direction: column;
      gap: 24px;
    }

    .day {
      width: auto;
    }
  }

  @media (max-width: 720px) {
    .month {
      gap: 16px;
    }

    .weekdays {
      font-size: 11px;
      letter-spacing: 0.1em;
      text-align: center;
    }

    .weekdays > span {
      padding: 0;
    }

    .long {
      display: none;
    }

    .short {
      display: inline;
    }

    .grid {
      grid-auto-rows: 52px;
    }

    .cell {
      align-items: center;
      padding: 6px 0;
    }

    .number {
      font-size: 20px;
    }

    .count,
    .bands {
      display: none;
    }

    .bar {
      display: block;
    }

    h3 {
      justify-content: space-between;
    }

    .phone-only {
      display: inline;
    }
  }
</style>
