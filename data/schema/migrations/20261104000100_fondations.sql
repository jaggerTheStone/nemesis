-- migrate:up

-- Extensions (partagées par toute la base, jamais supprimées par une migration).
create extension if not exists postgis;
create extension if not exists pg_trgm;
create extension if not exists unaccent;

-- Schémas (ADR-005) : réseau, mobilité, identité, exploitation.
create schema network;
create schema mobility;
create schema identity;
create schema ops;

comment on schema network is 'Réseau et données de référence : villes, lieux, arrêts, lignes, versions.';
comment on schema mobility is 'Observations, traces, positions et états dérivés. Aucune identité : seulement des pseudonymes.';
comment on schema identity is 'Comptes, appareils, consentements, récompenses. Accès réservé au rôle nemesis_identity (H-016).';
comment on schema ops is 'Exploitation : comptes du back-office, journal d''audit, maintenance des partitions.';

-- Rôles de groupe (sans connexion). Les comptes de connexion en deviennent membres.
-- Les rôles appartiennent à l'instance : une migration descendante ne les supprime pas.
do $$
declare
    role_name text;
begin
    foreach role_name in array array['nemesis_api', 'nemesis_identity', 'nemesis_analyst', 'nemesis_maintenance'] loop
        if not exists (select from pg_roles where rolname = role_name) then
            execute format('create role %I nologin', role_name);
        end if;
    end loop;
end
$$;

-- Normalisation du texte pour la recherche (partie 8.4) : minuscules, sans accents,
-- ponctuation remplacée par des espaces. unaccent est STABLE ; l'appel avec un
-- dictionnaire explicite permet de déclarer la fonction IMMUTABLE (usage courant).
create function network.normalize_text(value text) returns text
    language sql immutable parallel safe strict
    return btrim(regexp_replace(lower(public.unaccent('public.unaccent'::regdictionary, value)), '[^a-z0-9]+', ' ', 'g'));

-- Mise à jour automatique de updated_at.
create function ops.touch_updated_at() returns trigger
    language plpgsql
as $$
begin
    new.updated_at := now();
    return new;
end
$$;

-- Référentiels (données de vocabulaire, pas des données métier).
create table network.mode (
    code text primary key,
    family text not null check (family in ('conventionne', 'artisanal', 'lagunaire', 'ferre', 'individuel', 'interurbain')),
    sort_order smallint not null,
    label_key text not null
);

insert into network.mode (code, family, sort_order, label_key) values
    ('bus_sotra', 'conventionne', 10, 'mode.bus_sotra'),
    ('bus_express', 'conventionne', 20, 'mode.bus_express'),
    ('bateau_bus', 'lagunaire', 30, 'mode.bateau_bus'),
    ('pinasse', 'lagunaire', 40, 'mode.pinasse'),
    ('gbaka', 'artisanal', 50, 'mode.gbaka'),
    ('woro_communal', 'artisanal', 60, 'mode.woro_communal'),
    ('woro_intercommunal', 'artisanal', 70, 'mode.woro_intercommunal'),
    ('taxi_compteur', 'individuel', 80, 'mode.taxi_compteur'),
    ('moto_taxi', 'individuel', 90, 'mode.moto_taxi'),
    ('tricycle', 'individuel', 100, 'mode.tricycle'),
    ('metro', 'ferre', 110, 'mode.metro'),
    ('brt', 'conventionne', 120, 'mode.brt'),
    ('car_interurbain', 'interurbain', 130, 'mode.car_interurbain');

create table network.stop_kind (
    code text primary key,
    label_key text not null
);

insert into network.stop_kind (code, label_key) values
    ('sotra_stop', 'stop_kind.sotra_stop'),
    ('gare_artisanale', 'stop_kind.gare_artisanale'),
    ('arret_informel', 'stop_kind.arret_informel'),
    ('arret_minute', 'stop_kind.arret_minute'),
    ('embarcadere', 'stop_kind.embarcadere'),
    ('station_metro', 'stop_kind.station_metro'),
    ('station_brt', 'stop_kind.station_brt'),
    ('gare_interurbaine', 'stop_kind.gare_interurbaine');

-- Sources de données et leurs licences (docs/DATA.md).
create table network.source (
    id text primary key check (id ~ '^[a-z0-9_]+$'),
    name text not null,
    license text not null,
    attribution text,
    url text,
    is_fictional boolean not null default false
);

-- Comptes du back-office (partie 6.3). Double authentification obligatoire (12.3).
create table ops.staff_account (
    id uuid primary key default gen_random_uuid(),
    display_name text not null,
    email text not null,
    role text not null check (role in ('administrateur', 'curateur', 'moderateur', 'analyste', 'partenaire')),
    mfa_enabled boolean not null default false,
    active boolean not null default true,
    is_fictional boolean not null default false,
    created_at timestamptz not null default now(),
    constraint staff_account_mfa_required check (not active or mfa_enabled)
);

create unique index staff_account_email_key on ops.staff_account (lower(email));

-- migrate:down

drop schema ops cascade;
drop schema identity cascade;
drop schema mobility cascade;
drop schema network cascade;
