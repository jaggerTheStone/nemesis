import { NestFactory } from "@nestjs/core";
import { FastifyAdapter, type NestFastifyApplication } from "@nestjs/platform-fastify";
import { AppModule } from "./app.module.js";

/** Versioned REST prefix (cahier des charges, partie 9.6). */
export const API_PREFIX = "v1";

/** Applies the settings shared by the server and the tests. */
export function configureApp(app: NestFastifyApplication): NestFastifyApplication {
  app.setGlobalPrefix(API_PREFIX);
  return app;
}

export async function createApp(): Promise<NestFastifyApplication> {
  const app = await NestFactory.create<NestFastifyApplication>(AppModule, new FastifyAdapter(), {
    bufferLogs: true,
  });
  return configureApp(app);
}
