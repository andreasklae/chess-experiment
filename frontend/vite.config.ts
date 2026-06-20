import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Bind 0.0.0.0 so a phone on the same wifi can load the UI over the LAN
    // (e.g. http://192.168.1.7:5173). api.ts then talks to the backend on the
    // same host:8000, so no rebuild is needed between laptop and phone.
    host: true,
  },
});
