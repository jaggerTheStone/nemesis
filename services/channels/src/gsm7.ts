/**
 * GSM 03.38 (3GPP TS 23.038) 7-bit default alphabet helpers for the SMS channel.
 *
 * Cahier des charges, partie 11.3: SMS replies fit in at most 2 messages and use
 * GSM 7-bit characters only. French text needs care: é, è, à, ù are in the
 * basic alphabet, but ê, â, î, ô, û, ç are not ("wôrô-wôrô" must become
 * "woro-woro"), and any single non-GSM character would switch the whole
 * message to UCS-2 and cut its capacity from 160 to 70 characters.
 */

/** Maximum number of SMS segments for one reply (partie 11.3). */
export const MAX_SMS_SEGMENTS = 2;

const SINGLE_SEGMENT_SEPTETS = 160;
const MULTIPART_SEGMENT_SEPTETS = 153;

// Basic character set, in table order (the escape code 0x1B is omitted).
const BASIC = new Set(
  "@£$¥èéùìòÇ\nØø\rÅå" +
    "Δ_ΦΓΛΩΠΨΣΘΞÆæßÉ" +
    " !\"#¤%&'()*+,-./" +
    "0123456789:;<=>?" +
    "¡ABCDEFGHIJKLMNO" +
    "PQRSTUVWXYZÄÖÑÜ§" +
    "¿abcdefghijklmno" +
    "pqrstuvwxyzäöñüà",
);

// Extension table: each character costs two septets (escape + code).
const EXTENSION = new Set("\f^{}\\[~]|€");

// Closest GSM 7-bit rendering of characters common in Ivorian French text.
const TRANSLITERATIONS: Record<string, string> = {
  â: "a",
  ê: "e",
  ë: "e",
  î: "i",
  ï: "i",
  ô: "o",
  û: "u",
  ÿ: "y",
  ç: "c",
  À: "A",
  Â: "A",
  È: "E",
  Ê: "E",
  Ë: "E",
  Î: "I",
  Ï: "I",
  Ô: "O",
  Ù: "U",
  Û: "U",
  Œ: "OE",
  œ: "oe",
  "«": '"',
  "»": '"',
  "“": '"',
  "”": '"',
  "‘": "'",
  "’": "'",
  "–": "-",
  "—": "-",
  "…": "...",
  " ": " ",
  " ": " ",
};

const REPLACEMENT = "?";

function isGsm7Char(char: string): boolean {
  return BASIC.has(char) || EXTENSION.has(char);
}

/** True if every character of `text` is in the GSM 7-bit alphabet. */
export function isGsm7(text: string): boolean {
  for (const char of text) {
    if (!isGsm7Char(char)) return false;
  }
  return true;
}

/**
 * Converts `text` to the GSM 7-bit alphabet: known characters are
 * transliterated, anything else (emoji, other scripts) becomes "?".
 */
export function toGsm7(text: string): string {
  let result = "";
  for (const char of text) {
    if (isGsm7Char(char)) {
      result += char;
    } else {
      result += TRANSLITERATIONS[char] ?? REPLACEMENT;
    }
  }
  return result;
}

/** Number of septets needed to encode `text`; throws if it is not GSM 7-bit. */
export function gsm7Septets(text: string): number {
  let septets = 0;
  for (const char of text) {
    if (BASIC.has(char)) {
      septets += 1;
    } else if (EXTENSION.has(char)) {
      septets += 2;
    } else {
      throw new Error(`Character U+${char.codePointAt(0)?.toString(16)} is not GSM 7-bit`);
    }
  }
  return septets;
}

/**
 * Number of SMS segments needed for `text` (GSM 7-bit only).
 * Approximation: an escaped character is never split across segments in
 * practice, which can add one septet per segment boundary.
 */
export function smsSegmentCount(text: string): number {
  const septets = gsm7Septets(text);
  if (septets <= SINGLE_SEGMENT_SEPTETS) return 1;
  return Math.ceil(septets / MULTIPART_SEGMENT_SEPTETS);
}

/** True if `text` is GSM 7-bit and fits in `maxSegments` SMS (default: 2). */
export function fitsSmsBudget(text: string, maxSegments: number = MAX_SMS_SEGMENTS): boolean {
  return isGsm7(text) && smsSegmentCount(text) <= maxSegments;
}
