import { svelte } from "@sveltejs/vite-plugin-svelte";
import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [svelte()],
  // Relative asset URLs let the build work under /kfed-cal/ on GitHub Pages and at / locally.
  base: "./",
  build: {
    rolldownOptions: {
      input: {
        main: resolve(import.meta.dirname, "index.html"),
        status: resolve(import.meta.dirname, "status.html"),
      },
    },
  },
});
