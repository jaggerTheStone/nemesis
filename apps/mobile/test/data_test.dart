import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:nemesis_mobile/data/city.dart';
import 'package:nemesis_mobile/data/store.dart';
import 'package:nemesis_mobile/routing/plan.dart';

import 'support.dart';

void main() {
  group('embedded city', () {
    test('is fictional and complete', () {
      final city = testCity();
      expect(city.isFictional, isTrue);
      expect(city.stop('flamboyants')!.lines, contains('g1'));
      expect(city.line('g1')!.mode, 'gbaka');
      expect(city.waitsAt('flamboyants', 'ouvrable'), isNotEmpty);
    });

    test('search tolerates accents, case and aliases (F-01)', () {
      final city = testCity();
      expect(
        city.search('embarcadere sud').first.name,
        'Embarcadère Sud (fictif)',
      );
      expect(city.search('FLAMBO').first.stop?.code, 'flamboyants');
      expect(city.search('gare flamboyant').first.stop?.code, 'flamboyants');
      expect(city.search('zzz'), isEmpty);
    });

    test('search answers well under 300 ms offline (F-01)', () {
      final city = testCity();
      final watch = Stopwatch()..start();
      for (final q in ['gr', 'marché', 'embar', 'pharm', 'carrefour']) {
        city.search(q);
      }
      expect(watch.elapsedMilliseconds, lessThan(300));
    });

    test('normalize removes accents and the fictional mark', () {
      expect(
        normalize('Église du Quartier Nord (fictif)'),
        'eglise du quartier nord',
      );
      expect(normalize("  Rond-point   l'Acacia "), 'rond point l acacia');
    });
  });

  test('the engine response is read with its labels, waits and fares', () {
    final plan = fixturePlan();
    expect(plan.isFictional, isTrue);
    expect(plan.options.length, greaterThanOrEqualTo(3));
    final labels = plan.options.expand((o) => o.labels).toSet();
    expect(labels, containsAll(['cheapest', 'fastest', 'simplest']));
    final first = plan.options.first;
    expect(first.duration.low, lessThanOrEqualTo(first.duration.high));
    expect(first.rides, isNotEmpty);
    expect(first.firstWait!.regime, anyOf('A', 'B'));
  });

  test('the engine request carries the date and the time of day', () {
    final query = PlanQuery(
      const GeoPoint(2.045, -4.02),
      const GeoPoint(1.966, -3.99),
      DateTime(2026, 11, 10, 7, 30),
    );
    expect(jsonDecode(query.toEngineJson()), {
      'from': '2.045000,-4.020000',
      'to': '1.966000,-3.990000',
      'date': 20261110,
      'time': 27000,
    });
  });

  group('local store', () {
    test('keeps reports in the format of ContributionRequest (H-033)', () {
      final store = SqliteStore.inMemory();
      final report = Contribution(
        id: newUuid(),
        kind: 'file',
        observedAt: DateTime.utc(2026, 11, 10, 7, 31),
        city: 'lagune-fictive',
        stopId: testCity().stop('flamboyants')!.id,
        location: const GeoPoint(2.0438, -4.0182),
        accuracyM: 25,
        payload: const {'level': 'beaucoup'},
      );
      store.addContribution(report);
      store.addContribution(report); // a resend is not counted twice
      final pending = store.pendingContributions();
      expect(pending, hasLength(1));
      final json = jsonDecode(pending.single.toRequestJson()) as Map;
      expect(
        json.keys,
        containsAll(['id', 'kind', 'observed_at', 'city', 'payload']),
      );
      expect(json['payload'], {'level': 'beaucoup'});
      expect(json['observed_at'], '2026-11-10T07:31:00.000Z');
      expect(json.containsKey('route_id'), isFalse);
    });

    test('remembers recent trips, latest first', () {
      final store = SqliteStore.inMemory();
      store.addRecent(
        RecentTrip('A', const GeoPoint(2, -4), DateTime(2026, 11, 9)),
      );
      store.addRecent(
        RecentTrip('B', const GeoPoint(2, -4), DateTime(2026, 11, 10)),
      );
      expect(store.recentTrips().map((t) => t.name), ['B', 'A']);
    });

    test('identifiers are version 4 UUIDs', () {
      final id = newUuid();
      expect(
        RegExp(
          r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        ).hasMatch(id),
        isTrue,
      );
      expect(newUuid(), isNot(id));
    });
  });
}
