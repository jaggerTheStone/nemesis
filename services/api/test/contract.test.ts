/**
 * Contract tests (I0.6): generated from openapi.yaml for every operation marked
 * x-implemented, run against the NestJS skeleton and a migrated, seeded database.
 */
import "reflect-metadata";
import {
  createValidator,
  listOperations,
  loadSpec,
  resolve,
  type Operation,
  type Parameter,
} from "@nemesis/openapi";
import { FastifyAdapter, type NestFastifyApplication } from "@nestjs/platform-fastify";
import { Test } from "@nestjs/testing";
import pg from "pg";
import { afterAll, beforeAll, describe, expect, inject, it } from "vitest";
import { configureApp } from "../src/app.js";
import { AppModule } from "../src/app.module.js";
import { PG_POOL } from "../src/database/database.module.js";

const databaseUrl = inject("databaseUrl");
if (!databaseUrl && process.env.NEMESIS_REQUIRE_DB === "1") {
  throw new Error("NEMESIS_REQUIRE_DB=1 mais NEMESIS_TEST_DATABASE_URL est absent");
}

const spec = loadSpec();
const validator = createValidator(spec);
const implemented = listOperations(spec).filter(({ operation }) => operation["x-implemented"]);

// Deterministic identifiers of the fictional seed (data/fixtures_fictives).
const FLAMBOYANTS = "92598ca3-f053-5d34-ab35-7f7b05f464f7";
const MONDAY_0640 = "2026-11-09T06:40:00Z";
const SUNDAY_0640 = "2026-11-08T06:40:00Z";

const escape = (segment: string) => segment.replaceAll("~", "~0").replaceAll("/", "~1");

function parametersOf(operation: Operation): Parameter[] {
  return (operation.parameters ?? []).map((parameter) => resolve(spec, parameter));
}

/** Request URL from the examples of the contract, optionally leaving one parameter out. */
function exampleUrl(path: string, operation: Operation, omit?: string): string {
  let url = path;
  const query = new URLSearchParams();
  for (const parameter of parametersOf(operation)) {
    if (parameter.name === omit || parameter.example === undefined) continue;
    if (parameter.in === "path")
      url = url.replace(`{${parameter.name}}`, String(parameter.example));
    if (parameter.in === "query") query.set(parameter.name ?? "", String(parameter.example));
  }
  const search = query.toString();
  return search ? `${url}?${search}` : url;
}

/** JSON pointer to the JSON schema of a response, following a response $ref. */
function responseSchema(
  path: string,
  method: string,
  status: string,
  media = "application/json",
): string {
  const raw = (spec.paths[path]?.[method] as Operation).responses[status] ?? {};
  const base = raw.$ref ?? `#/paths/${escape(path)}/${method}/responses/${status}`;
  return `${base}/content/${escape(media)}/schema`;
}

