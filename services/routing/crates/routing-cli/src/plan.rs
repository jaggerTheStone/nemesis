//! `routing plan` and `routing bench` (I0.9): the engine on a city pack.

use std::collections::BTreeMap;
use std::path::PathBuf;
use std::time::Instant;

use routing_core::engine::{McRaptorEngine, PlanRequest, RoutingEngine};
use routing_core::geo::Point;
use routing_core::gtfs::parse_time;
use serde::{Deserialize, Serialize};

/// Spacing of the virtual boarding points by default (ADR-003).
pub const DEFAULT_VIRTUAL_SPACING_M: f64 = 250.0;

fn options(args: &[String], known: &[&str]) -> Result<BTreeMap<String, String>, String> {
    let mut values = BTreeMap::new();
    let mut iter = args.iter();
    while let Some(flag) = iter.next() {
        if !known.contains(&flag.as_str()) {
            return Err(format!("unknown option: {flag}"));
        }
        let value = iter.next().ok_or_else(|| format!("{flag} needs a value"))?;
        values.insert(flag.clone(), value.clone());
    }
    Ok(values)
}

fn required(values: &BTreeMap<String, String>, name: &str) -> Result<String, String> {
    values
        .get(name)
        .cloned()
        .ok_or_else(|| format!("{name} is required"))
}

fn spacing(values: &BTreeMap<String, String>) -> Result<Option<f64>, String> {
    let spacing = values
        .get("--virtual-spacing")
        .map_or(Ok(DEFAULT_VIRTUAL_SPACING_M), |v| {
            v.parse::<f64>()
                .map_err(|e| format!("--virtual-spacing: {e}"))
        })?;
    Ok((spacing > 0.0).then_some(spacing))
}

/// « AAAA-MM-JJTHH:MM » → (AAAAMMJJ, seconds).
///
/// # Errors
/// Any other shape.
pub fn parse_at(value: &str) -> Result<(u32, u32), String> {
    let (date, time) = value
        .split_once('T')
        .ok_or_else(|| format!("--at attend AAAA-MM-JJTHH:MM : {value}"))?;
    let date: u32 = date
        .replace('-', "")
        .parse()
        .map_err(|_| format!("date illisible : {date}"))?;
    let time = parse_time(&format!("{time}:00"))
        .or_else(|| parse_time(time))
        .ok_or_else(|| format!("heure illisible : {time}"))?;
    Ok((date, time))
}

/// Options of `routing plan`.
#[derive(Debug, PartialEq)]
pub struct PlanArgs {
    pub from: String,
    pub to: String,
    pub at: (u32, u32),
    pub data: PathBuf,
    pub virtual_spacing_m: Option<f64>,
}

impl PlanArgs {
    /// # Errors
    /// Unknown or missing options.
    pub fn parse(args: &[String]) -> Result<Self, String> {
        let v = options(
            args,
            &["--from", "--to", "--at", "--data", "--virtual-spacing"],
        )?;
        Ok(Self {
            from: required(&v, "--from")?,
            to: required(&v, "--to")?,
            at: parse_at(&required(&v, "--at")?)?,
            data: PathBuf::from(required(&v, "--data")?),
            virtual_spacing_m: spacing(&v)?,
        })
    }
}

#[derive(Serialize)]
struct PlanOutput<'a> {
    engine: &'a routing_core::engine::EngineInfo,
    from: String,
    to: String,
    computed_ms: f64,
    #[serde(flatten)]
    response: routing_core::engine::PlanResponse,
}

/// # Errors
/// Unreadable pack, unknown place or invalid request.
pub fn run_plan(args: &PlanArgs) -> Result<(), Box<dyn std::error::Error>> {
    let engine = McRaptorEngine::load(&args.data, args.virtual_spacing_m)?;
    let (from, from_name) = engine.resolve(&args.from)?;
    let (to, to_name) = engine.resolve(&args.to)?;
    let started = Instant::now();
    let response = engine.plan(&PlanRequest {
        from,
        to,
        date: args.at.0,
        time: args.at.1,
    })?;
    let output = PlanOutput {
        engine: engine.info(),
        from: from_name,
        to: to_name,
        computed_ms: started.elapsed().as_secs_f64() * 1000.0,
        response,
    };
    println!("{}", serde_json::to_string_pretty(&output)?);
    Ok(())
}

/// Options of `routing bench`.
#[derive(Debug, PartialEq)]
pub struct BenchArgs {
    pub data: PathBuf,
    pub pairs: PathBuf,
    pub date: u32,
    pub times: Vec<String>,
    pub out: PathBuf,
    pub virtual_spacing_m: Option<f64>,
}

