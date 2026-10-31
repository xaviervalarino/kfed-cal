<script lang="ts">
  import type { Calendar } from "./calendar.svelte";

  let { calendar }: { calendar: Calendar } = $props();

  let open = $state(false);
  let picker: HTMLElement;
</script>

<svelte:window
  onclick={(event) => {
    if (open && !picker.contains(event.target as Node)) open = false;
  }}
  onkeydown={(event) => {
    if (event.key === "Escape") open = false;
  }}
/>

<div class="picker" bind:this={picker}>
  <button class="button" aria-expanded={open} onclick={() => (open = !open)}>
    VENUES{calendar.shownVenues < calendar.venues.length
      ? ` · ${calendar.shownVenues}`
      : ""} <span aria-hidden="true">▾</span>
  </button>
  {#if open}
    <div class="panel">
      <div class="quick">
        <button class="link" onclick={() => calendar.showAllVenues()}
          >ALL</button
        >
        <button class="link" onclick={() => calendar.hideAllVenues()}
          >NONE</button
        >
      </div>
      {#each calendar.venues as venue (venue.name)}
        <label>
          <input
            type="checkbox"
            checked={!calendar.hiddenVenues.includes(venue.name)}
            onchange={() => calendar.toggleVenue(venue.name)}
          />
          {venue.name}
        </label>
      {/each}
      <label class="sold-out">
        <input type="checkbox" bind:checked={calendar.hideSoldOut} />
        Hide sold out
      </label>
    </div>
  {/if}
</div>

<style>
  .picker {
    position: relative;
  }

  .panel {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    z-index: 10;
    display: grid;
    grid-template-columns: repeat(2, max-content);
    gap: 8px 24px;
    padding: 16px;
    border: 1px solid var(--color-dusty);
    background: var(--color-panel);
  }

  .quick {
    grid-column: 1 / -1;
    display: flex;
    gap: 16px;
  }

  label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    cursor: pointer;
  }

  .sold-out {
    grid-column: 1 / -1;
    padding-top: 12px;
    border-top: 1px solid var(--color-rule);
  }

  input {
    accent-color: var(--color-dusty);
  }
</style>
