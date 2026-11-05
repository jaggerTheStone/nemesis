//! Frequency-based network: one pattern per GTFS trip, its service bands, walking
//! transfers between nearby stops and, optionally, virtual boarding points along the
//! route for continuous pickup (partie 8.1, ALGORITHMES.md section 2.1).

use crate::geo::{Grid, Point};
use crate::gtfs::Feed;

/// Network construction parameters (ALGORITHMES.md, « Paramètres de départ »).
#[derive(Debug, Clone, Copy, serde::Serialize)]
pub struct NetworkOptions {
    /// Walking speed: 4,5 km/h by default.
    pub walk_speed_mps: f64,
    /// Street distance over straight-line distance, while the OSM walking graph is not
    /// used (spike simplification; Dijkstra on OSM in I0.9).
    pub detour_factor: f64,
    /// Longest walking transfer between two stops, straight line.
    pub transfer_radius_m: f64,
    /// Longest walk from the origin or to the destination, straight line.
    pub access_radius_m: f64,
    /// Spacing of virtual boarding points along each route; `None` disables them.
    pub virtual_spacing_m: Option<f64>,
    /// Service day (AAAAMMJJ): only the trips running that day are kept.
    pub service_date: Option<u32>,
}

impl Default for NetworkOptions {
    fn default() -> Self {
        Self {
            walk_speed_mps: 4.5 / 3.6,
            detour_factor: 1.3,
            transfer_radius_m: 400.0,
            access_radius_m: 800.0,
            virtual_spacing_m: None,
            service_date: None,
        }
    }
}

/// A boarding point: a stop of the feed, or a virtual point on a route.
#[derive(Debug, Clone)]
pub struct StopNode {
    pub id: String,
    pub name: String,
    pub point: Point,
    pub is_virtual: bool,
}

/// One trip of the feed, run at the frequencies of its service bands.
#[derive(Debug, Clone)]
pub struct Pattern {
    pub trip_id: String,
    pub route_id: String,
    pub route_name: String,
    pub stops: Vec<u32>,
    /// Seconds from the first departure.
    pub arrivals: Vec<u32>,
    pub departures: Vec<u32>,
    /// (start, end, headway) of each band, seconds after midnight, for the first stop.
    pub bands: Vec<(u32, u32, u32)>,
}

impl Pattern {
    /// Headway of the vehicle passing position `pos` at `time`, if one runs then.
    #[must_use]
    pub fn headway_at(&self, pos: usize, time: u32) -> Option<u32> {
        let first_departure = time.checked_sub(self.departures[pos])?;
        self.bands
            .iter()
            .find(|(start, end, _)| *start <= first_departure && first_departure < *end)
            .map(|band| band.2)
    }
}

/// Walking leg between two points: duration and street length, both estimated.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Walk {
    pub seconds: u32,
    pub metres: u32,
}

/// The network the engine runs on.
#[derive(Debug)]
pub struct Network {
    pub stops: Vec<StopNode>,
    pub patterns: Vec<Pattern>,
    /// For each stop, the (pattern, position) pairs that serve it.
    pub stop_patterns: Vec<Vec<(u32, u32)>>,
    /// For each stop, walking transfers to nearby stops.
    pub footpaths: Vec<Vec<(u32, Walk)>>,
    pub options: NetworkOptions,
    points: Vec<Point>,
    grid: Grid,
}

/// Size of the network, for the spike measures.
#[derive(Debug, Clone, Copy, serde::Serialize)]
pub struct NetworkStats {
    pub stops: usize,
    pub virtual_stops: usize,
    pub patterns: usize,
    pub pattern_positions: usize,
    pub footpaths: usize,
}

