import { Controller, Get, Inject } from "@nestjs/common";
import type { components } from "@nemesis/openapi";
import type pg from "pg";
import { PG_POOL } from "../database/database.module.js";

type CityList = components["schemas"]["CityList"];

@Controller("cities")
export class CitiesController {
  constructor(@Inject(PG_POOL) private readonly pool: pg.Pool) {}

  @Get()
  async list(): Promise<CityList> {
    const { rows } = await this.pool.query<{
      code: string;
      name: string;
      timezone: string;
      currency: string;
      bbox: number[] | null;
      is_fictional: boolean;
    }>(
      `select code, name, timezone, currency, is_fictional,
              case when bbox is null then null
                   else array[st_xmin(bbox), st_ymin(bbox), st_xmax(bbox), st_ymax(bbox)] end as bbox
       from network.city order by code`,
    );
    return { items: rows.map((row) => ({ ...row, bbox: row.bbox?.map(Number) ?? null })) };
  }
}
