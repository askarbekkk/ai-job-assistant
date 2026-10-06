import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The FastAPI backend runs on :8000; the browser only talks to Vite.
    proxy: { "/api": "http://localhost:8000" },
  },
});
