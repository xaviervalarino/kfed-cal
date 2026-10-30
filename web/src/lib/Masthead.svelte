<script lang="ts">
  import { updatedLabel } from "./dates";

  let { updated }: { updated?: string } = $props();
</script>

<header>
  <h1><a href="./">KFED CAL</a></h1>
  {#if updated}
    <a class="updated" href="status.html">UPDATED {updatedLabel(updated)}</a>
  {/if}
</header>

<style>
  header {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    margin-bottom: 32px;
  }

  h1 {
    margin: 0;
    font-family: var(--font-masthead);
    font-weight: 400;
    font-size: 120px;
    line-height: 1;
    letter-spacing: 0.02em;
    color: var(--color-bone);
    text-shadow: 3px 2px 0 var(--color-red);
  }

  h1 a {
    color: inherit;
    text-decoration: none;
  }

  .updated {
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.2em;
    color: var(--color-pink);
    text-underline-offset: 4px;
  }

  @media (max-width: 720px) {
    header {
      margin-bottom: 20px;
    }

    h1 {
      font-size: 64px;
      text-shadow: 2px 2px 0 var(--color-red);
    }
  }
</style>