impl BenchArgs {
    /// # Errors
    /// Unknown or missing options.
    pub fn parse(args: &[String]) -> Result<Self, String> {
        let v = options(
            args,
            &[
                "--data",
                "--pairs",
                "--date",
                "--times",
                "--out",
                "--virtual-spacing",
            ],
        )?;
        Ok(Self {
            data: PathBuf::from(required(&v, "--data")?),
            pairs: PathBuf::from(required(&v, "--pairs")?),
            date: required(&v, "--date")?
                .replace('-', "")
                .parse()
                .map_err(|_| "--date: AAAA-MM-JJ".to_owned())?,
            times: v
                .get("--times")
                .map_or("06:30,11:00,18:30", String::as_str)
                .split(',')
                .map(str::to_owned)
                .collect(),
            out: PathBuf::from(required(&v, "--out")?),
            virtual_spacing_m: spacing(&v)?,
        })
    }
}

#[derive(Deserialize)]
struct PairRow {
    pair_id: String,
    origin_lat: f64,
    origin_lon: f64,
    destination_lat: f64,
    destination_lon: f64,
}

#[derive(Serialize)]
struct BenchQuery {
    pair_id: String,
    time: String,
    ms: f64,
    options: usize,
    labels: Vec<Vec<&'static str>>,
    best_p50_min: Option<u32>,
    best_p80_min: Option<u32>,
    notes: Vec<&'static str>,
}

#[derive(Serialize)]
struct BenchReport<'a> {
    engine: &'a routing_core::engine::EngineInfo,
    queries: usize,
    without_ride: usize,
    latency_p50_ms: f64,
    latency_p95_ms: f64,
    latency_max_ms: f64,
    results: Vec<BenchQuery>,
}

/// # Errors
/// Unreadable inputs.
#[allow(
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss
)]
pub fn run_bench(args: &BenchArgs) -> Result<(), Box<dyn std::error::Error>> {
    let engine = McRaptorEngine::load(&args.data, args.virtual_spacing_m)?;
    let pairs: Vec<PairRow> = csv::Reader::from_path(&args.pairs)?
        .deserialize()
        .collect::<Result<_, _>>()?;
    let mut results = Vec::new();
    for pair in &pairs {
        for time in &args.times {
            let (_, seconds) = parse_at(&format!("2000-01-01T{time}"))?;
            let request = PlanRequest {
                from: Point::new(pair.origin_lat, pair.origin_lon),
                to: Point::new(pair.destination_lat, pair.destination_lon),
                date: args.date,
                time: seconds,
            };
            let started = Instant::now();
            let response = engine.plan(&request)?;
            let ms = started.elapsed().as_secs_f64() * 1000.0;
            results.push(BenchQuery {
                pair_id: pair.pair_id.clone(),
                time: time.clone(),
                ms,
                options: response.options.len(),
                labels: response.options.iter().map(|o| o.labels.clone()).collect(),
                best_p50_min: response.options.iter().map(|o| o.p50_min).min(),
                best_p80_min: response.options.iter().map(|o| o.p80_min).min(),
                notes: response.notes,
            });
        }
    }
    let mut times: Vec<f64> = results.iter().map(|r| r.ms).collect();
    times.sort_by(f64::total_cmp);
    let at = |q: f64| {
        times
            .get(((times.len().max(1) - 1) as f64 * q).round() as usize)
            .copied()
            .unwrap_or(0.0)
    };
    let report = BenchReport {
        engine: engine.info(),
        queries: results.len(),
        without_ride: results
            .iter()
            .filter(|r| r.notes.contains(&"no_service"))
            .count(),
        latency_p50_ms: at(0.5),
        latency_p95_ms: at(0.95),
        latency_max_ms: times.last().copied().unwrap_or(0.0),
        results,
    };
    serde_json::to_writer_pretty(std::fs::File::create(&args.out)?, &report)?;
    eprintln!(
        "{} requêtes : latence p50 {:.1} ms, p95 {:.1} ms, max {:.1} ms ; {} sans véhicule ; chargement du pack {} ms",
        report.queries,
        report.latency_p50_ms,
        report.latency_p95_ms,
        report.latency_max_ms,
        report.without_ride,
        report.engine.load_ms
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
    fn parses_plan_options() {
        let parsed = PlanArgs::parse(&args(&[
            "--from",
            "5.3,-4.0",
            "--to",
            "Gare des Palmiers",
            "--at",
            "2026-11-10T07:30",
            "--data",
            "pack",
        ]))
        .unwrap();
        assert_eq!(parsed.at, (20261110, 27000));
        assert_eq!(parsed.virtual_spacing_m, Some(250.0));
        let no_virtual = PlanArgs::parse(&args(&[
            "--from",
            "a",
            "--to",
            "b",
            "--at",
            "2026-11-10T07:30",
            "--data",
            "p",
            "--virtual-spacing",
            "0",
        ]))
        .unwrap();
        assert_eq!(no_virtual.virtual_spacing_m, None);
        assert!(PlanArgs::parse(&args(&["--from", "a"])).is_err());
        assert!(parse_at("2026-11-10 07:30").is_err());
    }
}
