<script lang="ts">
  import { monthAndDay, weekday } from "./dates";
  import ShowCard from "./ShowCard.svelte";
  import type { Show } from "./types";
  import { weekDays } from "./week/days";
  import PhoneWeek from "./week/PhoneWeek.svelte";

  let {
    shows,
    start,
    today,
  }: {
    /** The week's shows that pass the filters, from today on. */
    shows: Show[];
    /** The week's Monday, "YYYY-MM-DD". */
    start: string;
    today: string;
  } = $props();

  const days = $derived(weekDays(shows, start, today));
</script>

<ol class="columns">
  {#each days as d (d.day)}
    <li class:past={d.past}>
      <h3
        aria-label="{weekday(d.day)}, {monthAndDay(d.day)}"
        aria-current={d.day === today ? "date" : undefined}
      >
        <span class="dow">{weekday(d.day, true)}</span>
        <span class="num">{Number(d.day.slice(8))}</span>
      </h3>
      <ul>
        {#each d.shows as show (show)}
          <ShowCard {show} />
        {/each}
      </ul>
    </li>
  {/each}
</ol>

<!-- Phone: a strip of day buttons and the picked day's shows. The key resets the pick each week. -->
<div class="phone">
  {#key start}
    <PhoneWeek {days} {today} />
  {/key}
</div>

<style>
  ol,
  ul {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .columns ul {
    --inset: 12px;
  }

  .columns {
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    border-left: 1px solid var(--color-rule);
  }

  li {
    min-width: 0;
    border-right: 1px solid var(--color-rule);
  }

  h3 {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 0;
    padding: 12px 0 8px;
    border-bottom: 2px solid var(--color-bone);
    font-weight: 400;
  }

  .past h3 {
    opacity: 0.35;
  }

  .dow {
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--color-pink);
  }

  .num {
    font-family: var(--font-date);
    font-size: 52px;
    line-height: 1;
  }

  .phone {
    display: none;
  }

  @media (max-width: 720px) {
    .columns {
      display: none;
    }

    .phone {
      display: block;
    }
  }
</style>
