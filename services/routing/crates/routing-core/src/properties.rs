//! Property tests of the engine (partie 14.1, ALGORITHMES.md 2.4), on random grid cities
//! drawn from fixed seeds:
//! - no option shown is dominated by another;
//! - adding a line never worsens the best value of any criterion;
//! - going and coming back take about the same time on a symmetric network.

use std::collections::HashMap;

use crate::engine::{McRaptorEngine, PackMeta, PlanRequest, RoutingEngine};
use crate::geo::{METRES_PER_DEGREE, Point};
use crate::gtfs::{FareEstimate, Feed, Service, Stop, Trip};
use crate::mcraptor::Found;
use crate::model::Rng;
use crate::walk::WalkGraph;

const SIDE: usize = 11;
const BLOCK_M: f64 = 400.0;

fn grid_point(node: usize) -> Point {
    let (row, col) = (node / SIDE, node % SIDE);
    #[allow(clippy::cast_precision_loss)]
    Point::new(
        5.3 + row as f64 * BLOCK_M / METRES_PER_DEGREE,
        -4.0 + col as f64 * BLOCK_M / METRES_PER_DEGREE,
    )
}

fn area(node: usize) -> String {
    format!(
        "z{}{}",
        usize::from(node / SIDE >= SIDE / 2),
        usize::from(node % SIDE >= SIDE / 2)
    )
}

/// A line: grid nodes visited, and its headway.
type Line = (Vec<usize>, u32);

fn random_lines(rng: &mut Rng, count: usize) -> Vec<Line> {
    #[allow(clippy::cast_possible_truncation)]
    let pick = |rng: &mut Rng, n: usize| (rng.next_u64() % n as u64) as usize;
    (0..count)
        .map(|_| {
            let mut node = pick(rng, SIDE * SIDE);
            let mut path = vec![node];
            let length = 5 + pick(rng, 6);
            while path.len() < length {
                let (row, col) = (node / SIDE, node % SIDE);
                let moves: Vec<usize> = [
                    (row > 0).then(|| node - SIDE),
                    (row + 1 < SIDE).then(|| node + SIDE),
                    (col > 0).then(|| node - 1),
                    (col + 1 < SIDE).then(|| node + 1),
                ]
                .into_iter()
                .flatten()
                .filter(|n| !path.contains(n))
                .collect();
                if moves.is_empty() {
                    break;
                }
                node = moves[pick(rng, moves.len())];
                path.push(node);
            }
            let headway = [300, 600, 900, 1200, 1800][pick(rng, 5)];
            (path, headway)
        })
        .collect()
}

/// Feed of the lines, both directions, with fares between the four quarters of the city.
fn feed(lines: &[Line]) -> Feed {
    let mut feed = Feed::default();
    let mut index = HashMap::new();
    for (n, (path, headway)) in lines.iter().enumerate() {
        let route = format!("L{n}");
        for direction in 0..2_u8 {
            let mut sequence = path.clone();
            if direction == 1 {
                sequence.reverse();
            }
            let mut stops = Vec::new();
            let mut offset = 0;
            for &node in &sequence {
                let stop = *index.entry(node).or_insert_with(|| {
                    feed.stops.push(Stop {
                        id: format!("s{node}"),
                        name: format!("Arrêt {node}"),
                        point: grid_point(node),
                    });
                    feed.stop_areas.push((area(node), format!("s{node}")));
                    feed.stops.len() - 1
                });
                stops.push((stop, offset, offset + 20));
                offset += 20 + 96; // 400 m at 15 km/h, plus 20 s at the stop
            }
            feed.trips.push(Trip {
                id: format!("{route}-{direction}"),
                route_id: route.clone(),
                route_name: route.clone(),
                service_id: "tous".to_owned(),
                direction_id: Some(direction),
                shape_id: None,
                stops,
                bands: vec![(5 * 3600, 22 * 3600, *headway)],
            });
        }
        for a in ["z00", "z01", "z10", "z11"] {
            for b in ["z00", "z01", "z10", "z11"] {
                let p50 = if a == b { 150 } else { 250 } + 50 * u32::try_from(n % 3).unwrap_or(0);
                feed.fare_estimates.push(FareEstimate {
                    route_id: route.clone(),
                    from_area: a.to_owned(),
                    to_area: b.to_owned(),
                    condition: "normale".to_owned(),
                    p10: p50 - 50,
                    p50,
                    p90: p50 + 100,
                    confidence: "moyenne".to_owned(),
                });
            }
        }
    }
    feed.services.insert(
        "tous".to_owned(),
        Service {
            weekdays: [true; 7],
            start: 20260101,
            end: 20301231,
            added: vec![],
            removed: vec![],
        },
    );
    feed
}

fn walk_graph() -> WalkGraph {
    let points: Vec<Point> = (0..SIDE * SIDE).map(grid_point).collect();
    let mut edges = Vec::new();
    for node in 0..SIDE * SIDE {
        for next in [
            (node % SIDE + 1 < SIDE).then_some(node + 1),
            (node / SIDE + 1 < SIDE).then_some(node + SIDE),
        ]
        .into_iter()
        .flatten()
        {
            #[allow(clippy::cast_possible_truncation)]
            let metres = points[node].distance_m(points[next]) as f32;
            edges.push((
                u32::try_from(node).unwrap_or(0),
                u32::try_from(next).unwrap_or(0),
                metres,
            ));
        }
    }
    WalkGraph::new(points, &edges)
}

