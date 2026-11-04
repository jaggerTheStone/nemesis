//! Routing engine core.
//!
//! The engine itself (the `RoutingEngine` interface of partie 8.1, McRAPTOR on a
//! frequency-based network) arrives in increments I0.8 and I0.9. This crate is
//! shared by the server and, through a native binding, the phone, so that
//! online and offline results stay identical.

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
