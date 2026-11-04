import { Module } from "@nestjs/common";
import { CitiesController } from "./cities/cities.controller.js";
import { DatabaseModule } from "./database/database.module.js";
import { HealthController } from "./health/health.controller.js";
import { PlacesController } from "./places/places.controller.js";
import { StopsController } from "./stops/stops.controller.js";

@Module({
  imports: [DatabaseModule],
  controllers: [HealthController, CitiesController, PlacesController, StopsController],
})
export class AppModule {}
