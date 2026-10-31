<script lang="ts">
  // A show stacked in a narrow space: a week column, or the month view's day panel.
  import {
    dotJoin,
    showHref,
    STATUS_LABELS,
    supportLine,
    timeLabel,
  } from "./shows";
  import type { Show } from "./types";

  let { show }: { show: Show } = $props();

  const venue = $derived(show.room ?? show.venue);
  // The mockup puts the price at the end of the support line. A sold out show has no price to show.
  const subline = $derived(
    dotJoin([supportLine(show), show.status !== "sold_out" && show.price]),
  );
</script>

<li class:sold-out={show.status === "sold_out"}>
  <span class="when">
    <span class="time">{timeLabel(show)}</span>
    <span class="venue" title={venue}>{venue}</span>
  </span>
  <a class="band" href={showHref(show)}>{show.title}</a>
  {#if subline}
    <span class="support">{subline}</span>
  {/if}
  {#if show.status}
    <span class="status-chip" class:sold-out={show.status === "sold_out"}
      >{STATUS_LABELS[show.status]}</span
    >
  {/if}
</li>

<style>
  /* The parent sets --inset: week columns pad the sides, the month panel doesn't. */
  li {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 12px var(--inset, 0);
    border-bottom: 1px solid var(--color-rule);
  }

  /* min-width: 0 lets the venue shrink and show its ellipsis. */
  .when {
    display: flex;
    align-items: baseline;
    gap: 6px;
    min-width: 0;
  }

  .time {
    flex-shrink: 0;
    font-weight: 700;
    font-size: 13px;
    color: var(--color-red);
  }

  .venue {
    overflow: hidden;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--color-pink);
  }

  .band {
    font-family: var(--font-band);
    font-weight: 700;
    font-size: 21px;
    line-height: 1.05;
    color: inherit;
    text-decoration: none;
    overflow-wrap: anywhere;
  }

  .band:hover {
    text-decoration: underline;
  }

  .sold-out .band {
    color: var(--color-dusty);
  }

  .support {
    font-size: 13px;
    line-height: 1.35;
    color: var(--color-dusty);
    overflow-wrap: anywhere;
  }

  .status-chip {
    align-self: flex-start;
  }

  /* On phones the month panel runs full width, so it takes the list's larger type. */
  @media (max-width: 720px) {
    .venue {
      font-size: 13px;
    }

    .band {
      font-size: 23px;
    }

    .support {
      font-size: 14px;
    }
  }
</style>
