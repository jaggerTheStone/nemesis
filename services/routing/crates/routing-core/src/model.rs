//! Wait and fare models of the engine (ALGORITHMES.md, sections 1 to 3), and the
//! deterministic random generator of the Monte-Carlo draws (section 2.2).

use std::collections::HashMap;

use serde::Serialize;

use crate::gtfs::{FareEstimate, Feed, WaitProfile};
use crate::network::Network;

/// Distribution of a wait, in seconds.
#[derive(Debug, Clone, Copy, PartialEq, Serialize)]
#[serde(tag = "law", rename_all = "snake_case")]
pub enum WaitLaw {
    /// Régime B: random passages, exponential law of mean `mean_s`.
    Exponential { mean_s: f64 },
    /// Régime A from a profile: log-normal law matching the profile's p50 and p80
    /// (v0 approximation of the Gamma law of ALGORITHMES.md 1.2).
    LogNormal { mu: f64, sigma: f64 },
}

/// z such that P(Z ≤ z) = 0,8 for a standard normal law.
const Z80: f64 = 0.841_621_233_572_914_2;

impl WaitLaw {
    #[must_use]
    pub fn median_s(self) -> f64 {
        match self {
            Self::Exponential { mean_s } => mean_s * std::f64::consts::LN_2,
            Self::LogNormal { mu, .. } => mu.exp(),
        }
    }

    #[must_use]
    pub fn p80_s(self) -> f64 {
        match self {
            Self::Exponential { mean_s } => mean_s * 5_f64.ln(),
            Self::LogNormal { mu, sigma } => (mu + sigma * Z80).exp(),
        }
    }

    /// One draw, from two uniform numbers in [0, 1).
    #[must_use]
    pub fn sample(self, u1: f64, u2: f64) -> f64 {
        match self {
            Self::Exponential { mean_s } => -mean_s * (1.0 - u1).ln(),
            Self::LogNormal { mu, sigma } => {
                // Box–Muller.
                let z = (-2.0 * (1.0 - u1).ln()).sqrt() * (std::f64::consts::TAU * u2).cos();
                (mu + sigma * z).exp()
            }
        }
    }

    /// Log-normal law with these two quantiles.
    #[must_use]
    pub fn from_quantiles(p50_s: f64, p80_s: f64) -> Self {
        let p50 = p50_s.max(1.0);
        let sigma = ((p80_s.max(p50) / p50).ln() / Z80).max(1e-6);
        Self::LogNormal {
            mu: p50.ln(),
            sigma,
        }
    }
}

/// Where a wait comes from, shown with each leg (règle 1.3.2).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum WaitSource {
    /// Historical profile of the stop, line and slot (`ext_wait_profiles.txt`).
    Profile,
    /// Headway of the GTFS service band, régime B.
    GtfsHeadway,
}

/// Wait before boarding: its law and its source.
#[derive(Debug, Clone, Copy, PartialEq, Serialize)]
pub struct WaitEstimate {
    pub law: WaitLaw,
    pub regime: char,
    pub source: WaitSource,
    /// Median, rounded to the second: the boarding cost of the search.
    #[serde(skip)]
    pub median_s: u32,
}

/// Day types of the profiles.
#[must_use]
pub fn day_type(weekday: usize) -> &'static str {
    match weekday {
        5 => "samedi",
        6 => "dimanche",
        _ => "ouvrable",
    }
}

/// (stop, line, direction, day type, start of the 15-minute slot).
type ProfileKey = (String, String, u8, String, u32);

/// Waits from the profiles of the feed, régime B from the headways otherwise.
#[derive(Debug, Default)]
pub struct WaitModel {
    profiles: HashMap<ProfileKey, (char, u32, u32)>,
}

const SLOT_S: u32 = 15 * 60;

impl WaitModel {
    #[must_use]
    pub fn new(profiles: &[WaitProfile]) -> Self {
        let profiles = profiles
            .iter()
            .map(|p| {
                let regime = p.regime.chars().next().unwrap_or('B');
                (
                    (
                        p.stop_id.clone(),
                        p.route_id.clone(),
                        p.direction_id,
                        p.day_type.clone(),
                        p.slot_start,
                    ),
                    (regime, p.p50_s, p.p80_s),
                )
            })
            .collect();
        Self { profiles }
    }

    #[must_use]
    pub fn profile_count(&self) -> usize {
        self.profiles.len()
    }

    /// Wait at position `pos` of `pattern` when arriving at `time` on a `day` day type.
    #[must_use]
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    pub fn wait(
        &self,
        network: &Network,
        pattern: usize,
        pos: usize,
        time: u32,
        day: &str,
    ) -> Option<WaitEstimate> {
        let p = &network.patterns[pattern];
        let headway = p.headway_at(pos, time)?;
        let stop = &network.stops[p.stops[pos] as usize];
        if let (false, Some(direction)) = (stop.is_virtual, p.direction_id) {
            let slot = (time % 86_400) / SLOT_S * SLOT_S;
            let key = (
                stop.id.clone(),
                p.route_id.clone(),
                direction,
                day.to_owned(),
                slot,
            );
            if let Some(&(regime, p50, p80)) = self.profiles.get(&key) {
                let law = if regime == 'A' {
                    WaitLaw::from_quantiles(f64::from(p50), f64::from(p80))
                } else {
                    WaitLaw::Exponential {
                        mean_s: f64::from(p50) / std::f64::consts::LN_2,
                    }
                };
                return Some(WaitEstimate {
                    law,
                    regime,
                    source: WaitSource::Profile,
                    median_s: p50,
                });
            }
        }
        let law = WaitLaw::Exponential {
            mean_s: f64::from(headway),
        };
        Some(WaitEstimate {
            law,
            regime: 'B',
            source: WaitSource::GtfsHeadway,
            median_s: law.median_s().round() as u32,
        })
    }
}

