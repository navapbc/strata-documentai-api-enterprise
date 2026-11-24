// Render caption, label, and end-card overlays as PNGs with Playwright.
//
// The local ffmpeg has no drawtext/subtitles filter, so text is drawn in a real
// browser and overlaid as transparent PNGs. Reuses the Chromium that
// `make playwright-install` already provides for the UI recordings.
//
// Usage: node render_overlays.mjs <spec.json> <outDir>
// spec: { width, height, captions: [{file, lines}], badges: [{file, text, pos}],
//         endCard: {file, question, repoUrl} }

import { readFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const trailerDir = dirname(fileURLToPath(import.meta.url));
const { chromium } = await import(
  join(trailerDir, "../../../../ui/demo/node_modules/playwright-core/index.mjs")
);

const [specPath, outDir] = process.argv.slice(2);
const spec = JSON.parse(readFileSync(specPath, "utf8"));
mkdirSync(outDir, { recursive: true });

// Heroicons (MIT, Tailwind Labs; see THIRD_PARTY_NOTICES.md). The SVGs ship with a fixed
// fill, so recolor to currentColor and let CSS size and tint them.
const icon = (name) =>
  readFileSync(join(trailerDir, "icons", `${name}.svg`), "utf8").replace(
    /#0F172A/gi,
    "currentColor",
  );

// The Nava logo lives in media/logos/ next to the other brand assets. Strip the XML
// prolog and comment so the SVG can be inlined.
const logo = {
  svg: readFileSync(join(trailerDir, "..", "logos", "Nava-Logo.svg"), "utf8").replace(
    /<\?xml[^>]*\?>|<!--[\s\S]*?-->/g,
    "",
  ),
};

// A real blurry pay stub from the API's test fixtures, inlined for the "blurry upload" callout.
const blurryDoc = `data:image/jpeg;base64,${readFileSync(
  join(
    trailerDir,
    "../../../../documentai-api/tests/helpers/fixtures/test-documents/blur/synthetic-disk-defocus.jpeg",
  ),
).toString("base64")}`;

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: spec.width, height: spec.height },
});
await page.goto(pathToFileURL(join(trailerDir, "overlays.html")).href);
await page.evaluate(
  ({ w, h }) => {
    document.documentElement.style.setProperty("--w", `${w}px`);
    document.documentElement.style.setProperty("--h", `${h}px`);
  },
  { w: spec.width, h: spec.height },
);

// Fill a template from overlays.html and save a transparent PNG of the page.
async function renderOverlay(file, template, content, options) {
  await page.evaluate(
    ({ template, content, options }) => fillTemplate(template, content, options),
    { template, content, options },
  );
  await page.screenshot({ path: join(outDir, file), omitBackground: true });
}

for (const c of spec.captions) {
  await renderOverlay(c.file, "caption", { p: c.lines });
}
for (const c of spec.chips ?? []) {
  await renderOverlay(
    c.file,
    "chip",
    { ".icon": { svg: icon("check-circle") }, ".text": c.text },
    { style: { "--chip-index": c.index } },
  );
}
for (const b of spec.badges) {
  await renderOverlay(b.file, "badge", { "": b.text }, { classes: [b.pos] });
}
// The "integrate" callouts: a dimmed backdrop, then the blurry upload and the portal.
if (spec.callouts) {
  const { design, blur, portal } = spec.callouts;
  await renderOverlay("backdrop.png", "backdrop", {});
  await renderOverlay("callout-design.png", "callout-design", {
    ".title": design.title,
    ".sample-name": design.name,
    ".sample-input": design.input,
    ".sample-alert": design.alert,
    ".sample-primary": design.primary,
    ".sample-secondary": design.secondary,
  });
  await renderOverlay("callout-blur.png", "callout-blur", {
    ".title": blur.title,
    ".doc": { svg: `<img src="${blurryDoc}" alt="" />` },
    ".alert-text": blur.alert,
  });
  const fields = Object.fromEntries(
    portal.fields.flatMap(([label, value], i) => [
      [`.f${i} label`, label],
      [`.f${i} .val`, value],
    ]),
  );
  await renderOverlay("callout-portal.png", "callout-portal", {
    ".title": portal.title,
    ...fields,
    ".button": portal.button,
  });
}
const titleCard = (c) => ({ h1: c.title, ".sub": c.subtitle });
await renderOverlay(spec.interstitial.file, "title-card", titleCard(spec.interstitial));
// The intro is four layers (see overlays.css) so assemble.py can stagger the fade-in.
for (const [layer, suffix] of [
  ["bg", ""],
  ["logo", "-logo"],
  ["title", "-title"],
  ["sub", "-subtitle"],
]) {
  await renderOverlay(
    spec.intro.file.replace(".png", `${suffix}.png`),
    "title-card",
    { ...titleCard(spec.intro), ".logo": logo },
    { classes: [`layer-${layer}`] },
  );
}
// The end card is two layers: the question and link, then the logo that fades in.
for (const [layer, suffix] of [
  ["end-bg", ""],
  ["end-logo", "-logo"],
]) {
  await renderOverlay(
    spec.endCard.file.replace(".png", `${suffix}.png`),
    "end-card",
    {
      ".logo": logo,
      h1: spec.endCard.question,
      ".repo": spec.endCard.repoUrl,
    },
    { classes: ["end", `layer-${layer}`] },
  );
}

await browser.close();
console.log(
  `Rendered ${spec.captions.length} captions, ${spec.badges.length} badges, end card -> ${outDir}`,
);
