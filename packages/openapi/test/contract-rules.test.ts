/**
 * Project rules on the contract itself (I0.6), complementing the Redocly linter:
 * honest estimates (rule 1.3.2), idempotent writes, declared rate limits, problem
 * responses, ETag caching, valid JSON Schemas and examples.
 */
import { describe, expect, it } from "vitest";
import {
  createValidator,
  loadSpec,
  listOperations,
  resolve,
  type Parameter,
  type Response,
} from "../src/index.js";

const spec = loadSpec();
const all = listOperations(spec);
const schemas = spec.components.schemas;
const ESTIMATE_META = "#/components/schemas/EstimateMeta";
const ESTIMATE_FIELDS = ["p10", "p50", "p90", "p50_s", "p80_s", "level"];

function parameters(operation: { parameters?: Parameter[] }): Parameter[] {
  return (operation.parameters ?? []).map((parameter) => resolve(spec, parameter));
}

describe("honest estimates (règle 1.3.2)", () => {
  it("EstimateMeta requires freshness, confidence and source", () => {
    expect(schemas.EstimateMeta?.required).toEqual(["observed_at", "confidence", "source"]);
  });

  it("every estimate schema requires a meta object of type EstimateMeta", () => {
    const estimates = Object.entries(schemas).filter(([, schema]) => schema["x-estimate"] === true);
    expect(estimates.map(([name]) => name).sort()).toEqual([
      "DurationEstimate",
      "FareEstimate",
      "QueueEstimate",
      "WaitEstimate",
      "WaitSeries",
    ]);
    for (const [name, schema] of estimates) {
      const properties = schema.properties as Record<string, { $ref?: string }>;
      expect(schema.required, name).toContain("meta");
      expect(properties.meta?.$ref, name).toBe(ESTIMATE_META);
    }
  });

  it("no schema carries estimate values without being an estimate", () => {
    for (const [name, schema] of Object.entries(schemas)) {
      const properties = Object.keys((schema.properties as object | undefined) ?? {});
      const hasValues = properties.some((property) => ESTIMATE_FIELDS.includes(property));
      if (hasValues) expect(schema["x-estimate"], name).toBe(true);
    }
  });

  it("an estimate without meta is rejected by the contract", () => {
    const validator = createValidator(spec);
    const wait = { p50_s: 300, p80_s: 600, regime: "A" };
    expect(validator.validate("#/components/schemas/WaitEstimate", wait)).not.toEqual([]);
    const meta = { observed_at: "2026-11-04T06:30:00Z", confidence: "moyenne", source: "usagers" };
    expect(validator.validate("#/components/schemas/WaitEstimate", { ...wait, meta })).toEqual([]);
    const withoutSource = { observed_at: meta.observed_at, confidence: meta.confidence };
    expect(
      validator.validate("#/components/schemas/WaitEstimate", { ...wait, meta: withoutSource }),
    ).not.toEqual([]);
  });
});

