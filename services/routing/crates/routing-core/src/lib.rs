//! Routing engine core.
//!
//! I0.8 (spike, ADR-003 option B): GTFS reading, frequency-based network with
//! virtual boarding points, wait models and RAPTOR with the wait as boarding cost.
//! The `RoutingEngine` interface and McRAPTOR arrive in I0.9. This crate is shared
//! by the server and, through a native binding, the phone, so that online and
//! offline results stay identical.

pub mod geo;
pub mod gtfs;
pub mod network;
pub mod raptor;
pub mod wait;

/// Version of the engine, reported by the CLI and the service.
pub const ENGINE_VERSION: &str = env!("CARGO_PKG_VERSION");

/// Returns the engine version string.
#[must_use]
pub fn version() -> &'static str {
    ENGINE_VERSION
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_matches_crate_version() {
        assert_eq!(version(), env!("CARGO_PKG_VERSION"));
        assert!(!version().is_empty());
    }
}
