import { Controller, Get, Inject, Query } from "@nestjs/common";
import type { components } from "@nemesis/openapi";
import type pg from "pg";
import { PG_POOL } from "../database/database.module.js";
import { cityCode, limit, near, notFound, requiredString } from "../http/params.js";

type PlaceSearchResponse = components["schemas"]["PlaceSearchResponse"];

/**
 * Place search (F-01, partie 8.4): trigram similarity on names and aliases, word
 * similarity for partial input, word-prefix matching for autocompletion.
 */
@Controller("places")
export class PlacesController {
  constructor(@Inject(PG_POOL) private readonly pool: pg.Pool) {}

  @Get()
  async search(@Query() query: Record<string, unknown>): Promise<PlaceSearchResponse> {
    const text = requiredString("q", query.q, 2, 120);
    const city = cityCode(query.city);
    const max = limit(query.limit);
    const position = near(query.near);

    const cities = await this.pool.query<{ id: string; is_fictional: boolean }>(
      "select id, is_fictional from network.city where code = $1",
      [city],
    );
    const found = cities.rows[0];
    if (!found) notFound(`Ville « ${city} » inconnue.`);

    const { rows } = await this.pool.query<{
      id: string;
      kind: "lieu" | "arret";
      name: string;
      category: string;
      lat: number;
      lon: number;
      alias: string;
      score: number;
      normalized_query: string;
    }>(SEARCH_SQL, [text, found.id, max * 2, position?.lon ?? null, position?.lat ?? null]);

    return {
      query: text,
      normalized_query: rows[0]?.normalized_query ?? (await this.normalize(text)),
      city,
      is_fictional: found.is_fictional,
      items: withoutDuplicates(rows, max).map((row) => ({
        id: row.id,
        kind: row.kind,
        name: row.name,
        category: row.category,
        location: { lat: row.lat, lon: row.lon },
        score: Math.round(row.score * 1000) / 1000,
        matched_alias: row.alias,
      })),
    };
  }

  private async normalize(text: string): Promise<string> {
    const { rows } = await this.pool.query<{ n: string }>(
      "select network.normalize_text($1) as n",
      [text],
    );
    return rows[0]?.n ?? "";
  }
}

const SEARCH_SQL = `
with q as (select network.normalize_text($1) as n),
candidates as (
    select p.id, 'lieu' as kind, p.name, p.category, p.geom, p.popularity, a.alias, a.normalized
    from network.place_alias a join network.place p on p.id = a.place_id
    where p.city_id = $2 and p.verification_status <> 'rejete'
    union all
    select s.id, 'arret', s.name, s.kind, s.geom, 0, a.alias, a.normalized
    from network.stop_alias a join network.stop s on s.id = a.stop_id
    where s.city_id = $2 and s.verification_status <> 'rejete'
),
scored as (
    select c.*, q.n as normalized_query,
           greatest(
               similarity(c.normalized, q.n),
               word_similarity(q.n, c.normalized),
               case when c.normalized like q.n || '%' or c.normalized like '% ' || q.n || '%'
                    then 0.6 else 0 end
           ) as score
    from candidates c, q
    where c.normalized % q.n or q.n <% c.normalized
       or c.normalized like q.n || '%' or c.normalized like '% ' || q.n || '%'
),
best as (
    select distinct on (id) * from scored order by id, score desc
)
select id, kind, name, category, st_y(geom) as lat, st_x(geom) as lon, alias, score, normalized_query
from best
order by score desc,
         case when $4::float8 is null then 0
              else st_distance(geom::geography, st_setsrid(st_makepoint($4, $5), 4326)::geography) end,
         popularity desc, name
limit $3`;

/**
 * A station is both a place and a stop: keep one result per name and location,
 * preferring the stop, which leads to an itinerary.
 */
function withoutDuplicates<T extends { kind: string; name: string; lat: number; lon: number }>(
  rows: T[],
  max: number,
): T[] {
  const key = (row: T) => `${row.name}|${row.lat.toFixed(3)}|${row.lon.toFixed(3)}`;
  const stops = new Set(rows.filter((row) => row.kind === "arret").map(key));
  const kept: T[] = [];
  const seen = new Set<string>();
  for (const row of rows) {
    const id = key(row);
    if ((row.kind === "lieu" && stops.has(id)) || seen.has(`${row.kind}|${id}`)) continue;
    seen.add(`${row.kind}|${id}`);
    kept.push(row);
  }
  return kept.slice(0, max);
}
