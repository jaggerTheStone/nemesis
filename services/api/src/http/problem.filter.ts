import {
  type ArgumentsHost,
  Catch,
  type ExceptionFilter,
  HttpException,
  HttpStatus,
  Logger,
} from "@nestjs/common";
import type { FastifyReply, FastifyRequest } from "fastify";

export interface FieldError {
  field: string;
  message: string;
}

/** HTTP error carrying field-level details, rendered as a problem. */
export class ProblemException extends HttpException {
  constructor(
    status: HttpStatus,
    readonly detail: string,
    readonly errors: FieldError[] = [],
  ) {
    super(detail, status);
  }
}

/** Renders every error as application/problem+json (RFC 9457); never leaks internals. */
@Catch()
export class ProblemFilter implements ExceptionFilter {
  private readonly logger = new Logger(ProblemFilter.name);

  catch(exception: unknown, host: ArgumentsHost): void {
    const http = host.switchToHttp();
    const reply = http.getResponse<FastifyReply>();
    const request = http.getRequest<FastifyRequest>();
    const status =
      exception instanceof HttpException ? exception.getStatus() : HttpStatus.INTERNAL_SERVER_ERROR;
    if (!(exception instanceof HttpException)) {
      this.logger.error(exception);
    }
    const problem: Record<string, unknown> = {
      type: "about:blank",
      title: titleFor(status),
      status,
      instance: request.url,
    };
    if (exception instanceof ProblemException) {
      problem.detail = exception.detail;
      if (exception.errors.length) problem.errors = exception.errors;
    } else if (exception instanceof HttpException && status < 500) {
      problem.detail = exception.message;
    }
    void reply.status(status).header("content-type", "application/problem+json").send(problem);
  }
}

function titleFor(status: number): string {
  const titles: Record<number, string> = {
    400: "Requête invalide",
    401: "Authentification requise",
    403: "Accès refusé",
    404: "Introuvable",
    409: "Conflit",
    429: "Trop de requêtes",
    501: "Pas encore disponible",
  };
  return titles[status] ?? (status >= 500 ? "Erreur interne" : "Erreur");
}
