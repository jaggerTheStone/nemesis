"""Cadre géographique commun de la maquette : Abidjan en Web Mercator (EPSG:3857).

Les fonds de carte, l'imagerie satellite et les éléments posés dessus (gares, véhicules,
trajets) partagent ces coordonnées : des pixels « CSS » au zoom 14 (environ 9,5 m par
pixel à Abidjan), origine en haut à gauche du cadre.
"""

from __future__ import annotations

import math

WEST, EAST, NORTH, SOUTH = -4.10, -3.92, 5.44, 5.24
ZOOM = 14
TILE = 256


def world(lon: float, lat: float, zoom: int = ZOOM) -> tuple[float, float]:
    """Global Web Mercator pixel coordinates at `zoom`."""
    scale = TILE * 2**zoom
    x = (lon + 180.0) / 360.0 * scale
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * scale
    return x, y


ORIGIN = world(WEST, NORTH)
_CORNER = world(EAST, SOUTH)
WIDTH = math.ceil(_CORNER[0] - ORIGIN[0])
HEIGHT = math.ceil(_CORNER[1] - ORIGIN[1])


def project(lon: float, lat: float) -> tuple[float, float]:
    """Frame pixel coordinates (CSS pixels at zoom 14) of a WGS 84 point."""
    x, y = world(lon, lat)
    return x - ORIGIN[0], y - ORIGIN[1]


def unproject(x: float, y: float) -> tuple[float, float]:
    """WGS 84 (lon, lat) of frame pixel coordinates."""
    scale = TILE * 2**ZOOM
    gx, gy = x + ORIGIN[0], y + ORIGIN[1]
    lon = gx / scale * 360.0 - 180.0
    n = math.pi * (1 - 2 * gy / scale)
    lat = math.degrees(math.atan(math.sinh(n)))
    return lon, lat