fn engine(lines: &[Line]) -> McRaptorEngine {
    let pack = PackMeta {
        format: 1,
        city: "grille".to_owned(),
        network_version: "test".to_owned(),
        is_fictional: true,
        usage: "produit".to_owned(),
        gtfs: String::new(),
        walk_nodes: String::new(),
        walk_edges: String::new(),
    };
    McRaptorEngine::from_parts(pack, feed(lines), walk_graph(), None)
}

fn queries(rng: &mut Rng, count: usize) -> Vec<PlanRequest> {
    #[allow(clippy::cast_possible_truncation)]
    let mut node = || (rng.next_u64() % (SIDE * SIDE) as u64) as usize;
    (0..count)
        .map(|_| PlanRequest {
            from: grid_point(node()),
            to: grid_point(node()),
            date: 20261110,
            time: 7 * 3600 + 1800,
        })
        .filter(|r| r.from.distance_m(r.to) > 1_000.0)
        .collect()
}

/// Best value of each criterion over a front: arrival, fare, walk, vehicles.
fn bests(front: &[Found]) -> (Option<u32>, Option<u32>, Option<u32>, Option<u8>) {
    (
        front.iter().map(|f| f.criteria.arrival).min(),
        front.iter().filter_map(|f| f.criteria.cost).min(),
        front.iter().map(|f| f.criteria.walk_m).min(),
        front.iter().map(|f| f.criteria.rides).min(),
    )
}

#[test]
fn no_option_shown_is_dominated() {
    let mut pairs = 0;
    for seed in 0..12 {
        let mut rng = Rng::new(seed);
        let engine = engine(&random_lines(&mut rng, 6));
        for request in queries(&mut rng, 6) {
            let options = engine.plan(&request).unwrap().options;
            pairs += options.len() * options.len().saturating_sub(1);
            for a in &options {
                for b in &options {
                    let (ap50, ap80, ac, ar, aw) = a.exact;
                    let (bp50, bp80, bc, br, bw) = b.exact;
                    let Some(cost) = (match (ac, bc) {
                        (Some(x), Some(y)) => Some(x <= y),
                        (None, None) => Some(true),
                        _ => None,
                    }) else {
                        continue;
                    };
                    let le = ap80 <= bp80 && ap50 <= bp50 && cost && ar <= br && aw <= bw;
                    let differs = (ap50, ap80, ac, ar, aw) != (bp50, bp80, bc, br, bw);
                    assert!(!(le && differs), "seed {seed}: {a:?} dominates {b:?}");
                }
            }
        }
    }
    assert!(pairs > 50, "too few options compared: {pairs}");
}

#[test]
fn adding_a_line_never_worsens_the_best_value_of_a_criterion() {
    let mut improved = 0;
    for seed in 100..112 {
        let mut rng = Rng::new(seed);
        let lines = random_lines(&mut rng, 5);
        let mut more = lines.clone();
        more.extend(random_lines(&mut rng, 1));
        let (before, after) = (engine(&lines), engine(&more));
        for request in queries(&mut rng, 6) {
            let (b, a) = (
                bests(&before.front(&request).unwrap()),
                bests(&after.front(&request).unwrap()),
            );
            let worse = |x: Option<u32>, y: Option<u32>| {
                matches!((x, y), (Some(x), Some(y)) if y > x) || (x.is_some() && y.is_none())
            };
            assert!(!worse(b.0, a.0), "seed {seed}: arrival {b:?} → {a:?}");
            assert!(!worse(b.1, a.1), "seed {seed}: fare {b:?} → {a:?}");
            assert!(!worse(b.2, a.2), "seed {seed}: walk {b:?} → {a:?}");
            assert!(
                !worse(b.3.map(u32::from), a.3.map(u32::from)),
                "seed {seed}: vehicles {b:?} → {a:?}"
            );
            improved += usize::from(a != b);
        }
    }
    assert!(
        improved > 0,
        "the added lines never changed anything: the test proves nothing"
    );
}

#[test]
fn going_and_coming_back_take_about_the_same_time() {
    let mut compared = 0;
    for seed in 200..212 {
        let mut rng = Rng::new(seed);
        let engine = engine(&random_lines(&mut rng, 7));
        for request in queries(&mut rng, 5) {
            let back = PlanRequest {
                from: request.to,
                to: request.from,
                ..request
            };
            let go = engine
                .front(&request)
                .unwrap()
                .iter()
                .map(|f| f.criteria.arrival - request.time)
                .min();
            let come = engine
                .front(&back)
                .unwrap()
                .iter()
                .map(|f| f.criteria.arrival - back.time)
                .min();
            match (go, come) {
                (Some(go), Some(come)) => {
                    let tolerance = go.max(come) / 4 + 600;
                    assert!(
                        go.abs_diff(come) <= tolerance,
                        "seed {seed}: {go} s there, {come} s back"
                    );
                    compared += 1;
                }
                (None, None) => {}
                other => panic!("seed {seed}: a way there but not back, {other:?}"),
            }
        }
    }
    assert!(compared > 30, "too few round trips compared: {compared}");
}
