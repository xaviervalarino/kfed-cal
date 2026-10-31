<script lang="ts">
  import type { StatusFile } from "../types";
  import { runLabel, weekdayLabel } from "./format";

  let { run }: { run: StatusFile["run"] } = $props();
</script>

<div class="bar">
  <h2>Scrape status</h2>
  <span class="times"
    >RUN {runLabel(run.finished)} · NEXT {weekdayLabel(run.next)}</span
  >
</div>

<style>
  .bar {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    /* Wraps on a phone, where the heading and the times don't fit on one line. */
    flex-wrap: wrap;
    gap: 4px 16px;
    padding: 12px 0;
    border-top: 1px solid var(--color-rule);
    border-bottom: 2px solid var(--color-bone);
  }

  h2 {
    margin: 0;
    font-family: var(--font-date);
    font-weight: 400;
    font-size: 40px;
    line-height: 1;
  }

  .times {
    font-size: 13px;
    letter-spacing: 0.1em;
    color: var(--color-pink);
  }
</style>
