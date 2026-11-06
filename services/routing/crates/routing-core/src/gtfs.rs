//! Minimal GTFS reader for the routing spike (I0.8): the files a frequency-based
//! network needs, read from an unzipped feed directory. Values are taken as
//! published; rows that cannot be read are counted, never guessed.

use std::collections::HashMap;
use std::fs::File;
use std::path::Path;

use serde::Deserialize;

use crate::geo::Point;

/// Error while reading a feed.
#[derive(Debug)]
pub enum GtfsError {
    Io(String, std::io::Error),
    Csv(String, csv::Error),
    Invalid(String),
}

impl std::fmt::Display for GtfsError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(file, error) => write!(f, "{file}: {error}"),
            Self::Csv(file, error) => write!(f, "{file}: {error}"),
            Self::Invalid(message) => write!(f, "{message}"),
        }
    }
}

impl std::error::Error for GtfsError {}

#[derive(Debug, Deserialize)]
struct StopRow {
    stop_id: String,
    #[serde(default)]
    stop_name: String,
    stop_lat: Option<f64>,
    stop_lon: Option<f64>,
}

#[derive(Debug, Deserialize)]
struct RouteRow {
    route_id: String,
    #[serde(default)]
    route_short_name: String,
    #[serde(default)]
    route_long_name: String,
}

#[derive(Debug, Deserialize)]
struct TripRow {
    route_id: String,
    service_id: String,
    trip_id: String,
    #[serde(default)]
    shape_id: String,
    direction_id: Option<u8>,
}

#[derive(Debug, Deserialize)]
struct WaitProfileRow {
    stop_id: String,
    route_id: String,
    direction_id: u8,
    day_type: String,
    slot_start: String,
    regime: String,
    wait_p50_s: u32,
    wait_p80_s: u32,
    #[serde(default)]
    confidence: String,
}

#[derive(Debug, Deserialize)]
struct FareRow {
    route_id: String,
    from_area_id: String,
    to_area_id: String,
    condition: String,
    fare_p10: u32,
    fare_p50: u32,
    fare_p90: u32,
    #[serde(default)]
    confidence: String,
}

#[derive(Debug, Deserialize)]
struct StopAreaRow {
    area_id: String,
    stop_id: String,
}

#[derive(Debug, Deserialize)]
struct StopAliasRow {
    stop_id: String,
    alias: String,
}

/// Historical wait at a stop for a line, a direction, a day type and a 15-minute slot
/// (`ext_wait_profiles.txt`, ADR-007).
#[derive(Debug, Clone, PartialEq)]
pub struct WaitProfile {
    pub stop_id: String,
    pub route_id: String,
    pub direction_id: u8,
    pub day_type: String,
    pub slot_start: u32,
    /// « A », « B » or « C » (ALGORITHMES.md, section 1).
    pub regime: String,
    pub p50_s: u32,
    pub p80_s: u32,
    pub confidence: String,
}

/// Fare range observed on a line between two areas (`ext_fare_estimates.txt`), in XOF.
#[derive(Debug, Clone, PartialEq)]
pub struct FareEstimate {
    pub route_id: String,
    pub from_area: String,
    pub to_area: String,
    pub condition: String,
    pub p10: u32,
    pub p50: u32,
    pub p90: u32,
    pub confidence: String,
}

#[derive(Debug, Deserialize)]
struct CalendarRow {
    service_id: String,
    monday: u8,
    tuesday: u8,
    wednesday: u8,
    thursday: u8,
    friday: u8,
    saturday: u8,
    sunday: u8,
    start_date: u32,
    end_date: u32,
}

#[derive(Debug, Deserialize)]
struct CalendarDateRow {
    service_id: String,
    date: u32,
    exception_type: u8,
}

/// Days a service runs (`calendar.txt` and `calendar_dates.txt`), dates as AAAAMMJJ.
#[derive(Debug, Clone, Default)]
pub struct Service {
    /// Monday first.
    pub weekdays: [bool; 7],
    pub start: u32,
    pub end: u32,
    pub added: Vec<u32>,
    pub removed: Vec<u32>,
}

impl Service {
    /// Whether the service runs on `date` (AAAAMMJJ).
    #[must_use]
    pub fn runs_on(&self, date: u32) -> bool {
        if self.removed.contains(&date) {
            return false;
        }
        if self.added.contains(&date) {
            return true;
        }
        self.start <= date && date <= self.end && weekday(date).is_some_and(|d| self.weekdays[d])
    }
}

