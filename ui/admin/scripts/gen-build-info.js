import { writeFileSync } from "fs";
import { fileURLToPath } from "url";
import { join, dirname } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const date = new Date().toISOString();
writeFileSync(
  join(__dirname, "../src/config/build-info.js"),
  `export const BUILD_DATE = "${date}";\n`,
);
