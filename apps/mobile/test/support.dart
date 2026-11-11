import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nemesis_mobile/app.dart';
import 'package:nemesis_mobile/data/city.dart';
import 'package:nemesis_mobile/data/store.dart';
import 'package:nemesis_mobile/routing/plan.dart';
import 'package:nemesis_mobile/services.dart';

/// A Tuesday morning: the fictional network runs.
final testNow = DateTime(2026, 11, 10, 7, 30);

CityData? _city;

/// The fictional city embedded in the app.
CityData testCity() => _city ??= CityData.fromJson(
  File('assets/fictif/city.json').readAsStringSync(),
);

String testMapJson() => File('assets/fictif/map.json').readAsStringSync();

/// A response of the real engine, saved by `routing plan` on the app's pack.
PlanResult fixturePlan() => PlanResult.fromJson(
  jsonDecode(
    File('test/fixtures/plan_flamboyants_embarcadere.json').readAsStringSync(),
  ) as Map<String, dynamic>,
);

/// Answers every query with the saved response of the engine.
class FixtureRouting implements RoutingService {
  final queries = <PlanQuery>[];

  @override
  Future<PlanResult> plan(PlanQuery query) async {
    queries.add(query);
    return fixturePlan();
  }
}

Widget mapPlaceholder(
  BuildContext context,
  CityData city,
  String mapJson,
  void Function(Stop stop) onStopTapped,
) => ColoredBox(
  key: const Key('map'),
  color: const Color(0xFFE9EFEA),
  child: Center(
    child: TextButton(
      onPressed: () => onStopTapped(city.stop('flamboyants')!),
      child: const Text('Carte'),
    ),
  ),
);

/// The app with test services: the saved engine response, SQLite in memory, a fixed
/// clock, and a placeholder instead of the native map.
Widget testApp({LocalStore? store, RoutingService? routing}) {
  final changes = ValueNotifier(0);
  final local = store ?? SqliteStore.inMemory();
  return NemesisApp(
    services: (child) => AppServices(
      city: testCity(),
      mapJson: testMapJson(),
      routing: routing ?? FixtureRouting(),
      store: local,
      mapBuilder: mapPlaceholder,
      now: () => testNow,
      showFictionalBanner: true,
      storeChanges: changes,
      child: child,
    ),
  );
}

/// A 5-inch phone (360 × 740 dp), at a text scale.
Future<void> phone(WidgetTester tester, {double textScale = 1}) async {
  tester.view.physicalSize = const Size(1080, 2220);
  tester.view.devicePixelRatio = 3;
  tester.platformDispatcher.textScaleFactorTestValue = textScale;
  addTearDown(tester.view.reset);
  addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
}

/// The placeholder map for another city: a tap opens its first stop.
MapBuilder mapPlaceholderFor(CityData city) =>
    (context, city, mapJson, onStopTapped) => ColoredBox(
      key: const Key('map'),
      color: const Color(0xFFFBF6EC),
      child: Center(
        child: TextButton(
          onPressed: () => onStopTapped(city.stops.first),
          child: const Text('Carte'),
        ),
      ),
    );
