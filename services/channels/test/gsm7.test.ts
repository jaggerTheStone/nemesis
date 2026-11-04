import { describe, expect, it } from "vitest";
import { fitsSmsBudget, gsm7Septets, isGsm7, smsSegmentCount, toGsm7 } from "../src/index.js";

describe("isGsm7", () => {
  it("accepts French accents that belong to the basic alphabet", () => {
    expect(isGsm7("Prends un gbaka à Adjamé : prévois 300 F, où tu descends.")).toBe(true);
  });

  it("rejects characters outside the alphabet", () => {
    expect(isGsm7("wôrô-wôrô")).toBe(false);
    expect(isGsm7("ça")).toBe(false);
    expect(isGsm7("🚌")).toBe(false);
  });
});

describe("toGsm7", () => {
  it("transliterates common Ivorian French characters", () => {
    expect(toGsm7("wôrô-wôrô")).toBe("woro-woro");
    expect(toGsm7("ça coûte 300 F")).toBe("ca coute 300 F");
    expect(toGsm7("« Adjamé Liberté ! »")).toBe('" Adjamé Liberté ! "');
  });

  it("replaces each unknown code point, including emoji, with a single ?", () => {
    expect(toGsm7("Bus 🚌 ok")).toBe("Bus ? ok");
  });

  it("always produces GSM 7-bit text", () => {
    expect(isGsm7(toGsm7("Arrêt « Siporex » — 6 h 30… 😀"))).toBe(true);
  });
});

describe("segments", () => {
  it("counts extension characters as two septets", () => {
    expect(gsm7Septets("a€")).toBe(3);
  });

  it("uses 160 septets for one SMS and 153 per part beyond", () => {
    expect(smsSegmentCount("a".repeat(160))).toBe(1);
    expect(smsSegmentCount("a".repeat(161))).toBe(2);
    expect(smsSegmentCount("a".repeat(306))).toBe(2);
    expect(smsSegmentCount("a".repeat(307))).toBe(3);
  });

  it("enforces the two-SMS budget of partie 11.3", () => {
    expect(fitsSmsBudget("a".repeat(306))).toBe(true);
    expect(fitsSmsBudget("a".repeat(307))).toBe(false);
    expect(fitsSmsBudget("wôrô")).toBe(false);
  });

  it("throws on non GSM 7-bit input", () => {
    expect(() => gsm7Septets("ô")).toThrow(/not GSM 7-bit/);
  });
});
