import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// During dev, proxy API + WebSocket to the FastAPI server (catan serve).
export default defineConfig({
    plugins: [react()],
    server: {
        proxy: {
            "/api": {
                target: "http://localhost:8000",
                changeOrigin: true,
                ws: true,
            },
        },
    },
});
