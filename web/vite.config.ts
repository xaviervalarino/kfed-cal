import { svelte } from "@sveltejs/vite-plugin-svelte";
import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig(({ mode }) => ({
  plugins: [svelte()],
  // Relative asset URLs let the build work under /kfed-cal/ on GitHub Pages and at / locally.
  base: "./",
  // Files here are served as-is next to the pages and copied into the build. site/ holds the
  // scraper's events.json and status.json; `--mode fixtures` serves the sample copies instead.
  publicDir: mode === "fixtures" ? "fixtures" : "../site",
  build: {
    rolldownOptions: {
      input: {
        main: resolve(import.meta.dirname, "index.html"),
        status: resolve(import.meta.dirname, "status.html"),
      },
    },
  },
}));
