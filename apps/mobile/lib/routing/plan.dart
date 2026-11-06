import 'dart:convert';

import '../data/city.dart';

/// A request to the engine: from, to, and when to leave (local time).
class PlanQuery {
  const PlanQuery(this.from, this.to, this.at);

  final GeoPoint from;
  final GeoPoint to;
  final DateTime at;

  /// The JSON the native engine reads (services/routing/crates/routing-ffi).
  String toEngineJson() => jsonEncode({
    'from': from.engineText,
    'to': to.engineText,
    'date': at.year * 10000 + at.month * 100 + at.day,
    'time': at.hour * 3600 + at.minute * 60,
  });
}

class Range {
  const Range(this.low, this.high);

  final int low;
  final int high;
}

/// Fare of a leg or of a journey, XOF, rounded to 50 F.
class Fare {
  const Fare(this.p10, this.p50, this.p90);

  factory Fare.fromJson(Map<String, dynamic> json) =>
      Fare(json['p10'] as int, json['p50'] as int, json['p90'] as int);

  final int p10;
  final int p50;
  final int p90;
}

class Wait {
  const Wait(this.p50Min, this.p80Min, this.regime, this.source);

  final int p50Min;
  final int p80Min;

  /// A (head of line, departs when full) or B (roadside).
  final String regime;

  /// `profile` (usual waits reported) or `gtfs_headway` (headway of the network).
  final String source;
}

class PlaceRef {
  const PlaceRef(this.name, this.stopCode, this.point);

  factory PlaceRef.fromJson(Map<String, dynamic> json) => PlaceRef(
    json['name'] as String,
    json['stop_id'] as String?,
    GeoPoint((json['lat'] as num).toDouble(), (json['lon'] as num).toDouble()),
  );

  final String name;
  final String? stopCode;
  final GeoPoint point;
}

sealed class Leg {
  const Leg(this.source);

  /// Where the leg comes from: `osm_walking_graph`, `straight_line`, `gtfs_timetable`.
  final String source;
}

class WalkLeg extends Leg {
  const WalkLeg(this.from, this.to, this.minutes, this.metres, super.source);

  final PlaceRef from;
  final PlaceRef to;
  final int minutes;
  final int metres;
}

class RideLeg extends Leg {
  const RideLeg({
    required this.line,
    required this.lineName,
    required this.board,
    required this.alight,
    required this.wait,
    required this.rideMinutes,
    required this.fare,
    required String source,
  }) : super(source);

  final String line;
  final String lineName;
  final PlaceRef board;
  final PlaceRef alight;
  final Wait wait;
  final int rideMinutes;
  final Fare? fare;
}

class TripOption {
  const TripOption({
    required this.labels,
    required this.duration,
    required this.depart,
    required this.arriveP50,
    required this.arriveP80,
    required this.transfers,
    required this.walkMetres,
    required this.fare,
    required this.legs,
  });

  final List<String> labels;

  /// p50 and p80 of the total duration, minutes.
  final Range duration;
  final String depart;
  final String arriveP50;
  final String arriveP80;
  final int transfers;
  final int walkMetres;
  final Fare? fare;
  final List<Leg> legs;

  Iterable<RideLeg> get rides => legs.whereType<RideLeg>();

  int get walkMinutes =>
      legs.whereType<WalkLeg>().fold(0, (total, leg) => total + leg.minutes);

  /// Wait at the first boarding, which is what decides when to leave.
  Wait? get firstWait => rides.isEmpty ? null : rides.first.wait;
}

class PlanResult {
  const PlanResult({
    required this.from,
    required this.to,
    required this.options,
    required this.notes,
    required this.networkVersion,
    required this.isFictional,
    required this.dayType,
    required this.computedMs,
  });

  /// Reads the document of `routing plan` (or the `ok` member of the native reply).
  factory PlanResult.fromJson(Map<String, dynamic> json) {
    Leg leg(Map<String, dynamic> l) => switch (l['type']) {
      'walk' => WalkLeg(
        PlaceRef.fromJson(l['from'] as Map<String, dynamic>),
        PlaceRef.fromJson(l['to'] as Map<String, dynamic>),
        l['minutes'] as int,
        l['metres'] as int,
        l['source'] as String,
      ),
      _ => RideLeg(
        line: l['route_id'] as String,
        lineName: l['route_name'] as String,
        board: PlaceRef.fromJson(l['board'] as Map<String, dynamic>),
        alight: PlaceRef.fromJson(l['alight'] as Map<String, dynamic>),
        wait: Wait(
          (l['wait'] as Map)['p50_min'] as int,
          (l['wait'] as Map)['p80_min'] as int,
          (l['wait'] as Map)['regime'] as String,
          (l['wait'] as Map)['source'] as String,
        ),
        rideMinutes: l['ride_minutes'] as int,
        fare: l['fare'] == null
            ? null
            : Fare.fromJson(l['fare'] as Map<String, dynamic>),
        source: l['source'] as String,
      ),
    };
    return PlanResult(
      from: json['from'] as String? ?? '',
      to: json['to'] as String? ?? '',
      networkVersion: json['network_version'] as String,
      isFictional: json['is_fictional'] as bool,
      dayType: json['day_type'] as String,
      computedMs: (json['computed_ms'] as num?)?.toDouble() ?? 0,
      notes: (json['notes'] as List).cast<String>(),
      options: [
        for (final o in (json['options'] as List).cast<Map<String, dynamic>>())
          TripOption(
            labels: (o['labels'] as List).cast<String>(),
            duration: Range(o['p50_min'] as int, o['p80_min'] as int),
            depart: o['depart'] as String,
            arriveP50: o['arrive_p50'] as String,
            arriveP80: o['arrive_p80'] as String,
            transfers: o['transfers'] as int,
            walkMetres: o['walk_m'] as int,
            fare: o['fare'] == null
                ? null
                : Fare.fromJson(o['fare'] as Map<String, dynamic>),
            legs: [
              for (final l in (o['legs'] as List).cast<Map<String, dynamic>>())
                leg(l),
            ],
          ),
      ],
    );
  }

  final String from;
  final String to;
  final List<TripOption> options;
  final List<String> notes;
  final String networkVersion;
  final bool isFictional;
  final String dayType;
  final double computedMs;

  bool get noService => notes.contains('no_service');
}

/// The routing interface of the app (partie 8.1) : le moteur natif embarqué, ou une
/// implémentation de test.
abstract interface class RoutingService {
  Future<PlanResult> plan(PlanQuery query);
}

class RoutingException implements Exception {
  const RoutingException(this.message);

  final String message;

  @override
  String toString() => message;
}
