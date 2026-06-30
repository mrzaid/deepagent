import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The built SPA is emitted straight into ../server/static so FastAPI serves it
// with no Node toolchain at runtime. In dev, `npm run dev` proxies the agent's
// API + SSE endpoints to the FastAPI server on :8000.
export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "../server/static",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/run": "http://127.0.0.1:8000",
      "/events": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
