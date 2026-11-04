# services/routing

Moteur d'itinéraires en Rust (cible : McRAPTOR, option B de la partie 8.1, à confirmer par l'ADR-003 après le spike I0.8).

- `routing-core` : bibliothèque partagée entre le serveur et le téléphone.
- `routing-cli` : binaire `routing` ; la commande `plan` arrive en I0.9.
- Contrôles : `make check-rust` ; audit : `make audit-rust` (cargo-deny : vulnérabilités, licences permissives, sources).
- Version de Rust figée dans `rust-toolchain.toml`.
