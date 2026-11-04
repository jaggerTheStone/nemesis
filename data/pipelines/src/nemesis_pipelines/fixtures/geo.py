"""Small geodesic helpers (WGS 84, short distances)."""

from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_000.0


def distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in metres (haversine)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def interpolate(
    start: tuple[float, float], end: tuple[float, float], fraction: float
) -> tuple[float, float]:
    """Point at `fraction` of the straight segment (lon, lat) start → end."""
    return (
        start[0] + (end[0] - start[0]) * fraction,
        start[1] + (end[1] - start[1]) * fraction,
    )


def polygon_wkt(lon_min: float, lat_min: float, lon_max: float, lat_max: float) -> str:
    return (
        f"POLYGON(({lon_min} {lat_min},{lon_max} {lat_min},{lon_max} {lat_max},"
        f"{lon_min} {lat_max},{lon_min} {lat_min}))"
    )
