/**
 * The API contract (openapi.yaml): loading, JSON Schema validation and generated types.
 * OpenAPI 3.1 schemas are JSON Schema 2020-12, validated here with Ajv.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { Ajv2020, type ErrorObject, type ValidateFunction } from "ajv/dist/2020.js";
import addFormatsModule from "ajv-formats";
import { parse } from "yaml";

export type { components, operations, paths } from "./schema.js";

export const SPEC_PATH = fileURLToPath(new URL("../openapi.yaml", import.meta.url));
const SPEC_ID = "openapi.json";

export type OpenApiDocument = {
  openapi: string;
  paths: Record<string, Record<string, Operation | unknown>>;
  components: {
    schemas: Record<string, Record<string, unknown>>;
    parameters: Record<string, Parameter>;
    responses: Record<string, Response>;
    headers: Record<string, unknown>;
    securitySchemes: Record<string, unknown>;
  };
  [key: string]: unknown;
};

export type Parameter = {
  name?: string;
  in?: string;
  required?: boolean;
  schema?: Record<string, unknown>;
  example?: unknown;
  $ref?: string;
};

export type Response = {
  description?: string;
  headers?: Record<string, unknown>;
  content?: Record<string, { schema?: Record<string, unknown> }>;
  $ref?: string;
};

export type Operation = {
  operationId: string;
  tags?: string[];
  summary?: string;
  parameters?: Parameter[];
  requestBody?: { content: Record<string, { schema: Record<string, unknown> }> };
  responses: Record<string, Response>;
  security?: unknown[];
  "x-implemented"?: boolean;
  "x-safe"?: boolean;
  "x-rate-limit"?: string;
};

export const HTTP_METHODS = ["get", "put", "post", "delete", "patch"] as const;

export function loadSpec(): OpenApiDocument {
  return parse(readFileSync(SPEC_PATH, "utf8")) as OpenApiDocument;
}

/** Every operation of the contract with its method and path. */
export function listOperations(
  spec: OpenApiDocument,
): { method: string; path: string; operation: Operation }[] {
  const result = [];
  for (const [path, item] of Object.entries(spec.paths)) {
    for (const method of HTTP_METHODS) {
      const operation = item[method] as Operation | undefined;
      if (operation) result.push({ method, path, operation });
    }
  }
  return result;
}

/** Follows a local "#/components/…" reference. */
export function resolve<T>(spec: OpenApiDocument, value: T & { $ref?: string }): T {
  if (!value.$ref) return value;
  const target = value.$ref
    .replace(/^#\//, "")
    .split("/")
    .reduce<unknown>((node, key) => (node as Record<string, unknown>)[key], spec);
  return resolve(spec, target as T & { $ref?: string });
}

export type Validator = {
  /** Validates `data` against a JSON pointer into the contract, e.g. "#/components/schemas/StopDetail". */
  validate(pointer: string, data: unknown): ErrorObject[];
  compile(pointer: string): ValidateFunction;
};

const addFormats = addFormatsModule as unknown as (ajv: Ajv2020) => Ajv2020;

export function createValidator(spec: OpenApiDocument = loadSpec()): Validator {
  // OpenAPI keywords (discriminator, example, x-…) are annotations here: oneOf does
  // the actual discrimination, so strict mode is off.
  const ajv = new Ajv2020({ strict: false, allErrors: true, validateSchema: false });
  addFormats(ajv);
  ajv.addSchema({ ...spec, $id: SPEC_ID });
  const cache = new Map<string, ValidateFunction>();
  const compile = (pointer: string): ValidateFunction => {
    let validate = cache.get(pointer);
    if (!validate) {
      validate = ajv.compile({ $ref: `${SPEC_ID}${pointer}` });
      cache.set(pointer, validate);
    }
    return validate;
  };
  return {
    compile,
    validate(pointer, data) {
      const validate = compile(pointer);
      return validate(data) ? [] : (validate.errors ?? []);
    },
  };
}
