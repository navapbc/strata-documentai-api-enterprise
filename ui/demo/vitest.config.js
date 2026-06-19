import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [
    {
      name: "raw-html",
      transform(code, id) {
        if (id.endsWith(".html")) {
          return { code: `export default ${JSON.stringify(code)};`, map: null };
        }
      },
    },
  ],
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.js"],
  },
});