impl Network {
    /// Builds the network of `feed`.
    #[must_use]
    pub fn build(feed: &Feed, options: NetworkOptions) -> Self {
        let mut stops: Vec<StopNode> = feed
            .stops
            .iter()
            .map(|s| StopNode {
                id: s.id.clone(),
                name: s.name.clone(),
                point: s.point,
                is_virtual: false,
            })
            .collect();
        let mut patterns = Vec::with_capacity(feed.trips.len());
        for trip in &feed.trips {
            if trip.stops.len() < 2 || trip.bands.is_empty() {
                continue;
            }
            if let Some(date) = options.service_date
                && !feed
                    .services
                    .get(&trip.service_id)
                    .is_some_and(|s| s.runs_on(date))
            {
                continue;
            }
            let mut pattern = Pattern {
                trip_id: trip.id.clone(),
                route_id: trip.route_id.clone(),
                route_name: trip.route_name.clone(),
                stops: Vec::new(),
                arrivals: Vec::new(),
                departures: Vec::new(),
                bands: trip.bands.clone(),
            };
            let shape = trip.shape_id.as_ref().and_then(|id| feed.shapes.get(id));
            let along = options.virtual_spacing_m.map(|_| {
                positions_along(
                    shape.map(Vec::as_slice),
                    trip.stops.iter().map(|s| feed.stops[s.0].point),
                )
            });
            for (index, &(stop, arrival, departure)) in trip.stops.iter().enumerate() {
                if let (Some(spacing), Some((cumulative, line)), true) =
                    (options.virtual_spacing_m, along.as_ref(), index > 0)
                {
                    let previous_departure = *pattern.departures.last().unwrap_or(&0);
                    let (from, to) = (cumulative[index - 1], cumulative[index]);
                    let gap = to - from;
                    let mut distance = from + spacing;
                    let mut serial = 0;
                    while gap > spacing * 1.5 && distance < to - spacing / 2.0 {
                        let fraction = (distance - from) / gap;
                        #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
                        let offset = previous_departure
                            + (f64::from(arrival.saturating_sub(previous_departure)) * fraction)
                                .round() as u32;
                        serial += 1;
                        let id = format!("virtuel:{}:{}:{}", trip.id, index, serial);
                        pattern
                            .stops
                            .push(u32::try_from(stops.len()).unwrap_or(u32::MAX));
                        stops.push(StopNode {
                            id,
                            name: format!(
                                "Bord de route après {}",
                                feed.stops[trip.stops[index - 1].0].name
                            ),
                            point: point_at(line, distance),
                            is_virtual: true,
                        });
                        pattern.arrivals.push(offset);
                        pattern.departures.push(offset);
                        distance += spacing;
                    }
                }
                pattern.stops.push(u32::try_from(stop).unwrap_or(u32::MAX));
                pattern.arrivals.push(arrival);
                pattern.departures.push(departure);
            }
            patterns.push(pattern);
        }

        let mut stop_patterns = vec![Vec::new(); stops.len()];
        for (p, pattern) in patterns.iter().enumerate() {
            for (pos, &stop) in pattern.stops.iter().enumerate() {
                stop_patterns[stop as usize].push((index_u32(p), index_u32(pos)));
            }
        }

        let points: Vec<Point> = stops.iter().map(|s| s.point).collect();
        let grid = Grid::new(&points, options.transfer_radius_m.max(100.0));
        let mut network = Self {
            stops,
            patterns,
            stop_patterns,
            footpaths: Vec::new(),
            options,
            points,
            grid,
        };
        network.footpaths = (0..network.stops.len())
            .map(|s| {
                let here = &network.stops[s];
                network
                    .grid
                    .within(&network.points, here.point, options.transfer_radius_m)
                    .into_iter()
                    .filter(|&(t, _)| {
                        t != s
                            && !(here.is_virtual
                                && network.stops[t].is_virtual
                                && same_trip(&here.id, &network.stops[t].id))
                    })
                    .filter(|&(t, _)| !network.stop_patterns[t].is_empty())
                    .map(|(t, d)| (index_u32(t), network.walk(d)))
                    .collect()
            })
            .collect();
        network
    }

