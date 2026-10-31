<script lang="ts">
  import { monthAndDay, weekday } from "./dates";
  import { groupByDay } from "./shows";
  import ShowRow from "./ShowRow.svelte";
  import type { Show } from "./types";

  let { shows, today }: { shows: Show[]; today: string } = $props();

  const days = $derived(groupByDay(shows));
</script>

{#each days as group (group.day)}
  <section>
    <h2>
      <span class="date">{monthAndDay(group.day)}</span>
      <span class="label">
        <span class="long">{weekday(group.day)}</span>
        <span class="short">{weekday(group.day, true)}</span>
        {#if group.day === today}· TONIGHT{/if}
      </span>
    </h2>
    <ul>
      {#each group.shows as show (show)}
        <ShowRow {show} />
      {/each}
    </ul>
  </section>
{/each}

<style>
  section {
    margin-bottom: 24px;
  }

  h2 {
    display: flex;
    align-items: baseline;
    gap: 16px;
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
    font-family: var(--font-text);
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--color-pink);
  }

  .short {
    display: none;
  }

  ul {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  @media (max-width: 720px) {
    h2 {
      justify-content: space-between;
    }

    /* A knockout sticker, so the date stands out while scrolling. */
    .date {
      padding: 2px 8px 0;
      background: var(--color-bone);
      color: var(--color-ground);
      font-size: 40px;
    }

    .long {
      display: none;
    }

    .short {
      display: inline;
    }
  }
</style>
