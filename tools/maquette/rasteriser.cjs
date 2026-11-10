// Rend des SVG en PNG avec le Chromium préinstallé : node rasteriser.cjs <largeur> <hauteur> <svg> <png> [transparent]…
const { chromium } = require("playwright");
const fs = require("fs");

(async () => {
  const [width, height, ...rest] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: Number(width), height: Number(height) },
    deviceScaleFactor: 2,
  });
  for (let i = 0; i < rest.length; i += 3) {
    const [svgPath, pngPath, transparent] = rest.slice(i, i + 3);
    const svg = fs.readFileSync(svgPath, "utf8");
    await page.setContent(
      `<html><body style="margin:0;background:transparent">${svg}</body></html>`,
    );
    await page.screenshot({ path: pngPath, omitBackground: transparent === "1" });
    console.log(pngPath);
  }
  await browser.close();
})();
