import { Controller, Get, Inject, Param, Query } from "@nestjs/common";
import type { components } from "@nemesis/openapi";
import type pg from "pg";
import { PG_POOL } from "../database/database.module.js";
import { instant, notFound, uuid } from "../http/params.js";

type Schemas = components["schemas"];
type StopDetail = Schemas["StopDetail"];
type Confidence = Schemas["Confidence"];
type DayType = Schemas["DayType"];
type Tristate = Schemas["Tristate"];

/** After 30 minutes without a report, the queue falls back to history (F-06). */
const LIVE_VALIDITY = "30 minutes";
const CONFIDENCE_ORDER: readonly Confidence[] = ["faible", "moyenne", "elevee"];
const rank = (confidence: Confidence): number => CONFIDENCE_ORDER.indexOf(confidence);

@Controller("stops")
export class StopsController {
  constructor(@Inject(PG_POOL) private readonly pool: pg.Pool) {}

  @Get(":stopId")
  async get(@Param("stopId") rawId: string, @Query("at") rawAt: unknown): Promise<StopDetail> {
    const stopId = uuid("stopId", rawId);
    const at = instant("at", rawAt);

    const stop = (
      await this.pool.query<{
        id: string;
        code: string;
        name: string;
        kind: StopDetail["kind"];
        lat: number;
        lon: number;
        boarding_radius_m: number | null;
        lighting: Tristate;
        shelter: Tristate;
        accessibility: Tristate;
        active_start: string | null;
        active_end: string | null;
        city: string;
        city_id: string;
        timezone: string;
        is_fictional: boolean;
      }>(
        `select s.id, s.code, s.name, s.kind, st_y(s.geom) as lat, st_x(s.geom) as lon,
                s.boarding_radius_m, s.lighting, s.shelter, s.accessibility,
                to_char(s.active_start, 'HH24:MI') as active_start,
                to_char(s.active_end, 'HH24:MI') as active_end,
                c.code as city, c.id as city_id, c.timezone, c.is_fictional
         from network.stop s join network.city c on c.id = s.city_id
         where s.id = $1`,
        [stopId],
      )
    ).rows[0];
    if (!stop) notFound("Arrêt introuvable.");

    const { dayType, slot } = localSlot(at, stop.timezone);
    const [aliases, lines, fares, queue, series, version] = await Promise.all([
      this.aliases(stopId),
      this.lines(stopId),
      this.fares(stopId),
      this.queue(stopId, at, dayType, slot),
      this.waitSeries(stopId, dayType),
      this.publishedVersion(stop.city_id),
    ]);

    return {
      id: stop.id,
      code: stop.code,
      name: stop.name,
      kind: stop.kind,
      city: stop.city,
      location: { lat: stop.lat, lon: stop.lon },
      boarding_radius_m: stop.boarding_radius_m,
      lighting: stop.lighting,
      shelter: stop.shelter,
      accessibility: stop.accessibility,
      active_hours:
        stop.active_start && stop.active_end
          ? { start: stop.active_start, end: stop.active_end }
          : null,
      aliases,
      lines,
      fares,
      queue,
      wait_series: series,
      day_type: dayType,
      at: at.toISOString(),
      network_version: version,
      is_fictional: stop.is_fictional,
    };
  }

  private async aliases(stopId: string): Promise<string[]> {
    const { rows } = await this.pool.query<{ alias: string }>(
      `select alias from network.stop_alias where stop_id = $1
       order by alias_kind = 'nom' desc, alias`,
      [stopId],
    );
    return rows.map((row) => row.alias);
  }

