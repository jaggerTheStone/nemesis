import swc from "unplugin-swc";
import { defineConfig } from "vitest/config";

// NestJS dependency injection relies on decorator metadata, which esbuild does
// not emit; SWC compiles the sources for tests instead.
export default defineConfig({
  plugins: [swc.vite({ module: { type: "es6" } })],
  test: {
    include: ["test/**/*.test.ts"],
  },
});
