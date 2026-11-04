import { Controller, Get } from "@nestjs/common";
import { SERVICE_VERSION } from "../version.js";

export interface HealthResponse {
  status: "ok";
  service: "api";
  version: string;
}

@Controller("health")
export class HealthController {
  @Get()
  getHealth(): HealthResponse {
    return { status: "ok", service: "api", version: SERVICE_VERSION };
  }
}
