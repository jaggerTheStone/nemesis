/**
 * Lightweight server-rendered pages (cahier des charges, partie 11.6):
 * shareable itinerary and live-trip pages that must stay under 100 KB and work
 * on lightweight browsers and feature phones, without any JavaScript framework.
 */

/** Maximum size of a rendered page, in bytes (partie 11.6). */
export const PAGE_BUDGET_BYTES = 100 * 1024;

export interface PageOptions {
  /** BCP 47 language tag, e.g. "fr-CI". */
  lang: string;
  /** Already-translated page title (plain text, escaped here). */
  title: string;
  /** Pre-rendered, already-escaped HTML body. */
  bodyHtml: string;
}

const HTML_ESCAPES: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

/** Escapes text for safe inclusion in HTML content and attribute values. */
export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (char) => HTML_ESCAPES[char] ?? char);
}

/**
 * Renders a complete HTML document with minimal inline styles.
 * Throws if the result exceeds the page budget, so oversized pages fail loudly
 * in tests instead of silently costing users data.
 */
export function renderPage(options: PageOptions): string {
  const html =
    "<!doctype html>" +
    `<html lang="${escapeHtml(options.lang)}">` +
    "<head>" +
    '<meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width, initial-scale=1">' +
    `<title>${escapeHtml(options.title)}</title>` +
    "<style>body{font-family:sans-serif;font-size:16px;line-height:1.4;margin:0 auto;max-width:40em;padding:0 16px;color:#111;background:#fff}</style>" +
    "</head>" +
    `<body>${options.bodyHtml}</body>` +
    "</html>";

  const size = Buffer.byteLength(html, "utf8");
  if (size > PAGE_BUDGET_BYTES) {
    throw new Error(`Rendered page is ${size} bytes, over the ${PAGE_BUDGET_BYTES}-byte budget`);
  }
  return html;
}
