//! From the Pareto front of the search to the options shown (ALGORITHMES.md 2.2, 2.3).
//!
//! Each journey is simulated 500 times: the waits are drawn from their laws, walking
//! and riding times are taken as computed. The 50th and 80th percentiles of the total
//! give the durations. Dominated options and near-duplicates are then removed, and the
//! options labelled « cheapest », « fastest » and « simplest ».

use serde::Serialize;

use crate::mcraptor::{Found, FoundLeg, WALK_BUCKET_M};
use crate::model::{Rng, WaitEstimate};

/// Near-duplicate tolerance: same lines, within 2 min and 50 F (ALGORITHMES.md 2.3).
pub const DUPLICATE_S: u32 = 120;
pub const DUPLICATE_XOF: u32 = 50;
/// An unlabelled option is shown only if its p80 is at most 1,5 × the best p80 + 15 min.
pub const RELEVANT_SLACK_S: u32 = 15 * 60;
/// Most options shown, labelled ones first in the order of the front.
pub const MAX_OPTIONS: usize = 5;

/// A journey with its simulated durations.
#[derive(Debug, Clone)]
pub struct Simulated {
    pub found: Found,
    pub p50_s: u32,
    pub p80_s: u32,
    /// Lines ridden, in order: the identity used for near-duplicates.
    pub lines: Vec<u32>,
    pub labels: Vec<&'static str>,
}

impl Simulated {
    #[must_use]
    pub fn cost(&self) -> Option<u32> {
        self.found.criteria.cost
    }

    #[must_use]
    pub fn rides(&self) -> u8 {
        self.found.criteria.rides
    }

    #[must_use]
    pub fn walk_m(&self) -> u32 {
        self.found.criteria.walk_m
    }

    /// Better or equal everywhere, better somewhere, on the criteria shown (2.1).
    #[must_use]
    pub fn dominates(&self, other: &Self) -> bool {
        let cost = match (self.cost(), other.cost()) {
            (Some(a), Some(b)) => Some(a.cmp(&b)),
            (None, None) => Some(std::cmp::Ordering::Equal),
            _ => None,
        };
        let Some(cost) = cost else { return false };
        let pairs = [
            self.p80_s.cmp(&other.p80_s),
            self.p50_s.cmp(&other.p50_s),
            cost,
            self.rides().cmp(&other.rides()),
            (self.walk_m() / WALK_BUCKET_M).cmp(&(other.walk_m() / WALK_BUCKET_M)),
        ];
        pairs.iter().all(|o| o.is_le()) && pairs.iter().any(|o| o.is_lt())
    }
}

/// Simulates `found` with `draws` draws; returns (p50, p80) of the duration, seconds.
#[must_use]
#[allow(
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    clippy::cast_precision_loss
)]
pub fn simulate(found: &Found, depart: u32, draws: usize, rng: &mut Rng) -> (u32, u32) {
    let mut totals: Vec<f64> = Vec::with_capacity(draws);
    for _ in 0..draws {
        let mut total = 0.0;
        for leg in &found.legs {
            total += match leg {
                FoundLeg::Walk { walk, .. } => f64::from(walk.seconds),
                FoundLeg::Ride {
                    wait, start, end, ..
                } => {
                    wait.law.sample(rng.unit(), rng.unit()) + f64::from(end.saturating_sub(*start))
                }
            };
        }
        totals.push(total);
    }
    if totals.is_empty() {
        let total = found.criteria.arrival.saturating_sub(depart);
        return (total, total);
    }
    totals.sort_by(f64::total_cmp);
    let at = |q: f64| totals[((totals.len() - 1) as f64 * q).round() as usize].round() as u32;
    (at(0.5), at(0.8))
}

/// Ordering key of a label: smallest wins.
type SortKey = (u32, u32, u32);

/// Pareto filter, near-duplicates and labels, in the order of the front.
#[must_use]
pub fn select(mut options: Vec<Simulated>) -> Vec<Simulated> {
    let snapshot = options.clone();
    options.retain(|o| !snapshot.iter().any(|other| other.dominates(o)));

    let mut kept: Vec<Simulated> = Vec::new();
    options.sort_by_key(|o| (o.p80_s, o.p50_s, o.rides(), o.walk_m()));
    for option in options {
        let duplicate = kept.iter().any(|k| {
            k.lines == option.lines
                && k.p50_s.abs_diff(option.p50_s) <= DUPLICATE_S
                && match (k.cost(), option.cost()) {
                    (Some(a), Some(b)) => a.abs_diff(b) <= DUPLICATE_XOF,
                    (None, None) => true,
                    _ => false,
                }
        });
        if !duplicate {
            kept.push(option);
        }
    }

    let pick = |key: &dyn Fn(&Simulated) -> Option<SortKey>| {
        kept.iter()
            .enumerate()
            .filter_map(|(i, o)| key(o).map(|k| (k, i)))
            .min()
            .map(|(_, i)| i)
    };
    let cheapest = pick(&|o| o.cost().map(|c| (c, o.p80_s, o.p50_s)));
    let fastest = pick(&|o| Some((o.p80_s, o.p50_s, u32::from(o.rides()))));
    // « Le plus simple » : fewest changes, then walking counted by 5 minutes (375 m).
    let simplest = pick(&|o| Some((u32::from(o.rides()), o.walk_m() / 375, o.p80_s)));
    for (index, label) in [
        (cheapest, "cheapest"),
        (fastest, "fastest"),
        (simplest, "simplest"),
    ] {
        if let Some(i) = index {
            kept[i].labels.push(label);
        }
    }
    // Unlabelled options only when reasonably fast, and at most five options in all
    // (addition to ALGORITHMES.md 2.3, à calibrer).
    let fastest_p80 = kept.iter().map(|o| o.p80_s).min().unwrap_or(0);
    let limit = fastest_p80 + fastest_p80 / 2 + RELEVANT_SLACK_S;
    let mut shown = 0;
    kept.retain(|o| {
        let keep = !o.labels.is_empty() || (o.p80_s <= limit && shown < MAX_OPTIONS);
        shown += usize::from(keep);
        keep
    });
    kept
}

