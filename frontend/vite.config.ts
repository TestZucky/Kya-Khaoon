import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Read VITE_* from the single .env at the repo root.
  envDir: path.resolve(root, ".."),
  resolve: {
    alias: { "@": path.resolve(root, "./src") },
  },
  server: {
    port: 5173,
    host: true,
    // Accept requests proxied through a Cloudflare/ngrok tunnel (dev only —
    // the Host header is the tunnel domain, which Vite blocks by default).
    allowedHosts: true,
    // Same-origin API: the frontend calls "/api/*" and Vite forwards to the
    // backend, so a single tunnel origin serves both (no mixed content, no CORS).
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
