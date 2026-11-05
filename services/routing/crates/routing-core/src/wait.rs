//! Boarding cost: the wait at a stop, given the line and the time (ALGORITHMES.md, 1.3).

use crate::network::Network;

/// Waiting time model used as the boarding cost of the engine.
pub trait WaitModel {
    /// Wait in seconds before boarding `pattern` at position `pos` when arriving at
    /// `time`; `None` when the line does not run then.
    fn wait_s(&self, network: &Network, pattern: usize, pos: usize, time: u32) -> Option<u32>;
    /// Short name, for the reports.
    fn name(&self) -> String;
}

/// Régime B: random passages at the headway of the service band; median wait
/// p50 = ln 2 × H (the exponential case, ALGORITHMES.md section 1.3).
#[derive(Debug, Clone, Copy, Default)]
pub struct MedianRegimeB;

impl WaitModel for MedianRegimeB {
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    fn wait_s(&self, network: &Network, pattern: usize, pos: usize, time: u32) -> Option<u32> {
        let headway = network.patterns[pattern].headway_at(pos, time)?;
        Some((std::f64::consts::LN_2 * f64::from(headway)).round() as u32)
    }

    fn name(&self) -> String {
        "regime_b_mediane".to_owned()
    }
}

/// Simulated live conditions for the spike: the régime B median multiplied, per stop
/// and per line, by a factor between 0,5 and 3 drawn from a seeded hash. These are
/// test conditions, never presented as observations.
#[derive(Debug, Clone, Copy)]
pub struct SimulatedLive {
    pub seed: u64,
}

impl SimulatedLive {
    /// Factor applied at `stop_id` for `route_id`: 0,5 + 2,5 u, u uniform in [0, 1).
    /// The same function exists in tools/routing-spike/compare.py.
    #[must_use]
    pub fn factor(seed: u64, stop_id: &str, route_id: &str) -> f64 {
        let key = format!("{seed}|{stop_id}|{route_id}");
        let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
        for byte in key.bytes() {
            hash ^= u64::from(byte);
            hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
        }
        #[allow(clippy::cast_precision_loss)]
        let unit = (hash >> 11) as f64 / (1_u64 << 53) as f64;
        0.5 + 2.5 * unit
    }
}

impl WaitModel for SimulatedLive {
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    fn wait_s(&self, network: &Network, pattern: usize, pos: usize, time: u32) -> Option<u32> {
        let base = MedianRegimeB.wait_s(network, pattern, pos, time)?;
        let p = &network.patterns[pattern];
        let stop = &network.stops[p.stops[pos] as usize];
        Some((f64::from(base) * Self::factor(self.seed, &stop.id, &p.route_id)).round() as u32)
    }

    fn name(&self) -> String {
        format!("attentes_simulees_{}", self.seed)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn simulated_factors_are_reproducible_and_bounded() {
        let a = SimulatedLive::factor(7, "node/1", "10179006");
        assert!((a - SimulatedLive::factor(7, "node/1", "10179006")).abs() < f64::EPSILON);
        assert!((0.5..3.0).contains(&a));
        let spread: Vec<f64> = (0..1000)
            .map(|i| SimulatedLive::factor(7, &format!("s{i}"), "r"))
            .collect();
        let mean = spread.iter().sum::<f64>() / 1000.0;
        assert!((mean - 1.75).abs() < 0.1, "{mean}");
    }

    #[test]
    fn simulated_factor_matches_the_python_reference() {
        // Value computed by tools/routing-spike/compare.py: same hash, same formula.
        let factor = SimulatedLive::factor(2026, "node/7055147061", "10179006");
        assert!((factor - 1.021_076_272_766_270_3).abs() < 1e-12, "{factor}");
    }
}
