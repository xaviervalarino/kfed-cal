<script lang="ts">
  import ListView from "./lib/ListView.svelte";
  import Masthead from "./lib/Masthead.svelte";
  import { getJson } from "./lib/data";
  import { dayOf, todayInLA } from "./lib/dates";
  import type { EventsFile } from "./lib/types";

  let today = $state(todayInLA());
  let file = $state.raw<EventsFile>();
  let failed = $state(false);

  getJson<EventsFile>("events.json").then(
    (loaded) => (file = loaded),
    (error) => {
      console.error(error);
      failed = true;
    },
  );

  // events.json is up to a week old, so drop the days that have passed since the scrape.
  const upcoming = $derived(
    file?.events.filter((show) => dayOf(show.start) >= today) ?? [],
  );
</script>

<!-- A tab left open past midnight moves to the new day when it's shown again. -->
<svelte:document onvisibilitychange={() => (today = todayInLA())} />

<Masthead updated={file?.updated} />
<main>
  {#if failed}
    <p class="message">The calendar didn't load. Try again later.</p>
  {:else if file && upcoming.length === 0}
    <p class="message">No upcoming shows are listed.</p>
  {:else if file}
    <ListView shows={upcoming} {today} />
  {/if}
</main>

<style>
  main {
    max-width: 1040px;
    margin: 0 auto;
  }

  .message {
    color: var(--color-dusty);
  }
</style>
