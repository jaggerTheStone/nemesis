import 'dart:convert';
import 'dart:math';

import 'package:sqlite3/sqlite3.dart';

import 'city.dart';

/// A report made in two taps (F-07), in the format of `ContributionRequest` (OpenAPI)
/// with the payload conventions of H-033. It waits in the local queue until the network
/// comes back; the prototype has no server, so it stays there.
class Contribution {
  const Contribution({
    required this.id,
    required this.kind,
    required this.observedAt,
    required this.city,
    required this.stopId,
    required this.payload,
    this.routeId,
    this.location,
    this.accuracyM,
  });

  factory Contribution.fromRequestJson(String text) {
    final json = jsonDecode(text) as Map<String, dynamic>;
    final location = json['location'] as Map<String, dynamic>?;
    return Contribution(
      id: json['id'] as String,
      kind: json['kind'] as String,
      observedAt: DateTime.parse(json['observed_at'] as String),
      city: json['city'] as String,
      stopId: json['stop_id'] as String?,
      routeId: json['route_id'] as String?,
      location: location == null
          ? null
          : GeoPoint(
              (location['lat'] as num).toDouble(),
              (location['lon'] as num).toDouble(),
            ),
      accuracyM: (json['accuracy_m'] as num?)?.toDouble(),
      payload: (json['payload'] as Map<String, dynamic>?) ?? const {},
    );
  }

  final String id;
  final String kind;
  final DateTime observedAt;
  final String city;
  final String? stopId;
  final String? routeId;
  final GeoPoint? location;
  final double? accuracyM;
  final Map<String, dynamic> payload;

  /// The body of `POST /contributions`.
  String toRequestJson() => jsonEncode({
    'id': id,
    'kind': kind,
    'observed_at': observedAt.toUtc().toIso8601String(),
    'city': city,
    'stop_id': ?stopId,
    'route_id': ?routeId,
    if (location != null)
      'location': {'lat': location!.lat, 'lon': location!.lon},
    'accuracy_m': ?accuracyM,
    'payload': payload,
  });
}

/// UUID version 4 from a secure source: the id is the idempotency key (7.2).
String newUuid([Random? random]) {
  final rng = random ?? Random.secure();
  final bytes = List<int>.generate(16, (_) => rng.nextInt(256));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-'
      '${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
}

class RecentTrip {
  const RecentTrip(this.name, this.point, this.at);

  final String name;
  final GeoPoint point;
  final DateTime at;
}

/// What the app keeps on the phone.
abstract interface class LocalStore {
  void addContribution(Contribution contribution);
  List<Contribution> pendingContributions();
  void addRecent(RecentTrip trip);
  List<RecentTrip> recentTrips({int limit = 5});
}

/// SQLite on the phone (and in host tests). No identity is stored (H-016, H-020).
class SqliteStore implements LocalStore {
  SqliteStore(this._db) {
    _db.execute('''
      create table if not exists outbox (
        id text primary key,
        created_at text not null,
        request text not null
      );
      create table if not exists recent_trip (
        name text primary key,
        lat real not null,
        lon real not null,
        at text not null
      );
    ''');
  }

  factory SqliteStore.open(String path) => SqliteStore(sqlite3.open(path));

  factory SqliteStore.inMemory() => SqliteStore(sqlite3.openInMemory());

  final Database _db;

  @override
  void addContribution(Contribution contribution) {
    _db.execute(
      'insert or ignore into outbox (id, created_at, request) values (?, ?, ?)',
      [
        contribution.id,
        contribution.observedAt.toUtc().toIso8601String(),
        contribution.toRequestJson(),
      ],
    );
  }

  @override
  List<Contribution> pendingContributions() => [
    for (final row in _db.select(
      'select request from outbox order by created_at desc, id',
    ))
      Contribution.fromRequestJson(row['request'] as String),
  ];

  @override
  void addRecent(RecentTrip trip) {
    _db.execute(
      'insert or replace into recent_trip (name, lat, lon, at) values (?, ?, ?, ?)',
      [trip.name, trip.point.lat, trip.point.lon, trip.at.toIso8601String()],
    );
  }

  @override
  List<RecentTrip> recentTrips({int limit = 5}) => [
    for (final row in _db.select(
      'select name, lat, lon, at from recent_trip order by at desc limit ?',
      [limit],
    ))
      RecentTrip(
        row['name'] as String,
        GeoPoint(row['lat'] as double, row['lon'] as double),
        DateTime.parse(row['at'] as String),
      ),
  ];

  void close() => _db.close();
}
