<script lang="ts">
  import { getJson } from "./lib/data";
  import Masthead from "./lib/Masthead.svelte";
  import RunBar from "./lib/status/RunBar.svelte";
  import Tiles from "./lib/status/Tiles.svelte";
  import VenueTable from "./lib/status/VenueTable.svelte";
  import type { StatusFile } from "./lib/types";

  let status = $state.raw<StatusFile>();
  let failed = $state(false);

  getJson<StatusFile>("status.json").then(
    (loaded) => (status = loaded),
    (error) => {
      console.error(error);
      failed = true;
    },
  );
</script>

<Masthead updated={status?.run.finished} />
<main>
  {#if status}
    <RunBar run={status.run} />
    <Tiles {status} />
    <VenueTable venues={status.venues} />
  {:else if failed}
    <p class="error">The status report didn’t load. Try again later.</p>
  {/if}
</main>

<style>
  main {
    display: flex;
    flex-direction: column;
    gap: 24px;
    max-width: 1200px;
    margin: 0 auto;
  }

  .error {
    margin: 16px 0 0;
    font-size: 14px;
    line-height: 1.4;
    color: var(--color-dusty);
  }
</style>
