//! The `RoutingEngine` interface (partie 8.1) and its McRAPTOR implementation on a city
//! pack. The server and, later, the phone call only this interface.

use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::time::Instant;

use serde::{Deserialize, Serialize};

use crate::geo::Point;
use crate::gtfs::{Feed, GtfsError, Service, read_feed, weekday};
use crate::mcraptor::{Found, FoundLeg, Place, Search, search};
use crate::model::{FareModel, Rng, WaitModel, WaitSource, day_type, fnv1a};
use crate::network::{Network, NetworkOptions, Walk, same_trip};
use crate::options::{Fare, Simulated, select, simulate, wait_minutes};
use crate::walk::{Snap, WalkGraph};

/// Spacing of the virtual boarding points by default, metres (ADR-003): the same on the
/// server, on the command line and on the phone.
pub const DEFAULT_VIRTUAL_SPACING_M: f64 = 250.0;

/// Longest walk from the origin or to the destination, on the graph (2.1).
pub const ACCESS_M: f64 = 1_500.0;
/// Longest walking transfer between two stops, on the graph.
pub const TRANSFER_M: f64 = 500.0;
/// Longest walk shown as a journey of its own.
pub const DIRECT_M: f64 = 2_000.0;
/// Straight-line radius used where the walking graph does not reach.
pub const STRAIGHT_RADIUS_M: f64 = 800.0;
/// Monte-Carlo draws (partie 8.1).
pub const DRAWS: usize = 500;
/// Most vehicles in one journey.
pub const MAX_RIDES: u8 = 5;

/// A journey request: points, local day (AAAAMMJJ) and time (seconds after midnight).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PlanRequest {
    pub from: Point,
    pub to: Point,
    pub date: u32,
    pub time: u32,
}

/// Why a request cannot be answered.
#[derive(Debug, PartialEq, Eq)]
pub enum PlanError {
    BadDate(u32),
}

impl std::fmt::Display for PlanError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::BadDate(date) => write!(f, "date illisible : {date}"),
        }
    }
}

impl std::error::Error for PlanError {}

/// The single routing interface of the system (partie 8.1).
pub trait RoutingEngine {
    /// Options for a request, labelled and with their uncertainty.
    ///
    /// # Errors
    /// An invalid request.
    fn plan(&self, request: &PlanRequest) -> Result<PlanResponse, PlanError>;
    /// What the engine runs on.
    fn info(&self) -> &EngineInfo;
}

/// `pack.json` (data/pipelines/src/nemesis_pipelines/pack/build.py).
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct PackMeta {
    pub format: u32,
    pub city: String,
    pub network_version: String,
    pub is_fictional: bool,
    pub usage: String,
    pub gtfs: String,
    pub walk_nodes: String,
    pub walk_edges: String,
}

/// Description of the loaded pack, with its size and loading time.
#[derive(Debug, Clone, Serialize)]
pub struct EngineInfo {
    pub engine: &'static str,
    pub engine_version: &'static str,
    #[serde(flatten)]
    pub pack: PackMeta,
    pub stops: usize,
    pub virtual_stops: usize,
    pub patterns: usize,
    pub footpaths: usize,
    pub walk_nodes: usize,
    pub walk_edges: usize,
    pub stops_off_graph: usize,
    pub wait_profiles: usize,
    pub fares_known: bool,
    pub load_ms: u64,
}

/// A point of a leg.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PlaceOut {
    pub name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stop_id: Option<String>,
    pub lat: f64,
    pub lon: f64,
}

/// Wait before a ride: quantiles, regime, source (règle 1.3.2).
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct WaitOut {
    pub p50_min: u32,
    pub p80_min: u32,
    pub regime: char,
    pub source: WaitSource,
}

/// A leg of an option.
#[derive(Debug, Clone, Serialize, PartialEq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum LegOut {
    Walk {
        from: PlaceOut,
        to: PlaceOut,
        minutes: u32,
        metres: u32,
        /// « osm_walking_graph », or « straight_line » where the graph does not reach.
        source: &'static str,
    },
    Ride {
        route_id: String,
        route_name: String,
        trip_id: String,
        board: PlaceOut,
        alight: PlaceOut,
        wait: WaitOut,
        ride_minutes: u32,
        /// « gtfs_timetable »: riding times are those of the feed.
        source: &'static str,
        fare: Option<Fare>,
    },
}

