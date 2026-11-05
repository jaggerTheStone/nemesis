//! `routing spike`: measures of option B for the ADR-003 spike (I0.8).
//!
//! Loads an unzipped GTFS, builds the frequency-based network, then plans every
//! origin-destination pair of the spike at every departure time, repeating each
//! query to measure its latency. Writes the journeys and the measures as JSON.

use std::collections::BTreeMap;
use std::fs::File;
use std::io::BufWriter;
use std::path::PathBuf;
use std::time::Instant;

use routing_core::geo::Point;
use routing_core::gtfs::{ReadReport, parse_time, read_feed};
use routing_core::network::{Network, NetworkOptions, NetworkStats};
use routing_core::raptor::{Journey, Query, plan};
use routing_core::wait::{MedianRegimeB, SimulatedLive, WaitModel};
use serde::{Deserialize, Serialize};

/// Options of `routing spike`.
#[derive(Debug, PartialEq)]
pub struct SpikeArgs {
    pub gtfs: PathBuf,
    pub pairs: PathBuf,
    pub out: PathBuf,
    pub times: Vec<String>,
    pub virtual_spacing_m: Option<f64>,
    pub simulated_waits: Option<u64>,
    pub repeat: usize,
    /// Service day, AAAAMMJJ.
    pub date: Option<u32>,
}

impl SpikeArgs {
    /// Parses the arguments that follow `spike`.
    ///
    /// # Errors
    /// Unknown or incomplete arguments.
    pub fn parse(args: &[String]) -> Result<Self, String> {
        let mut values: BTreeMap<&str, &str> = BTreeMap::new();
        let mut iter = args.iter();
        while let Some(flag) = iter.next() {
            let known = [
                "--gtfs",
                "--pairs",
                "--out",
                "--times",
                "--virtual-spacing",
                "--simulated-waits",
                "--repeat",
                "--date",
            ];
            if !known.contains(&flag.as_str()) {
                return Err(format!("unknown option: {flag}"));
            }
            let value = iter.next().ok_or_else(|| format!("{flag} needs a value"))?;
            values.insert(flag.as_str(), value.as_str());
        }
        let required = |name: &str| {
            values
                .get(name)
                .map(PathBuf::from)
                .ok_or_else(|| format!("{name} is required"))
        };
        Ok(Self {
            gtfs: required("--gtfs")?,
            pairs: required("--pairs")?,
            out: required("--out")?,
            times: values
                .get("--times")
                .unwrap_or(&"06:30,11:00,18:30")
                .split(',')
                .map(str::to_owned)
                .collect(),
            virtual_spacing_m: values
                .get("--virtual-spacing")
                .map(|v| {
                    v.parse::<f64>()
                        .map_err(|e| format!("--virtual-spacing: {e}"))
                })
                .transpose()?,
            simulated_waits: values
                .get("--simulated-waits")
                .map(|v| {
                    v.parse::<u64>()
                        .map_err(|e| format!("--simulated-waits: {e}"))
                })
                .transpose()?,
            repeat: values
                .get("--repeat")
                .map_or(Ok(20), |v| {
                    v.parse::<usize>().map_err(|e| format!("--repeat: {e}"))
                })?
                .max(1),
            date: values
                .get("--date")
                .map(|v| {
                    v.replace('-', "")
                        .parse::<u32>()
                        .map_err(|e| format!("--date: {e}"))
                })
                .transpose()?,
        })
    }
}

#[derive(Debug, Deserialize)]
struct PairRow {
    pair_id: String,
    band: String,
    origin_name: String,
    origin_lat: f64,
    origin_lon: f64,
    destination_name: String,
    destination_lat: f64,
    destination_lon: f64,
}

#[derive(Debug, Serialize)]
struct Latency {
    p50_ms: f64,
    p95_ms: f64,
    max_ms: f64,
}

#[derive(Debug, Serialize)]
struct QueryResult {
    pair_id: String,
    band: String,
    origin: String,
    destination: String,
    time: String,
    latency: Latency,
    journeys: Vec<Journey>,
}

#[derive(Debug, Serialize)]
struct Report {
    engine: &'static str,
    engine_version: &'static str,
    wait_model: String,
    options: NetworkOptions,
    read_ms: f64,
    build_ms: f64,
    network: NetworkStats,
    read_report: ReadReportOut,
    peak_rss_kib: Option<u64>,
    repeat: usize,
    latency_all: Latency,
    queries_without_journey: usize,
    queries: Vec<QueryResult>,
}

#[derive(Debug, Serialize)]
struct ReadReportOut {
    stops_without_position: usize,
    stop_times_without_time: usize,
    trips_without_stop_times: usize,
    trips_without_frequencies: usize,
    trips_with_decreasing_times: usize,
}

impl From<&ReadReport> for ReadReportOut {
    fn from(r: &ReadReport) -> Self {
        Self {
            stops_without_position: r.stops_without_position,
            stop_times_without_time: r.stop_times_without_time,
            trips_without_stop_times: r.trips_without_stop_times,
            trips_without_frequencies: r.trips_without_frequencies,
            trips_with_decreasing_times: r.trips_with_decreasing_times,
        }
    }
}

fn millis(start: Instant) -> f64 {
    start.elapsed().as_secs_f64() * 1000.0
}

