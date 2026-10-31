<script lang="ts">
  // A show's details, opened by a "#show=…" link (showHref). The hash is the state, so Back
  // closes the dialog and a shared link opens it.
  import { clockTime, dayOf, monthAndDay, weekday } from "./dates";
  import { STATUS_LABELS, showFromHash, supportLine, timeLabel } from "./shows";
  import type { Artist, ArtistLinkKind, Show, Venue } from "./types";

  let {
    shows,
    venues,
    artists,
  }: {
    /** Typeset shows, so their keys match the rows' links. */
    shows: Show[];
    venues: Venue[];
    /** Keyed by typeset name, as the shows' titles and support are. */
    artists: Record<string, Artist>;
  } = $props();

  /** Profile links in the contract's order (docs/DATA.md, Artist fields). */
  const LINKS: [ArtistLinkKind, string][] = [
    ["spotify", "SPOTIFY"],
    ["bandcamp", "BANDCAMP"],
    ["qobuz", "QOBUZ"],
    ["apple_music", "APPLE MUSIC"],
    ["soundcloud", "SOUNDCLOUD"],
    ["youtube", "YOUTUBE"],
    ["homepage", "WEBSITE"],
    ["instagram", "INSTAGRAM"],
  ];

  /** Acts without a Spotify, Bandcamp or Qobuz link get a search there instead. */
  const SEARCHES: [ArtistLinkKind, string, string][] = [
    ["spotify", "SEARCH SPOTIFY", "https://open.spotify.com/search/"],
    [
      "bandcamp",
      "SEARCH BANDCAMP",
      "https://bandcamp.com/search?item_type=b&q=",
    ],
    ["qobuz", "SEARCH QOBUZ", "https://www.qobuz.com/us-en/search?q="],
  ];

  let dialog: HTMLDialogElement;
  // Where the last pointerdown landed; a plain variable, since nothing renders from it.
  let pressed: EventTarget | null = null;
  let hash = $state(location.hash);
  // Set once the hash changes on the page: the history entry below the show's is then this page.
  let navigated = false;

  const show = $derived(showFromHash(shows, hash));

  $effect(() => {
    if (show && !dialog.open) dialog.showModal();
    else if (!show && dialog.open) dialog.close();
  });

  // Drops the hash without adding a history entry, so Back still leaves the site.
  function dropHash() {
    history.replaceState(
      history.state,
      "",
      location.pathname + location.search,
    );
    hash = "";
  }

  // A link to a show that is no longer listed would leave its hash in the URL over the list.
  $effect(() => {
    if (hash.startsWith("#show=") && !show) dropHash();
  });

  // Closing goes back to the entry below the show's or, for a link opened from outside, drops the hash.
  function onclose() {
    if (!show) return;
    if (navigated) history.back();
    else dropHash();
  }

  const credit = (source: string) =>
    URL.parse(source)?.hostname.endsWith("wikipedia.org")
      ? "From Wikipedia"
      : "From MusicBrainz";

  // Ticketmaster serves one photo in several crops ("…/<id>_ARTIST_PAGE_3_2.jpg",
  // "…/<id>_TABLET_LANDSCAPE_LARGE_16_9.jpg"), so images compare without the crop suffix.
  const photo = (url?: string) => url?.replace(/_[A-Z0-9_]+\.jpg$/, "");
</script>

<svelte:window
  onhashchange={() => {
    hash = location.hash;
    navigated = true;
  }}
/>

<!-- The dialog's padding is zero, so a press and click that both land on the dialog itself hit the backdrop. -->
<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
<dialog
  bind:this={dialog}
  aria-labelledby="show-title"
  {onclose}
  onpointerdown={(event) => (pressed = event.target)}
  onclick={(event) => {
    if (event.target === dialog && pressed === dialog) dialog.close();
  }}
