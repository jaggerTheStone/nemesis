-- migrate:up

-- Règle commune à toutes les tables métier : (city_id, is_fictional) référence
-- network.city (id, is_fictional). Une ligne a donc toujours le même statut fictif
-- que sa ville : la base interdit de mêler données fictives et réelles (règle 1.3.1).
-- Les références entre entités passent par (id, city_id) : pas de mélange entre villes.

create table network.city (
    id uuid primary key default gen_random_uuid(),
    code text not null unique check (code ~ '^[a-z0-9-]+$'),
    name text not null,
    timezone text not null default 'Africa/Abidjan',
    currency char(3) not null default 'XOF' check (currency ~ '^[A-Z]{3}$'),
    metric_srid integer not null references public.spatial_ref_sys (srid),
    bbox geometry(Polygon, 4326),
    is_fictional boolean not null default false,
    created_at timestamptz not null default now(),
    unique (id, is_fictional)
);

comment on column network.city.metric_srid is 'Projection métrique pour les calculs de distance (EPSG:32630 pour Abidjan, H-014).';

create table network.admin_area (
    id uuid primary key default gen_random_uuid(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    kind text not null check (kind in ('commune', 'quartier')),
    code text not null,
    name text not null,
    parent_id uuid,
    geom geometry(MultiPolygon, 4326),
    source_id text references network.source (id),
    unique (city_id, code),
    unique (id, city_id),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (parent_id, city_id) references network.admin_area (id, city_id)
);

create table network.place (
    id uuid primary key default gen_random_uuid(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    category text not null check (category in (
        'carrefour', 'pharmacie', 'eglise', 'mosquee', 'maquis', 'marche', 'gare', 'terminus',
        'ecole', 'quartier', 'commune', 'batiment_public', 'entreprise', 'autre')),
    name text not null,
    geom geometry(Point, 4326) not null,
    admin_area_id uuid,
    popularity real not null default 0 check (popularity >= 0),
    source_id text not null references network.source (id),
    confidence text not null default 'faible' check (confidence in ('faible', 'moyenne', 'elevee')),
    verification_status text not null default 'non_verifie'
        check (verification_status in ('non_verifie', 'verifie', 'rejete')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (id, city_id),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (admin_area_id, city_id) references network.admin_area (id, city_id)
);

create index place_geom_idx on network.place using gist (geom);
create trigger place_touch before update on network.place
    for each row execute function ops.touch_updated_at();

-- Noms et alias tels qu'on les dit (orthographes, abréviations, nouchi), partie 7.2.
create table network.place_alias (
    id bigint generated always as identity primary key,
    place_id uuid not null,
    city_id uuid not null,
    is_fictional boolean not null default false,
    alias text not null check (btrim(alias) <> ''),
    alias_kind text not null check (alias_kind in ('nom', 'orthographe', 'abreviation', 'nouchi', 'ancien_nom', 'autre')),
    language text not null default 'fr',
    normalized text generated always as (network.normalize_text(alias)) stored,
    phonetic_key text,
    unique (place_id, alias),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (place_id, city_id) references network.place (id, city_id) on delete cascade
);

create index place_alias_trgm_idx on network.place_alias using gin (normalized public.gin_trgm_ops);
create index place_alias_phonetic_idx on network.place_alias (phonetic_key) where phonetic_key is not null;

create table network.stop (
    id uuid primary key default gen_random_uuid(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    code text not null,
    kind text not null references network.stop_kind (code),
    name text not null,
    geom geometry(Point, 4326) not null,
    boarding_radius_m integer check (boarding_radius_m between 1 and 500),
    boarding_zone geometry(Polygon, 4326),
    parent_stop_id uuid,
    lighting text not null default 'inconnu' check (lighting in ('oui', 'non', 'inconnu')),
    shelter text not null default 'inconnu' check (shelter in ('oui', 'non', 'inconnu')),
    accessibility text not null default 'inconnu' check (accessibility in ('oui', 'non', 'inconnu')),
    active_start time,
    active_end time,
    source_id text not null references network.source (id),
    confidence text not null default 'faible' check (confidence in ('faible', 'moyenne', 'elevee')),
    verification_status text not null default 'non_verifie'
        check (verification_status in ('non_verifie', 'verifie', 'rejete')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (city_id, code),
    unique (id, city_id),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (parent_stop_id, city_id) references network.stop (id, city_id)
);

comment on column network.stop.boarding_zone is 'Zone de montée floue d''un arrêt informel (partie 7.2) ; à défaut, boarding_radius_m.';

create index stop_geom_idx on network.stop using gist (geom);
create trigger stop_touch before update on network.stop
    for each row execute function ops.touch_updated_at();

create table network.stop_alias (
    id bigint generated always as identity primary key,
    stop_id uuid not null,
    city_id uuid not null,
    is_fictional boolean not null default false,
    alias text not null check (btrim(alias) <> ''),
    alias_kind text not null check (alias_kind in ('nom', 'orthographe', 'abreviation', 'nouchi', 'ancien_nom', 'autre')),
    language text not null default 'fr',
    normalized text generated always as (network.normalize_text(alias)) stored,
    phonetic_key text,
    unique (stop_id, alias),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (stop_id, city_id) references network.stop (id, city_id) on delete cascade
);

create index stop_alias_trgm_idx on network.stop_alias using gin (normalized public.gin_trgm_ops);

-- Photos de gares, de lieux et de points de montée, avec modération.
create table network.photo (
    id uuid primary key default gen_random_uuid(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    place_id uuid,
    stop_id uuid,
    storage_key text not null,
    moderation_status text not null default 'en_attente'
        check (moderation_status in ('en_attente', 'acceptee', 'rejetee')),
    created_at timestamptz not null default now(),
    check (num_nonnulls(place_id, stop_id) = 1),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (place_id, city_id) references network.place (id, city_id) on delete cascade,
    foreign key (stop_id, city_id) references network.stop (id, city_id) on delete cascade
);

create table network.operator (
    id uuid primary key default gen_random_uuid(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    code text not null,
    name text not null,
    kind text not null check (kind in ('public', 'prive', 'cooperative', 'syndicat', 'generique')),
    unique (city_id, code),
    unique (id, city_id),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional)
);

create table network.route (
    id uuid primary key default gen_random_uuid(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    code text not null,
    operator_id uuid,
    mode text not null references network.mode (code),
    spoken_name text not null,
    commune_area_id uuid,
    body_color text,
    color_pattern text,
    markings text,
    announced_as text,
    active boolean not null default true,
    source_id text not null references network.source (id),
    confidence text not null default 'faible' check (confidence in ('faible', 'moyenne', 'elevee')),
    verification_status text not null default 'non_verifie'
        check (verification_status in ('non_verifie', 'verifie', 'rejete')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (city_id, code),
    unique (id, city_id),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (operator_id, city_id) references network.operator (id, city_id),
    foreign key (commune_area_id, city_id) references network.admin_area (id, city_id)
);

comment on column network.route.spoken_name is 'Nom tel qu''on le dit : « Yopougon–Adjamé ».';
comment on column network.route.announced_as is 'Ce que crie l''apprenti (ADR-007).';

create trigger route_touch before update on network.route
    for each row execute function ops.touch_updated_at();

create table network.route_pattern (
    id uuid primary key default gen_random_uuid(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    route_id uuid not null,
    code text not null,
    direction_id smallint not null check (direction_id in (0, 1)),
    headsign text,
    shape geometry(LineString, 4326),
    continuous_pickup boolean not null default false,
    continuous_drop_off boolean not null default false,
    valid_start time,
    valid_end time,
    variant_reason text,
    is_main boolean not null default true,
    unique (city_id, code),
    unique (id, city_id),
    check ((valid_start is null) = (valid_end is null)),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (route_id, city_id) references network.route (id, city_id) on delete cascade
);

comment on column network.route_pattern.variant_reason is 'Motif d''une variante : « terminus raccourci en cas de bouchon ».';

create table network.route_pattern_stop (
    route_pattern_id uuid not null,
    sequence integer not null check (sequence >= 0),
    stop_id uuid not null,
    city_id uuid not null,
    is_fictional boolean not null default false,
    distance_along_m real check (distance_along_m >= 0),
    is_virtual_boarding_point boolean not null default false,
    primary key (route_pattern_id, sequence),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (route_pattern_id, city_id) references network.route_pattern (id, city_id) on delete cascade,
    foreign key (stop_id, city_id) references network.stop (id, city_id)
);

comment on column network.route_pattern_stop.is_virtual_boarding_point is 'Point de montée virtuel le long du tracé, pour la montée continue (partie 8.1).';

create table network.service_profile (
    id bigint generated always as identity primary key,
    city_id uuid not null,
    is_fictional boolean not null default false,
    route_pattern_id uuid not null,
    stop_id uuid not null,
    day_type text not null check (day_type in ('ouvrable', 'samedi', 'dimanche', 'ferie')),
    slot_start time not null check (extract(minute from slot_start)::int % 15 = 0 and extract(second from slot_start) = 0),
    active boolean not null,
    headway_mean_s integer check (headway_mean_s > 0),
    headway_cv real check (headway_cv >= 0),
    departs_when_full boolean not null default false,
    seats integer check (seats > 0),
    n_obs integer not null default 0 check (n_obs >= 0),
    updated_at timestamptz not null default now(),
    unique (route_pattern_id, stop_id, day_type, slot_start),
    check (not active or headway_mean_s is not null or departs_when_full),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (route_pattern_id, city_id) references network.route_pattern (id, city_id) on delete cascade,
    foreign key (stop_id, city_id) references network.stop (id, city_id)
);

-- Zones tarifaires (GTFS-Fares v2, areas.txt) pour les prix observés et estimés.
create table network.fare_area (
    id uuid primary key default gen_random_uuid(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    code text not null,
    name text not null,
    geom geometry(MultiPolygon, 4326),
    unique (city_id, code),
    unique (id, city_id),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional)
);

create table network.fare_area_stop (
    fare_area_id uuid not null,
    stop_id uuid not null,
    city_id uuid not null,
    is_fictional boolean not null default false,
    primary key (fare_area_id, stop_id),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (fare_area_id, city_id) references network.fare_area (id, city_id) on delete cascade,
    foreign key (stop_id, city_id) references network.stop (id, city_id) on delete cascade
);

create table network.incident (
    id uuid primary key default gen_random_uuid(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    kind text not null check (kind in ('accident', 'inondation', 'route_barree', 'travaux', 'manifestation', 'autre')),
    geom geometry(Geometry, 4326) not null,
    severity text not null default 'moyenne' check (severity in ('faible', 'moyenne', 'forte')),
    starts_at timestamptz not null default now(),
    ends_at timestamptz,
    status text not null default 'signale' check (status in ('signale', 'confirme', 'resolu', 'rejete')),
    source_id text not null references network.source (id),
    created_at timestamptz not null default now(),
    check (ends_at is null or ends_at >= starts_at),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional)
);

create index incident_geom_idx on network.incident using gist (geom);
create index incident_active_idx on network.incident (city_id, starts_at) where status in ('signale', 'confirme');

create table network.partner_feed (
    id uuid primary key default gen_random_uuid(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    kind text not null check (kind in ('gtfs', 'gtfs_rt_positions', 'gtfs_rt_alertes', 'gtfs_rt_trajets', 'autre')),
    name text not null,
    url text,
    operator_id uuid,
    last_sync_at timestamptz,
    last_status text not null default 'inconnu' check (last_status in ('ok', 'erreur', 'inconnu')),
    last_error text,
    foreign key (city_id, is_fictional) references network.city (id, is_fictional),
    foreign key (operator_id, city_id) references network.operator (id, city_id)
);

-- migrate:down

drop table network.partner_feed;
drop table network.incident;
drop table network.fare_area_stop;
drop table network.fare_area;
drop table network.service_profile;
drop table network.route_pattern_stop;
drop table network.route_pattern;
drop table network.route;
drop table network.operator;
drop table network.photo;
drop table network.stop_alias;
drop table network.stop;
drop table network.place_alias;
drop table network.place;
drop table network.admin_area;
drop table network.city;
