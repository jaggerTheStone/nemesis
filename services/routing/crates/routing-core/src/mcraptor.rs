//! McRAPTOR on the frequency-based network (ADR-003, ALGORITHMES.md 2.1).
//!
//! Each stop keeps bags of labels that do not dominate one another on four criteria:
//! arrival (with median waits), fare (p50, XOF), walking distance and number of vehicles.
//! Round k scans the lines from the labels created in round k − 1. Boarding costs the
//! wait given by the caller at the stop and time of boarding. Walking transfers leave
//! only from arrivals by vehicle, so that a journey never chains two walks. The search
//! returns the Pareto front at the destination.

use std::collections::HashMap;

use crate::model::WaitEstimate;
use crate::network::{Network, Walk};

/// Walking is compared by steps of 250 m (about 3 min): a front that kept every metre
/// of difference would offer journeys with four changes to save 50 m (à calibrer).
pub const WALK_BUCKET_M: u32 = 250;

/// Criteria of a label. A fare that is not known for every ride is `None`: it is then
/// compared with nothing, so that an unknown price never hides a known one.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Criteria {
    pub arrival: u32,
    pub cost: Option<u32>,
    pub walk_m: u32,
    pub rides: u8,
}

impl Criteria {
    /// Better or equal on every criterion.
    #[must_use]
    pub fn dominates(&self, other: &Self) -> bool {
        let cost = match (self.cost, other.cost) {
            (Some(a), Some(b)) => a <= b,
            (None, None) => true,
            _ => false,
        };
        cost && self.arrival <= other.arrival
            && self.walk_m / WALK_BUCKET_M <= other.walk_m / WALK_BUCKET_M
            && self.rides <= other.rides
    }
}

/// An end of a leg.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Place {
    Origin,
    Destination,
    Stop(u32),
}

/// A leg of a journey found by the search.
#[derive(Debug, Clone, PartialEq)]
pub enum FoundLeg {
    Walk {
        from: Place,
        to: Place,
        start: u32,
        end: u32,
        walk: Walk,
    },
    Ride {
        pattern: u32,
        board_pos: u32,
        alight_pos: u32,
        at_stop: u32,
        wait: WaitEstimate,
        start: u32,
        end: u32,
        /// p10, p50 and p90 of the fare, XOF.
        fare: Option<[u32; 3]>,
    },
}

/// A journey of the Pareto front.
#[derive(Debug, Clone, PartialEq)]
pub struct Found {
    pub criteria: Criteria,
    pub legs: Vec<FoundLeg>,
}

/// What the search needs from the engine for one request.
pub struct Search<'a> {
    pub network: &'a Network,
    /// Patterns running on the day of the request.
    pub active: &'a [bool],
    pub depart: u32,
    pub max_rides: u8,
    /// Stops within walking distance of the origin, and of the destination.
    pub access: &'a [(u32, Walk)],
    pub egress: &'a HashMap<u32, Walk>,
    /// Walking all the way, when short enough.
    pub direct: Option<Walk>,
    /// Wait at (pattern, position) when arriving at the stop at a time.
    pub wait: &'a dyn Fn(usize, usize, u32) -> Option<WaitEstimate>,
    /// Fare of (pattern, boarding position, alighting position).
    pub fare: &'a dyn Fn(usize, usize, usize) -> Option<[u32; 3]>,
    /// Area of a boarding, to compare two boardings of the same vehicle.
    pub board_area: &'a dyn Fn(usize, usize) -> Option<u32>,
}

#[derive(Debug, Clone, Copy)]
enum Step {
    Access(Walk),
    Ride {
        pattern: u32,
        board_pos: u32,
        alight_pos: u32,
        at_stop: u32,
        wait: WaitEstimate,
        fare: Option<[u32; 3]>,
    },
    Walk(Walk),
}

#[derive(Debug, Clone, Copy)]
struct Label {
    criteria: Criteria,
    stop: u32,
    previous: Option<u32>,
    step: Step,
}

#[derive(Debug, Clone, Copy)]
struct Boarded {
    parent: u32,
    board_pos: u32,
    at_stop: u32,
    wait: WaitEstimate,
    /// Departure time shifted to the first stop of the pattern: comparable along it.
    start: u32,
    cost: Option<u32>,
    walk_m: u32,
    area: Option<u32>,
}

impl Boarded {
    fn dominates(&self, other: &Self) -> bool {
        let cost = match (self.cost, other.cost) {
            (Some(a), Some(b)) => a <= b,
            (None, None) => true,
            _ => false,
        };
        cost && self.area == other.area
            && self.start <= other.start
            && self.walk_m / WALK_BUCKET_M <= other.walk_m / WALK_BUCKET_M
    }
}

