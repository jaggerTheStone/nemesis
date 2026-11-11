import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:maplibre_gl/maplibre_gl.dart';

import '../data/city.dart';

/// Offline style: GeoJSON sources, no tiles and no text (text would need glyphs from a
/// server). With the lines of 2023, the yafohi background comes as four images whose
/// district names are drawn in (map.json, « background »). The real city will use the
/// PMTiles of ADR-009.
String offlineStyle(CityData city, String mapJson) {
  final map = jsonDecode(mapJson) as Map<String, dynamic>;
  final background = map['background'] as Map<String, dynamic>?;
  final images = (background?['images'] as List? ?? const [])
      .cast<Map<String, dynamic>>();
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
    'name': 'nemesis-${city.code}',
    'sources': {
      'roads': {'type': 'geojson', 'data': map['roads']},
      'lines': {'type': 'geojson', 'data': map['lines']},
      'stops': {'type': 'geojson', 'data': stops},
      for (final image in images)
        'fond-${image['file']}': {
          'type': 'image',
          'url': image['url'],
          'coordinates': image['coordinates'],
        },
    },
    'layers': [
      {
        'id': 'background',
        'type': 'background',
        'paint': {
          'background-color': background?['color'] as String? ?? '#E9EFEA',
        },
      },
      for (final image in images)
        {
          'id': 'fond-${image['file']}',
          'type': 'raster',
          'source': 'fond-${image['file']}',
          'paint': {'raster-fade-duration': 0},
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
          'line-width': images.isEmpty ? 3 : 2,
          'line-opacity': images.isEmpty ? 0.85 : 0.55,
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
            images.isEmpty ? 8 : 6,
            images.isEmpty ? 5 : 3,
          ],
          'circle-color': '#FFFFFF',
          'circle-stroke-color': '#16130F',
          'circle-stroke-width': images.isEmpty ? 3 : 1.5,
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
    initialCameraPosition: city.isFictional
        ? CameraPosition(
            target: LatLng(centre.lat - 0.03, centre.lon + 0.01),
            zoom: 12.5,
          )
        : CameraPosition(target: LatLng(centre.lat, centre.lon), zoom: 13.5),
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