/// Day of the week of a AAAAMMJJ date, Monday = 0 (proleptic Gregorian calendar).
#[must_use]
pub fn weekday(date: u32) -> Option<usize> {
    let (year, month, day) = (
        i64::from(date / 10_000),
        i64::from(date / 100 % 100),
        i64::from(date % 100),
    );
    if !(1..=12).contains(&month) || !(1..=31).contains(&day) {
        return None;
    }
    // Days from 1970-01-01 (H. Hinnant, « days_from_civil »); 1970-01-01 was a Thursday.
    let y = if month <= 2 { year - 1 } else { year };
    let era = y.div_euclid(400);
    let yoe = y - era * 400;
    let doy = (153 * (month + if month > 2 { -3 } else { 9 }) + 2) / 5 + day - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    let days = era * 146_097 + doe - 719_468;
    usize::try_from((days + 3).rem_euclid(7)).ok()
}

#[derive(Debug, Deserialize)]
struct StopTimeRow {
    trip_id: String,
    stop_id: String,
    stop_sequence: u32,
    #[serde(default)]
    arrival_time: String,
    #[serde(default)]
    departure_time: String,
}

#[derive(Debug, Deserialize)]
struct FrequencyRow {
    trip_id: String,
    start_time: String,
    end_time: String,
    headway_secs: u32,
}

#[derive(Debug, Deserialize)]
struct ShapeRow {
    shape_id: String,
    shape_pt_lat: f64,
    shape_pt_lon: f64,
    shape_pt_sequence: u32,
}

/// A stop of the feed.
#[derive(Debug, Clone)]
pub struct Stop {
    pub id: String,
    pub name: String,
    pub point: Point,
}

/// A trip: its ordered stops with times relative to the first departure.
#[derive(Debug, Clone)]
pub struct Trip {
    pub id: String,
    pub route_id: String,
    pub route_name: String,
    pub service_id: String,
    pub direction_id: Option<u8>,
    pub shape_id: Option<String>,
    /// (stop index, arrival offset, departure offset) in seconds from the first departure.
    pub stops: Vec<(usize, u32, u32)>,
    /// Service bands of `frequencies.txt`: (start, end, headway), in seconds after midnight.
    pub bands: Vec<(u32, u32, u32)>,
}

/// What was read, and what could not be.
#[derive(Debug, Default, Clone)]
pub struct ReadReport {
    pub stops_without_position: usize,
    pub stop_times_without_time: usize,
    pub trips_without_stop_times: usize,
    pub trips_without_frequencies: usize,
    /// Trips whose times go backwards somewhere: kept as published, counted here.
    pub trips_with_decreasing_times: usize,
}

/// The parts of a feed used by the routing engine.
#[derive(Debug, Default)]
pub struct Feed {
    pub stops: Vec<Stop>,
    pub trips: Vec<Trip>,
    pub services: HashMap<String, Service>,
    pub shapes: HashMap<String, Vec<Point>>,
    /// Extension of the project (ADR-007), empty when the feed has none.
    pub wait_profiles: Vec<WaitProfile>,
    pub fare_estimates: Vec<FareEstimate>,
    /// (area id, stop id) of `stop_areas.txt` (GTFS-Fares v2).
    pub stop_areas: Vec<(String, String)>,
    /// (stop id, alias) of `ext_stop_aliases.txt`.
    pub stop_aliases: Vec<(String, String)>,
    pub report: ReadReport,
}

/// Parses `HH:MM:SS` (hours may exceed 23) into seconds.
#[must_use]
pub fn parse_time(value: &str) -> Option<u32> {
    let mut parts = value.trim().split(':');
    let hours: u32 = parts.next()?.parse().ok()?;
    let minutes: u32 = parts.next()?.parse().ok()?;
    let seconds: u32 = parts.next()?.parse().ok()?;
    if parts.next().is_some() || minutes > 59 || seconds > 59 {
        return None;
    }
    Some(hours * 3600 + minutes * 60 + seconds)
}

