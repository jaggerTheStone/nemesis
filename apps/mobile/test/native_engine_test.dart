import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:nemesis_mobile/data/city.dart';
import 'package:nemesis_mobile/routing/native_engine.dart';
import 'package:nemesis_mobile/routing/plan.dart';

/// The real engine through `dart:ffi`, on the pack the app carries. It needs the library
/// built for this computer:
///   cargo build --release -p routing-ffi   (in services/routing)
///   NEMESIS_ROUTING_LIB=…/target/release/libnemesis_routing.so flutter test
void main() {
  final library = Platform.environment['NEMESIS_ROUTING_LIB'];
  final skip = library == null ? 'NEMESIS_ROUTING_LIB absent' : null;

  test('plans offline with the engine of the server', () async {
    final engine = NativeRoutingService.open(
      Directory('assets/fictif/pack').absolute.path,
      library: library,
    );
    addTearDown(engine.close);
    expect(engine.info()['city'], 'lagune-fictive');
    final result = await engine.plan(
      PlanQuery(
        const GeoPoint(2.045, -4.02),
        const GeoPoint(1.966, -3.99),
        DateTime(2026, 11, 10, 7, 30),
      ),
    );
    expect(result.isFictional, isTrue);
    expect(result.options.length, greaterThanOrEqualTo(3));
    expect(
      result.options.expand((o) => o.labels).toSet(),
      containsAll(['cheapest', 'fastest', 'simplest']),
    );
  }, skip: skip);

  test('a bad pack is reported, not a crash', () {
    expect(
      () => NativeRoutingService.open('/nulle/part', library: library),
      throwsA(isA<RoutingException>()),
    );
  }, skip: skip);
}