/// One option of the answer.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct OptionOut {
    /// Values before rounding, for checks: p50 and p80 in seconds, fare p50, vehicles, metres.
    #[serde(skip)]
    pub exact: (u32, u32, Option<u32>, u8, u32),
    /// « cheapest », « fastest », « simplest »; several or none.
    pub labels: Vec<&'static str>,
    pub p50_min: u32,
    pub p80_min: u32,
    pub depart: String,
    pub arrive_p50: String,
    pub arrive_p80: String,
    pub transfers: u8,
    pub walk_m: u32,
    /// Sum of the fares when every one is known, else `None` (« prix inconnu »).
    pub fare: Option<Fare>,
    pub legs: Vec<LegOut>,
}

/// Answer to a request.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct PlanResponse {
    pub city: String,
    pub network_version: String,
    pub is_fictional: bool,
    pub usage: String,
    pub date: u32,
    pub time: String,
    pub day_type: &'static str,
    pub options: Vec<OptionOut>,
    pub draws: usize,
    pub seed: String,
    /// Codes: « fictional_data », « evaluation_only_data », « fares_unknown », « no_service ».
    pub notes: Vec<&'static str>,
}

/// McRAPTOR on a city pack.
pub struct McRaptorEngine {
    info: EngineInfo,
    network: Network,
    walk: WalkGraph,
    snaps: Vec<Option<Snap>>,
    node_stops: HashMap<u32, Vec<u32>>,
    waits: WaitModel,
    fares: FareModel,
    areas: HashMap<String, u32>,
    services: HashMap<String, Service>,
    names: Vec<(String, usize)>,
}