/// Quantiles of a wait, minutes, for the legs shown.
#[must_use]
#[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
pub fn wait_minutes(wait: &WaitEstimate) -> (u32, u32) {
    (
        (wait.law.median_s() / 60.0).round() as u32,
        (wait.law.p80_s() / 60.0).round() as u32,
    )
}

/// Fare range rounded to 50 F (DATA.md, « Règles d'affichage »).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct Fare {
    pub p10: u32,
    pub p50: u32,
    pub p90: u32,
    pub currency: &'static str,
}

impl Fare {
    #[must_use]
    pub fn rounded(raw: [u32; 3]) -> Self {
        Self {
            p10: raw[0] / 50 * 50,
            p50: (raw[1] + 25) / 50 * 50,
            p90: raw[2].div_ceil(50) * 50,
            currency: "XOF",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::mcraptor::{Criteria, Place};
    use crate::model::{WaitLaw, WaitSource};
    use crate::network::Walk;

    fn option(
        p50: u32,
        p80: u32,
        cost: Option<u32>,
        rides: u8,
        walk: u32,
        lines: Vec<u32>,
    ) -> Simulated {
        Simulated {
            found: Found {
                criteria: Criteria {
                    arrival: 0,
                    cost,
                    walk_m: walk,
                    rides,
                },
                legs: vec![],
            },
            p50_s: p50,
            p80_s: p80,
            lines,
            labels: vec![],
        }
    }

    #[test]
    fn dominated_options_and_near_duplicates_go() {
        let options = vec![
            option(1800, 2400, Some(300), 1, 200, vec![1]),
            option(1900, 2500, Some(300), 1, 300, vec![2]), // dominated by the first
            option(1860, 2460, Some(320), 1, 150, vec![1]), // same line, 1 min and 20 F away
            option(2400, 3000, Some(200), 2, 100, vec![3, 4]),
            option(1500, 2000, None, 2, 600, vec![5, 6]), // unknown fare: not compared
        ];
        let kept = select(options);
        let lines: Vec<Vec<u32>> = kept.iter().map(|o| o.lines.clone()).collect();
        assert_eq!(lines, vec![vec![5, 6], vec![1], vec![3, 4]]);
        assert_eq!(kept[0].labels, vec!["fastest"]);
        assert_eq!(kept[1].labels, vec!["simplest"]);
        assert_eq!(kept[2].labels, vec!["cheapest"]);
    }

    #[test]
    fn durations_are_simulated_from_the_wait_laws() {
        let wait = WaitEstimate {
            law: WaitLaw::Exponential { mean_s: 600.0 },
            regime: 'B',
            source: WaitSource::GtfsHeadway,
            median_s: 416,
        };
        let found = Found {
            criteria: Criteria {
                arrival: 0,
                cost: Some(0),
                walk_m: 0,
                rides: 1,
            },
            legs: vec![
                FoundLeg::Walk {
                    from: Place::Origin,
                    to: Place::Stop(0),
                    start: 0,
                    end: 120,
                    walk: Walk {
                        seconds: 120,
                        metres: 150,
                        straight: false,
                    },
                },
                FoundLeg::Ride {
                    pattern: 0,
                    board_pos: 0,
                    alight_pos: 1,
                    at_stop: 120,
                    wait,
                    start: 536,
                    end: 1736,
                    fare: None,
                },
            ],
        };
        let (p50, p80) = simulate(&found, 0, 500, &mut Rng::new(7));
        // 2 min walk + 20 min ride + exponential wait (p50 6,9 min, p80 16,1 min).
        assert!((p50 as i64 - (120 + 1200 + 416)).abs() < 90, "{p50}");
        assert!((p80 as i64 - (120 + 1200 + 966)).abs() < 150, "{p80}");
        assert_eq!(simulate(&found, 0, 500, &mut Rng::new(7)), (p50, p80));
    }

    #[test]
    fn fares_are_rounded_to_fifty_francs_outwards() {
        assert_eq!(
            Fare::rounded([160, 230, 310]),
            Fare {
                p10: 150,
                p50: 250,
                p90: 350,
                currency: "XOF"
            }
        );
    }
}