  private async lines(stopId: string): Promise<StopDetail["lines"]> {
    const { rows } = await this.pool.query<{
      route_id: string;
      code: string;
      name: string;
      mode: Schemas["Mode"];
      body_color: string | null;
      color_pattern: string | null;
      announced_as: string | null;
      direction_id: 0 | 1;
      headsign: string | null;
    }>(
      `select distinct r.id as route_id, r.code, r.spoken_name as name, r.mode, r.body_color,
              r.color_pattern, r.announced_as, p.direction_id, p.headsign
       from network.route_pattern_stop ps
       join network.route_pattern p on p.id = ps.route_pattern_id
       join network.route r on r.id = p.route_id
       where ps.stop_id = $1 and r.active
       order by r.code, p.direction_id`,
      [stopId],
    );
    const lines = new Map<string, StopDetail["lines"][number]>();
    for (const row of rows) {
      const line = lines.get(row.route_id) ?? {
        route_id: row.route_id,
        code: row.code,
        name: row.name,
        mode: row.mode,
        body_color: row.body_color,
        color_pattern: row.color_pattern,
        announced_as: row.announced_as,
        directions: [],
      };
      line.directions.push({ direction_id: row.direction_id, headsign: row.headsign ?? "" });
      lines.set(row.route_id, line);
    }
    return [...lines.values()];
  }

  private async fares(stopId: string): Promise<StopDetail["fares"]> {
    const { rows } = await this.pool.query<{
      route_id: string;
      to_area: string;
      fare_p10: number;
      fare_p50: number;
      fare_p90: number;
      last_observed_at: Date;
      confidence: Confidence;
      n_contributors: number;
    }>(
      `select fe.route_id, ta.code as to_area, fe.fare_p10, fe.fare_p50, fe.fare_p90,
              fe.last_observed_at, fe.confidence, fe.n_contributors
       from network.fare_area_stop fas
       join mobility.fare_estimate fe on fe.from_area_id = fas.fare_area_id
       join network.fare_area ta on ta.id = fe.to_area_id
       where fas.stop_id = $1 and fe.condition = 'normale'
         and fe.route_id in (
             select p.route_id from network.route_pattern_stop ps
             join network.route_pattern p on p.id = ps.route_pattern_id
             where ps.stop_id = $1)
       order by fe.route_id, ta.code`,
      [stopId],
    );
    return rows.map((row) => ({
      route_id: row.route_id,
      to_area: row.to_area,
      fare: {
        p10: row.fare_p10,
        p50: row.fare_p50,
        p90: row.fare_p90,
        currency: "XOF",
        condition: "normale",
        meta: {
          observed_at: row.last_observed_at.toISOString(),
          confidence: row.confidence,
          source: "usagers",
          contributors: row.n_contributors,
        },
      },
    }));
  }

  /** Live state if a report is less than 30 minutes old, otherwise history, otherwise null. */
  private async queue(
    stopId: string,
    at: Date,
    dayType: DayType,
    slot: string,
  ): Promise<StopDetail["queue"]> {
    const live = (
      await this.pool.query<{
        level: Schemas["QueueEstimate"]["level"];
        people_low: number | null;
        people_high: number | null;
        vehicles_low: number | null;
        vehicles_high: number | null;
        regime: "A" | "B" | "C" | null;
        wait_p50_s: number | null;
        wait_p80_s: number | null;
        confidence: Confidence;
        main_source: Schemas["DataSource"];
        last_observed_at: Date;
      }>(
        `select level, people_low, people_high, vehicles_low, vehicles_high, regime,
                wait_p50_s, wait_p80_s, confidence, main_source, last_observed_at
         from mobility.queue_state
         where stop_id = $1 and route_id is null
           and last_observed_at between $2::timestamptz - interval '${LIVE_VALIDITY}' and $2::timestamptz`,
        [stopId, at],
      )
    ).rows[0];
    if (live) {
      const meta = {
        observed_at: live.last_observed_at.toISOString(),
        confidence: live.confidence,
        source: live.main_source,
      };
      return {
        level: live.level,
        ...(live.people_low !== null && {
          people: { low: live.people_low, high: live.people_high },
        }),
        ...(live.vehicles_low !== null && {
          vehicles: { low: live.vehicles_low, high: live.vehicles_high },
        }),
        ...(live.wait_p50_s !== null &&
          live.wait_p80_s !== null && {
            wait: {
              p50_s: live.wait_p50_s,
              p80_s: live.wait_p80_s,
              ...(live.regime && { regime: live.regime }),
              meta,
            },
          }),
        meta,
      };
    }

    const history = (
      await this.pool.query<{
        regime: "A" | "B" | "C";
        wait_p50_s: number;
        wait_p80_s: number;
        confidence: Confidence;
        n_contributors: number;
        updated_at: Date;
      }>(
        `select regime, wait_p50_s, wait_p80_s, confidence, n_contributors, updated_at
         from mobility.wait_profile
         where stop_id = $1 and day_type = $2 and slot_start = $3::time
         order by wait_p50_s, route_id limit 1`,
        [stopId, dayType, slot],
      )
    ).rows[0];
    if (!history) return null;
    const meta = {
      observed_at: history.updated_at.toISOString(),
      confidence: history.confidence,
      source: "historique" as const,
      contributors: history.n_contributors,
    };
    return {
      level: "inconnu",
      wait: { p50_s: history.wait_p50_s, p80_s: history.wait_p80_s, regime: history.regime, meta },
      meta,
    };
  }

