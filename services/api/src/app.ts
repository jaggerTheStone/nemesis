import { constants } from "node:zlib";
import compress from "@fastify/compress";
import { NestFactory } from "@nestjs/core";
import { FastifyAdapter, type NestFastifyApplication } from "@nestjs/platform-fastify";
import { AppModule } from "./app.module.js";
import { EtagInterceptor } from "./http/etag.interceptor.js";
import { ProblemFilter } from "./http/problem.filter.js";

/** Versioned REST prefix (cahier des charges, partie 9.6). */
export const API_PREFIX = "v1";

/** Applies the settings shared by the server and the tests. */
export async function configureApp(app: NestFastifyApplication): Promise<NestFastifyApplication> {
  // Brotli then gzip above 1 KB (partie 9.6); moderate quality to spare CPU at peak.
  await app.register(compress, {
    encodings: ["br", "gzip"],
    threshold: 1024,
    brotliOptions: { params: { [constants.BROTLI_PARAM_QUALITY]: 5 } },
  });
  app.setGlobalPrefix(API_PREFIX);
  app.useGlobalFilters(new ProblemFilter());
  app.useGlobalInterceptors(new EtagInterceptor());
  app.enableShutdownHooks();
  return app;
}

export async function createApp(): Promise<NestFastifyApplication> {
  const app = await NestFactory.create<NestFastifyApplication>(AppModule, new FastifyAdapter(), {
    bufferLogs: true,
  });
  return configureApp(app);
}
