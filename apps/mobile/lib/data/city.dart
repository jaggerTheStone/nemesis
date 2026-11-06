import 'dart:convert';
import 'dart:math' as math;

/// A point, WGS 84.
class GeoPoint {
  const GeoPoint(this.lat, this.lon);

  final double lat;
  final double lon;

  /// Great-circle distance, metres.
  double distanceTo(GeoPoint other) {
    const r = 6371000.0;
    final p1 = lat * math.pi / 180;
    final p2 = other.lat * math.pi / 180;
    final dp = p2 - p1;
    final dl = (other.lon - lon) * math.pi / 180;
    final h =
        math.sin(dp / 2) * math.sin(dp / 2) +
        math.cos(p1) * math.cos(p2) * math.sin(dl / 2) * math.sin(dl / 2);
    return 2 * r * math.asin(math.sqrt(h));
  }

  /// « lat,lon », the way the engine reads a place.
  String get engineText =>
      '${lat.toStringAsFixed(6)},${lon.toStringAsFixed(6)}';
}

class Stop {
  const Stop({
    required this.code,
    required this.id,
    required this.name,
    required this.kind,
    required this.point,
    required this.area,
    required this.aliases,
    required this.lighting,
    required this.lines,
    required this.hours,
  });

  final String code;

  /// Identifier in the database and in reports (uuid).
  final String id;
  final String name;
  final String kind;
  final GeoPoint point;
  final String area;
  final List<String> aliases;
  final String lighting;
  final List<String> lines;
  final (String, String) hours;

  bool get isStation => kind == 'gare_artisanale' || kind == 'embarcadere';
}

class Line {
  const Line({
    required this.code,
    required this.id,
    required this.shortName,
    required this.longName,
    required this.mode,
    required this.color,
    required this.bodyColor,
    required this.colorPattern,
    required this.announcedAs,
    required this.terminals,
  });

  final String code;
  final String id;
  final String shortName;
  final String longName;
  final String mode;
  final int color;
  final String bodyColor;
  final String? colorPattern;
  final String? announcedAs;
  final List<String> terminals;
}

class Place {
  const Place({
    required this.code,
    required this.name,
    required this.category,
    required this.point,
    required this.aliases,
  });

  final String code;
  final String name;
  final String category;
  final GeoPoint point;
  final List<String> aliases;
}

/// Fictional fare range of a line between two areas, XOF.
class FareRow {
  const FareRow(
    this.line,
    this.fromArea,
    this.toArea,
    this.condition,
    this.p10,
    this.p50,
    this.p90,
    this.confidence,
  );

  final String line;
  final String fromArea;
  final String toArea;
  final String condition;
  final int p10;
  final int p50;
  final int p90;
  final String confidence;
}

/// Usual wait of a line at a stop, by 15-min slot, for a type of day.
class WaitSeries {
  const WaitSeries({
    required this.stop,
    required this.line,
    required this.dayType,
    required this.regime,
    required this.slots,
  });

  final String stop;
  final String line;
  final String dayType;
  final String regime;

  /// (slot start in seconds, p50 s, p80 s, contributors).
  final List<(int, int, int, int)> slots;

  (int, int, int, int)? at(int secondsOfDay) {
    (int, int, int, int)? found;
    for (final slot in slots) {
      if (slot.$1 <= secondsOfDay) found = slot;
    }
    if (found == null || secondsOfDay - found.$1 >= 900) return null;
    return found;
  }
}

/// Something one can go to: a stop or a place.
class Destination {
  const Destination(this.name, this.point, {this.stop, this.place});

  final String name;
  final GeoPoint point;
  final Stop? stop;
  final Place? place;
}

/// The fictional city embedded in the app (assets/fictif/city.json).
class CityData {
  CityData({
    required this.code,
    required this.id,
    required this.name,
    required this.isFictional,
    required this.networkVersion,
    required this.areas,
    required this.position,
    required this.stops,
    required this.lines,
    required this.places,
    required this.fares,
    required this.waits,
  });

