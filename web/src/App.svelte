<script lang="ts">
  import { Calendar } from "./lib/calendar.svelte";
  import Controls from "./lib/Controls.svelte";
  import ListView from "./lib/ListView.svelte";
  import Masthead from "./lib/Masthead.svelte";
  import MonthView from "./lib/MonthView.svelte";
  import WeekView from "./lib/WeekView.svelte";
  import { getJson } from "./lib/data";
  import type { EventsFile } from "./lib/types";

  const calendar = new Calendar();
  let file = $state.raw<EventsFile>();
  let failed = $state(false);

  getJson<EventsFile>("events.json").then(
    (loaded) => {
      file = loaded;
      calendar.shows = loaded.events;
      calendar.venues = loaded.venues;
    },
    (error) => {
      console.error(error);
      failed = true;
    },
  );

  // A tab left open past midnight rolls over; background tabs throttle timers, so
  // the visibilitychange handler below covers the return to the tab.
  $effect(() => {
    const timer = setInterval(() => calendar.refreshToday(), 60_000);
    return () => clearInterval(timer);
  });
</script>

<svelte:document onvisibilitychange={() => calendar.refreshToday()} />

<Masthead updated={file?.updated} />
<main class:wide={calendar.view !== "list"}>
  {#if failed}
    <p class="message">The calendar didn't load. Try again later.</p>
  {:else if file}
    <Controls {calendar} />
    {#if calendar.view !== "list" && !calendar.visible.length && calendar.filtered}
      <p class="message">No shows match these filters.</p>
    {/if}
    {#if calendar.view === "week"}
      <WeekView
        shows={calendar.visible}
        start={calendar.anchor}
        today={calendar.today}
      />
    {:else if calendar.view === "month"}
      <MonthView
        shows={calendar.visible}
        start={calendar.anchor}
        today={calendar.today}
      />
    {:else if calendar.visible.length}
      <ListView shows={calendar.visible} today={calendar.today} />
    {:else}
      <p class="message">
        {calendar.filtered
          ? "No shows match these filters."
          : "No upcoming shows are listed."}
      </p>
    {/if}
  {/if}
</main>

<style>
  /* The list reads best narrow; week and month use the full width (mockups). */
  main {
    max-width: 1040px;
    margin: 0 auto;
  }

  main.wide {
    max-width: 1200px;
  }

  .message {
    color: var(--color-dusty);
  }
</style>
