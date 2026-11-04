-- migrate:up

-- Aucune table de ce schéma ne contient d'identité : seulement des pseudonymes
-- (H-016). Les tables d'événements sont partitionnées par jour (ADR-005) ; leurs
-- partitions sont créées et supprimées par ops.maintain_partitions().

-- Pseudonyme stable d'un contributeur, pour la réputation et la lutte contre la
-- fraude (partie 7.5). Distinct du pseudonyme des traces, qui est renouvelé.
create table mobility.trust_score (
    contributor_pseudonym text primary key,
    alpha real not null default 1 check (alpha > 0),
    beta real not null default 3 check (beta > 0),
    quarantined boolean not null default false,
    is_fictional boolean not null default false,
    updated_at timestamptz not null default now()
);

comment on table mobility.trust_score is 'Réputation Bêta(alpha, beta) par contributeur ; nouveau compte : Bêta(1, 3), poids 0,25 (ALGORITHMES.md, 1.6).';

-- Observations brutes (partie 7.2). L'identifiant est généré par le téléphone et
-- sert de clé d'idempotence : un renvoi après coupure n'est jamais compté deux fois.
create table mobility.observation (
    id uuid not null,
    observed_at timestamptz not null,
    received_at timestamptz not null default now(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    kind text not null check (kind in (
        'dans_la_file', 'file', 'vehicules_presents', 'montee', 'depart', 'vehicule_plein', 'prix_paye',
        'incident', 'arret_deplace', 'deviation', 'photo', 'attente_reelle', 'nouveau_lieu')),
    stop_id uuid,
    route_id uuid,
    direction_id smallint check (direction_id in (0, 1)),
    geom geometry(Point, 4326),
    accuracy_m real check (accuracy_m >= 0),
    payload jsonb not null default '{}' check (jsonb_typeof(payload) = 'object'),
    source_kind text not null check (source_kind in ('usager', 'chef_de_gare', 'eclaireur', 'pro', 'partenaire', 'systeme')),
    contributor_pseudonym text,
    weight real check (weight >= 0),
    status text not null default 'recue' check (status in ('recue', 'acceptee', 'rejetee', 'quarantaine')),
    reject_reason text,
    primary key (id, observed_at),
    check (observed_at <= received_at + interval '5 minutes'),
    check (status <> 'rejetee' or reject_reason is not null),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (stop_id, city_id) references network.stop (id, city_id),
    foreign key (route_id, city_id) references network.route (id, city_id)
) partition by range (observed_at);

create index observation_stop_idx on mobility.observation (stop_id, observed_at);
create index observation_contributor_idx on mobility.observation (contributor_pseudonym, observed_at);

-- Segments de trajets suivis, déjà tronqués de 300 m au départ et à l'arrivée sur
-- le téléphone (partie 7.4). Le pseudonyme est renouvelé : il ne relie pas les jours.
create table mobility.trace_segment (
    id uuid not null,
    started_at timestamptz not null,
    ended_at timestamptz not null,
    received_at timestamptz not null default now(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    trace_pseudonym text not null,
    geom geometry(LineStringM, 4326) not null,
    detected_mode text references network.mode (code),
    route_id uuid,
    primary key (id, started_at),
    check (ended_at >= started_at),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (route_id, city_id) references network.route (id, city_id)
) partition by range (started_at);

-- Sessions de véhicules : chauffeurs Pro en service, partenaires, ou véhicules
-- inférés. Jamais de plaque ni de nom (parties 3.5 et 12.4).
create table mobility.vehicle_session (
    id uuid primary key default gen_random_uuid(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    source_kind text not null check (source_kind in ('pro', 'partenaire', 'infere')),
    vehicle_pseudonym text not null,
    route_id uuid,
    direction_id smallint check (direction_id in (0, 1)),
    started_at timestamptz not null,
    ended_at timestamptz,
    check (ended_at is null or ended_at >= started_at),
    unique (id, city_id),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (route_id, city_id) references network.route (id, city_id)
);

create sequence mobility.position_event_id_seq;

create table mobility.position_event (
    id bigint not null default nextval('mobility.position_event_id_seq'),
    recorded_at timestamptz not null,
    received_at timestamptz not null default now(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    vehicle_session_id uuid not null,
    geom geometry(Point, 4326) not null,
    speed_mps real check (speed_mps >= 0),
    heading_deg smallint check (heading_deg between 0 and 359),
    accuracy_m real check (accuracy_m >= 0),
    primary key (id, recorded_at),
    check (recorded_at <= received_at + interval '5 minutes'),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (vehicle_session_id, city_id) references mobility.vehicle_session (id, city_id) on delete cascade
) partition by range (recorded_at);

alter sequence mobility.position_event_id_seq owned by mobility.position_event.id;

-- État publié d'une gare ou d'un arrêt (partie 7.2). Toute estimation porte sa
-- fraîcheur, sa confiance et sa source : la règle 1.3.2 est inscrite dans le schéma.
create table mobility.queue_state (
    id bigint generated always as identity primary key,
    city_id uuid not null,
    is_fictional boolean not null default false,
    stop_id uuid not null,
    route_id uuid,
    direction_id smallint check (direction_id in (0, 1)),
    level text not null check (level in ('peu', 'moyen', 'beaucoup', 'tres_long', 'inconnu')),
    people_low integer check (people_low >= 0),
    people_high integer,
    vehicles_low integer check (vehicles_low >= 0),
    vehicles_high integer,
    regime text check (regime in ('A', 'B', 'C')),
    wait_p50_s integer check (wait_p50_s >= 0),
    wait_p80_s integer,
    confidence text not null check (confidence in ('faible', 'moyenne', 'elevee')),
    main_source text not null check (main_source in ('usagers', 'chef_de_gare', 'gps', 'historique', 'partenaire')),
    last_observed_at timestamptz not null,
    computed_at timestamptz not null default now(),
    check (people_high is null or people_high >= people_low),
    check (vehicles_high is null or vehicles_high >= vehicles_low),
    check ((wait_p50_s is null) = (wait_p80_s is null) and (wait_p80_s is null or wait_p80_s >= wait_p50_s)),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (stop_id, city_id) references network.stop (id, city_id),
    foreign key (route_id, city_id) references network.route (id, city_id)
);

create unique index queue_state_key on mobility.queue_state
    (stop_id, coalesce(route_id, '00000000-0000-0000-0000-000000000000'::uuid), coalesce(direction_id, -1));

-- Profils historiques d'attente (ext_wait_profiles.txt, ADR-007).
create table mobility.wait_profile (
    id bigint generated always as identity primary key,
    city_id uuid not null,
    is_fictional boolean not null default false,
    stop_id uuid not null,
    route_id uuid not null,
    direction_id smallint not null check (direction_id in (0, 1)),
    day_type text not null check (day_type in ('ouvrable', 'samedi', 'dimanche', 'ferie')),
    slot_start time not null check (extract(minute from slot_start)::int % 15 = 0 and extract(second from slot_start) = 0),
    regime text not null check (regime in ('A', 'B', 'C')),
    wait_p50_s integer not null check (wait_p50_s >= 0),
    wait_p80_s integer not null,
    n_obs integer not null check (n_obs >= 0),
    n_contributors integer not null check (n_contributors >= 0),
    confidence text not null check (confidence in ('faible', 'moyenne', 'elevee')),
    updated_at timestamptz not null default now(),
    unique (stop_id, route_id, direction_id, day_type, slot_start),
    check (wait_p80_s >= wait_p50_s),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (stop_id, city_id) references network.stop (id, city_id),
    foreign key (route_id, city_id) references network.route (id, city_id)
);

-- Prix payés (partie 7.2). Conservés 12 mois, comme les observations brutes.
create table mobility.fare_observation (
    id uuid primary key default gen_random_uuid(),
    observation_id uuid,
    observed_at timestamptz not null,
    city_id uuid not null,
    is_fictional boolean not null default false,
    route_id uuid not null,
    from_stop_id uuid,
    to_stop_id uuid,
    from_area_id uuid,
    to_area_id uuid,
    amount_xof integer not null check (amount_xof > 0 and amount_xof <= 100000),
    conditions text[] not null default '{}' check (conditions <@ array['pointe', 'pluie', 'nuit', 'fete']),
    source_kind text not null check (source_kind in ('usager', 'chef_de_gare', 'eclaireur', 'pro', 'partenaire')),
    contributor_pseudonym text,
    weight real check (weight >= 0),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (route_id, city_id) references network.route (id, city_id),
    foreign key (from_stop_id, city_id) references network.stop (id, city_id),
    foreign key (to_stop_id, city_id) references network.stop (id, city_id),
    foreign key (from_area_id, city_id) references network.fare_area (id, city_id),
    foreign key (to_area_id, city_id) references network.fare_area (id, city_id)
);

create index fare_observation_route_idx on mobility.fare_observation (route_id, observed_at);

-- Prix estimés (ext_fare_estimates.txt) : centiles 10, 50 et 90, jamais inventés.
create table mobility.fare_estimate (
    id bigint generated always as identity primary key,
    city_id uuid not null,
    is_fictional boolean not null default false,
    route_id uuid not null,
    from_area_id uuid not null,
    to_area_id uuid not null,
    condition text not null check (condition in ('normale', 'pointe', 'pluie', 'nuit', 'fete')),
    fare_p10 integer not null check (fare_p10 > 0),
    fare_p50 integer not null,
    fare_p90 integer not null,
    n_obs integer not null check (n_obs > 0),
    n_contributors integer not null check (n_contributors > 0),
    last_observed_at timestamptz not null,
    confidence text not null check (confidence in ('faible', 'moyenne', 'elevee')),
    updated_at timestamptz not null default now(),
    unique (route_id, from_area_id, to_area_id, condition),
    check (fare_p10 <= fare_p50 and fare_p50 <= fare_p90),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (route_id, city_id) references network.route (id, city_id),
    foreign key (from_area_id, city_id) references network.fare_area (id, city_id),
    foreign key (to_area_id, city_id) references network.fare_area (id, city_id)
);

-- Vitesses par tronçon OSM et par tranche de 15 min (partie 8.6).
create table mobility.segment_speed (
    id bigint generated always as identity primary key,
    city_id uuid not null,
    is_fictional boolean not null default false,
    osm_way_id bigint not null,
    direction smallint not null check (direction in (0, 1)),
    day_type text not null check (day_type in ('ouvrable', 'samedi', 'dimanche', 'ferie')),
    slot_start time not null check (extract(minute from slot_start)::int % 15 = 0 and extract(second from slot_start) = 0),
    speed_p50_mps real not null check (speed_p50_mps >= 0),
    free_flow_mps real check (free_flow_mps > 0),
    n_obs integer not null check (n_obs >= 0),
    updated_at timestamptz not null default now(),
    unique (city_id, osm_way_id, direction, day_type, slot_start),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional)
);

-- migrate:down

drop table mobility.segment_speed;
drop table mobility.fare_estimate;
drop table mobility.fare_observation;
drop table mobility.wait_profile;
drop table mobility.queue_state;
drop table mobility.position_event;
drop table mobility.vehicle_session;
drop table mobility.trace_segment;
drop table mobility.observation;
drop table mobility.trust_score;