  factory CityData.fromJson(String text) {
    final json = jsonDecode(text) as Map<String, dynamic>;
    final city = json['city'] as Map<String, dynamic>;
    GeoPoint point(Map<String, dynamic> m) =>
        GeoPoint((m['lat'] as num).toDouble(), (m['lon'] as num).toDouble());
    List<String> strings(Object? list) =>
        (list as List<dynamic>? ?? []).cast<String>();
    return CityData(
      code: city['code'] as String,
      id: city['id'] as String,
      name: city['name'] as String,
      isFictional: city['is_fictional'] as bool,
      networkVersion: city['network_version'] as String,
      areas: (city['areas'] as Map<String, dynamic>).cast<String, String>(),
      position: point(json['position'] as Map<String, dynamic>),
      stops: [
        for (final s in (json['stops'] as List).cast<Map<String, dynamic>>())
          Stop(
            code: s['code'] as String,
            id: s['id'] as String,
            name: s['name'] as String,
            kind: s['kind'] as String,
            point: point(s),
            area: s['area'] as String,
            aliases: strings(s['aliases']),
            lighting: s['lighting'] as String,
            lines: strings(s['lines']),
            hours: (strings(s['hours'])[0], strings(s['hours'])[1]),
          ),
      ],
      lines: [
        for (final l in (json['lines'] as List).cast<Map<String, dynamic>>())
          Line(
            code: l['code'] as String,
            id: l['id'] as String,
            shortName: l['short_name'] as String,
            longName: l['long_name'] as String,
            mode: l['mode'] as String,
            color: int.parse('FF${l['color']}', radix: 16),
            bodyColor: l['body_color'] as String,
            colorPattern: l['color_pattern'] as String?,
            announcedAs: l['announced_as'] as String?,
            terminals: strings(l['terminals']),
          ),
      ],
      places: [
        for (final p in (json['places'] as List).cast<Map<String, dynamic>>())
          Place(
            code: p['code'] as String,
            name: p['name'] as String,
            category: p['category'] as String,
            point: point(p),
            aliases: strings(p['aliases']),
          ),
      ],
      fares: [
        for (final f in (json['fares'] as List).cast<List<dynamic>>())
          FareRow(
            f[0] as String,
            f[1] as String,
            f[2] as String,
            f[3] as String,
            f[4] as int,
            f[5] as int,
            f[6] as int,
            f[7] as String,
          ),
      ],
      waits: [
        for (final w in (json['waits'] as List).cast<Map<String, dynamic>>())
          WaitSeries(
            stop: w['stop'] as String,
            line: w['line'] as String,
            dayType: w['day_type'] as String,
            regime: w['regime'] as String,
            slots: [
              for (final s in (w['slots'] as List).cast<List<dynamic>>())
                (s[0] as int, s[1] as int, s[2] as int, s[3] as int),
            ],
          ),
      ],
    );
  }

  final String code;
  final String id;
  final String name;
  final bool isFictional;
  final String networkVersion;
  final Map<String, String> areas;

  /// Where the demo user stands, without GPS.
  final GeoPoint position;
  final List<Stop> stops;
  final List<Line> lines;
  final List<Place> places;
  final List<FareRow> fares;
  final List<WaitSeries> waits;

  Stop? stop(String code) {
    for (final s in stops) {
      if (s.code == code) return s;
    }
    return null;
  }

  Line? line(String code) {
    for (final l in lines) {
      if (l.code == code) return l;
    }
    return null;
  }

  /// Stations closest to a point, nearest first.
  List<Stop> nearestStations(GeoPoint point, {int count = 3}) {
    final stations = stops.where((s) => s.isStation).toList()
      ..sort(
        (a, b) =>
            a.point.distanceTo(point).compareTo(b.point.distanceTo(point)),
      );
    return stations.take(count).toList();
  }

  /// Usual waits at a stop for a type of day, one series per line.
  List<WaitSeries> waitsAt(String stop, String dayType) => [
    for (final w in waits)
      if (w.stop == stop && w.dayType == dayType) w,
  ];

  /// Fares of a line from a stop to its terminal, normal condition.
  FareRow? fareTo(Line line, Stop from, String condition) {
    final terminal = line.terminals.isEmpty ? null : stop(line.terminals.last);
    if (terminal == null) return null;
    for (final f in fares) {
      if (f.line == line.code &&
          f.fromArea == from.area &&
          f.toArea == terminal.area &&
          f.condition == condition) {
        return f;
      }
    }
    return null;
  }

  /// Places and stops matching what the person typed (F-01) : sans accents, sans
  /// casse, sur le nom et les alias, les débuts de mots d'abord.
  List<Destination> search(String query, {int limit = 8}) {
    final q = normalize(query);
    if (q.isEmpty) return const [];
    final scored = <(int, Destination)>[];
    void consider(String name, List<String> aliases, Destination d) {
      var best = 0;
      for (final text in [name, ...aliases]) {
        final n = normalize(text);
        final score = n == q
            ? 4
            : n.startsWith(q)
            ? 3
            : n.split(' ').any((w) => w.startsWith(q))
            ? 2
            : n.contains(q)
            ? 1
            : 0;
        if (score > best) best = score;
      }
      if (best > 0) scored.add((best, d));
    }

    for (final s in stops) {
      consider(s.name, s.aliases, Destination(s.name, s.point, stop: s));
    }
    for (final p in places) {
      consider(p.name, p.aliases, Destination(p.name, p.point, place: p));
    }
    scored.sort((a, b) {
      final byScore = b.$1.compareTo(a.$1);
      return byScore != 0 ? byScore : a.$2.name.compareTo(b.$2.name);
    });
    return [for (final s in scored.take(limit)) s.$2];
  }
}

const _accents = {
  'à': 'a', 'â': 'a', 'ä': 'a', 'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e', //
  'î': 'i', 'ï': 'i', 'ô': 'o', 'ö': 'o', 'ù': 'u', 'û': 'u', 'ü': 'u', //
  'ç': 'c', 'œ': 'oe', 'æ': 'ae', '’': ' ', "'": ' ', '-': ' ',
};

/// Lower case, without accents, apostrophes or dashes, single spaces, without the
/// « (fictif) » mark.
String normalize(String text) {
  final lower = text.toLowerCase().replaceAll('(fictif)', '');
  final buffer = StringBuffer();
  for (final rune in lower.runes) {
    final c = String.fromCharCode(rune);
    buffer.write(_accents[c] ?? c);
  }
  return buffer
      .toString()
      .split(RegExp(r'\s+'))
      .where((w) => w.isNotEmpty)
      .join(' ');
}
