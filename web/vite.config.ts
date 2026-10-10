import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import tailwind from "@tailwindcss/vite";
import { researchPreview } from "./scripts/research-preview.ts";
import { fixtureGuard } from "./scripts/fixture-guard.ts";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwind(), researchPreview(), fixtureGuard()],
  server: {
    host: "127.0.0.1",
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: true } },
  },
});