/// Inserts `criteria` in a Pareto set unless an element dominates it; returns whether it
/// went in. Elements it dominates are removed.
fn insert<T: Copy>(set: &mut Vec<(Criteria, T)>, criteria: Criteria, value: T) -> bool {
    if set.iter().any(|(c, _)| c.dominates(&criteria)) {
        return false;
    }
    set.retain(|(c, _)| !criteria.dominates(c));
    set.push((criteria, value));
    true
}

fn add(cost: Option<u32>, fare: Option<[u32; 3]>) -> Option<u32> {
    Some(cost? + fare?[1])
}

/// Runs the search.
#[must_use]
#[allow(clippy::too_many_lines)]
pub fn search(s: &Search<'_>) -> Vec<Found> {
    let stops = s.network.stops.len();
    let mut labels: Vec<Label> = Vec::new();
    // Two bags per stop. An arrival by vehicle can reach the destination or walk on; an
    // arrival on foot can only board. So arrivals by vehicle are compared with arrivals by
    // vehicle only, and arrivals on foot with every label that can board there.
    let mut best_ride: Vec<Vec<(Criteria, u32)>> = vec![Vec::new(); stops];
    let mut best_any: Vec<Vec<(Criteria, u32)>> = vec![Vec::new(); stops];
    let mut target: Vec<(Criteria, (Option<u32>, Walk))> = Vec::new();
    if let Some(walk) = s.direct {
        let criteria = Criteria {
            arrival: s.depart + walk.seconds,
            cost: Some(0),
            walk_m: walk.metres,
            rides: 0,
        };
        insert(&mut target, criteria, (None, walk));
    }

    // Round 0: walking from the origin.
    let mut fresh: HashMap<u32, Vec<u32>> = HashMap::new();
    for &(stop, walk) in s.access {
        let criteria = Criteria {
            arrival: s.depart + walk.seconds,
            cost: Some(0),
            walk_m: walk.metres,
            rides: 0,
        };
        let id = u32::try_from(labels.len()).unwrap_or(u32::MAX);
        if insert(&mut best_any[stop as usize], criteria, id) {
            labels.push(Label {
                criteria,
                stop,
                previous: None,
                step: Step::Access(walk),
            });
            fresh.entry(stop).or_default().push(id);
        }
    }

    let pruned =
        |c: &Criteria, best: &[(Criteria, u32)], target: &[(Criteria, (Option<u32>, Walk))]| {
            best.iter().any(|(b, _)| b.dominates(c)) || target.iter().any(|(t, _)| t.dominates(c))
        };

    for round in 1..=s.max_rides {
        // Lines to scan, from the earliest position where a fresh label can board.
        let mut queue: HashMap<u32, u32> = HashMap::new();
        for &stop in fresh.keys() {
            for &(pattern, pos) in &s.network.stop_patterns[stop as usize] {
                if s.active[pattern as usize] {
                    queue
                        .entry(pattern)
                        .and_modify(|p| *p = (*p).min(pos))
                        .or_insert(pos);
                }
            }
        }
        let mut rides: Vec<u32> = Vec::new();
        let mut patterns: Vec<(u32, u32)> = queue.into_iter().collect();
        patterns.sort_unstable();
        for (p, start) in patterns {
            let pattern = &s.network.patterns[p as usize];
            let mut bag: Vec<Boarded> = Vec::new();
            for pos in start as usize..pattern.stops.len() {
                let stop = pattern.stops[pos];
                for r in &bag {
                    let fare = (s.fare)(p as usize, r.board_pos as usize, pos);
                    let criteria = Criteria {
                        arrival: r.start + pattern.arrivals[pos],
                        cost: add(r.cost, fare),
                        walk_m: r.walk_m,
                        rides: round,
                    };
                    if pruned(&criteria, &best_ride[stop as usize], &target) {
                        continue;
                    }
                    let id = u32::try_from(labels.len()).unwrap_or(u32::MAX);
                    insert(&mut best_ride[stop as usize], criteria, id);
                    insert(&mut best_any[stop as usize], criteria, id);
                    labels.push(Label {
                        criteria,
                        stop,
                        previous: Some(r.parent),
                        step: Step::Ride {
                            pattern: p,
                            board_pos: r.board_pos,
                            alight_pos: u32::try_from(pos).unwrap_or(u32::MAX),
                            at_stop: r.at_stop,
                            wait: r.wait,
                            fare,
                        },
                    });
                    rides.push(id);
                }
                let Some(parents) = fresh.get(&stop) else {
                    continue;
                };
                for &parent in parents {
                    let label = labels[parent as usize];
                    let Some(wait) = (s.wait)(p as usize, pos, label.criteria.arrival) else {
                        continue;
                    };
                    let departure = label.criteria.arrival + wait.median_s;
                    let boarded = Boarded {
                        parent,
                        board_pos: u32::try_from(pos).unwrap_or(u32::MAX),
                        at_stop: label.criteria.arrival,
                        wait,
                        start: departure.saturating_sub(pattern.departures[pos]),
                        cost: label.criteria.cost,
                        walk_m: label.criteria.walk_m,
                        area: (s.board_area)(p as usize, pos),
                    };
                    if !bag.iter().any(|b| b.dominates(&boarded)) {
                        bag.retain(|b| !boarded.dominates(b));
                        bag.push(boarded);
                    }
                }
            }
        }

        // Destination, then walking transfers, from the arrivals by vehicle of this round.
        let mut next: HashMap<u32, Vec<u32>> = HashMap::new();
        for &id in &rides {
            let label = labels[id as usize];
            next.entry(label.stop).or_default().push(id);
            if let Some(&walk) = s.egress.get(&label.stop) {
                let c = label.criteria;
                let criteria = Criteria {
                    arrival: c.arrival + walk.seconds,
                    cost: c.cost,
                    walk_m: c.walk_m + walk.metres,
                    rides: c.rides,
                };
                insert(&mut target, criteria, (Some(id), walk));
            }
        }
        for &id in &rides {
            let label = labels[id as usize];
            for &(to, walk) in &s.network.footpaths[label.stop as usize] {
                let c = label.criteria;
                let criteria = Criteria {
                    arrival: c.arrival + walk.seconds,
                    cost: c.cost,
                    walk_m: c.walk_m + walk.metres,
                    rides: c.rides,
                };
                if pruned(&criteria, &best_any[to as usize], &target) {
                    continue;
                }
                let walk_id = u32::try_from(labels.len()).unwrap_or(u32::MAX);
                insert(&mut best_any[to as usize], criteria, walk_id);
                labels.push(Label {
                    criteria,
                    stop: to,
                    previous: Some(id),
                    step: Step::Walk(walk),
                });
                next.entry(to).or_default().push(walk_id);
            }
        }
        if next.is_empty() {
            break;
        }
        fresh = next;
    }

    let mut found: Vec<Found> = target
        .iter()
        .map(|&(criteria, (last, egress))| reconstruct(s, &labels, criteria, last, egress))
        .collect();
    found.sort_by_key(|f| (f.criteria.rides, f.criteria.arrival));
    found
}