describe.skipIf(!databaseUrl)("contrat de l'API contre la base", () => {
  let app: NestFastifyApplication;
  let admin: pg.Client;

  beforeAll(async () => {
    process.env.DATABASE_URL = databaseUrl ?? "";
    // The API assumes its production group role: grants are tested too (H-016).
    process.env.DATABASE_ROLE = "nemesis_api";
    const moduleRef = await Test.createTestingModule({ imports: [AppModule] }).compile();
    app = await configureApp(
      moduleRef.createNestApplication<NestFastifyApplication>(new FastifyAdapter()),
    );
    await app.init();
    await app.getHttpAdapter().getInstance().ready();
    admin = new pg.Client({ connectionString: databaseUrl ?? "" });
    await admin.connect();
  });

  afterAll(async () => {
    await admin?.end();
    await app?.close();
  });

  const get = (url: string, headers: Record<string, string> = {}) =>
    app.inject({ method: "GET", url, headers });

  it("covers every operation marked as implemented", () => {
    expect(implemented.map(({ operation }) => operation.operationId).sort()).toEqual([
      "getHealth",
      "getStop",
      "listCities",
      "searchPlaces",
    ]);
  });

  for (const { method, path, operation } of implemented) {
    describe(operation.operationId, () => {
      it("answers 200 with a body valid against the contract", async () => {
        const response = await app.inject({
          method: method.toUpperCase() as "GET",
          url: exampleUrl(path, operation),
        });
        expect(response.statusCode, response.body).toBe(200);
        expect(validator.validate(responseSchema(path, method, "200"), response.json())).toEqual(
          [],
        );
      });

      if (operation.responses["304"]) {
        it("answers 304 to its own ETag", async () => {
          const url = exampleUrl(path, operation);
          const first = await get(url);
          const etag = String(first.headers.etag);
          expect(etag).toMatch(/^W\/"/);
          const second = await get(url, { "if-none-match": etag });
          expect(second.statusCode).toBe(304);
          expect(second.body).toBe("");
        });
      }

      for (const parameter of parametersOf(operation)) {
        if (parameter.in !== "query" || !parameter.required) continue;
        it(`answers a 400 problem without « ${parameter.name} »`, async () => {
          const response = await get(exampleUrl(path, operation, parameter.name));
          expect(response.statusCode).toBe(400);
          expect(response.headers["content-type"]).toContain("application/problem+json");
          expect(
            validator.validate(
              responseSchema(path, method, "400", "application/problem+json"),
              response.json(),
            ),
          ).toEqual([]);
        });
      }
    });
  }

  describe("recherche de lieux (F-01)", () => {
    const search = async (q: string) =>
      (await get(`/v1/places?city=lagune-fictive&q=${encodeURIComponent(q)}`)).json();

    it("tolerates missing accents, abbreviations and partial words", async () => {
      expect((await search("flamboyant")).items[0].name).toContain("Flamboyants");
      expect((await search("Gd Marché")).items[0].name).toContain("Grand Marché");
      expect((await search("pharma lagune")).items[0].name).toContain("Pharmacie de la Lagune");
      expect((await search("embarcadere sud")).items[0].name).toContain("Embarcadère Sud");
    });

    it("returns a station once, as a stop", async () => {
      const items = (await search("gare du grand marche")).items as {
        name: string;
        kind: string;
      }[];
      const stations = items.filter((item) => item.name.startsWith("Gare du Grand Marché"));
      expect(stations).toEqual([expect.objectContaining({ kind: "arret" })]);
    });

    it("marks fictional data", async () => {
      expect((await search("baobab")).is_fictional).toBe(true);
    });

    it("answers 404 for an unknown city", async () => {
      const response = await get("/v1/places?city=inconnue&q=gare");
      expect(response.statusCode).toBe(404);
      expect(response.headers["content-type"]).toContain("application/problem+json");
    });
  });

  describe("fiche d'arrêt (F-06)", () => {
    it("lists lines, fares with their meta and the day's wait series", async () => {
      const stop = (await get(`/v1/stops/${FLAMBOYANTS}?at=${MONDAY_0640}`)).json();
      expect(stop.lines.map((line: { code: string }) => line.code)).toEqual(
        expect.arrayContaining(["g1", "g4", "w1", "b1"]),
      );
      expect(stop.fares.length).toBeGreaterThan(0);
      for (const { fare } of stop.fares) expect(fare.meta.source).toBe("usagers");
      expect(stop.day_type).toBe("ouvrable");
      expect(stop.wait_series.length).toBeGreaterThan(0);
      expect(stop.network_version).toBeNull();
    });

    it("falls back to history, presented as such, without a recent report", async () => {
      const stop = (await get(`/v1/stops/${FLAMBOYANTS}?at=${MONDAY_0640}`)).json();
      expect(stop.queue.level).toBe("inconnu");
      expect(stop.queue.meta.source).toBe("historique");
      expect(stop.queue.wait.p50_s).toBeLessThanOrEqual(stop.queue.wait.p80_s);
    });

    it("uses a report younger than 30 minutes, then falls back again", async () => {
      const insert = (minutesAgo: number) =>
        admin.query(
          `insert into mobility.queue_state
             (city_id, is_fictional, stop_id, level, wait_p50_s, wait_p80_s, confidence, main_source, last_observed_at)
           select city_id, true, id, 'beaucoup', 900, 1500, 'moyenne', 'usagers', $2::timestamptz - make_interval(mins => $3)
           from network.stop where id = $1`,
          [FLAMBOYANTS, MONDAY_0640, minutesAgo],
        );
      try {
        await insert(5);
        const fresh = (await get(`/v1/stops/${FLAMBOYANTS}?at=${MONDAY_0640}`)).json();
        expect(fresh.queue.level).toBe("beaucoup");
        expect(fresh.queue.meta.source).toBe("usagers");
        await admin.query("delete from mobility.queue_state where stop_id = $1", [FLAMBOYANTS]);
        await insert(40);
        const stale = (await get(`/v1/stops/${FLAMBOYANTS}?at=${MONDAY_0640}`)).json();
        expect(stale.queue.meta.source).toBe("historique");
      } finally {
        await admin.query("delete from mobility.queue_state where stop_id = $1", [FLAMBOYANTS]);
      }
    });

    it("invents nothing when there is no data (Sunday profiles are absent)", async () => {
      const response = await get(`/v1/stops/${FLAMBOYANTS}?at=${SUNDAY_0640}`);
      const stop = response.json();
      expect(stop.day_type).toBe("dimanche");
      expect(stop.queue).toBeNull();
      expect(stop.wait_series).toEqual([]);
      expect(validator.validate(responseSchema("/v1/stops/{stopId}", "get", "200"), stop)).toEqual(
        [],
      );
    });

    it("answers 404 for an unknown stop and 400 for a malformed id", async () => {
      expect((await get("/v1/stops/00000000-0000-4000-8000-000000000000")).statusCode).toBe(404);
      expect((await get("/v1/stops/pas-un-uuid")).statusCode).toBe(400);
    });
  });

  it("compresses large responses with Brotli (partie 9.6)", async () => {
    const response = await get(`/v1/stops/${FLAMBOYANTS}?at=${MONDAY_0640}`, {
      "accept-encoding": "br, gzip",
    });
    expect(response.headers["content-encoding"]).toBe("br");
    expect(response.rawPayload.length).toBeLessThan(5000);
  });

  it("connects with the API role, which cannot read identities (H-016)", async () => {
    const pool = app.get<pg.Pool>(PG_POOL);
    const { rows } = await pool.query<{ role: string }>("select current_role as role");
    expect(rows[0]?.role).toBe("nemesis_api");
    await expect(pool.query("select count(*) from identity.account")).rejects.toThrow(
      /permission denied/,
    );
  });
});
