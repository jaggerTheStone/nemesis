//! Walking on the OpenStreetMap graph of the city pack (ALGORITHMES.md 2.1).
//!
//! Points (origin, destination, stops) are attached to their nearest graph node when it
//! is close enough; walking distances are then shortest paths, bounded by Dijkstra. A
//! point the graph does not reach is walked to in a straight line × the detour factor,
//! and the leg says so.

use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap};
use std::path::Path;

use serde::Deserialize;

use crate::geo::{Grid, Point};
use crate::gtfs::GtfsError;

/// Farthest a point may be from the graph to be attached to it, straight line.
pub const SNAP_M: f64 = 200.0;

#[derive(Debug, Deserialize)]
struct NodeRow {
    node: u32,
    lat: f64,
    lon: f64,
}

#[derive(Debug, Deserialize)]
struct EdgeRow {
    from: u32,
    to: u32,
    metres: f32,
}

/// Undirected walking graph in compressed adjacency form.
#[derive(Debug)]
pub struct WalkGraph {
    pub points: Vec<Point>,
    offsets: Vec<u32>,
    targets: Vec<u32>,
    metres: Vec<f32>,
    grid: Grid,
}

/// A point attached to the graph: its node and the straight distance to it.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Snap {
    pub node: u32,
    pub metres: f64,
}

impl WalkGraph {
    /// Builds the graph from undirected edges.
    #[must_use]
    pub fn new(points: Vec<Point>, edges: &[(u32, u32, f32)]) -> Self {
        let mut degree = vec![0_u32; points.len() + 1];
        for &(a, b, _) in edges {
            degree[a as usize + 1] += 1;
            degree[b as usize + 1] += 1;
        }
        for i in 1..degree.len() {
            degree[i] += degree[i - 1];
        }
        let offsets = degree.clone();
        let mut fill = degree;
        let mut targets = vec![0; edges.len() * 2];
        let mut metres = vec![0.0; edges.len() * 2];
        for &(a, b, m) in edges {
            for (from, to) in [(a, b), (b, a)] {
                let slot = fill[from as usize] as usize;
                targets[slot] = to;
                metres[slot] = m;
                fill[from as usize] += 1;
            }
        }
        let grid = Grid::new(&points, 150.0);
        Self {
            points,
            offsets,
            targets,
            metres,
            grid,
        }
    }

    /// Reads `walk_nodes.csv` and `walk_edges.csv`.
    ///
    /// # Errors
    /// Unreadable files, or an edge naming an unknown node.
    pub fn read(nodes: &Path, edges: &Path) -> Result<Self, GtfsError> {
        let open = |path: &Path| {
            csv::Reader::from_path(path).map_err(|e| GtfsError::Csv(path.display().to_string(), e))
        };
        let mut points = Vec::new();
        for (index, row) in open(nodes)?.deserialize::<NodeRow>().enumerate() {
            let row = row.map_err(|e| GtfsError::Csv(nodes.display().to_string(), e))?;
            if row.node as usize != index {
                return Err(GtfsError::Invalid(format!(
                    "{} : nœuds non numérotés de 0 à n",
                    nodes.display()
                )));
            }
            points.push(Point::new(row.lat, row.lon));
        }
        let mut list = Vec::new();
        for row in open(edges)?.deserialize::<EdgeRow>() {
            let row = row.map_err(|e| GtfsError::Csv(edges.display().to_string(), e))?;
            if row.from as usize >= points.len() || row.to as usize >= points.len() {
                return Err(GtfsError::Invalid(format!(
                    "{} : nœud inconnu",
                    edges.display()
                )));
            }
            list.push((row.from, row.to, row.metres));
        }
        Ok(Self::new(points, &list))
    }

    #[must_use]
    pub fn edge_count(&self) -> usize {
        self.targets.len() / 2
    }

    /// Nearest node within [`SNAP_M`].
    #[must_use]
    pub fn snap(&self, point: Point) -> Option<Snap> {
        self.grid
            .within(&self.points, point, SNAP_M)
            .into_iter()
            .min_by(|a, b| a.1.total_cmp(&b.1))
            .map(|(node, metres)| Snap {
                node: u32::try_from(node).unwrap_or(u32::MAX),
                metres,
            })
    }

    /// Shortest walking distance from `start` to every node within `limit_m`.
    #[must_use]
    #[allow(
        clippy::cast_possible_truncation,
        clippy::cast_sign_loss,
        clippy::cast_precision_loss
    )]
    pub fn distances(&self, start: Snap, limit_m: f64) -> HashMap<u32, f64> {
        // Distances in decimetres, as integers, for the priority queue.
        let mut best: HashMap<u32, u32> = HashMap::new();
        let mut queue = BinaryHeap::new();
        let first = (start.metres * 10.0).round() as u32;
        let limit = (limit_m * 10.0).round() as u32;
        if first <= limit {
            best.insert(start.node, first);
            queue.push(Reverse((first, start.node)));
        }
        while let Some(Reverse((distance, node))) = queue.pop() {
            if best.get(&node).is_some_and(|&d| d < distance) {
                continue;
            }
            let (from, to) = (
                self.offsets[node as usize] as usize,
                self.offsets[node as usize + 1] as usize,
            );
            for slot in from..to {
                let next = self.targets[slot];
                let candidate = distance + (self.metres[slot] * 10.0).round() as u32;
                if candidate <= limit && best.get(&next).is_none_or(|&d| candidate < d) {
                    best.insert(next, candidate);
                    queue.push(Reverse((candidate, next)));
                }
            }
        }
        best.into_iter()
            .map(|(node, d)| (node, f64::from(d) / 10.0))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A square block: four corners, the walk around is 4 × 100 m.
    fn square() -> WalkGraph {
        let m = 1.0 / crate::geo::METRES_PER_DEGREE;
        let points = vec![
            Point::new(5.3, -4.0),
            Point::new(5.3, -4.0 + 100.0 * m),
            Point::new(5.3 + 100.0 * m, -4.0 + 100.0 * m),
            Point::new(5.3 + 100.0 * m, -4.0),
        ];
        WalkGraph::new(
            points,
            &[(0, 1, 100.0), (1, 2, 100.0), (2, 3, 100.0), (3, 0, 100.0)],
        )
    }

    #[test]
    fn shortest_paths_follow_the_streets() {
        let graph = square();
        let from = Snap {
            node: 0,
            metres: 5.0,
        };
        let d = graph.distances(from, 1000.0);
        assert!((d[&2] - 205.0).abs() < 0.2, "{d:?}");
        assert!((d[&1] - 105.0).abs() < 0.2);
        assert_eq!(graph.edge_count(), 4);
    }

    #[test]
    fn the_search_stops_at_its_bound() {
        let d = square().distances(
            Snap {
                node: 0,
                metres: 0.0,
            },
            150.0,
        );
        assert_eq!(d.len(), 3);
        assert!(!d.contains_key(&2));
    }

    #[test]
    fn points_far_from_the_graph_are_not_attached() {
        let graph = square();
        assert_eq!(graph.snap(Point::new(5.3, -4.0)).map(|s| s.node), Some(0));
        assert!(graph.snap(Point::new(5.31, -4.0)).is_none());
    }
}
