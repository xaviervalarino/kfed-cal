<script lang="ts">
  import { PICKS, type Calendar, type View } from "./calendar.svelte";
  import FilterSheet from "./FilterSheet.svelte";
  import VenuePicker from "./VenuePicker.svelte";

  let { calendar }: { calendar: Calendar } = $props();

  const VIEWS: View[] = ["list", "week", "month"];
</script>

<!-- Phones stack this in two rows: date picks or the pager, then the view switch and FILTER. -->
<div class="rail">
  <div class="when" class:pager={calendar.view !== "list"}>
    {#if calendar.view === "list"}
      {#each PICKS as { pick, label, short } (pick)}
        <button
          class="button"
          aria-pressed={calendar.isPicked(pick)}
          onclick={() => calendar.togglePick(pick)}
        >
          <span class="long">{label}</span><span class="short">{short}</span>
        </button>
      {/each}
    {:else}
      <button
        class="button step"
        aria-label="Previous {calendar.view}"
        disabled={!calendar.canGoBack}
        onclick={() => calendar.step(-1)}
      >
        ‹<span class="long">&nbsp;PREV</span>
      </button>
      <h2>{calendar.title}</h2>
      <button
        class="button step"
        aria-label="Next {calendar.view}"
        onclick={() => calendar.step(1)}
      >
        <span class="long">NEXT&nbsp;</span>›
      </button>
    {/if}
  </div>
  <div class="tools">
    <!-- On phones these move into the filter sheet. -->
    <div class="filters">
      <VenuePicker {calendar} />
      <input
        type="search"
        aria-label="Search bands"
        placeholder="search a band…"
        bind:value={calendar.search}
      />
    </div>
    <div class="switch" role="group" aria-label="View">
      {#each VIEWS as view (view)}
        <button
          class="button"
          aria-pressed={calendar.view === view}
          onclick={() => calendar.setView(view)}>{view.toUpperCase()}</button
        >
      {/each}
    </div>
    <!-- The FILTER button and its sheet; the button shows on phones only. -->
    <FilterSheet {calendar} />
  </div>
</div>

<style>
  /* One row: the search box shrinks first. It wraps only when the buttons alone don't fit (under
     about 860px wide in list view, 960px in week view). */
  .rail {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px 24px;
    margin-bottom: 24px;
    padding: 12px 0;
    border-top: 1px solid var(--color-rule);
    border-bottom: 1px solid var(--color-rule);
  }

  .when,
  .tools {
    display: flex;
    align-items: center;
  }

  .when {
    gap: 8px;
  }

  /* A zero basis makes the row wrap by this group's smallest width (search at 100px), not its full one. */
  .tools {
    flex: 1 1 0;
    justify-content: flex-end;
    gap: 16px;
  }

  /* Its children sit in the tools row; the wrapper exists so phones can hide them together. */
  .filters {
    display: contents;
  }

  h2 {
    margin: 0 8px;
    font-family: var(--font-date);
    font-weight: 400;
    font-size: 36px;
    line-height: 1;
    white-space: nowrap;
  }

  input {
    /* The width sets its smallest size (an input's built-in width is wider); the basis lets it grow to 200px. */
    flex: 0 1 200px;
    width: 100px;
    min-width: 100px;
    padding: 8px 2px;
    border: 0;
    border-bottom: 2px solid var(--color-bone);
    background: transparent;
    color: var(--color-bone);
    font-family: var(--font-text);
    font-size: 15px;
  }

  .switch {
    display: flex;
    border: 1px solid var(--color-dusty);
  }

  .switch .button {
    height: 42px;
    border: 0;
  }

  .short {
    display: none;
  }

  /* Narrow desktops and phones: the pager shows only its arrows and "NEXT 7 DAYS" reads "7 DAYS",
     so the bar stays on one row. This breakpoint is for the bar only. */
  @media (max-width: 1100px) {
    .long {
      display: none;
    }

    .short {
      display: inline;
    }

    .step {
      width: 44px;
      padding: 0;
    }
  }

  @media (max-width: 720px) {
    .rail {
      flex-direction: column;
      align-items: stretch;
      gap: 12px;
      margin-bottom: 16px;
    }

    .pager,
    .tools {
      justify-content: space-between;
    }

    /* A week that crosses into another year ("Dec 28 – Jan 3, 2027") wraps. */
    h2 {
      margin: 0;
      font-size: 30px;
      text-align: center;
      white-space: normal;
    }

    .filters {
      display: none;
    }
  }
</style>