  private async waitSeries(stopId: string, dayType: DayType): Promise<StopDetail["wait_series"]> {
    const { rows } = await this.pool.query<{
      route_id: string;
      direction_id: 0 | 1;
      slot: string;
      wait_p50_s: number;
      wait_p80_s: number;
      confidence: Confidence;
      n_contributors: number;
      updated_at: Date;
    }>(
      `select route_id, direction_id, to_char(slot_start, 'HH24:MI') as slot, wait_p50_s, wait_p80_s,
              confidence, n_contributors, updated_at
       from mobility.wait_profile
       where stop_id = $1 and day_type = $2
       order by route_id, direction_id, slot_start`,
      [stopId, dayType],
    );
    const series = new Map<string, StopDetail["wait_series"][number]>();
    for (const row of rows) {
      const key = `${row.route_id}:${row.direction_id}`;
      let entry = series.get(key);
      if (!entry) {
        entry = {
          route_id: row.route_id,
          direction_id: row.direction_id,
          day_type: dayType,
          slots: [],
          meta: {
            observed_at: row.updated_at.toISOString(),
            confidence: row.confidence,
            source: "historique",
            contributors: row.n_contributors,
          },
        };
        series.set(key, entry);
      }
      entry.slots.push({ slot_start: row.slot, p50_s: row.wait_p50_s, p80_s: row.wait_p80_s });
      // The series is only as trustworthy as its weakest slot.
      if (rank(row.confidence) < rank(entry.meta.confidence)) {
        entry.meta.confidence = row.confidence;
      }
      entry.meta.contributors = Math.min(
        entry.meta.contributors ?? row.n_contributors,
        row.n_contributors,
      );
      if (row.updated_at.toISOString() > entry.meta.observed_at) {
        entry.meta.observed_at = row.updated_at.toISOString();
      }
    }
    return [...series.values()];
  }

  private async publishedVersion(cityId: string): Promise<number | null> {
    const { rows } = await this.pool.query<{ number: number | null }>(
      `select max(number) as number from network.network_version
       where city_id = $1 and status = 'publiee'`,
      [cityId],
    );
    return rows[0]?.number ?? null;
  }
}

/** Day type and 15-minute slot of `at` in the city's time zone. */
export function localSlot(at: Date, timeZone: string): { dayType: DayType; slot: string } {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone,
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(at);
  const value = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  const weekday = value("weekday");
  const dayType: DayType =
    weekday === "Sat" ? "samedi" : weekday === "Sun" ? "dimanche" : "ouvrable";
  const minutes = Math.floor(Number(value("minute")) / 15) * 15;
  return { dayType, slot: `${value("hour")}:${String(minutes).padStart(2, "0")}` };
}
