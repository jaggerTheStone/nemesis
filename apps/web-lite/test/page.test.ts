import { describe, expect, it } from "vitest";
import { escapeHtml, PAGE_BUDGET_BYTES, renderPage } from "../src/index.js";

describe("escapeHtml", () => {
  it("neutralises HTML special characters", () => {
    expect(escapeHtml(`<script>alert("x")</script> & 'y'`)).toBe(
      "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; &#39;y&#39;",
    );
  });
});

describe("renderPage", () => {
  it("renders a complete document with the requested language", () => {
    const html = renderPage({ lang: "fr-CI", title: "Ton trajet", bodyHtml: "<p>ok</p>" });
    expect(html.startsWith("<!doctype html>")).toBe(true);
    expect(html).toContain('<html lang="fr-CI">');
    expect(html).toContain("<title>Ton trajet</title>");
    expect(html).toContain("<p>ok</p>");
  });

  it("escapes the title", () => {
    const html = renderPage({ lang: "fr-CI", title: "<b>x</b>", bodyHtml: "" });
    expect(html).toContain("<title>&lt;b&gt;x&lt;/b&gt;</title>");
  });

  it("rejects pages over the 100 KB budget", () => {
    const bodyHtml = "a".repeat(PAGE_BUDGET_BYTES);
    expect(() => renderPage({ lang: "fr-CI", title: "t", bodyHtml })).toThrow(/budget/);
  });
});
