//! RAPTOR on a frequency-based network (spike I0.8, ADR-003 option B).
//!
//! Round k finds the earliest arrivals with k rides. Boarding costs the wait given
//! by the [`WaitModel`] at the stop and time of boarding: the live wait enters the
//! search itself, instead of re-scoring candidates found without it. Each round that
//! improves the arrival at the destination yields one journey: together they form
//! the Pareto front « arrival time × number of rides ». The full McRAPTOR (cost,
//! walking, p80) comes in I0.9.

use std::collections::HashMap;

use serde::Serialize;

use crate::geo::Point;
use crate::network::{Network, Walk};
use crate::wait::WaitModel;

const UNREACHED: u32 = u32::MAX;
/// Longest walk accepted as a journey on its own, straight line.
pub const DIRECT_WALK_M: f64 = 2_000.0;

/// A journey request.
#[derive(Debug, Clone, Copy)]
pub struct Query {
    pub origin: Point,
    pub destination: Point,
    /// Departure, in seconds after midnight.
    pub depart: u32,
    /// Most vehicles in one journey (rides), so at most `max_rides - 1` transfers.
    pub max_rides: usize,
}

/// One end of a leg.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct Place {
    /// GTFS stop id, `virtuel:…` for a virtual boarding point, empty for the
    /// origin or the destination.
    pub stop_id: String,
    pub name: String,
    pub lat: f64,
    pub lon: f64,
}

/// A step of a journey.
#[derive(Debug, Clone, Serialize, PartialEq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Leg {
    Walk {
        from: Place,
        to: Place,
        start: u32,
        end: u32,
        metres: u32,
    },
    Ride {
        trip_id: String,
        route_id: String,
        route_name: String,
        board: Place,
        alight: Place,
        /// Arrival at the boarding stop; the wait follows.
        at_stop: u32,
        wait: u32,
        start: u32,
        end: u32,
    },
}

/// A complete journey.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct Journey {
    pub depart: u32,
    pub arrive: u32,
    pub rides: usize,
    pub walk_metres: u32,
    pub wait_seconds: u32,
    pub legs: Vec<Leg>,
}

#[derive(Debug, Clone, Copy)]
enum Label {
    None,
    Access(Walk),
    /// Arrival `end` by a vehicle boarded at `board_pos` in round `round`.
    Ride {
        round: u32,
        pattern: u32,
        board_pos: u32,
        alight_pos: u32,
        at_stop: u32,
        wait: u32,
        end: u32,
    },
    /// Arrival `end` on foot from `from`, itself reached by a vehicle in round `round`.
    Walk {
        round: u32,
        from: u32,
        walk: Walk,
        end: u32,
    },
}

fn place(network: &Network, stop: u32) -> Place {
    let node = &network.stops[stop as usize];
    Place {
        stop_id: node.id.clone(),
        name: node.name.clone(),
        lat: node.point.lat,
        lon: node.point.lon,
    }
}

fn endpoint(point: Point, name: &str) -> Place {
    Place {
        stop_id: String::new(),
        name: name.to_owned(),
        lat: point.lat,
        lon: point.lon,
    }
}

