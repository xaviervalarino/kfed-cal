<script lang="ts">
  import type { VenueStatus } from "../types";

  let { status }: { status: VenueStatus } = $props();

  const LABELS: Record<VenueStatus, string> = {
    ok: "OK",
    partial: "PARTIAL",
    kept: "KEPT LAST WEEK",
    failed: "FAILED",
    no_source: "NO SOURCE",
  };
</script>

<span class="chip {status}">{LABELS[status]}</span>

<style>
  .chip {
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.12em;
    white-space: nowrap;
  }

  /* Outlined chips use 1px padding and filled chips 2px, so both measure the same. */
  .ok {
    padding: 1px 6px;
    color: var(--color-bone);
    border: 1px solid var(--color-bone);
  }

  .partial {
    padding: 2px 6px;
    color: var(--color-ground);
    background: var(--color-dusty);
  }

  /* A failed venue gets the kept look but says FAILED (docs/DATA.md). */
  .kept,
  .failed {
    padding: 2px 6px;
    color: var(--color-ground);
    background: var(--color-red);
  }

  .no_source {
    padding: 1px 6px;
    color: var(--color-dusty);
    border: 1px dashed var(--color-dusty);
  }
</style>
