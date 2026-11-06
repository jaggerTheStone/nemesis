import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:maplibre_gl/maplibre_gl.dart';

import '../data/city.dart';

/// Offline style of the fictional city: GeoJSON sources only, no tiles and no text (text
/// would need glyphs from a server). The real city will use the PMTiles of ADR-009.
String offlineStyle(CityData city, String mapJson) {
  final map = jsonDecode(mapJson) as Map<String, dynamic>;
  final stops = {
    'type': 'FeatureCollection',
    'features': [
      for (final stop in city.stops)
        {
          'type': 'Feature',
          'properties': {'code': stop.code, 'station': stop.isStation},
          'geometry': {
            'type': 'Point',
            'coordinates': [stop.point.lon, stop.point.lat],
          },
        },
    ],
  };
  Map<String, Object> line(
    String id,
    List<String> classes,
    String color,
    num width,
  ) => {
    'id': id,
    'type': 'line',
    'source': 'roads',
    'filter': [
      'in',
      ['get', 'class'],
      ['literal', classes],
    ],
    'layout': {'line-cap': 'round', 'line-join': 'round'},
    'paint': {'line-color': color, 'line-width': width},
  };
  return jsonEncode({
    'version': 8,
    'name': 'nemesis-fictif',
    'sources': {
      'roads': {'type': 'geojson', 'data': map['roads']},
      'lines': {'type': 'geojson', 'data': map['lines']},
      'stops': {'type': 'geojson', 'data': stops},
    },
    'layers': [
      {
        'id': 'background',
        'type': 'background',
        'paint': {'background-color': '#E9EFEA'},
      },
      {
        ...line('ferry', ['ferry'], '#3E7CB1', 2),
        'paint': {
          'line-color': '#3E7CB1',
          'line-width': 2,
          'line-dasharray': [2, 2],
        },
      },
      line('roads-minor', ['residential', 'footway'], '#FFFFFF', 2),
      line(
        'roads-major-casing',
        ['primary', 'secondary', 'tertiary'],
        '#B8C2BC',
        7,
      ),
      line('roads-major', ['primary', 'secondary', 'tertiary'], '#FFFFFF', 5),
      {
        'id': 'lines',
        'type': 'line',
        'source': 'lines',
        'layout': {'line-cap': 'round', 'line-join': 'round'},
        'paint': {
          'line-color': ['get', 'color'],
          'line-width': 3,
          'line-opacity': 0.85,
        },
      },
      {
        'id': 'stops',
        'type': 'circle',
        'source': 'stops',
        'paint': {
          'circle-radius': [
            'case',
            ['get', 'station'],
            8,
            5,
          ],
          'circle-color': '#FFFFFF',
          'circle-stroke-color': '#0A5C5A',
          'circle-stroke-width': 3,
        },
      },
    ],
  });
}

/// The native map (MapLibre), used on the phone.
Widget mapLibreBuilder(
  BuildContext context,
  CityData city,
  String mapJson,
  void Function(Stop stop) onStopTapped,
) {
  final centre = city.position;
  return MapLibreMap(
    styleString: offlineStyle(city, mapJson),
    initialCameraPosition: CameraPosition(
      target: LatLng(centre.lat - 0.03, centre.lon + 0.01),
      zoom: 12.5,
    ),
    compassEnabled: false,
    onMapClick: (_, coordinates) {
      final tapped = GeoPoint(coordinates.latitude, coordinates.longitude);
      Stop? nearest;
      var best = 250.0;
      for (final stop in city.stops) {
        final d = stop.point.distanceTo(tapped);
        if (d < best) {
          best = d;
          nearest = stop;
        }
      }
      if (nearest != null) onStopTapped(nearest);
    },
  );
}