#[allow(
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    clippy::cast_precision_loss
)]
fn latency(mut samples: Vec<f64>) -> Latency {
    samples.sort_by(f64::total_cmp);
    let at = |q: f64| samples[((samples.len() as f64 - 1.0) * q).round() as usize];
    Latency {
        p50_ms: at(0.5),
        p95_ms: at(0.95),
        max_ms: *samples.last().unwrap_or(&0.0),
    }
}

/// Peak resident memory of this process (Linux), in KiB.
fn peak_rss_kib() -> Option<u64> {
    let status = std::fs::read_to_string("/proc/self/status").ok()?;
    status
        .lines()
        .find(|line| line.starts_with("VmHWM:"))
        .and_then(|line| line.split_whitespace().nth(1))
        .and_then(|value| value.parse().ok())
}

/// Runs the spike measures.
///
/// # Errors
/// Unreadable inputs or output.
pub fn run(args: &SpikeArgs) -> Result<(), Box<dyn std::error::Error>> {
    let started = Instant::now();
    let feed = read_feed(&args.gtfs)?;
    let read_ms = millis(started);
    let options = NetworkOptions {
        virtual_spacing_m: args.virtual_spacing_m,
        service_date: args.date,
        ..NetworkOptions::default()
    };
    let started = Instant::now();
    let network = Network::build(&feed, options);
    let build_ms = millis(started);
    let waits: Box<dyn WaitModel> = match args.simulated_waits {
        Some(seed) => Box::new(SimulatedLive { seed }),
        None => Box::new(MedianRegimeB),
    };

    let mut reader = csv::Reader::from_path(&args.pairs)?;
    let pairs: Vec<PairRow> = reader.deserialize().collect::<Result<_, _>>()?;
    let mut queries = Vec::new();
    let mut all = Vec::new();
    for pair in &pairs {
        for time in &args.times {
            let depart = parse_time(&format!("{time}:00"))
                .ok_or_else(|| format!("heure illisible : {time}"))?;
            let query = Query {
                origin: Point::new(pair.origin_lat, pair.origin_lon),
                destination: Point::new(pair.destination_lat, pair.destination_lon),
                depart,
                max_rides: 5,
            };
            let mut samples = Vec::with_capacity(args.repeat);
            let mut journeys = Vec::new();
            for _ in 0..args.repeat {
                let started = Instant::now();
                journeys = plan(&network, waits.as_ref(), &query);
                samples.push(millis(started));
            }
            all.extend_from_slice(&samples);
            queries.push(QueryResult {
                pair_id: pair.pair_id.clone(),
                band: pair.band.clone(),
                origin: pair.origin_name.clone(),
                destination: pair.destination_name.clone(),
                time: time.clone(),
                latency: latency(samples),
                journeys,
            });
        }
    }
    let report = Report {
        engine: "nemesis-raptor-frequences (spike I0.8)",
        engine_version: routing_core::version(),
        wait_model: waits.name(),
        options,
        read_ms,
        build_ms,
        network: network.stats(),
        read_report: (&feed.report).into(),
        peak_rss_kib: peak_rss_kib(),
        repeat: args.repeat,
        latency_all: latency(all),
        queries_without_journey: queries
            .iter()
            .filter(|q| q.journeys.iter().all(|j| j.rides == 0))
            .count(),
        queries,
    };
    serde_json::to_writer_pretty(BufWriter::new(File::create(&args.out)?), &report)?;
    eprintln!(
        "{} requêtes, latence p50 {:.2} ms, p95 {:.2} ms ; réseau {} arrêts ({} virtuels), {} correspondances ; mémoire max {} Kio",
        report.queries.len(),
        report.latency_all.p50_ms,
        report.latency_all.p95_ms,
        report.network.stops,
        report.network.virtual_stops,
        report.network.footpaths,
        report.peak_rss_kib.unwrap_or(0)
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(values: &[&str]) -> Vec<String> {
        values.iter().map(|v| (*v).to_owned()).collect()
    }

    #[test]
    fn parses_the_spike_options_with_defaults() {
        let parsed = SpikeArgs::parse(&args(&[
            "--gtfs", "g", "--pairs", "p.csv", "--out", "o.json",
        ]))
        .unwrap();
        assert_eq!(parsed.times, vec!["06:30", "11:00", "18:30"]);
        assert_eq!(
            (
                parsed.virtual_spacing_m,
                parsed.simulated_waits,
                parsed.repeat
            ),
            (None, None, 20)
        );
        let parsed = SpikeArgs::parse(&args(&[
            "--gtfs",
            "g",
            "--pairs",
            "p",
            "--out",
            "o",
            "--virtual-spacing",
            "250",
            "--simulated-waits",
            "7",
            "--repeat",
            "3",
        ]))
        .unwrap();
        assert_eq!(
            (
                parsed.virtual_spacing_m,
                parsed.simulated_waits,
                parsed.repeat
            ),
            (Some(250.0), Some(7), 3)
        );
        let parsed = SpikeArgs::parse(&args(&[
            "--gtfs",
            "g",
            "--pairs",
            "p",
            "--out",
            "o",
            "--date",
            "2023-06-13",
        ]))
        .unwrap();
        assert_eq!(parsed.date, Some(20230613));
    }

    #[test]
    fn rejects_incomplete_options() {
        assert!(SpikeArgs::parse(&args(&["--gtfs", "g"])).is_err());
        assert!(SpikeArgs::parse(&args(&["--gtfs"])).is_err());
        assert!(SpikeArgs::parse(&args(&["--nope", "x"])).is_err());
    }
}