fn reconstruct(
    s: &Search<'_>,
    labels: &[Label],
    criteria: Criteria,
    last: Option<u32>,
    egress: Walk,
) -> Found {
    let mut legs = Vec::new();
    let end = criteria.arrival;
    let Some(mut id) = last else {
        legs.push(FoundLeg::Walk {
            from: Place::Origin,
            to: Place::Destination,
            start: s.depart,
            end,
            walk: egress,
        });
        return Found { criteria, legs };
    };
    legs.push(FoundLeg::Walk {
        from: Place::Stop(labels[id as usize].stop),
        to: Place::Destination,
        start: end - egress.seconds,
        end,
        walk: egress,
    });
    loop {
        let label = labels[id as usize];
        match label.step {
            Step::Access(walk) => {
                legs.push(FoundLeg::Walk {
                    from: Place::Origin,
                    to: Place::Stop(label.stop),
                    start: s.depart,
                    end: label.criteria.arrival,
                    walk,
                });
                break;
            }
            Step::Walk(walk) => {
                let from = labels[label.previous.unwrap_or_default() as usize].stop;
                legs.push(FoundLeg::Walk {
                    from: Place::Stop(from),
                    to: Place::Stop(label.stop),
                    start: label.criteria.arrival - walk.seconds,
                    end: label.criteria.arrival,
                    walk,
                });
            }
            Step::Ride {
                pattern,
                board_pos,
                alight_pos,
                at_stop,
                wait,
                fare,
            } => {
                legs.push(FoundLeg::Ride {
                    pattern,
                    board_pos,
                    alight_pos,
                    at_stop,
                    wait,
                    start: at_stop + wait.median_s,
                    end: label.criteria.arrival,
                    fare,
                });
            }
        }
        match label.previous {
            Some(previous) => id = previous,
            None => break,
        }
    }
    legs.reverse();
    Found { criteria, legs }
}
