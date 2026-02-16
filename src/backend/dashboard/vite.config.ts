import { defineConfig } from "vite";

export default defineConfig({
  base: "/dashboard/",
  server: {
    host: "0.0.0.0",
    port: 5174
  },
  preview: {
    host: "0.0.0.0",
    port: 5174
  }
});
