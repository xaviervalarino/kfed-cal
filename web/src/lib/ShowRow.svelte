<script lang="ts">
  import { STATUS_LABELS, showHref, supportLine, timeLabel } from "./shows";
  import type { Show } from "./types";

  let { show }: { show: Show } = $props();

  const support = $derived(supportLine(show));
</script>

<li class:sold-out={show.status === "sold_out"}>
  <span class="time">{timeLabel(show)}</span>
  <span class="what">
    <a class="band" href={showHref(show)}>{show.title}</a>
    {#if support}
      <span class="support">{support}</span>
    {/if}
  </span>
  <span class="venue">{show.room ?? show.venue}</span>
  <span class="price">
    {#if show.status}
      <span class="status-chip" class:sold-out={show.status === "sold_out"}
        >{STATUS_LABELS[show.status]}</span
      >
    {/if}
    {#if show.price && show.status !== "sold_out"}
      <span>{show.price}</span>
    {/if}
  </span>
</li>

<style>
  /* Fixed columns keep the venues lined up from row to row; long prices
     ("$10 ADVANCE / $15 DOS") wrap inside theirs. */
  li {
    display: grid;
    grid-template-columns: 80px minmax(0, 1fr) 200px 120px;
    grid-template-areas: "time what venue price";
    column-gap: 16px;
    align-items: baseline;
    padding: 12px 0;
    border-bottom: 1px solid var(--color-rule);
  }

  .time {
    grid-area: time;
    font-weight: 700;
    font-size: 14px;
    color: var(--color-red);
  }

  /* Band and support stack in one column, so a venue that wraps doesn't push the support line down. */
  .what {
    grid-area: what;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .band {
    font-family: var(--font-band);
    font-weight: 700;
    font-size: 26px;
    line-height: 1.05;
    color: inherit;
    text-decoration: none;
  }

  .band:hover {
    text-decoration: underline;
  }

  .sold-out .band {
    color: var(--color-dusty);
  }

  .support {
    font-size: 14px;
    line-height: 1.35;
    color: var(--color-dusty);
  }

  .venue {
    grid-area: venue;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--color-pink);
  }

  /* A postponed or rescheduled show keeps its price under the chip; sold out shows only the chip. */
  .price {
    grid-area: price;
    justify-self: end;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    text-align: right;
    gap: 4px;
    font-size: 14px;
    color: var(--color-dusty);
  }

  /* Phone: time · venue · price on one line, then the band, then support. */
  @media (max-width: 720px) {
    li {
      grid-template-columns: auto minmax(0, 1fr) fit-content(45%);
      grid-template-areas:
        "time venue price"
        "what what what";
      column-gap: 8px;
    }

    .time,
    .price {
      font-size: 13px;
    }

    .venue {
      letter-spacing: 0.1em;
    }

    .what {
      margin-top: 4px;
    }

    .band {
      font-size: 25px;
    }
  }
</style>
