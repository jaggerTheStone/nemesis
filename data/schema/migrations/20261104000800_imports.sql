-- migrate:up

-- Imports de sources externes (I0.7) : provenance de chaque exécution, zones
-- intermédiaires pour le GTFS et OSM, et garde de licence (docs/DATA.md).

-- Usage permis par la licence d'une source. « evaluation » : analyse interne
-- seulement, par exemple sous licence non commerciale (H-030). Une telle source
-- n'entre jamais dans les tables du réseau, que l'appli publie.
alter table network.source
    add column usage text not null default 'produit' check (usage in ('produit', 'evaluation')),
    add column license_url text,
    add unique (id, is_fictional);

comment on column network.source.usage is
    'produit : publiable dans l''appli ; evaluation : analyse interne seulement (H-030).';

-- Une exécution d'import : quel fichier, d'où, quand, avec quelle empreinte.
create table ops.import_run (
    id uuid primary key default gen_random_uuid(),
    source_id text not null,
    is_fictional boolean not null,
    kind text not null check (kind in ('osm', 'gtfs')),
    url text not null,
    file_name text not null,
    sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$'),
    size_bytes bigint not null check (size_bytes >= 0),
    verified_by text not null check (verified_by in ('sha256_epinglee', 'md5_publiee', 'fichier_du_depot')),
    retrieved_at timestamptz not null,
    data_timestamp timestamptz,
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    status text not null default 'en_cours' check (status in ('en_cours', 'termine', 'echec')),
    counts jsonb not null default '{}',
    foreign key (source_id, is_fictional) references network.source (id, is_fictional),
    check ((status = 'en_cours') = (finished_at is null))
);

comment on column ops.import_run.data_timestamp is
    'Date des données selon la source : en-tête de l''extrait OSM, feed_info du GTFS.';

-- GTFS tel que publié : chaque ligne de chaque fichier, valeurs intactes (texte).
-- Rien n'est corrigé à l'import ; les vues typées laissent à null une valeur
-- illisible, que le rapport du validateur signale.
create schema staging_gtfs;

create table staging_gtfs.file (
    import_run_id uuid not null references ops.import_run (id) on delete cascade,
    file_name text not null check (file_name ~ '^[a-z0-9_]+\.txt$'),
    columns text[] not null,
    row_count integer not null check (row_count >= 0),
    primary key (import_run_id, file_name)
);

create table staging_gtfs.record (
    import_run_id uuid not null,
    file_name text not null,
    line_no integer not null check (line_no >= 2),
    data jsonb not null,
    primary key (import_run_id, file_name, line_no),
    foreign key (import_run_id, file_name) references staging_gtfs.file on delete cascade
);

create function staging_gtfs.as_double(value text) returns double precision
    language sql immutable parallel safe
    return case when value ~ '^\s*[-+]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][-+]?[0-9]+)?\s*$'
                then value::double precision end;

create function staging_gtfs.as_integer(value text) returns integer
    language sql immutable parallel safe
    return case when value ~ '^\s*[-+]?[0-9]{1,9}\s*$' then value::integer end;

create view staging_gtfs.stop as
select r.import_run_id, r.line_no,
       r.data ->> 'stop_id' as stop_id,
       r.data ->> 'stop_name' as stop_name,
       coalesce(staging_gtfs.as_integer(r.data ->> 'location_type'), 0) as location_type,
       nullif(r.data ->> 'parent_station', '') as parent_station,
       case when c.lat between -90 and 90 and c.lon between -180 and 180
            then public.st_setsrid(public.st_makepoint(c.lon, c.lat), 4326) end as geom
from staging_gtfs.record r
cross join lateral (select staging_gtfs.as_double(r.data ->> 'stop_lat') as lat,
                           staging_gtfs.as_double(r.data ->> 'stop_lon') as lon) c
where r.file_name = 'stops.txt';

create view staging_gtfs.route as
select r.import_run_id, r.line_no,
       r.data ->> 'route_id' as route_id,
       nullif(r.data ->> 'agency_id', '') as agency_id,
       nullif(r.data ->> 'route_short_name', '') as route_short_name,
       nullif(r.data ->> 'route_long_name', '') as route_long_name,
       staging_gtfs.as_integer(r.data ->> 'route_type') as route_type
from staging_gtfs.record r
where r.file_name = 'routes.txt';

create view staging_gtfs.trip as
select r.import_run_id, r.line_no,
       r.data ->> 'trip_id' as trip_id,
       r.data ->> 'route_id' as route_id,
       r.data ->> 'service_id' as service_id,
       nullif(r.data ->> 'shape_id', '') as shape_id,
       staging_gtfs.as_integer(r.data ->> 'direction_id') as direction_id,
       nullif(r.data ->> 'trip_headsign', '') as trip_headsign
from staging_gtfs.record r
where r.file_name = 'trips.txt';

