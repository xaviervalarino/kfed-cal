<script lang="ts">
  import type { VenueReport } from "../types";
  import { monthAndYear, percent, venueDetails } from "./format";
  import StatusChip from "./StatusChip.svelte";

  let { venues }: { venues: VenueReport[] } = $props();
</script>

<!-- On a narrow desktop window only this wrapper scrolls sideways; the page itself never does. -->
<div class="scroller">
  <table>
    <colgroup>
      <col style="width: 216px" />
      <col style="width: 196px" />
      <col style="width: 166px" />
      <col style="width: 86px" />
      <col style="width: 126px" />
      <col style="width: 96px" />
      <col />
    </colgroup>
    <thead>
      <tr>
        <th>VENUE</th>
        <th>SOURCE</th>
        <th>STATUS</th>
        <th>SHOWS</th>
        <th>THROUGH</th>
        <th>W/ TIME</th>
        <th>NOTES</th>
      </tr>
    </thead>
    <tbody>
      {#each venues as venue (venue.name)}
        <tr>
          <td class="venue">{venue.name}</td>
          <td class="muted">{venue.source}</td>
          <td><StatusChip status={venue.status} /></td>
          <td class="shows">{venue.events}</td>
          <td>{venue.through ? monthAndYear(venue.through) : ""}</td>
          <td
            >{venue.with_time === undefined ? "" : percent(venue.with_time)}</td
          >
          <td class="muted">{venue.note}</td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<!-- Phone layout: a table of seven columns doesn't fit, so each venue is a short block instead. -->
<ul class="cards">
  {#each venues as venue (venue.name)}
    <li>
      <div class="top">
        <span class="venue">{venue.name}</span>
        <StatusChip status={venue.status} />
      </div>
      <div class="details">{venueDetails(venue)}</div>
      {#if venue.note}
        <div class="details">{venue.note}</div>
      {/if}
    </li>
  {/each}
</ul>

<style>
  .scroller {
    overflow-x: auto;
  }

  .cards {
    display: none;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  li {
    padding: 10px 0;
    border-bottom: 1px solid var(--color-rule);
  }

  .top {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
  }

  .details {
    margin-top: 2px;
    font-size: 13px;
    color: var(--color-dusty);
  }

  table {
    width: 100%;
    /* Keeps the notes column readable; narrower screens scroll the wrapper. */
    min-width: 1100px;
    table-layout: fixed;
    border-collapse: collapse;
    font-size: 14px;
  }

  th,
  td {
    padding: 7px 16px 7px 0;
    vertical-align: baseline;
    text-align: left;
    border-bottom: 1px solid var(--color-rule);
  }

  th:last-child,
  td:last-child {
    padding-right: 0;
  }

  th {
    padding-top: 8px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--color-bone);
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.15em;
    color: var(--color-pink);
  }

  .venue {
    font-family: var(--font-band);
    font-weight: 700;
    font-size: 18px;
  }

  .shows {
    font-weight: 700;
  }

  .muted {
    color: var(--color-dusty);
  }

  @media (max-width: 720px) {
    .scroller {
      display: none;
    }

    .cards {
      display: block;
    }
  }
</style>
