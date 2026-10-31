<script lang="ts">
  import { monthAndDay, weekday } from "../dates";
  import ListView from "../ListView.svelte";
  import { showCount } from "../shows";
  import type { WeekDay } from "./days";

  let { days, today }: { days: WeekDay[]; today: string } = $props();

  // The parent remounts this for each week, so a pick never carries over to another week.
  let chosen = $state<string>();

  // Today, else the first day with shows, else Monday. Past days hold no shows.
  const picked = $derived(
    days.find((d) => d.day === chosen && !d.past) ??
      days.find((d) => d.day === today) ??
      days.find((d) => d.shows.length) ??
      days[0],
  );

  const label = ({ day, shows }: WeekDay) =>
    `${weekday(day)}, ${monthAndDay(day)}, ${showCount(shows.length)}`;
</script>

<div class="strip" role="group" aria-label="Pick a day">
  {#each days as d (d.day)}
    <button
      type="button"
      class="day"
      aria-label={label(d)}
      aria-pressed={d.day === picked.day}
      disabled={d.past}
      onclick={() => (chosen = d.day)}
    >
      <span class="dow">{weekday(d.day, true)}</span>
      <span class="num">{Number(d.day.slice(8))}</span>
      <span class="count">{d.shows.length}</span>
    </button>
  {/each}
</div>

{#if picked.shows.length}
  <ListView shows={picked.shows} {today} />
{:else}
  <p class="empty">No shows on {monthAndDay(picked.day)}.</p>
{/if}

<style>
  .strip {
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    gap: 4px;
    margin-bottom: 16px;
  }

  .day {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-height: 64px;
    padding: 6px 0;
    border: 1px solid var(--color-rule);
    background: transparent;
    color: var(--color-bone);
    font-family: var(--font-text);
    cursor: pointer;
  }

  .day:disabled {
    opacity: 0.35;
    cursor: default;
  }

  .day[aria-pressed="true"] {
    border-color: var(--color-bone);
    background: var(--color-bone);
    color: var(--color-ground);
  }

  .dow {
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--color-pink);
  }

  .num {
    font-family: var(--font-date);
    font-size: 26px;
    line-height: 1.1;
  }

  .count {
    font-size: 11px;
    color: var(--color-dusty);
  }

  .day[aria-pressed="true"] :is(.dow, .count) {
    color: var(--color-ground);
  }

  .empty {
    margin: 16px 0 0;
    font-size: 14px;
    line-height: 1.4;
    color: var(--color-dusty);
  }
</style>
