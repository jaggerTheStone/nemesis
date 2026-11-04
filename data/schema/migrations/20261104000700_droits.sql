-- migrate:up

-- Droits par rôle (ADR-005, H-016). Les rôles de connexion héritent de ces rôles
-- de groupe ; aucun accès n'est donné à PUBLIC.

revoke all on schema network, mobility, identity, ops from public;
revoke execute on function ops.maintain_partitions(timestamptz), ops.purge_expired(timestamptz) from public;

-- API principale : réseau, mobilité, journal d'audit. Aucun accès à l'identité.
grant usage on schema network, mobility, ops to nemesis_api;
grant select, insert, update, delete on all tables in schema network to nemesis_api;
grant select, insert, update on all tables in schema mobility to nemesis_api;
grant select on ops.staff_account to nemesis_api;
grant select, insert on ops.audit_log to nemesis_api;
grant usage, select on all sequences in schema network, mobility to nemesis_api;
alter default privileges in schema network grant select, insert, update, delete on tables to nemesis_api;
alter default privileges in schema mobility grant select, insert, update on tables to nemesis_api;

-- Identité : comptes, appareils, consentements, récompenses, et le strict nécessaire
-- des observations pour attribuer les points des contributions validées.
grant usage on schema identity, mobility, ops to nemesis_identity;
grant select, insert, update, delete on all tables in schema identity to nemesis_identity;
grant usage, select on all sequences in schema identity to nemesis_identity;
grant select (id, observed_at, status, contributor_pseudonym) on mobility.observation to nemesis_identity;
grant select, insert on ops.audit_log to nemesis_identity;
alter default privileges in schema identity grant select, insert, update, delete on tables to nemesis_identity;

-- Analystes : le réseau et les agrégats, jamais les données brutes.
grant usage on schema network, mobility to nemesis_analyst;
grant select on all tables in schema network to nemesis_analyst;
grant select on mobility.queue_state, mobility.wait_profile, mobility.fare_estimate, mobility.segment_speed
    to nemesis_analyst;

-- Maintenance planifiée : partitions et purges.
grant usage on schema ops to nemesis_maintenance;
grant execute on function ops.maintain_partitions(timestamptz), ops.purge_expired(timestamptz) to nemesis_maintenance;

-- migrate:down

alter default privileges in schema identity revoke select, insert, update, delete on tables from nemesis_identity;
alter default privileges in schema mobility revoke select, insert, update on tables from nemesis_api;
alter default privileges in schema network revoke select, insert, update, delete on tables from nemesis_api;
revoke all on all tables in schema network, mobility, identity, ops from nemesis_api, nemesis_identity, nemesis_analyst;
revoke all on all sequences in schema network, mobility, identity from nemesis_api, nemesis_identity;
revoke all on schema network, mobility, identity, ops from nemesis_api, nemesis_identity, nemesis_analyst, nemesis_maintenance;
revoke execute on function ops.maintain_partitions(timestamptz), ops.purge_expired(timestamptz) from nemesis_maintenance;
