import { HttpStatus } from "@nestjs/common";
import { ProblemException } from "./problem.filter.js";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const CITY = /^[a-z0-9-]{1,60}$/;
const NEAR = /^(-?\d{1,2}(?:\.\d+)?),(-?\d{1,3}(?:\.\d+)?)$/;

function invalid(field: string, message: string): never {
  throw new ProblemException(HttpStatus.BAD_REQUEST, `Paramètre « ${field} » invalide.`, [
    { field, message },
  ]);
}

export function requiredString(field: string, value: unknown, min: number, max: number): string {
  if (typeof value !== "string" || value.trim().length < min) {
    invalid(field, `au moins ${min} caractères attendus`);
  }
  const text = value.trim();
  if (text.length > max) invalid(field, `au plus ${max} caractères`);
  return text;
}

export function cityCode(value: unknown): string {
  if (typeof value !== "string" || !CITY.test(value)) invalid("city", "code de ville attendu");
  return value;
}

export function uuid(field: string, value: unknown): string {
  if (typeof value !== "string" || !UUID.test(value)) invalid(field, "UUID attendu");
  return value.toLowerCase();
}

export function limit(value: unknown, fallback = 10, max = 50): number {
  if (value === undefined) return fallback;
  const number = Number(value);
  if (!Number.isInteger(number) || number < 1 || number > max) {
    invalid("limit", `entier entre 1 et ${max} attendu`);
  }
  return number;
}

export function near(value: unknown): { lat: number; lon: number } | undefined {
  if (value === undefined) return undefined;
  const match = typeof value === "string" ? NEAR.exec(value) : null;
  if (!match) invalid("near", "« latitude,longitude » attendu");
  const lat = Number(match[1]);
  const lon = Number(match[2]);
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) invalid("near", "coordonnées hors limites");
  return { lat, lon };
}

export function instant(field: string, value: unknown): Date {
  if (value === undefined) return new Date();
  const date = typeof value === "string" ? new Date(value) : new Date(Number.NaN);
  if (Number.isNaN(date.getTime())) invalid(field, "date ISO 8601 attendue");
  return date;
}

export function notFound(detail: string): never {
  throw new ProblemException(HttpStatus.NOT_FOUND, detail);
}