/// Lower case, without accents nor punctuation, single spaces (place search).
#[must_use]
pub fn normalize(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for c in text.to_lowercase().chars() {
        let plain = match c {
            'à' | 'â' | 'ä' | 'á' => 'a',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'î' | 'ï' | 'í' => 'i',
            'ô' | 'ö' | 'ó' => 'o',
            'ù' | 'û' | 'ü' | 'ú' => 'u',
            'ÿ' => 'y',
            'ç' => 'c',
            'œ' => {
                out.push('o');
                'e'
            }
            c if c.is_ascii_alphanumeric() => c,
            _ => ' ',
        };
        out.push(plain);
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn clock(seconds: u32) -> String {
    format!("{:02}:{:02}", seconds / 3600 % 24, seconds / 60 % 60)
}

#[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
fn graph_walk(network: &Network, metres: f64) -> Walk {
    Walk {
        seconds: (metres / network.options.walk_speed_mps).ceil() as u32,
        metres: metres.round() as u32,
        straight: false,
    }
}

impl McRaptorEngine {
    /// Loads a city pack; `virtual_spacing_m` places virtual boarding points (ADR-003).
    ///
    /// # Errors
    /// Missing or unreadable pack files.
    pub fn load(dir: &Path, virtual_spacing_m: Option<f64>) -> Result<Self, GtfsError> {
        let started = Instant::now();
        let meta_path = dir.join("pack.json");
        let text = std::fs::read_to_string(&meta_path)
            .map_err(|e| GtfsError::Io(meta_path.display().to_string(), e))?;
        let pack: PackMeta = serde_json::from_str(&text)
            .map_err(|e| GtfsError::Invalid(format!("pack.json : {e}")))?;
        let feed = read_feed(&dir.join(&pack.gtfs))?;
        let walk = WalkGraph::read(&dir.join(&pack.walk_nodes), &dir.join(&pack.walk_edges))?;
        let mut engine = Self::from_parts(pack, feed, walk, virtual_spacing_m);
        engine.info.load_ms = u64::try_from(started.elapsed().as_millis()).unwrap_or(u64::MAX);
        Ok(engine)
    }

    /// Builds the engine from a feed and a walking graph already in memory.
    #[must_use]
    pub fn from_parts(
        pack: PackMeta,
        feed: Feed,
        walk: WalkGraph,
        virtual_spacing_m: Option<f64>,
    ) -> Self {
        let started = Instant::now();
        let options = NetworkOptions {
            virtual_spacing_m,
            ..NetworkOptions::default()
        };
        let mut network = Network::build(&feed, options);

        let snaps: Vec<Option<Snap>> = network.stops.iter().map(|s| walk.snap(s.point)).collect();
        let mut node_stops: HashMap<u32, Vec<u32>> = HashMap::new();
        for (stop, snap) in snaps.iter().enumerate() {
            if let Some(snap) = snap {
                node_stops
                    .entry(snap.node)
                    .or_default()
                    .push(u32::try_from(stop).unwrap_or(u32::MAX));
            }
        }
        // Walking transfers on the graph; straight line for stops off the graph.
        let footpaths = (0..network.stops.len())
            .map(|s| {
                let here = &network.stops[s];
                let keep = |t: usize| {
                    t != s
                        && !network.stop_patterns[t].is_empty()
                        && !(here.is_virtual
                            && network.stops[t].is_virtual
                            && same_trip(&here.id, &network.stops[t].id))
                };
                match snaps[s] {
                    Some(snap) => {
                        let mut out = Vec::new();
                        for (node, metres) in walk.distances(snap, TRANSFER_M) {
                            for &t in node_stops.get(&node).into_iter().flatten() {
                                let total = metres + snaps[t as usize].map_or(0.0, |x| x.metres);
                                if keep(t as usize) && total <= TRANSFER_M {
                                    out.push((t, graph_walk(&network, total)));
                                }
                            }
                        }
                        out
                    }
                    None => network.footpaths[s]
                        .iter()
                        .copied()
                        .filter(|(t, _)| keep(*t as usize))
                        .collect(),
                }
            })
            .collect();
        network.set_footpaths(footpaths);

        let fares = FareModel::new(&feed);
        let mut areas = HashMap::new();
        for (area, _) in &feed.stop_areas {
            let next = u32::try_from(areas.len()).unwrap_or(u32::MAX);
            areas.entry(area.clone()).or_insert(next);
        }
        let index: HashMap<&str, usize> = network
            .stops
            .iter()
            .enumerate()
            .filter(|(_, s)| !s.is_virtual)
            .map(|(i, s)| (s.id.as_str(), i))
            .collect();
        let mut names: Vec<(String, usize)> = network
            .stops
            .iter()
            .enumerate()
            .filter(|(_, s)| !s.is_virtual)
            .map(|(i, s)| (normalize(&s.name), i))
            .collect();
        names.extend(
            feed.stop_aliases.iter().filter_map(|(stop, alias)| {
                index.get(stop.as_str()).map(|&i| (normalize(alias), i))
            }),
        );

        let stats = network.stats();
        let info = EngineInfo {
            engine: "nemesis-mcraptor",
            engine_version: crate::version(),
            pack,
            stops: stats.stops,
            virtual_stops: stats.virtual_stops,
            patterns: stats.patterns,
            footpaths: stats.footpaths,
            walk_nodes: walk.points.len(),
            walk_edges: walk.edge_count(),
            stops_off_graph: snaps.iter().filter(|s| s.is_none()).count(),
            wait_profiles: feed.wait_profiles.len(),
            fares_known: !fares.is_empty(),
            load_ms: u64::try_from(started.elapsed().as_millis()).unwrap_or(u64::MAX),
        };
        Self {
            info,
            network,
            walk,
            snaps,
            node_stops,
            waits: WaitModel::new(&feed.wait_profiles),
            fares,
            areas,
            services: feed.services,
            names,
        }
    }

    /// Point of a place given as « lat,lon » or by the name of a stop (or an alias).
    ///
    /// # Errors
    /// Unknown or ambiguous name.
    pub fn resolve(&self, text: &str) -> Result<(Point, String), String> {
        let parts: Vec<&str> = text.split(',').map(str::trim).collect();
        if let [lat, lon] = parts.as_slice()
            && let (Ok(lat), Ok(lon)) = (lat.parse::<f64>(), lon.parse::<f64>())
        {
            return Ok((Point::new(lat, lon), format!("{lat:.6},{lon:.6}")));
        }
        let wanted = normalize(text);
        let exact: Vec<usize> = self
            .names
            .iter()
            .filter(|(n, _)| *n == wanted)
            .map(|(_, i)| *i)
            .collect();
        let found = if exact.is_empty() {
            self.names
                .iter()
                .filter(|(n, _)| n.contains(&wanted))
                .map(|(_, i)| *i)
                .collect()
        } else {
            exact
        };
        let mut found: Vec<usize> = found
            .into_iter()
            .collect::<HashSet<_>>()
            .into_iter()
            .collect();
        found.sort_unstable();
        let Some(&first) = found.first() else {
            return Err(format!("lieu inconnu : « {text} »"));
        };
        let point = self.network.stops[first].point;
        // Stops of one name on both sides of a road, or of one station, count as one place.
        if found
            .iter()
            .all(|&i| self.network.stops[i].point.distance_m(point) <= 500.0)
        {
            #[allow(clippy::cast_precision_loss)]
            let n = found.len() as f64;
            let lat = found
                .iter()
                .map(|&i| self.network.stops[i].point.lat)
                .sum::<f64>()
                / n;
            let lon = found
                .iter()
                .map(|&i| self.network.stops[i].point.lon)
                .sum::<f64>()
                / n;
            return Ok((Point::new(lat, lon), self.network.stops[first].name.clone()));
        }
        let names: Vec<String> = found
            .iter()
            .take(5)
            .map(|&i| self.network.stops[i].name.clone())
            .collect();
        Err(format!(
            "lieu ambigu : « {text} » ({} arrêts : {}…)",
            found.len(),
            names.join(", ")
        ))
    }

    /// Stops within walking distance of `point`, and the direct walk to `other`.
    fn walks(&self, point: Point, other: Point) -> (Vec<(u32, Walk)>, Option<Walk>) {
        let mut best: HashMap<u32, Walk> = HashMap::new();
        let mut direct = None;
        if let Some(snap) = self.walk.snap(point) {
            let reached = self.walk.distances(snap, DIRECT_M);
            for (&node, &metres) in &reached {
                for &stop in self.node_stops.get(&node).into_iter().flatten() {
                    let total = metres + self.snaps[stop as usize].map_or(0.0, |s| s.metres);
                    if total <= ACCESS_M && !self.network.stop_patterns[stop as usize].is_empty() {
                        let walk = graph_walk(&self.network, total);
                        best.entry(stop)
                            .and_modify(|w| {
                                if walk.seconds < w.seconds {
                                    *w = walk
                                }
                            })
                            .or_insert(walk);
                    }
                }
            }
            if let Some(end) = self.walk.snap(other) {
                direct = reached
                    .get(&end.node)
                    .map(|m| graph_walk(&self.network, m + end.metres));
            }
        }
        // Where the graph does not reach: straight line.
        for (stop, straight) in self.network.nearby(point, STRAIGHT_RADIUS_M) {
            let stop = u32::try_from(stop).unwrap_or(u32::MAX);
            if !best.contains_key(&stop)
                && (self.snaps[stop as usize].is_none() || self.walk.snap(point).is_none())
            {
                best.insert(stop, self.network.walk(straight));
            }
        }
        if direct.is_none() {
            let straight = point.distance_m(other);
            if straight * self.network.options.detour_factor <= DIRECT_M
                && self.walk.snap(point).is_none()
            {
                direct = Some(self.network.walk(straight));
            }
        }
        let mut list: Vec<(u32, Walk)> = best.into_iter().collect();
        list.sort_unstable_by_key(|(s, _)| *s);
        (list, direct.filter(|w| f64::from(w.metres) <= DIRECT_M))
    }

    /// Pareto front of the search for `request`, before the Monte-Carlo draws.
    ///
    /// # Errors
    /// An invalid date.
    pub fn front(&self, request: &PlanRequest) -> Result<Vec<Found>, PlanError> {
        let day_type = day_type(weekday(request.date).ok_or(PlanError::BadDate(request.date))?);
        let running: HashSet<&str> = self
            .services
            .iter()
            .filter(|(_, s)| s.runs_on(request.date))
            .map(|(id, _)| id.as_str())
            .collect();
        let active: Vec<bool> = self
            .network
            .patterns
            .iter()
            .map(|p| running.contains(p.service_id.as_str()))
            .collect();
        let (access, direct) = self.walks(request.from, request.to);
        let (egress, _) = self.walks(request.to, request.from);
        let egress: HashMap<u32, Walk> = egress.into_iter().collect();

        let network = &self.network;
        let wait = |p: usize, pos: usize, t: u32| self.waits.wait(network, p, pos, t, day_type);
        let fare = |p: usize, b: usize, a: usize| {
            self.fares
                .fare(network, p, b, a)
                .map(|f| [f.p10, f.p50, f.p90])
        };
        let area = |p: usize, b: usize| {
            self.fares
                .board_area(network, p, b)
                .and_then(|a| self.areas.get(a).copied())
        };
        let found = search(&Search {
            network,
            active: &active,
            depart: request.time,
            max_rides: MAX_RIDES,
            access: &access,
            egress: &egress,
            direct,
            wait: &wait,
            fare: &fare,
            board_area: &area,
        });
        Ok(found)
    }

    fn place(&self, place: Place, request: &PlanRequest) -> PlaceOut {
        match place {
            Place::Origin => PlaceOut {
                name: "Départ".to_owned(),
                stop_id: None,
                lat: request.from.lat,
                lon: request.from.lon,
            },
            Place::Destination => PlaceOut {
                name: "Arrivée".to_owned(),
                stop_id: None,
                lat: request.to.lat,
                lon: request.to.lon,
            },
            Place::Stop(stop) => {
                let s = &self.network.stops[stop as usize];
                PlaceOut {
                    name: s.name.clone(),
                    stop_id: (!s.is_virtual).then(|| s.id.clone()),
                    lat: s.point.lat,
                    lon: s.point.lon,
                }
            }
        }
    }

    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    fn option_out(&self, option: &Simulated, request: &PlanRequest) -> OptionOut {
        let legs = option
            .found
            .legs
            .iter()
            .map(|leg| match *leg {
                FoundLeg::Walk { from, to, walk, .. } => LegOut::Walk {
                    from: self.place(from, request),
                    to: self.place(to, request),
                    minutes: walk.seconds.div_ceil(60),
                    metres: walk.metres,
                    source: if walk.straight {
                        "straight_line"
                    } else {
                        "osm_walking_graph"
                    },
                },
                FoundLeg::Ride {
                    pattern,
                    board_pos,
                    alight_pos,
                    wait,
                    start,
                    end,
                    fare,
                    ..
                } => {
                    let p = &self.network.patterns[pattern as usize];
                    let (p50, p80) = wait_minutes(&wait);
                    LegOut::Ride {
                        route_id: p.route_id.clone(),
                        route_name: p.route_name.clone(),
                        trip_id: p.trip_id.clone(),
                        board: self.place(Place::Stop(p.stops[board_pos as usize]), request),
                        alight: self.place(Place::Stop(p.stops[alight_pos as usize]), request),
                        wait: WaitOut {
                            p50_min: p50,
                            p80_min: p80,
                            regime: wait.regime,
                            source: wait.source,
                        },
                        ride_minutes: (end.saturating_sub(start) as f64 / 60.0).round() as u32,
                        source: "gtfs_timetable",
                        fare: fare.map(Fare::rounded),
                    }
                }
            })
            .collect();
        let fare = option.cost().map(|_| {
            let mut sum = [0_u32; 3];
            for leg in &option.found.legs {
                if let FoundLeg::Ride { fare: Some(f), .. } = leg {
                    for i in 0..3 {
                        sum[i] += f[i];
                    }
                }
            }
            Fare::rounded(sum)
        });
        let rides = option.rides();
        OptionOut {
            exact: (
                option.p50_s,
                option.p80_s,
                option.cost(),
                rides,
                option.walk_m(),
            ),
            labels: option.labels.clone(),
            p50_min: (f64::from(option.p50_s) / 60.0).round() as u32,
            p80_min: (f64::from(option.p80_s) / 60.0).round() as u32,
            depart: clock(request.time),
            arrive_p50: clock(request.time + option.p50_s),
            arrive_p80: clock(request.time + option.p80_s),
            transfers: rides.saturating_sub(1),
            walk_m: option.walk_m(),
            fare: if rides == 0 { None } else { fare },
            legs,
        }
    }
}

impl RoutingEngine for McRaptorEngine {
    fn info(&self) -> &EngineInfo {
        &self.info
    }

    fn plan(&self, request: &PlanRequest) -> Result<PlanResponse, PlanError> {
        let day_type = day_type(weekday(request.date).ok_or(PlanError::BadDate(request.date))?);
        let found = self.front(request)?;
        let seed = fnv1a(&format!(
            "{:.6},{:.6}|{:.6},{:.6}|{}|{}|{}",
            request.from.lat,
            request.from.lon,
            request.to.lat,
            request.to.lon,
            request.date,
            request.time,
            self.info.pack.network_version
        ));
        let mut rng = Rng::new(seed);
        let simulated: Vec<Simulated> = found
            .into_iter()
            .map(|f| {
                let (p50_s, p80_s) = simulate(&f, request.time, DRAWS, &mut rng);
                let lines = f
                    .legs
                    .iter()
                    .filter_map(|l| {
                        if let FoundLeg::Ride { pattern, .. } = l {
                            Some(*pattern)
                        } else {
                            None
                        }
                    })
                    .collect();
                Simulated {
                    found: f,
                    p50_s,
                    p80_s,
                    lines,
                    labels: Vec::new(),
                }
            })
            .collect();
        let options: Vec<OptionOut> = select(simulated)
            .iter()
            .map(|o| self.option_out(o, request))
            .collect();

        let mut notes = Vec::new();
        if self.info.pack.is_fictional {
            notes.push("fictional_data");
        }
        if self.info.pack.usage == "evaluation" {
            notes.push("evaluation_only_data");
        }
        let rides = |o: &OptionOut| o.legs.iter().any(|l| matches!(l, LegOut::Ride { .. }));
        if options.iter().any(|o| o.fare.is_none() && rides(o)) {
            notes.push("fares_unknown");
        }
        if !options.iter().any(rides) {
            notes.push("no_service");
        }
        notes.dedup();
        Ok(PlanResponse {
            city: self.info.pack.city.clone(),
            network_version: self.info.pack.network_version.clone(),
            is_fictional: self.info.pack.is_fictional,
            usage: self.info.pack.usage.clone(),
            date: request.date,
            time: clock(request.time),
            day_type,
            options,
            draws: DRAWS,
            seed: format!("{seed:016x}"),
            notes,
        })
    }
}

/// Path of the fictional pack, from this crate (tests).
#[must_use]
pub fn fixture_pack() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../../data/fixtures_fictives/pack")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn engine() -> McRaptorEngine {
        McRaptorEngine::load(&fixture_pack(), Some(250.0)).expect("pack fictif")
    }

    fn request(engine: &McRaptorEngine, from: &str, to: &str) -> PlanRequest {
        let (from, _) = engine.resolve(from).unwrap();
        let (to, _) = engine.resolve(to).unwrap();
        // A Tuesday at 07:30.
        PlanRequest {
            from,
            to,
            date: 20261110,
            time: 7 * 3600 + 1800,
        }
    }

    fn dominates(a: &OptionOut, b: &OptionOut) -> bool {
        let (ap50, ap80, acost, arides, awalk) = a.exact;
        let (bp50, bp80, bcost, brides, bwalk) = b.exact;
        let cost = match (acost, bcost) {
            (Some(x), Some(y)) => x.cmp(&y),
            (None, None) => std::cmp::Ordering::Equal,
            _ => return false,
        };
        let all = [
            ap80.cmp(&bp80),
            ap50.cmp(&bp50),
            cost,
            arides.cmp(&brides),
            awalk.cmp(&bwalk),
        ];
        all.iter().all(|o| o.is_le()) && all.iter().any(|o| o.is_lt())
    }

    #[test]
    fn plans_labelled_options_with_their_sources_on_the_fictional_pack() {
        let engine = engine();
        let info = engine.info();
        assert!(info.pack.is_fictional && info.fares_known && info.wait_profiles > 0);
        let response = engine
            .plan(&request(&engine, "Gare des Flamboyants", "Embarcadère Sud"))
            .unwrap();
        assert_eq!(response.notes, vec!["fictional_data"]);
        assert_eq!(response.day_type, "ouvrable");
        let labels: HashSet<&str> = response
            .options
            .iter()
            .flat_map(|o| o.labels.iter().copied())
            .collect();
        assert_eq!(labels, HashSet::from(["cheapest", "fastest", "simplest"]));
        for option in &response.options {
            assert!(option.p50_min <= option.p80_min);
            assert!(
                option.fare.is_some(),
                "fares are known on the fictional network"
            );
            for other in &response.options {
                assert!(!dominates(other, option), "{other:?} dominates {option:?}");
            }
            for leg in &option.legs {
                match leg {
                    LegOut::Walk { source, .. } => {
                        assert!(["osm_walking_graph", "straight_line"].contains(source))
                    }
                    LegOut::Ride { wait, source, .. } => {
                        assert_eq!(*source, "gtfs_timetable");
                        assert!(wait.p50_min <= wait.p80_min);
                    }
                }
            }
        }
        let regimes: HashSet<char> = response
            .options
            .iter()
            .flat_map(|o| o.legs.iter())
            .filter_map(|l| {
                if let LegOut::Ride { wait, .. } = l {
                    Some(wait.regime)
                } else {
                    None
                }
            })
            .collect();
        assert!(
            regimes.contains(&'A'),
            "fictional profiles carry régime A waits"
        );
    }

    #[test]
    fn the_same_request_gives_the_same_answer() {
        let engine = engine();
        let r = request(&engine, "Gare des Palmiers", "Gare de la Lagune-Sud");
        assert_eq!(engine.plan(&r).unwrap(), engine.plan(&r).unwrap());
    }

    #[test]
    fn places_are_found_by_name_or_alias_without_accents() {
        let engine = engine();
        let (point, name) = engine.resolve("gare flamboyant").unwrap();
        assert_eq!(name, "Gare des Flamboyants (fictif)");
        assert_eq!(engine.resolve("GARE DES FLAMBOYANTS").unwrap().0, point);
        assert_eq!(
            engine.resolve("2.045,-4.02").unwrap().0,
            Point::new(2.045, -4.02)
        );
        assert!(
            engine
                .resolve("Treichville")
                .unwrap_err()
                .contains("inconnu")
        );
        assert!(engine.resolve("gare").unwrap_err().contains("ambigu"));
    }

    #[test]
    fn sunday_has_its_own_service_and_no_invented_profile() {
        let engine = engine();
        let mut sunday = request(&engine, "Gare des Flamboyants", "Gare du Grand Marché");
        sunday.date = 20261108;
        let response = engine.plan(&sunday).unwrap();
        assert_eq!(response.day_type, "dimanche");
        assert!(!response.options.is_empty());
        // No Sunday profile is published (fewer than 20 contributors): waits come from headways.
        for leg in response.options.iter().flat_map(|o| o.legs.iter()) {
            if let LegOut::Ride { wait, .. } = leg {
                assert_eq!(wait.source, WaitSource::GtfsHeadway);
            }
        }
    }

    #[test]
    fn no_service_at_night_and_a_bad_date_is_refused() {
        let engine = engine();
        let mut night = request(&engine, "Gare des Flamboyants", "Embarcadère Sud");
        night.time = 23 * 3600 + 30 * 60;
        assert!(engine.plan(&night).unwrap().notes.contains(&"no_service"));
        night.date = 20261341;
        assert_eq!(
            engine.plan(&night).unwrap_err(),
            PlanError::BadDate(20261341)
        );
    }

    #[test]
    fn normalize_removes_accents_and_punctuation() {
        assert_eq!(
            normalize("Embarcadère  Sud (fictif)"),
            "embarcadere sud fictif"
        );
        assert_eq!(normalize("Œuvre-d'Art"), "oeuvre d art");
    }
}
