import { createHash } from "node:crypto";
import {
  type CallHandler,
  type ExecutionContext,
  HttpStatus,
  Injectable,
  type NestInterceptor,
} from "@nestjs/common";
import type { FastifyReply, FastifyRequest } from "fastify";
import { map, type Observable } from "rxjs";

/**
 * Weak ETag on JSON GET responses; If-None-Match answers 304 without a body
 * (partie 9.6: every byte has a cost for the user).
 */
@Injectable()
export class EtagInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    const http = context.switchToHttp();
    const request = http.getRequest<FastifyRequest>();
    const reply = http.getResponse<FastifyReply>();
    if (request.method !== "GET") return next.handle();
    return next.handle().pipe(
      map((body: unknown) => {
        const digest = createHash("sha256").update(JSON.stringify(body)).digest("base64url");
        const etag = `W/"${digest.slice(0, 27)}"`;
        void reply.header("etag", etag);
        const candidates = String(request.headers["if-none-match"] ?? "")
          .split(",")
          .map((value) => value.trim());
        if (candidates.includes(etag) || candidates.includes("*")) {
          void reply.status(HttpStatus.NOT_MODIFIED);
          return undefined;
        }
        return body;
      }),
    );
  }
}