/// Fares observed between areas (GTFS-Fares v2 areas and `ext_fare_estimates.txt`).
#[derive(Debug, Default)]
pub struct FareModel {
    area_of: HashMap<String, String>,
    fares: HashMap<(String, String, String), FareEstimate>,
}

impl FareModel {
    #[must_use]
    pub fn new(feed: &Feed) -> Self {
        Self {
            area_of: feed
                .stop_areas
                .iter()
                .map(|(area, stop)| (stop.clone(), area.clone()))
                .collect(),
            fares: feed
                .fare_estimates
                .iter()
                .filter(|f| f.condition == "normale")
                .map(|f| {
                    (
                        (f.route_id.clone(), f.from_area.clone(), f.to_area.clone()),
                        f.clone(),
                    )
                })
                .collect(),
        }
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.fares.is_empty()
    }

    /// Fare of a ride, from the real stops before or at each position (a virtual
    /// boarding point is priced like the stop before it).
    #[must_use]
    pub fn fare(
        &self,
        network: &Network,
        pattern: usize,
        board: usize,
        alight: usize,
    ) -> Option<&FareEstimate> {
        let p = &network.patterns[pattern];
        let real = |pos: usize| {
            (0..=pos)
                .rev()
                .map(|i| &network.stops[p.stops[i] as usize])
                .find(|s| !s.is_virtual)
        };
        let from = self.area_of.get(&real(board)?.id)?;
        let to = self.area_of.get(&real(alight)?.id)?;
        self.fares
            .get(&(p.route_id.clone(), from.clone(), to.clone()))
    }

    /// Area used to compare two boardings on the same vehicle.
    #[must_use]
    pub fn board_area(&self, network: &Network, pattern: usize, board: usize) -> Option<&str> {
        let p = &network.patterns[pattern];
        (0..=board)
            .rev()
            .map(|i| &network.stops[p.stops[i] as usize])
            .find(|s| !s.is_virtual)
            .and_then(|s| self.area_of.get(&s.id))
            .map(String::as_str)
    }
}

/// SplitMix64: small, fast, and the same numbers on every platform.
#[derive(Debug, Clone)]
pub struct Rng(u64);

impl Rng {
    #[must_use]
    pub const fn new(seed: u64) -> Self {
        Self(seed)
    }

    pub fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9e37_79b9_7f4a_7c15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
        z ^ (z >> 31)
    }

    /// Uniform in [0, 1).
    #[allow(clippy::cast_precision_loss)]
    pub fn unit(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / (1_u64 << 53) as f64
    }
}

/// FNV-1a hash, for seeds derived from a request (ALGORITHMES.md 2.2).
#[must_use]
pub fn fnv1a(text: &str) -> u64 {
    let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
    for byte in text.bytes() {
        hash ^= u64::from(byte);
        hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
    }
    hash
}

#[cfg(test)]
mod tests {
    use super::*;

    fn quantile(mut draws: Vec<f64>, q: f64) -> f64 {
        draws.sort_by(f64::total_cmp);
        #[allow(
            clippy::cast_precision_loss,
            clippy::cast_possible_truncation,
            clippy::cast_sign_loss
        )]
        draws[((draws.len() - 1) as f64 * q).round() as usize]
    }

    #[test]
    fn exponential_waits_have_the_regime_b_quantiles() {
        let law = WaitLaw::Exponential { mean_s: 600.0 };
        assert!((law.median_s() - 415.9).abs() < 0.1);
        assert!((law.p80_s() - 965.7).abs() < 0.1);
        let mut rng = Rng::new(1);
        let draws: Vec<f64> = (0..20_000)
            .map(|_| law.sample(rng.unit(), rng.unit()))
            .collect();
        assert!((quantile(draws.clone(), 0.5) - 415.9).abs() < 20.0);
        assert!((quantile(draws, 0.8) - 965.7).abs() < 40.0);
    }

    #[test]
    fn log_normal_waits_match_the_profile_quantiles() {
        let law = WaitLaw::from_quantiles(326.0, 415.0);
        assert!((law.median_s() - 326.0).abs() < 0.01);
        assert!((law.p80_s() - 415.0).abs() < 0.01);
        let mut rng = Rng::new(2);
        let draws: Vec<f64> = (0..20_000)
            .map(|_| law.sample(rng.unit(), rng.unit()))
            .collect();
        assert!((quantile(draws.clone(), 0.5) - 326.0).abs() < 8.0);
        assert!((quantile(draws, 0.8) - 415.0).abs() < 10.0);
    }

    #[test]
    fn the_generator_is_reproducible() {
        let mut a = Rng::new(fnv1a("requête"));
        let mut b = Rng::new(fnv1a("requête"));
        assert_eq!((a.next_u64(), a.next_u64()), (b.next_u64(), b.next_u64()));
        assert!((0.0..1.0).contains(&Rng::new(3).unit()));
        assert_eq!(day_type(0), "ouvrable");
        assert_eq!(day_type(6), "dimanche");
    }
}
