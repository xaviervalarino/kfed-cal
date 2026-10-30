<header>
  <h1><a href="./">KFED CAL</a></h1>
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
    color: var(--bone);
    text-shadow: 3px 2px 0 var(--red);
  }

  h1 a {
    color: inherit;
    text-decoration: none;
  }

  @media (max-width: 720px) {
    header {
      margin-bottom: 20px;
    }

    h1 {
      font-size: 64px;
      text-shadow: 2px 2px 0 var(--red);
    }
  }
</style>
