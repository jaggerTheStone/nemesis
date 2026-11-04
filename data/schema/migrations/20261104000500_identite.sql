-- migrate:up

-- Identité (T2, T9 et T10 du registre de docs/PRIVACY.md). Accès réservé au rôle
-- nemesis_identity : l'API ordinaire ne peut pas relier une trace à un compte.

create table identity.account (
    id uuid primary key default gen_random_uuid(),
    phone_hmac bytea not null unique check (octet_length(phone_hmac) = 32),
    phone_encrypted bytea not null,
    locale text not null default 'fr-CI',
    preferences jsonb not null default '{}' check (jsonb_typeof(preferences) = 'object'),
    is_fictional boolean not null default false,
    created_at timestamptz not null default now(),
    deleted_at timestamptz
);

comment on column identity.account.phone_hmac is 'HMAC-SHA256 du numéro avec un secret serveur, pour les recherches (H-016).';
comment on column identity.account.phone_encrypted is 'Numéro chiffré par l''application (chiffrement d''enveloppe), pour l''envoi des SMS.';
comment on column identity.account.deleted_at is 'Suppression demandée : effacement définitif après 30 jours (ops.purge_expired).';

create table identity.device (
    id uuid primary key default gen_random_uuid(),
    account_id uuid references identity.account (id) on delete set null,
    contributor_pseudonym text not null unique,
    platform text not null check (platform in ('android', 'ios', 'web', 'whatsapp', 'sms', 'ussd')),
    integrity_verdict text,
    is_fictional boolean not null default false,
    created_at timestamptz not null default now(),
    last_seen_at timestamptz
);

-- Consentements, un par finalité, retirables séparément (partie 12.1).
create table identity.consent (
    id bigint generated always as identity primary key,
    device_id uuid not null references identity.device (id) on delete cascade,
    purpose text not null check (purpose in (
        'contributions', 'suivi_passif', 'notifications', 'partage_trajet', 'mode_pro', 'abonnement_canal')),
    text_version text not null,
    granted_at timestamptz not null default now(),
    withdrawn_at timestamptz,
    is_fictional boolean not null default false,
    check (withdrawn_at is null or withdrawn_at >= granted_at)
);

create unique index consent_active_key on identity.consent (device_id, purpose) where withdrawn_at is null;

-- Contributions validées qui donnent droit à des points (F-14).
create table identity.contribution (
    id bigint generated always as identity primary key,
    account_id uuid not null references identity.account (id) on delete cascade,
    observation_id uuid not null,
    observed_at timestamptz not null,
    validated_at timestamptz not null,
    points integer not null check (points >= 0),
    is_fictional boolean not null default false,
    unique (observation_id, observed_at)
);

create table identity.reward_ledger (
    id bigint generated always as identity primary key,
    account_id uuid not null references identity.account (id) on delete cascade,
    delta_points integer not null check (delta_points <> 0),
    reason text not null check (reason in ('contribution_validee', 'echange', 'correction', 'expiration')),
    reference text,
    is_fictional boolean not null default false,
    created_at timestamptz not null default now()
);

-- migrate:down

drop table identity.reward_ledger;
drop table identity.contribution;
drop table identity.consent;
drop table identity.device;
drop table identity.account;
