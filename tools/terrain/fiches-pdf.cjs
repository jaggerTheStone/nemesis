// Renders the paper forms (docs/TERRAIN/fiches/*.html) to A4 PDFs in
// docs/TERRAIN/pdf/, and records the SHA-256 of their sources so that a test
// can detect PDFs older than their HTML. Usage: node tools/terrain/fiches-pdf.cjs
// Requires Playwright with Chromium (not a project dependency: run `make fiches-pdf`
// on a machine where `require("playwright")` works).
"use strict";

const { createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..", "..");
const sourceDir = path.join(root, "docs", "TERRAIN", "fiches");
const outputDir = path.join(root, "docs", "TERRAIN", "pdf");

function sha256(file) {
  return createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

async function main() {
  const forms = fs
    .readdirSync(sourceDir)
    .filter((name) => name.endsWith(".html"))
    .sort();
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    for (const name of forms) {
      await page.goto("file://" + path.join(sourceDir, name));
      const target = path.join(outputDir, name.replace(/\.html$/, ".pdf"));
      await page.pdf({ path: target, preferCSSPageSize: true, printBackground: true });
      console.log("écrit", path.relative(root, target));
    }
  } finally {
    await browser.close();
  }
  const sources = [...forms, "fiches.css"].map(
    (name) => `${sha256(path.join(sourceDir, name))}  docs/TERRAIN/fiches/${name}`,
  );
  fs.writeFileSync(path.join(outputDir, "SOURCES.sha256"), sources.join("\n") + "\n");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
