import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Relative asset URLs so the build can also be served from a static host
  // that mounts it under a subpath.
  base: "./",
  build: {
    outDir: "dist",
    assetsDir: "assets",
    // Stable filenames: the build is republished to a fixed set of asset
    // paths, so content hashes would only churn the file list.
    rollupOptions: {
      output: {
        entryFileNames: "assets/app.js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: "assets/app.[ext]",
      },
    },
  },
});
