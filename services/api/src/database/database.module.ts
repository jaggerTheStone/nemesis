import { Global, Inject, Module, type OnApplicationShutdown } from "@nestjs/common";
import pg from "pg";
import { loadConfig } from "../config.js";

export const PG_POOL = Symbol("PG_POOL");

@Global()
@Module({
  providers: [
    {
      provide: PG_POOL,
      useFactory: () => {
        const config = loadConfig();
        return new pg.Pool({
          connectionString: config.databaseUrl,
          // Assume the API group role so that grants are those of production (ADR-005).
          options: config.databaseRole ? `-c role=${config.databaseRole}` : undefined,
          max: 10,
        });
      },
    },
  ],
  exports: [PG_POOL],
})
export class DatabaseModule implements OnApplicationShutdown {
  constructor(@Inject(PG_POOL) private readonly pool: pg.Pool) {}

  async onApplicationShutdown(): Promise<void> {
    await this.pool.end();
  }
}