/// Plans `query` on `network`; journeys are sorted by number of rides.
#[must_use]
pub fn plan(network: &Network, waits: &dyn WaitModel, query: &Query) -> Vec<Journey> {
    let stop_count = network.stops.len();
    let rounds = query.max_rides + 1;
    let mut tau = vec![vec![UNREACHED; stop_count]; rounds];
    let mut labels = vec![vec![Label::None; stop_count]; rounds];
    // Arrivals by a vehicle in each round, kept apart from walking ones: transfers on
    // foot leave only from these, so a journey never chains two walks, and every time
    // announced is the time of the steps reconstructed.
    let mut ride_labels = vec![vec![Label::None; stop_count]; rounds];
    let mut best = vec![UNREACHED; stop_count];
    let mut journeys = Vec::new();

    let direct = query.origin.distance_m(query.destination);
    let mut target_best = UNREACHED;
    if direct <= DIRECT_WALK_M {
        let walk = network.walk(direct);
        target_best = query.depart + walk.seconds;
        journeys.push(Journey {
            depart: query.depart,
            arrive: target_best,
            rides: 0,
            walk_metres: walk.metres,
            wait_seconds: 0,
            legs: vec![Leg::Walk {
                from: endpoint(query.origin, "Départ"),
                to: endpoint(query.destination, "Arrivée"),
                start: query.depart,
                end: target_best,
                metres: walk.metres,
            }],
        });
    }

    let radius = network.options.access_radius_m;
    let mut marked: Vec<u32> = Vec::new();
    for (stop, distance) in network.nearby(query.origin, radius) {
        let walk = network.walk(distance);
        let arrival = query.depart + walk.seconds;
        if arrival < tau[0][stop] {
            tau[0][stop] = arrival;
            best[stop] = arrival;
            labels[0][stop] = Label::Access(walk);
            marked.push(u32::try_from(stop).unwrap_or(u32::MAX));
        }
    }
    let egress: Vec<(usize, Walk)> = network
        .nearby(query.destination, radius)
        .into_iter()
        .map(|(stop, distance)| (stop, network.walk(distance)))
        .collect();

    let mut in_marked = vec![false; stop_count];
    for k in 1..rounds {
        let (previous, current) = tau.split_at_mut(k);
        let (previous, current) = (&previous[k - 1], &mut current[0]);
        current.copy_from_slice(previous);
        let (label_prev, label_cur) = labels.split_at_mut(k);
        label_cur[0].copy_from_slice(&label_prev[k - 1]);
        let label_cur = &mut label_cur[0];

        // Patterns to scan, from the earliest marked position.
        let mut queue: HashMap<u32, u32> = HashMap::new();
        for &stop in &marked {
            for &(pattern, pos) in &network.stop_patterns[stop as usize] {
                queue
                    .entry(pattern)
                    .and_modify(|p| *p = (*p).min(pos))
                    .or_insert(pos);
            }
        }
        let mut improved: Vec<u32> = Vec::new();
        let round = u32::try_from(k).unwrap_or(u32::MAX);
        for (&p, &start) in &queue {
            let pattern = &network.patterns[p as usize];
            // Boarded vehicle: (boarding position, departure there, arrival at stop, wait).
            let mut boarded: Option<(usize, u32, u32, u32)> = None;
            for pos in start as usize..pattern.stops.len() {
                let stop = pattern.stops[pos] as usize;
                if let Some((board_pos, departure, at_stop, wait)) = boarded {
                    let arrival = departure
                        + pattern.arrivals[pos].saturating_sub(pattern.departures[board_pos]);
                    if arrival < best[stop].min(target_best) && arrival < current[stop] {
                        current[stop] = arrival;
                        best[stop] = arrival;
                        let label = Label::Ride {
                            round,
                            pattern: p,
                            board_pos: u32::try_from(board_pos).unwrap_or(u32::MAX),
                            alight_pos: u32::try_from(pos).unwrap_or(u32::MAX),
                            at_stop,
                            wait,
                            end: arrival,
                        };
                        label_cur[stop] = label;
                        ride_labels[k][stop] = label;
                        if !in_marked[stop] {
                            in_marked[stop] = true;
                            improved.push(u32::try_from(stop).unwrap_or(u32::MAX));
                        }
                    }
                }
                let reached = previous[stop];
                if reached == UNREACHED {
                    continue;
                }
                if let Some(wait) = waits.wait_s(network, p as usize, pos, reached) {
                    let departure = reached + wait;
                    let current_departure = boarded.map(|(b, d, _, _)| {
                        d + pattern.departures[pos].saturating_sub(pattern.departures[b])
                    });
                    if current_departure.is_none_or(|d| departure < d) {
                        boarded = Some((pos, departure, reached, wait));
                    }
                }
            }
        }

        // Walking transfers from the stops a vehicle reached in this round.
        let mut walked: Vec<u32> = Vec::new();
        for &stop in &improved {
            let Label::Ride { end: arrival, .. } = ride_labels[k][stop as usize] else {
                continue;
            };
            for &(next, walk) in &network.footpaths[stop as usize] {
                let next = next as usize;
                let at = arrival + walk.seconds;
                if at < best[next].min(target_best) && at < current[next] {
                    current[next] = at;
                    best[next] = at;
                    label_cur[next] = Label::Walk {
                        round,
                        from: stop,
                        walk,
                        end: at,
                    };
                    if !in_marked[next] {
                        in_marked[next] = true;
                        walked.push(u32::try_from(next).unwrap_or(u32::MAX));
                    }
                }
            }
        }
        marked = improved;
        marked.extend(walked);
        for &stop in &marked {
            in_marked[stop as usize] = false;
        }

        // Destination: one journey per round that improves the arrival.
        let arrival = egress
            .iter()
            .filter_map(|&(stop, walk)| match ride_labels[k][stop] {
                Label::Ride { end, .. } => Some((end + walk.seconds, stop, walk)),
                _ => None,
            })
            .min_by_key(|item| item.0);
        if let Some((at, stop, walk)) = arrival
            && at < target_best
        {
            target_best = at;
            journeys.push(reconstruct(
                network,
                &labels,
                &ride_labels,
                k,
                stop,
                walk,
                query,
                at,
            ));
        }
        if marked.is_empty() {
            break;
        }
    }
    journeys
}

