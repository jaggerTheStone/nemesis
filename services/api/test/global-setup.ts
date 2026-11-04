/**
 * Contract tests need a database: with NEMESIS_TEST_DATABASE_URL (administrator URL
 * of a PostgreSQL 16 + PostGIS server), a throwaway database is created, migrated
 * with dbmate (same files as docker compose) and loaded with the fictional seed.
 */
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import pg from "pg";
import type { TestProject } from "vitest/node";

declare module "vitest" {
  export interface ProvidedContext {
    databaseUrl: string | null;
  }
}

const ROOT = fileURLToPath(new URL("../../../", import.meta.url));

export default async function setup(project: TestProject): Promise<(() => Promise<void>) | void> {
  const base = process.env.NEMESIS_TEST_DATABASE_URL;
  if (!base) {
    project.provide("databaseUrl", null);
    return;
  }
  const name = `nemesis_api_test_${randomUUID().slice(0, 8)}`;
  const admin = new pg.Client({ connectionString: base });
  await admin.connect();
  await admin.query(`create database "${name}"`);
  const url = new URL(base);
  url.pathname = `/${name}`;

  const dbmateUrl = new URL(url);
  dbmateUrl.searchParams.set("sslmode", "disable");
  execFileSync(`${ROOT}node_modules/.bin/dbmate`, ["--no-dump-schema", "up"], {
    env: {
      ...process.env,
      DATABASE_URL: dbmateUrl.toString(),
      DBMATE_MIGRATIONS_DIR: `${ROOT}data/schema/migrations`,
    },
    stdio: "pipe",
  });
  const client = new pg.Client({ connectionString: url.toString() });
  await client.connect();
  await client.query(readFileSync(`${ROOT}data/fixtures_fictives/db/seed.sql`, "utf8"));
  await client.end();

  project.provide("databaseUrl", url.toString());
  return async () => {
    await admin.query(`drop database "${name}" with (force)`);
    await admin.end();
  };
}
