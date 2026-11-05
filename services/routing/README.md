# services/routing

Moteur d'itinéraires en Rust (cible : McRAPTOR, option B de la partie 8.1, à confirmer par l'ADR-003 après le spike I0.8).

- `routing-core` : bibliothèque partagée entre le serveur et le téléphone.
- `routing-core` (I0.8) :
  - lecture du GTFS, avec les calendriers ;
  - réseau à fréquences : une variante par course, ses tranches et des correspondances à pied ;
  - points de montée virtuels le long des tracés (option) ;
  - modèles d'attente : médiane du régime B, attentes en direct simulées ;
  - RAPTOR où l'attente est le coût de montée.
- `routing-cli` : binaire `routing`.
  - `routing spike` mesure l'option B du spike ([tools/routing-spike](../../tools/routing-spike/README.md)).
  - La commande `plan` arrive en I0.9.
- Simplifications du spike, reprises en I0.9 :
  - la marche est estimée en ligne droite × 1,3, sans le graphe piéton d'OSM ;
  - le front de Pareto ne porte que sur l'heure d'arrivée et le nombre de véhicules (McRAPTOR complet en I0.9).
- Contrôles : `make check-rust` ; audit : `make audit-rust` (cargo-deny : vulnérabilités, licences permissives, sources).
- Version de Rust figée dans `rust-toolchain.toml`.