#[allow(clippy::too_many_arguments)]
fn reconstruct(
    network: &Network,
    labels: &[Vec<Label>],
    ride_labels: &[Vec<Label>],
    round: usize,
    last_stop: usize,
    egress: Walk,
    query: &Query,
    arrive: u32,
) -> Journey {
    let mut legs = Vec::new();
    let last = place(network, u32::try_from(last_stop).unwrap_or(u32::MAX));
    legs.push(Leg::Walk {
        to: endpoint(query.destination, "Arrivée"),
        from: last,
        start: arrive - egress.seconds,
        end: arrive,
        metres: egress.metres,
    });
    let mut label = ride_labels[round][last_stop];
    let mut stop = last_stop;
    loop {
        match label {
            Label::Access(walk) => {
                legs.push(Leg::Walk {
                    from: endpoint(query.origin, "Départ"),
                    to: place(network, u32::try_from(stop).unwrap_or(u32::MAX)),
                    start: query.depart,
                    end: query.depart + walk.seconds,
                    metres: walk.metres,
                });
                break;
            }
            Label::Walk {
                round,
                from,
                walk,
                end,
            } => {
                legs.push(Leg::Walk {
                    from: place(network, from),
                    to: place(network, u32::try_from(stop).unwrap_or(u32::MAX)),
                    start: end - walk.seconds,
                    end,
                    metres: walk.metres,
                });
                label = ride_labels[round as usize][from as usize];
                stop = from as usize;
            }
            Label::Ride {
                round,
                pattern,
                board_pos,
                alight_pos,
                at_stop,
                wait,
                end,
            } => {
                let p = &network.patterns[pattern as usize];
                let board_stop = p.stops[board_pos as usize];
                legs.push(Leg::Ride {
                    trip_id: p.trip_id.clone(),
                    route_id: p.route_id.clone(),
                    route_name: p.route_name.clone(),
                    board: place(network, board_stop),
                    alight: place(network, p.stops[alight_pos as usize]),
                    at_stop,
                    wait,
                    start: at_stop + wait,
                    end,
                });
                label = labels[round as usize - 1][board_stop as usize];
                stop = board_stop as usize;
            }
            Label::None => unreachable!("a reached stop always has a label"),
        }
    }
    legs.reverse();
    let walk_metres = legs
        .iter()
        .map(|l| {
            if let Leg::Walk { metres, .. } = l {
                *metres
            } else {
                0
            }
        })
        .sum();
    let wait_seconds = legs
        .iter()
        .map(|l| {
            if let Leg::Ride { wait, .. } = l {
                *wait
            } else {
                0
            }
        })
        .sum();
    let rides = legs
        .iter()
        .filter(|l| matches!(l, Leg::Ride { .. }))
        .count();
    Journey {
        depart: query.depart,
        arrive,
        rides,
        walk_metres,
        wait_seconds,
        legs,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::gtfs::{Feed, Stop, Trip};
    use crate::network::NetworkOptions;
    use crate::wait::MedianRegimeB;

    const METRE: f64 = 1.0 / crate::geo::METRES_PER_DEGREE;

    /// Stops on a west-east axis at latitude 5.3, `x` metres from longitude -4.0.
    fn stop(id: &str, x: f64, y: f64) -> Stop {
        Stop {
            id: id.to_owned(),
            name: id.to_owned(),
            point: Point::new(5.3 + y * METRE, -4.0 + x * METRE),
        }
    }

    fn trip(id: &str, stops: &[(usize, u32)], headway: u32) -> Trip {
        Trip {
            id: id.to_owned(),
            route_id: id.to_owned(),
            route_name: id.to_owned(),
            service_id: "s".to_owned(),
            shape_id: None,
            stops: stops.iter().map(|&(s, t)| (s, t, t)).collect(),
            bands: vec![(5 * 3600, 22 * 3600, headway)],
        }
    }

    /// A ── B ── C on line « ouest » (every 10 min), C ── D on line « nord » (every 20 min),
    /// and a slow direct line A ── D (every 60 min).
    fn feed() -> Feed {
        Feed {
            stops: vec![
                stop("A", 0.0, 0.0),
                stop("B", 3000.0, 0.0),
                stop("C", 6000.0, 0.0),
                stop("D", 6000.0, 4000.0),
            ],
            trips: vec![
                trip("ouest", &[(0, 0), (1, 600), (2, 1200)], 600),
                trip("nord", &[(2, 0), (3, 600)], 1200),
                trip("direct", &[(0, 0), (3, 3000)], 3600),
            ],
            ..Feed::default()
        }
    }

    fn query(from: Point, to: Point) -> Query {
        Query {
            origin: from,
            destination: to,
            depart: 7 * 3600,
            max_rides: 4,
        }
    }

    fn rides(journey: &Journey) -> Vec<String> {
        journey
            .legs
            .iter()
            .filter_map(|l| {
                if let Leg::Ride { route_name, .. } = l {
                    Some(route_name.clone())
                } else {
                    None
                }
            })
            .collect()
    }

    #[test]
    fn finds_a_transfer_and_keeps_the_slower_direct_line_on_the_pareto_front() {
        let feed = feed();
        let network = Network::build(&feed, NetworkOptions::default());
        let (a, d) = (feed.stops[0].point, feed.stops[3].point);
        let journeys = plan(&network, &MedianRegimeB, &query(a, d));
        // Direct: wait ln2 × 60 min = 41.6 min, then 50 min. Transfer: 6.9 + 20 + 13.9 + 10 min.
        assert_eq!(
            journeys.iter().map(rides).collect::<Vec<_>>(),
            vec![vec!["direct"], vec!["ouest", "nord"]]
        );
        assert!(journeys[1].arrive < journeys[0].arrive);
        assert_eq!(journeys[1].wait_seconds, 416 + 832);
        assert_eq!(journeys[1].arrive, 7 * 3600 + 416 + 1200 + 832 + 600);
    }

    #[test]
    fn the_wait_is_part_of_the_search() {
        struct LongWaitAtC;
        impl WaitModel for LongWaitAtC {
            fn wait_s(
                &self,
                network: &Network,
                pattern: usize,
                pos: usize,
                time: u32,
            ) -> Option<u32> {
                let base = MedianRegimeB.wait_s(network, pattern, pos, time)?;
                let stop = &network.stops[network.patterns[pattern].stops[pos] as usize];
                Some(if stop.id == "C" {
                    base + 3 * 3600
                } else {
                    base
                })
            }
            fn name(&self) -> String {
                "test".to_owned()
            }
        }
        let feed = feed();
        let network = Network::build(&feed, NetworkOptions::default());
        let journeys = plan(
            &network,
            &LongWaitAtC,
            &query(feed.stops[0].point, feed.stops[3].point),
        );
        // With a three-hour queue at C, the direct line is the only sensible answer.
        assert_eq!(
            journeys.iter().map(rides).collect::<Vec<_>>(),
            vec![vec!["direct"]]
        );
    }

    #[test]
    fn no_service_outside_the_bands() {
        let feed = feed();
        let network = Network::build(&feed, NetworkOptions::default());
        let mut late = query(feed.stops[0].point, feed.stops[3].point);
        late.depart = 23 * 3600;
        assert!(plan(&network, &MedianRegimeB, &late).is_empty());
    }

    #[test]
    fn virtual_points_let_people_board_between_stops() {
        let feed = feed();
        // Halfway between A and B, 600 m off the line: 1,5 km from both stops.
        let roadside = Point::new(5.3 + 600.0 * METRE, -4.0 + 1500.0 * METRE);
        let to = feed.stops[2].point;
        let without = Network::build(&feed, NetworkOptions::default());
        assert!(plan(&without, &MedianRegimeB, &query(roadside, to)).is_empty());
        let options = NetworkOptions {
            virtual_spacing_m: Some(250.0),
            ..NetworkOptions::default()
        };
        let with = Network::build(&feed, options);
        let journeys = plan(&with, &MedianRegimeB, &query(roadside, to));
        assert_eq!(journeys.len(), 1);
        let Leg::Ride { board, .. } = &journeys[0].legs[1] else {
            panic!("expected a ride")
        };
        assert!(
            board.stop_id.starts_with("virtuel:ouest:"),
            "{}",
            board.stop_id
        );
        assert!(journeys[0].walk_metres < 1000);
    }

    /// Every step starts when the previous one ends, at the latest, and the announced
    /// arrival is the end of the last step (regression of the spike: a walk chained to a
    /// stop improved on foot in the same round broke this).
    fn assert_consistent(journey: &Journey) {
        let mut clock = journey.depart;
        for leg in &journey.legs {
            let (start, end) = match leg {
                Leg::Walk { start, end, .. } => (*start, *end),
                Leg::Ride { at_stop, wait, start, end, .. } => {
                    assert_eq!(*start, at_stop + wait);
                    assert!(*at_stop >= clock, "{journey:?}");
                    (*at_stop, *end)
                }
            };
            assert!(start >= clock && end >= start, "{journey:?}");
            clock = end;
        }
        assert_eq!(journey.arrive, clock);
        let walks = journey.legs.windows(2).filter(|w| matches!(w, [Leg::Walk { .. }, Leg::Walk { .. }]));
        assert_eq!(walks.count(), 0, "two walks in a row: {journey:?}");
    }

    #[test]
    fn journeys_are_consistent_on_a_dense_grid_of_lines() {
        // Twelve crossing lines on a 3 km square, stops every 300 m: many transfers on foot.
        let mut stops = Vec::new();
        let mut trips = Vec::new();
        for line in 0..6 {
            let offset = f64::from(line) * 500.0 + 120.0;
            for (axis, prefix) in [(true, "est"), (false, "nord")] {
                let first = stops.len();
                for i in 0..10 {
                    let along = f64::from(i) * 300.0;
                    let (x, y) = if axis { (along, offset) } else { (offset, along) };
                    stops.push(stop(&format!("{prefix}{line}-{i}"), x, y));
                }
                let sequence: Vec<(usize, u32)> = (0..10).map(|i| (first + i, u32::try_from(i).unwrap() * 90)).collect();
                trips.push(trip(&format!("{prefix}{line}"), &sequence, 300 + 120 * u32::try_from(line).unwrap()));
            }
        }
        let feed = Feed { stops, trips, ..Feed::default() };
        let network = Network::build(&feed, NetworkOptions::default());
        let mut checked = 0;
        for (from, to) in [(0, 119), (5, 64), (33, 90), (12, 107), (70, 9)] {
            for journey in plan(&network, &MedianRegimeB, &query(feed.stops[from].point, feed.stops[to].point)) {
                assert_consistent(&journey);
                checked += 1;
            }
        }
        assert!(checked >= 5);
    }

    #[test]
    fn a_short_trip_on_foot_is_a_journey_of_its_own() {
        let feed = feed();
        let network = Network::build(&feed, NetworkOptions::default());
        let halfway = Point::new(5.3, -4.0 + 1500.0 * METRE);
        let journeys = plan(
            &network,
            &MedianRegimeB,
            &query(feed.stops[0].point, halfway),
        );
        assert_eq!(journeys[0].rides, 0);
        // 1,5 km in longitude degrees at 5,3° N is a little less than 1,5 km; × 1,3 on foot.
        assert!(
            (1900..1960).contains(&journeys[0].walk_metres),
            "{}",
            journeys[0].walk_metres
        );
    }
}
