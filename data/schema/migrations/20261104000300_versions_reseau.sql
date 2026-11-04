-- migrate:up

-- Versionnement du réseau (partie 6.3, ADR-008) : les tables du réseau portent
-- l'état publié courant ; chaque modification passe par une demande revue par une
-- autre personne, puis par une version publiée qui en garde la trace avant/après.

create table network.network_version (
    id bigint generated always as identity primary key,
    city_id uuid not null,
    is_fictional boolean not null default false,
    number integer not null check (number > 0),
    status text not null default 'brouillon' check (status in ('brouillon', 'en_revue', 'publiee', 'abandonnee')),
    effective_from timestamptz,
    published_at timestamptz,
    notes text,
    export_uri text,
    created_at timestamptz not null default now(),
    unique (city_id, number),
    check ((status = 'publiee') = (published_at is not null)),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional)
);

comment on column network.network_version.export_uri is 'Archive GTFS et pack ville produits pour cette version (stockage objet).';

-- Numéro de version attribué par ville, à la suite.
create function network.assign_version_number() returns trigger
    language plpgsql
as $$
begin
    if new.number is null then
        perform 1 from network.city where id = new.city_id for update;
        select coalesce(max(number), 0) + 1 into new.number
            from network.network_version where city_id = new.city_id;
    end if;
    return new;
end
$$;

create trigger network_version_number before insert on network.network_version
    for each row execute function network.assign_version_number();

-- Une version publiée est immuable : on corrige par une nouvelle version.
create function network.protect_published_version() returns trigger
    language plpgsql
as $$
begin
    if old.status = 'publiee' then
        raise exception 'la version % (ville %) est publiée : elle ne peut plus être modifiée', old.number, old.city_id
            using errcode = 'NM002';
    end if;
    if tg_op = 'UPDATE' and new.status = 'publiee' and current_setting('nemesis.publishing', true) is distinct from 'on' then
        raise exception 'publier une version passe par network.publish_version()'
            using errcode = 'NM002';
    end if;
    return case when tg_op = 'DELETE' then old else new end;
end
$$;

create trigger network_version_protect before update or delete on network.network_version
    for each row execute function network.protect_published_version();

create table network.change_request (
    id uuid primary key default gen_random_uuid(),
    city_id uuid not null,
    is_fictional boolean not null default false,
    title text not null,
    operations jsonb not null check (jsonb_typeof(operations) = 'array'),
    status text not null default 'proposee' check (status in ('proposee', 'approuvee', 'rejetee', 'appliquee')),
    proposed_by uuid not null references ops.staff_account (id),
    reviewed_by uuid references ops.staff_account (id),
    review_reason text,
    network_version_id bigint references network.network_version (id),
    created_at timestamptz not null default now(),
    reviewed_at timestamptz,
    constraint change_request_reviewer_differs check (reviewed_by is null or reviewed_by <> proposed_by),
    constraint change_request_reviewed check (status = 'proposee' or (reviewed_by is not null and reviewed_at is not null)),
    constraint change_request_reject_reason check (status <> 'rejetee' or nullif(btrim(review_reason), '') is not null),
    constraint change_request_applied_version check (status <> 'appliquee' or network_version_id is not null),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional)
);

comment on column network.change_request.operations is 'Liste d''opérations proposées : [{"op": "update", "table": "stop", "id": "…", "set": {…}}].';

-- Historique avant/après de chaque entité modifiée : comparaison et retour arrière.
create table network.entity_change (
    id bigint generated always as identity primary key,
    city_id uuid not null,
    is_fictional boolean not null default false,
    network_version_id bigint not null references network.network_version (id),
    change_request_id uuid references network.change_request (id),
    entity_table text not null,
    entity_id uuid not null,
    operation text not null check (operation in ('insert', 'update', 'delete')),
    before jsonb,
    after jsonb,
    changed_at timestamptz not null default now(),
    check ((operation = 'insert') = (before is null)),
    check ((operation = 'delete') = (after is null)),
    foreign key (city_id, is_fictional) references network.city (id, is_fictional)
);

create index entity_change_entity_idx on network.entity_change (entity_table, entity_id, network_version_id);

-- Publication d'une version. Refusée pour une ville fictive en production
-- (réglage nemesis.environment = 'production', posé par ALTER DATABASE).
create function network.publish_version(version_id bigint) returns network.network_version
    language plpgsql
as $$
declare
    version network.network_version;
    fictional boolean;
begin
    select * into version from network.network_version where id = version_id for update;
    if not found then
        raise exception 'version % introuvable', version_id using errcode = 'NM002';
    end if;
    if version.status <> 'en_revue' then
        raise exception 'seule une version en revue peut être publiée (statut actuel : %)', version.status
            using errcode = 'NM002';
    end if;
    select is_fictional into fictional from network.city where id = version.city_id;
    if fictional and current_setting('nemesis.environment', true) = 'production' then
        raise exception 'publication refusée : la ville est fictive et l''environnement est la production'
            using errcode = 'NM001';
    end if;

    perform set_config('nemesis.publishing', 'on', true);
    update network.network_version
        set status = 'publiee', published_at = now(), effective_from = coalesce(effective_from, now())
        where id = version_id
        returning * into version;
    perform set_config('nemesis.publishing', 'off', true);
    return version;
end
$$;

-- migrate:down

drop function network.publish_version(bigint);
drop table network.entity_change;
drop table network.change_request;
drop table network.network_version;
drop function network.protect_published_version();
drop function network.assign_version_number();