>
  {#if show}
    {@const day = dayOf(show.start)}
    {@const support = supportLine(show)}
    {@const image = show.image ?? artists[show.title]?.image}
    {@const website = venues.find((v) => v.name === show.venue)?.website}
    <!-- DICE and venue pages sell tickets on the event page itself. -->
    {@const tickets =
      show.ticket_url ?? (show.url !== website ? show.url : undefined)}
    <!-- A doors-only show already has its doors time in the red time. -->
    {@const doors = show.start.length > 10 && show.doors}
    {@const price = show.status !== "sold_out" && show.price}
    {@const acts = [show.title, ...(show.support ?? [])].map((name) => ({
      name,
      artist: artists[name] ?? {},
    }))}
    <div class="panel">
      <div class="show">
        <div class="day">
          <span class="date">{monthAndDay(day)}</span>
          <span class="label">{weekday(day)}</span>
        </div>

        <div class="when">
          <span class="time">{timeLabel(show)}</span>
          <span class="venue">{show.room ?? show.venue}</span>
          <!-- autofocus: an overflowing panel is focusable too, and would take focus first. -->
          <!-- svelte-ignore a11y_autofocus -->
          <button class="close" autofocus onclick={() => dialog.close()}
            >CLOSE <span aria-hidden="true">×</span></button
          >
        </div>

        <div class="what">
          <h2 id="show-title" class:sold-out={show.status === "sold_out"}>
            {show.title}
          </h2>
          {#if support}
            <p class="support">{support}</p>
          {/if}
        </div>

        {#if image}
          <img class="image" src={image} alt="" />
        {/if}

        {#if show.status || price || doors || show.age}
          <dl>
            {#if show.status || price}
              <dt>TICKETS</dt>
              <dd class="tickets">
                {#if show.status}
                  <span
                    class="status-chip"
                    class:sold-out={show.status === "sold_out"}
                    >{STATUS_LABELS[show.status]}</span
                  >
                {/if}
                {#if price}{price}{/if}
              </dd>
            {/if}
            {#if doors}
              <dt>DOORS</dt>
              <dd>{clockTime(doors)}</dd>
            {/if}
            {#if show.age}
              <dt>AGES</dt>
              <dd>{show.age}</dd>
            {/if}
          </dl>
        {/if}

        <div class="actions">
          {#if tickets}
            <a class="primary" href={tickets} target="_blank" rel="noopener"
              >GET TICKETS <span aria-hidden="true">↗</span></a
            >
          {/if}
          {#if website}
            <a
              class="button outline"
              href={website}
              target="_blank"
              rel="noopener">VENUE</a
            >
          {/if}
          {#if show.url !== tickets && show.url !== website}
            <a
              class="button outline"
              href={show.url}
              target="_blank"
              rel="noopener">EVENT PAGE <span aria-hidden="true">↗</span></a
            >
          {/if}
        </div>
      </div>

      <div class="acts">
        {#each acts as { name, artist } (name)}
          <section class="act">
            <h3>{name}</h3>
            {#if artist.about}
              <p class="about">{artist.about}</p>
              {#if artist.about_source}
                <a
                  class="credit"
                  href={artist.about_source}
                  target="_blank"
                  rel="noopener">{credit(artist.about_source)}</a
                >
              {/if}
            {/if}
            {#if artist.image && photo(artist.image) !== photo(image)}
              <img class="image" src={artist.image} alt="" />
            {/if}
            <div class="links">
              {#each LINKS as [kind, label] (kind)}
                {#if artist.links?.[kind]}
                  <a href={artist.links[kind]} target="_blank" rel="noopener"
                    >{label}</a
                  >
                {/if}
              {/each}
              {#each SEARCHES as [kind, label, url] (kind)}
                {#if !artist.links?.[kind]}
                  <a
                    href={url + encodeURIComponent(name)}
                    target="_blank"
                    rel="noopener">{label}</a
                  >
                {/if}
              {/each}
            </div>
          </section>
        {/each}
      </div>
    </div>
  {/if}
</dialog>

<style>
  /* Desktop: a centered panel. The browser caps a modal dialog's size, so set it outright. */
  dialog {
    width: min(960px, calc(100% - 32px));
    max-width: none;
    max-height: calc(100dvh - 64px);
    padding: 0;
    border: 1px solid var(--color-rule);
    background: var(--color-ground);
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

  /* Desktop: the show on the left, its acts on the right, each column scrolling on its own. */
  .panel {
    display: flex;
    gap: 32px;
    flex: 1;
    min-height: 0;
    padding: 24px;
  }

  .show,
  .acts {
    display: flex;
    flex-direction: column;
    gap: 12px;
    flex: 1 1 0;
    min-width: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  /* A scrolling column squashes its children to fit unless told not to. */
  .show > *,
  .acts > * {
    flex-shrink: 0;
  }

  @media (min-width: 721px) {
    /* CLOSE hangs 8px past the column's edge. The padding keeps it and its focus ring inside the scroller. */
    .show {
      margin-right: -8px;
      padding-right: 8px;
    }

    .acts {
      padding-left: 32px;
      border-left: 1px solid var(--color-rule);
    }

    .acts > .act:first-child {
      margin-top: 0;
      padding-top: 0;
      border-top: 0;
    }
  }

  .day {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--color-bone);
  }

  .date {
    font-family: var(--font-date);
    font-size: 40px;
    line-height: 1;
  }

  .label,
  dt {
    color: var(--color-pink);
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
  }

  .when {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }

  .time {
    font-weight: 700;
    font-size: 13px;
    color: var(--color-red);
  }

  .venue {
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--color-pink);
  }

  /* The negative margins give a bigger tap target without moving the row. */
  .close {
    flex-shrink: 0;
    height: 40px;
    margin: -10px -8px -10px auto;
    padding: 0 8px;
    border: 0;
    background: none;
    color: var(--color-dusty);
    font: inherit;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.1em;
    cursor: pointer;
  }

  .what {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  h2 {
    margin: 0;
    font-family: var(--font-band);
    font-weight: 700;
    font-size: 32px;
    line-height: 1.05;
  }

  h2.sold-out {
    color: var(--color-dusty);
  }

  .support {
    margin: 0;
    font-size: 14px;
    line-height: 1.35;
    color: var(--color-dusty);
  }

  /* Flyers and DICE images can be square; contain keeps the whole flyer readable. */
  .image {
    display: block;
    width: 100%;
    max-height: 360px;
    object-fit: contain;
    border: 1px solid var(--color-rule);
    background: var(--color-panel);
  }

  dl {
    display: grid;
    grid-template-columns: 96px minmax(0, 1fr);
    gap: 6px 12px;
    margin: 0;
    font-size: 14px;
  }

  dt {
    align-self: baseline;
    letter-spacing: 0.1em;
  }

  dd {
    margin: 0;
  }

  .tickets {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 8px;
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .primary,
  .outline {
    flex: 1 0 auto;
    display: flex;
    align-items: center;
    justify-content: center;
    /* A flex box drops the space before the ↗ span; the gap stands in for it. */
    gap: 0.6em;
    height: 48px;
    padding: 0 16px;
    text-decoration: none;
  }

  /* The color also beats the global a:hover white, which would vanish on bone. */
  .primary {
    flex-grow: 2;
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 0.1em;
    background: var(--color-bone);
    color: var(--color-ground);
  }

  .act {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 12px;
    padding-top: 16px;
    border-top: 1px solid var(--color-rule);
  }

  h3 {
    margin: 0;
    font-family: var(--font-band);
    font-weight: 700;
    font-size: 24px;
    line-height: 1.05;
  }

  .about {
    margin: 0;
    font-size: 14px;
    line-height: 1.45;
  }

  .credit {
    align-self: flex-start;
    font-size: 12px;
    color: var(--color-dusty);
    text-underline-offset: 3px;
  }

  .links {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .links a {
    display: flex;
    align-items: center;
    height: 36px;
    padding: 0 10px;
    border: 1px solid var(--color-dusty);
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.08em;
    text-decoration: none;
  }

  /* Phone: full screen, one scrolling column with the acts under the show. */
  @media (max-width: 720px) {
    dialog {
      width: 100%;
      height: 100%;
      max-height: none;
      margin: 0;
      border: 0;
    }

    .panel {
      flex-direction: column;
      gap: 12px;
      padding: 24px 16px;
      overflow-y: auto;
      overscroll-behavior: contain;
    }

    /* The columns' children join the panel's one column. */
    .show,
    .acts {
      display: contents;
    }
  }
</style>