create view staging_gtfs.stop_time as
select r.import_run_id, r.line_no,
       r.data ->> 'trip_id' as trip_id,
       r.data ->> 'stop_id' as stop_id,
       staging_gtfs.as_integer(r.data ->> 'stop_sequence') as stop_sequence
from staging_gtfs.record r
where r.file_name = 'stop_times.txt';

create view staging_gtfs.shape_point as
select r.import_run_id, r.line_no,
       r.data ->> 'shape_id' as shape_id,
       staging_gtfs.as_integer(r.data ->> 'shape_pt_sequence') as sequence,
       case when c.lat between -90 and 90 and c.lon between -180 and 180
            then public.st_setsrid(public.st_makepoint(c.lon, c.lat), 4326) end as geom
from staging_gtfs.record r
cross join lateral (select staging_gtfs.as_double(r.data ->> 'shape_pt_lat') as lat,
                           staging_gtfs.as_double(r.data ->> 'shape_pt_lon') as lon) c
where r.file_name = 'shapes.txt';

-- Tables d'osm2pgsql (style data/pipelines/src/nemesis_pipelines/osm/nemesis.lua),
-- recréées à chaque import complet.
create schema staging_osm;

-- Lieux issus d'une source externe : référence dans la source et import d'origine,
-- pour que les imports suivants mettent à jour au lieu de dupliquer.
alter table network.place
    add column external_ref text check (external_ref is null or btrim(external_ref) <> ''),
    add column import_run_id uuid references ops.import_run (id);

create unique index place_external_ref_key on network.place (city_id, source_id, external_ref)
    where external_ref is not null;

-- Garde de licence : une source réservée à l'évaluation n'entre pas dans le réseau.
create function network.reject_evaluation_source() returns trigger
    language plpgsql
as $$
begin
    if exists (select from network.source where id = new.source_id and usage = 'evaluation') then
        raise exception 'la source % est réservée à l''évaluation (licence) : interdite dans %.%',
            new.source_id, tg_table_schema, tg_table_name
            using errcode = 'NM004';
    end if;
    return new;
end;
$$;

create trigger admin_area_source_usage before insert or update of source_id on network.admin_area
    for each row execute function network.reject_evaluation_source();
create trigger place_source_usage before insert or update of source_id on network.place
    for each row execute function network.reject_evaluation_source();
create trigger stop_source_usage before insert or update of source_id on network.stop
    for each row execute function network.reject_evaluation_source();
create trigger route_source_usage before insert or update of source_id on network.route
    for each row execute function network.reject_evaluation_source();
create trigger incident_source_usage before insert or update of source_id on network.incident
    for each row execute function network.reject_evaluation_source();

-- Une source déjà utilisée par le réseau ne peut pas passer en évaluation.
create function network.protect_source_usage() returns trigger
    language plpgsql
as $$
begin
    if new.usage = 'evaluation' and old.usage <> 'evaluation' and (
        exists (select from network.admin_area where source_id = new.id)
        or exists (select from network.place where source_id = new.id)
        or exists (select from network.stop where source_id = new.id)
        or exists (select from network.route where source_id = new.id)
        or exists (select from network.incident where source_id = new.id)) then
        raise exception 'la source % est déjà utilisée par le réseau', new.id using errcode = 'NM004';
    end if;
    return new;
end;
$$;

create trigger source_usage_protect before update of usage on network.source
    for each row execute function network.protect_source_usage();

-- Droits : l'API ne lit pas les zones intermédiaires ; les analystes les lisent.
revoke all on schema staging_gtfs, staging_osm from public;
grant usage on schema staging_gtfs, staging_osm to nemesis_analyst;
grant select on all tables in schema staging_gtfs to nemesis_analyst;
alter default privileges in schema staging_gtfs grant select on tables to nemesis_analyst;
alter default privileges in schema staging_osm grant select on tables to nemesis_analyst;
grant select on ops.import_run to nemesis_analyst;
grant select on ops.import_run to nemesis_api;

-- migrate:down

revoke select on ops.import_run from nemesis_api, nemesis_analyst;
alter default privileges in schema staging_osm revoke select on tables from nemesis_analyst;
alter default privileges in schema staging_gtfs revoke select on tables from nemesis_analyst;
drop trigger source_usage_protect on network.source;
drop function network.protect_source_usage();
drop trigger incident_source_usage on network.incident;
drop trigger route_source_usage on network.route;
drop trigger stop_source_usage on network.stop;
drop trigger place_source_usage on network.place;
drop trigger admin_area_source_usage on network.admin_area;
drop function network.reject_evaluation_source();
drop index network.place_external_ref_key;
alter table network.place drop column import_run_id, drop column external_ref;
drop schema staging_osm cascade;
drop schema staging_gtfs cascade;
drop table ops.import_run;
alter table network.source
    drop constraint source_id_is_fictional_key,
    drop column license_url,
    drop column usage;