fn rows<T: for<'de> Deserialize<'de>>(
    dir: &Path,
    name: &str,
    required: bool,
) -> Result<Vec<T>, GtfsError> {
    let path = dir.join(name);
    if !path.exists() {
        return if required {
            Err(GtfsError::Invalid(format!(
                "{name} absent de {}",
                dir.display()
            )))
        } else {
            Ok(Vec::new())
        };
    }
    let file = File::open(&path).map_err(|e| GtfsError::Io(name.to_owned(), e))?;
    let mut reader = csv::ReaderBuilder::new()
        .trim(csv::Trim::All)
        .from_reader(file);
    let mut out = Vec::new();
    for row in reader.deserialize() {
        out.push(row.map_err(|e| GtfsError::Csv(name.to_owned(), e))?);
    }
    Ok(out)
}

/// Reads the feed in `dir` (an unzipped GTFS).
///
/// # Errors
/// A required file is missing or a row does not parse.
pub fn read_feed(dir: &Path) -> Result<Feed, GtfsError> {
    let mut feed = Feed::default();
    let mut stop_index = HashMap::new();
    for row in rows::<StopRow>(dir, "stops.txt", true)? {
        let (Some(lat), Some(lon)) = (row.stop_lat, row.stop_lon) else {
            feed.report.stops_without_position += 1;
            continue;
        };
        stop_index.insert(row.stop_id.clone(), feed.stops.len());
        feed.stops.push(Stop {
            id: row.stop_id,
            name: row.stop_name,
            point: Point::new(lat, lon),
        });
    }

    let routes: HashMap<String, String> = rows::<RouteRow>(dir, "routes.txt", true)?
        .into_iter()
        .map(|r| {
            let name = if r.route_short_name.is_empty() {
                r.route_long_name
            } else {
                r.route_short_name
            };
            (r.route_id, name)
        })
        .collect();

    // (stop_sequence, stop index, arrival, departure) for each trip.
    type TimedStop = (u32, usize, Option<u32>, Option<u32>);
    let mut times: HashMap<String, Vec<TimedStop>> = HashMap::new();
    for row in rows::<StopTimeRow>(dir, "stop_times.txt", true)? {
        let Some(&stop) = stop_index.get(&row.stop_id) else {
            continue;
        };
        let arrival = parse_time(&row.arrival_time);
        let departure = parse_time(&row.departure_time).or(arrival);
        times.entry(row.trip_id).or_default().push((
            row.stop_sequence,
            stop,
            arrival.or(departure),
            departure,
        ));
    }

    let mut bands: HashMap<String, Vec<(u32, u32, u32)>> = HashMap::new();
    for row in rows::<FrequencyRow>(dir, "frequencies.txt", false)? {
        if let (Some(start), Some(end)) = (parse_time(&row.start_time), parse_time(&row.end_time))
            && row.headway_secs > 0
            && end > start
        {
            bands
                .entry(row.trip_id)
                .or_default()
                .push((start, end, row.headway_secs));
        }
    }

    for row in rows::<TripRow>(dir, "trips.txt", true)? {
        let Some(mut sequence) = times.remove(&row.trip_id) else {
            feed.report.trips_without_stop_times += 1;
            continue;
        };
        sequence.sort_by_key(|entry| entry.0);
        // Offsets from the first departure; untimed intermediate stops are interpolated
        // between their timed neighbours (GTFS allows untimed stops; none are guessed).
        let Some(first) = sequence.first().and_then(|e| e.3) else {
            feed.report.stop_times_without_time += sequence.len();
            continue;
        };
        let mut stops = Vec::with_capacity(sequence.len());
        let mut last = 0;
        for (index, &(_, stop, arrival, departure)) in sequence.iter().enumerate() {
            let arrival = match arrival {
                Some(time) => time.saturating_sub(first),
                None => {
                    feed.report.stop_times_without_time += 1;
                    let next = sequence[index..]
                        .iter()
                        .find_map(|e| e.2)
                        .map(|t| t.saturating_sub(first));
                    next.map_or(last, |n| last + (n.saturating_sub(last)) / 2)
                }
            };
            let departure = departure
                .map_or(arrival, |t| t.saturating_sub(first))
                .max(arrival);
            last = departure;
            stops.push((stop, arrival, departure));
        }
        if stops.windows(2).any(|w| w[1].1 < w[0].2) {
            feed.report.trips_with_decreasing_times += 1;
        }
        let trip_bands = bands.remove(&row.trip_id).unwrap_or_default();
        if trip_bands.is_empty() {
            feed.report.trips_without_frequencies += 1;
        }
        let route_name = routes.get(&row.route_id).cloned().unwrap_or_default();
        feed.trips.push(Trip {
            id: row.trip_id,
            route_id: row.route_id,
            route_name,
            service_id: row.service_id,
            direction_id: row.direction_id,
            shape_id: (!row.shape_id.is_empty()).then_some(row.shape_id),
            stops,
            bands: trip_bands,
        });
    }

    for row in rows::<CalendarRow>(dir, "calendar.txt", false)? {
        let days = [
            row.monday,
            row.tuesday,
            row.wednesday,
            row.thursday,
            row.friday,
            row.saturday,
            row.sunday,
        ];
        let service = feed.services.entry(row.service_id).or_default();
        service.weekdays = days.map(|d| d == 1);
        service.start = row.start_date;
        service.end = row.end_date;
    }
    for row in rows::<CalendarDateRow>(dir, "calendar_dates.txt", false)? {
        let service = feed.services.entry(row.service_id).or_default();
        match row.exception_type {
            1 => service.added.push(row.date),
            2 => service.removed.push(row.date),
            _ => {}
        }
    }

    let mut shapes: HashMap<String, Vec<(u32, Point)>> = HashMap::new();
    for row in rows::<ShapeRow>(dir, "shapes.txt", false)? {
        shapes.entry(row.shape_id).or_default().push((
            row.shape_pt_sequence,
            Point::new(row.shape_pt_lat, row.shape_pt_lon),
        ));
    }
    feed.shapes = shapes
        .into_iter()
        .map(|(id, mut points)| {
            points.sort_by_key(|p| p.0);
            (id, points.into_iter().map(|p| p.1).collect())
        })
        .collect();
    for row in rows::<WaitProfileRow>(dir, "ext_wait_profiles.txt", false)? {
        let Some(slot_start) = parse_time(&row.slot_start) else {
            continue;
        };
        feed.wait_profiles.push(WaitProfile {
            stop_id: row.stop_id,
            route_id: row.route_id,
            direction_id: row.direction_id,
            day_type: row.day_type,
            slot_start,
            regime: row.regime,
            p50_s: row.wait_p50_s,
            p80_s: row.wait_p80_s.max(row.wait_p50_s),
            confidence: row.confidence,
        });
    }
    for row in rows::<FareRow>(dir, "ext_fare_estimates.txt", false)? {
        feed.fare_estimates.push(FareEstimate {
            route_id: row.route_id,
            from_area: row.from_area_id,
            to_area: row.to_area_id,
            condition: row.condition,
            p10: row.fare_p10,
            p50: row.fare_p50,
            p90: row.fare_p90,
            confidence: row.confidence,
        });
    }
    feed.stop_areas = rows::<StopAreaRow>(dir, "stop_areas.txt", false)?
        .into_iter()
        .map(|r| (r.area_id, r.stop_id))
        .collect();
    feed.stop_aliases = rows::<StopAliasRow>(dir, "ext_stop_aliases.txt", false)?
        .into_iter()
        .map(|r| (r.stop_id, r.alias))
        .collect();
    Ok(feed)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn computes_weekdays() {
        assert_eq!(weekday(20230613), Some(1)); // a Tuesday
        assert_eq!(weekday(20261108), Some(6)); // a Sunday
        assert_eq!(weekday(20000229), Some(1));
        assert_eq!(weekday(20261301), None);
    }

    #[test]
    fn services_follow_calendar_and_exceptions() {
        let service = Service {
            weekdays: [true, true, true, true, true, false, false],
            start: 20230101,
            end: 20231231,
            added: vec![20230617],
            removed: vec![20230613],
        };
        assert!(service.runs_on(20230614));
        assert!(!service.runs_on(20230613));
        assert!(service.runs_on(20230617));
        assert!(!service.runs_on(20230618));
        assert!(!service.runs_on(20240102));
    }

    #[test]
    fn parses_gtfs_times_beyond_midnight() {
        assert_eq!(parse_time("06:30:00"), Some(23_400));
        assert_eq!(parse_time("25:00:01"), Some(90_001));
        assert_eq!(parse_time("6:5"), None);
        assert_eq!(parse_time("06:61:00"), None);
    }
}
