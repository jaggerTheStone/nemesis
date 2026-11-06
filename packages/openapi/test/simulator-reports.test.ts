/**
 * The simulator (tools/simulator, I0.10) writes reports in the format of the API: every
 * request of its versioned example must be a valid ContributionRequest, with the payload
 * conventions of H-033.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { createValidator, loadSpec } from "../src/index.js";

const EXAMPLE = fileURLToPath(
  new URL("../../../tools/simulator/exemples/observations.jsonl", import.meta.url),
);
const SOURCE_KINDS = ["usager", "chef_de_gare", "eclaireur", "pro", "partenaire", "systeme"];
const PAYLOAD_KEYS: Record<string, string[]> = {
  file: ["level"],
  vehicules_presents: ["vehicles"],
  attente_reelle: ["wait_s"],
  prix_paye: ["amount_xof"],
  vehicule_plein: [],
};

interface Envelope {
  received_at: string;
  source_kind: string;
  contributor: string;
  request: { kind: string; observed_at: string; payload: Record<string, unknown> };
}

const envelopes: Envelope[] = readFileSync(EXAMPLE, "utf-8")
  .split("\n")
  .filter((line) => line.trim() !== "")
  .map((line) => JSON.parse(line) as Envelope);

describe("simulated reports (I0.10)", () => {
  const validator = createValidator(loadSpec());

  it("the example is not empty and covers several kinds of report", () => {
    expect(envelopes.length).toBeGreaterThan(20);
    expect(new Set(envelopes.map((e) => e.request.kind)).size).toBeGreaterThanOrEqual(3);
  });

  it("every request is a valid ContributionRequest", () => {
    for (const envelope of envelopes) {
      expect(
        validator.validate("#/components/schemas/ContributionRequest", envelope.request),
      ).toEqual([]);
    }
  });

  it("payloads follow the conventions of H-033, sources those of the database", () => {
    for (const { request, source_kind } of envelopes) {
      expect(Object.keys(request.payload).sort(), request.kind).toEqual(PAYLOAD_KEYS[request.kind]);
      expect(SOURCE_KINDS).toContain(source_kind);
    }
  });

  it("no report is received before it was observed", () => {
    for (const { request, received_at } of envelopes) {
      expect(Date.parse(received_at)).toBeGreaterThanOrEqual(Date.parse(request.observed_at));
    }
  });
});
