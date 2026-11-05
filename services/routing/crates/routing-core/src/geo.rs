//! Short-distance geometry on WGS 84 coordinates.

/// Mean Earth radius in metres.
const EARTH_RADIUS_M: f64 = 6_371_000.0;
/// Metres per degree of latitude.
pub const METRES_PER_DEGREE: f64 = 111_320.0;

/// A point in degrees.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Point {
    pub lat: f64,
    pub lon: f64,
}

impl Point {
    #[must_use]
    pub const fn new(lat: f64, lon: f64) -> Self {
        Self { lat, lon }
    }

    /// Great-circle distance in metres (haversine).
    #[must_use]
    pub fn distance_m(self, other: Self) -> f64 {
        let (p1, p2) = (self.lat.to_radians(), other.lat.to_radians());
        let dp = p2 - p1;
        let dl = (other.lon - self.lon).to_radians();
        let a = (dp / 2.0).sin().powi(2) + p1.cos() * p2.cos() * (dl / 2.0).sin().powi(2);
        2.0 * EARTH_RADIUS_M * a.sqrt().asin()
    }

    /// Point at `fraction` of the straight segment self → other.
    #[must_use]
    pub fn lerp(self, other: Self, fraction: f64) -> Self {
        Self::new(
            self.lat + (other.lat - self.lat) * fraction,
            self.lon + (other.lon - self.lon) * fraction,
        )
    }
}

/// Uniform grid of points, for « every point within r metres » queries.
#[derive(Debug)]
pub struct Grid {
    cell_deg: f64,
    cells: std::collections::HashMap<(i32, i32), Vec<usize>>,
}

impl Grid {
    /// Builds a grid whose cells are about `cell_m` metres high.
    #[must_use]
    pub fn new(points: &[Point], cell_m: f64) -> Self {
        let cell_deg = cell_m / METRES_PER_DEGREE;
        let mut cells: std::collections::HashMap<(i32, i32), Vec<usize>> =
            std::collections::HashMap::new();
        for (index, point) in points.iter().enumerate() {
            cells
                .entry(Self::key(*point, cell_deg))
                .or_default()
                .push(index);
        }
        Self { cell_deg, cells }
    }

    #[allow(clippy::cast_possible_truncation)]
    fn key(point: Point, cell_deg: f64) -> (i32, i32) {
        (
            (point.lat / cell_deg).floor() as i32,
            (point.lon / cell_deg).floor() as i32,
        )
    }

    /// Indices of the points within `radius_m` of `center`, with their distance.
    #[must_use]
    #[allow(clippy::cast_possible_truncation)]
    pub fn within(&self, points: &[Point], center: Point, radius_m: f64) -> Vec<(usize, f64)> {
        // Longitude degrees shrink with latitude: widen the search accordingly.
        let lat_cells = (radius_m / METRES_PER_DEGREE / self.cell_deg).ceil() as i32;
        let lon_cells =
            (f64::from(lat_cells) / center.lat.to_radians().cos().max(0.1)).ceil() as i32;
        let (row, col) = Self::key(center, self.cell_deg);
        let mut found = Vec::new();
        for dr in -lat_cells..=lat_cells {
            for dc in -lon_cells..=lon_cells {
                if let Some(indices) = self.cells.get(&(row + dr, col + dc)) {
                    for &index in indices {
                        let distance = center.distance_m(points[index]);
                        if distance <= radius_m {
                            found.push((index, distance));
                        }
                    }
                }
            }
        }
        found
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn one_degree_of_latitude_is_about_111_km() {
        let d = Point::new(5.0, -4.0).distance_m(Point::new(6.0, -4.0));
        assert!((d - 111_195.0).abs() < 50.0, "{d}");
    }

    #[test]
    fn grid_finds_exactly_the_points_within_the_radius() {
        let points: Vec<Point> = (0..200)
            .map(|i| {
                Point::new(
                    5.3 + f64::from(i) * 0.0005,
                    -4.0 + f64::from(i % 7) * 0.0007,
                )
            })
            .collect();
        let grid = Grid::new(&points, 250.0);
        let center = Point::new(5.33, -3.998);
        let mut found: Vec<usize> = grid
            .within(&points, center, 400.0)
            .into_iter()
            .map(|f| f.0)
            .collect();
        found.sort_unstable();
        let expected: Vec<usize> = (0..points.len())
            .filter(|&i| center.distance_m(points[i]) <= 400.0)
            .collect();
        assert_eq!(found, expected);
        assert!(!expected.is_empty());
    }
}
