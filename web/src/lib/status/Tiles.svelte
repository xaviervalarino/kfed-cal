<script lang="ts">
  import type { StatusFile } from "../types";

  let { status }: { status: StatusFile } = $props();

  // "Needs a look" is this week's problems only: partial and no_source are known gaps.
  const venuesOk = $derived(
    status.venues.filter((v) => v.status === "ok").length,
  );
  const needsLook = $derived(
    status.venues.filter((v) => v.status === "kept" || v.status === "failed")
      .length,
  );

  const tiles = $derived([
    { label: "SHOWS", value: status.totals.events.toLocaleString("en-US") },
    { label: "VENUES OK", value: `${venuesOk} / ${status.totals.venues}` },
    { label: "NEEDS A LOOK", value: String(needsLook) },
    { label: "HAIKU THIS RUN", value: `$${status.haiku.dollars.toFixed(3)}` },
  ]);
</script>

<div class="tiles">
  {#each tiles as tile (tile.label)}
    <div class="tile">
      <span class="label">{tile.label}</span>
      <span class="value">{tile.value}</span>
    </div>
  {/each}
</div>

<style>
  .tiles {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
  }

  .tile {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 12px 16px;
    border: 1px solid var(--color-rule);
  }

  .label {
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.2em;
    color: var(--color-pink);
  }

  .value {
    font-family: var(--font-band);
    font-weight: 700;
    font-size: 36px;
    line-height: 1.1;
  }

  @media (max-width: 720px) {
    .tiles {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
