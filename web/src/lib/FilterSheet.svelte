<script lang="ts">
  import { tick } from "svelte";
  import { PICKS, type Calendar } from "./calendar.svelte";
  import { showCount } from "./shows";

  let { calendar }: { calendar: Calendar } = $props();

  /** Venue chips shown before "+ N MORE". */
  const FIRST_CHIPS = 12;

  let dialog: HTMLDialogElement;
  let chips: HTMLElement;
  let expanded = $state(false);

  const venues = $derived(calendar.venues);
  const venuesLabel = $derived(
    calendar.shownVenues === venues.length
      ? "VENUES · ALL"
      : `VENUES · ${calendar.shownVenues} PICKED`,
  );
  const chipVenues = $derived(expanded ? venues : venues.slice(0, FIRST_CHIPS));
  const count = $derived(calendar.visible.length);
  const showLabel = $derived(
    count === 0 ? "NO SHOWS MATCH" : `SHOW ${showCount(count).toUpperCase()}`,
  );

  // The "+ N MORE" chip leaves the page when pressed, so focus moves to the first new chip.
  async function showAll() {
    expanded = true;
    await tick();
    (chips.children[FIRST_CHIPS] as HTMLElement | undefined)?.focus();
  }
</script>

<button
  class="button open"
  aria-haspopup="dialog"
  onclick={() => dialog.showModal()}>FILTER</button
>

<!-- The dialog's padding is zero, so a click that lands on the dialog itself hit the backdrop. -->
<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
<dialog
  bind:this={dialog}
  aria-labelledby="filters-title"
  onclick={(event) => {
    if (event.target === dialog) dialog.close();
  }}
>
  <div class="sheet">
    <div class="top">
      <h2 id="filters-title">Filters</h2>
      <button class="close" onclick={() => dialog.close()}>CLOSE ×</button>
    </div>

    <label class="field">
      <span class="label">SEARCH</span>
      <input
        type="search"
        placeholder="band or night name"
        autocomplete="off"
        bind:value={calendar.search}
      />
    </label>

    <div class="field" role="group" aria-labelledby="filters-when">
      <span class="label" id="filters-when">WHEN</span>
      <div class="chips">
        {#each PICKS as { pick, short } (pick)}
          <button
            class="button pick"
            aria-pressed={calendar.isPicked(pick)}
            onclick={() => calendar.togglePick(pick)}>{short}</button
          >
        {/each}
      </div>
    </div>

    <div class="field" role="group" aria-labelledby="filters-venues">
      <div class="venues-head">
        <span class="label" id="filters-venues">{venuesLabel}</span>
        <span class="quick">
          <button class="link" onclick={() => calendar.showAllVenues()}
            >ALL</button
          >
          <button class="link" onclick={() => calendar.hideAllVenues()}
            >NONE</button
          >
        </span>
      </div>
      <div class="chips" bind:this={chips}>
        {#each chipVenues as venue (venue.name)}
          <button
            class="button chip"
            aria-pressed={!calendar.hiddenVenues.includes(venue.name)}
            onclick={() => calendar.toggleVenue(venue.name)}
            >{venue.name}</button
          >
        {/each}
        {#if !expanded && venues.length > FIRST_CHIPS}
          <button class="button chip" onclick={showAll}
            >+ {venues.length - FIRST_CHIPS} MORE</button
          >
        {/if}
      </div>
    </div>

    <label class="sold-out">
      <span>Hide sold out</span>
      <input type="checkbox" bind:checked={calendar.hideSoldOut} />
    </label>

    <button class="show" aria-live="polite" onclick={() => dialog.close()}
      >{showLabel}</button
    >
  </div>
</dialog>

<style>
  /* Phones only: desktops have the venue dropdown and search in the bar. */
  .open {
    display: none;
  }

  @media (max-width: 720px) {
    .open {
      display: block;
    }
  }

  dialog {
    /* Bottom sheet: the browser centers a modal dialog and caps its width, so undo that. */
    width: 100%;
    max-width: none;
    max-height: calc(100dvh - 48px);
    margin: auto 0 0;
    padding: 0;
    border: 0;
    border-top: 2px solid var(--color-bone);
    background: var(--color-panel);
    color: var(--color-bone);
  }

  /* display is set only while open, or this rule would keep a closed dialog on screen. */
  dialog[open] {
    display: flex;
    flex-direction: column;
  }

  dialog::backdrop {
    background: color-mix(in srgb, var(--color-ground) 75%, transparent);
  }

  .sheet {
    display: flex;
    flex-direction: column;
    gap: 24px;
    flex: 1;
    min-height: 0;
    padding: 16px 16px 24px;
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  /* A scrolling column squashes its children to fit unless told not to. */
  .sheet > * {
    flex-shrink: 0;
  }

  .top {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  h2 {
    margin: 0;
    font-family: var(--font-date);
    font-weight: 400;
    font-size: 36px;
    line-height: 1;
  }

  .close {
    height: 44px;
    padding: 0;
    border: 0;
    background: none;
    color: var(--color-pink);
    font: inherit;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.1em;
    cursor: pointer;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .label {
    color: var(--color-pink);
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.2em;
  }

  input[type="search"] {
    padding: 8px 2px;
    border: 0;
    border-bottom: 2px solid var(--color-bone);
    border-radius: 0;
    appearance: none;
    background: transparent;
    color: var(--color-bone);
    font-family: var(--font-text);
    /* 16px, one more than the mockup: iOS Safari zooms the page into smaller text fields. */
    font-size: 16px;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .pick {
    padding: 0 12px;
  }

  .chip {
    height: 40px;
    padding: 0 10px;
    font-size: 12px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .venues-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .quick {
    display: flex;
    gap: 16px;
  }

  .sold-out {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 44px;
    font-size: 15px;
    cursor: pointer;
  }

  .sold-out input {
    width: 22px;
    height: 22px;
    accent-color: var(--color-bone);
  }

  .show {
    height: 52px;
    border: 0;
    background: var(--color-bone);
    color: var(--color-ground);
    font-family: var(--font-text);
    font-weight: 700;
    font-size: 15px;
    letter-spacing: 0.1em;
    cursor: pointer;
  }
</style>
