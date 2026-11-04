/** Runtime configuration, read from the environment (see .env.example). */
export interface ApiConfig {
  databaseUrl: string;
  /** Group role assumed by the connection (H-016); unset when the login is already that role. */
  databaseRole: string | undefined;
  port: number;
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): ApiConfig {
  return {
    databaseUrl:
      env.DATABASE_URL ?? "postgres://nemesis_api_dev:nemesis_dev@127.0.0.1:5432/nemesis",
    databaseRole: env.DATABASE_ROLE || undefined,
    port: Number(env.PORT ?? 3000),
  };
}