    /// Walking duration and street length for a straight-line distance.
    #[must_use]
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    pub fn walk(&self, straight_m: f64) -> Walk {
        let metres = straight_m * self.options.detour_factor;
        Walk {
            seconds: (metres / self.options.walk_speed_mps).ceil() as u32,
            metres: metres.round() as u32,
        }
    }

    /// Served stops within `radius_m` of `point`.
    #[must_use]
    pub fn nearby(&self, point: Point, radius_m: f64) -> Vec<(usize, f64)> {
        self.grid
            .within(&self.points, point, radius_m)
            .into_iter()
            .filter(|&(s, _)| !self.stop_patterns[s].is_empty())
            .collect()
    }

    #[must_use]
    pub fn stats(&self) -> NetworkStats {
        NetworkStats {
            stops: self.stops.len(),
            virtual_stops: self.stops.iter().filter(|s| s.is_virtual).count(),
            patterns: self.patterns.len(),
            pattern_positions: self.patterns.iter().map(|p| p.stops.len()).sum(),
            footpaths: self.footpaths.iter().map(Vec::len).sum(),
        }
    }
}

fn index_u32(index: usize) -> u32 {
    u32::try_from(index).unwrap_or(u32::MAX)
}

/// Two virtual points of the same trip (« virtuel:<trip>:<stop>:<serial> », the trip id
/// may itself contain colons).
fn same_trip(a: &str, b: &str) -> bool {
    let trip = |id: &str| id.rsplitn(3, ':').nth(2).map(str::to_owned);
    trip(a) == trip(b)
}

/// Distance along the line of each stop, and the line itself (the shape when it fits
/// the stops, otherwise the straight segments between stops).
fn positions_along(
    shape: Option<&[Point]>,
    stops: impl Iterator<Item = Point>,
) -> (Vec<f64>, Vec<Point>) {
    let stops: Vec<Point> = stops.collect();
    if let Some(line) = shape.filter(|line| line.len() >= 2) {
        let mut cumulative = vec![0.0];
        for pair in line.windows(2) {
            cumulative.push(cumulative.last().unwrap_or(&0.0) + pair[0].distance_m(pair[1]));
        }
        let mut positions = Vec::with_capacity(stops.len());
        let mut start = 0;
        for stop in &stops {
            // Nearest shape vertex at or after the previous stop's: shapes run forward.
            let (best, _) = (start..line.len())
                .map(|i| (i, line[i].distance_m(*stop)))
                .fold((start, f64::INFINITY), |acc, item| {
                    if item.1 < acc.1 { item } else { acc }
                });
            positions.push(cumulative[best]);
            start = best;
        }
        let ordered = positions.windows(2).all(|w| w[1] >= w[0]);
        let close = stops
            .iter()
            .zip(&positions)
            .all(|(stop, &d)| point_on(line, &cumulative, d).distance_m(*stop) < 150.0);
        if ordered && close {
            return (positions, line.to_vec());
        }
    }
    let mut positions = vec![0.0];
    for pair in stops.windows(2) {
        positions.push(positions.last().unwrap_or(&0.0) + pair[0].distance_m(pair[1]));
    }
    (positions, stops)
}

fn point_on(line: &[Point], cumulative: &[f64], distance: f64) -> Point {
    for (i, pair) in line.windows(2).enumerate() {
        let (a, b) = (cumulative[i], cumulative[i + 1]);
        if distance <= b || i + 2 == line.len() {
            let fraction = if b > a {
                ((distance - a) / (b - a)).clamp(0.0, 1.0)
            } else {
                0.0
            };
            return pair[0].lerp(pair[1], fraction);
        }
    }
    line[0]
}

fn point_at(line: &[Point], distance: f64) -> Point {
    let mut cumulative = vec![0.0];
    for pair in line.windows(2) {
        cumulative.push(cumulative.last().unwrap_or(&0.0) + pair[0].distance_m(pair[1]));
    }
    point_on(line, &cumulative, distance)
}