describe("operations", () => {
  it("each operation declares an id, tags, a summary, a rate limit and a 429 response", () => {
    expect(all.length).toBeGreaterThanOrEqual(25);
    for (const { method, path, operation } of all) {
      const where = `${method.toUpperCase()} ${path}`;
      expect(operation.operationId, where).toBeTruthy();
      expect(operation.tags?.length, where).toBeGreaterThan(0);
      expect(operation.summary, where).toBeTruthy();
      expect(operation["x-rate-limit"], where).toBeTruthy();
      expect(operation.responses["429"], where).toBeDefined();
    }
  });

  it("every write requires an Idempotency-Key header", () => {
    for (const { method, path, operation } of all) {
      if (method === "get" || operation["x-safe"]) continue;
      const key = parameters(operation).find(
        (p) => p.in === "header" && p.name === "Idempotency-Key",
      );
      expect(key?.required, `${method.toUpperCase()} ${path}`).toBe(true);
    }
  });

  it("only searches are declared safe despite using POST", () => {
    const safe = all
      .filter(({ operation }) => operation["x-safe"])
      .map(({ operation }) => operation.operationId);
    expect(safe).toEqual(["searchItineraries"]);
  });

  it("errors use application/problem+json", () => {
    for (const { method, path, operation } of all) {
      for (const [status, raw] of Object.entries(operation.responses)) {
        if (Number(status) < 400) continue;
        const response = resolve<Response>(spec, raw);
        expect(Object.keys(response.content ?? {}), `${method} ${path} ${status}`).toEqual([
          "application/problem+json",
        ]);
      }
    }
  });

  it("responses with an ETag accept If-None-Match and answer 304", () => {
    for (const { method, path, operation } of all) {
      const ok = resolve<Response>(spec, operation.responses["200"] ?? {});
      if (!ok.headers?.ETag) continue;
      const where = `${method.toUpperCase()} ${path}`;
      expect(method, where).toBe("get");
      expect(
        parameters(operation).some((p) => p.name === "If-None-Match"),
        where,
      ).toBe(true);
      expect(operation.responses["304"], where).toBeDefined();
    }
  });

  it("collections are paginated with a cursor", () => {
    for (const name of ["IncidentPage", "ChangeRequestPage", "ModerationPage"]) {
      expect(schemas[name]?.required, name).toEqual(["items", "next_cursor"]);
    }
  });
});

describe("schemas and examples", () => {
  const validator = createValidator(spec);

  it("every component schema compiles", () => {
    for (const name of Object.keys(schemas)) {
      expect(() => validator.compile(`#/components/schemas/${name}`), name).not.toThrow();
    }
  });

  it("parameter examples are valid", () => {
    const escape = (segment: string) => segment.replaceAll("~", "~0").replaceAll("/", "~1");
    let checked = 0;
    for (const { method, path, operation } of all) {
      (operation.parameters ?? []).forEach((raw, index) => {
        const parameter = resolve(spec, raw);
        if (parameter.example === undefined) return;
        const pointer = raw.$ref
          ? `${raw.$ref}/schema`
          : `#/paths/${escape(path)}/${method}/parameters/${index}/schema`;
        expect(validator.validate(pointer, parameter.example), `${parameter.name}`).toEqual([]);
        checked += 1;
      });
    }
    expect(checked).toBeGreaterThanOrEqual(5);
  });

  it("legs are discriminated by their kind", () => {
    const walk = {
      kind: "marche",
      from: { lat: 2, lon: -4 },
      to: { lat: 2.01, lon: -4 },
      duration_s: 300,
      distance_m: 400,
    };
    expect(validator.validate("#/components/schemas/Leg", walk)).toEqual([]);
    expect(
      validator.validate("#/components/schemas/Leg", { ...walk, kind: "vehicule" }),
    ).not.toEqual([]);
  });

  it("a rejection without a reason is invalid", () => {
    expect(validator.validate("#/components/schemas/Review", { decision: "approuver" })).toEqual(
      [],
    );
    expect(validator.validate("#/components/schemas/Review", { decision: "rejeter" })).not.toEqual(
      [],
    );
    expect(
      validator.validate("#/components/schemas/Review", { decision: "rejeter", reason: "Doublon" }),
    ).toEqual([]);
  });

  it("an itinerary search cannot fix both departure and arrival", () => {
    const base = {
      city: "lagune-fictive",
      from: { stop_id: "92598ca3-f053-5d34-ab35-7f7b05f464f7" },
      to: { location: { lat: 1.99, lon: -3.98 } },
    };
    expect(validator.validate("#/components/schemas/ItinerarySearchRequest", base)).toEqual([]);
    expect(
      validator.validate("#/components/schemas/ItinerarySearchRequest", {
        ...base,
        depart_at: "2026-11-09T06:30:00Z",
        arrive_by: "2026-11-09T07:30:00Z",
      }),
    ).not.toEqual([]);
  });
});
