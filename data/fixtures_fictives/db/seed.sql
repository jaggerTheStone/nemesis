-- Jeu de départ entièrement fictif pour l'environnement de développement (I0.4).
-- Ville « Lagune-Fictive », placée en pleine mer (golfe de Guinée) pour ne jamais
-- être confondue avec un lieu réel. Chaque ligne porte is_fictional = true (règle 1.3.1).
-- Idempotent : on peut le rejouer à chaque « docker compose up ».
-- Le jeu complet, généré, arrive en I0.5.

begin;

insert into network.source (id, name, license, attribution, is_fictional) values
    ('fixtures_fictives', 'Données fictives du projet', 'Données de test, sans valeur réelle', null, true)
on conflict (id) do nothing;

insert into network.city (id, code, name, timezone, currency, metric_srid, bbox, is_fictional) values
    ('00000000-0000-4000-8000-000000000001', 'lagune-fictive', 'Lagune-Fictive', 'Africa/Abidjan', 'XOF', 32630,
     ST_MakeEnvelope(-4.05, 1.95, -3.95, 2.05, 4326), true)
on conflict (id) do nothing;

insert into network.admin_area (id, city_id, is_fictional, kind, code, name, geom, source_id) values
    ('00000000-0000-4000-8001-000000000001', '00000000-0000-4000-8000-000000000001', true, 'commune', 'nord',
     'Lagune-Nord (fictif)', ST_Multi(ST_MakeEnvelope(-4.05, 2.00, -3.95, 2.05, 4326)), 'fixtures_fictives'),
    ('00000000-0000-4000-8001-000000000002', '00000000-0000-4000-8000-000000000001', true, 'commune', 'sud',
     'Lagune-Sud (fictif)', ST_Multi(ST_MakeEnvelope(-4.05, 1.95, -3.95, 2.00, 4326)), 'fixtures_fictives')
on conflict (id) do nothing;

insert into network.stop (id, city_id, is_fictional, code, kind, name, geom, boarding_radius_m, lighting, source_id) values
    ('00000000-0000-4000-8002-000000000001', '00000000-0000-4000-8000-000000000001', true, 'flamboyants',
     'gare_artisanale', 'Gare des Flamboyants (fictif)', ST_SetSRID(ST_MakePoint(-4.010, 2.030), 4326), 60, 'oui', 'fixtures_fictives'),
    ('00000000-0000-4000-8002-000000000002', '00000000-0000-4000-8000-000000000001', true, 'baobab',
     'arret_informel', 'Carrefour du Baobab (fictif)', ST_SetSRID(ST_MakePoint(-4.000, 2.010), 4326), 120, 'non', 'fixtures_fictives'),
    ('00000000-0000-4000-8002-000000000003', '00000000-0000-4000-8000-000000000001', true, 'marche',
     'arret_informel', 'Marché des Flamboyants (fictif)', ST_SetSRID(ST_MakePoint(-3.990, 2.025), 4326), 80, 'oui', 'fixtures_fictives'),
    ('00000000-0000-4000-8002-000000000004', '00000000-0000-4000-8000-000000000001', true, 'embarcadere-sud',
     'embarcadere', 'Embarcadère Sud (fictif)', ST_SetSRID(ST_MakePoint(-3.995, 1.965), 4326), 40, 'oui', 'fixtures_fictives')
on conflict (id) do nothing;

insert into network.place (id, city_id, is_fictional, category, name, geom, admin_area_id, source_id) values
    ('00000000-0000-4000-8003-000000000001', '00000000-0000-4000-8000-000000000001', true, 'marche',
     'Marché des Flamboyants (fictif)', ST_SetSRID(ST_MakePoint(-3.991, 2.026), 4326),
     '00000000-0000-4000-8001-000000000001', 'fixtures_fictives'),
    ('00000000-0000-4000-8003-000000000002', '00000000-0000-4000-8000-000000000001', true, 'pharmacie',
     'Pharmacie de la Lagune (fictif)', ST_SetSRID(ST_MakePoint(-4.002, 2.012), 4326),
     '00000000-0000-4000-8001-000000000002', 'fixtures_fictives')
on conflict (id) do nothing;

insert into network.place_alias (place_id, city_id, is_fictional, alias, alias_kind) values
    ('00000000-0000-4000-8003-000000000001', '00000000-0000-4000-8000-000000000001', true, 'Marché des Flamboyants', 'nom'),
    ('00000000-0000-4000-8003-000000000001', '00000000-0000-4000-8000-000000000001', true, 'flamboyant marché', 'orthographe'),
    ('00000000-0000-4000-8003-000000000002', '00000000-0000-4000-8000-000000000001', true, 'Pharmacie de la Lagune', 'nom'),
    ('00000000-0000-4000-8003-000000000002', '00000000-0000-4000-8000-000000000001', true, 'pharma Lagune', 'abreviation')
on conflict (place_id, alias) do nothing;

insert into network.operator (id, city_id, is_fictional, code, name, kind) values
    ('00000000-0000-4000-8004-000000000001', '00000000-0000-4000-8000-000000000001', true, 'artisanal',
     'Transport artisanal (fictif)', 'generique')
on conflict (id) do nothing;

insert into network.route (id, city_id, is_fictional, code, operator_id, mode, spoken_name, body_color, announced_as, source_id) values
    ('00000000-0000-4000-8005-000000000001', '00000000-0000-4000-8000-000000000001', true, 'g-flamboyants-marche',
     '00000000-0000-4000-8004-000000000001', 'gbaka', 'Flamboyants–Marché (fictif)', 'blanc', 'Marché ! (fictif)', 'fixtures_fictives'),
    ('00000000-0000-4000-8005-000000000002', '00000000-0000-4000-8000-000000000001', true, 'w-baobab-embarcadere',
     '00000000-0000-4000-8004-000000000001', 'woro_communal', 'Baobab–Embarcadère (fictif)', 'vert', null, 'fixtures_fictives')
on conflict (id) do nothing;

insert into network.route_pattern (id, city_id, is_fictional, route_id, code, direction_id, headsign, shape, continuous_pickup, continuous_drop_off) values
    ('00000000-0000-4000-8006-000000000001', '00000000-0000-4000-8000-000000000001', true,
     '00000000-0000-4000-8005-000000000001', 'g-flamboyants-marche-0', 0, 'Marché (fictif)',
     ST_SetSRID(ST_MakeLine(ARRAY[ST_MakePoint(-4.010, 2.030), ST_MakePoint(-4.000, 2.028), ST_MakePoint(-3.990, 2.025)]), 4326), true, true),
    ('00000000-0000-4000-8006-000000000002', '00000000-0000-4000-8000-000000000001', true,
     '00000000-0000-4000-8005-000000000002', 'w-baobab-embarcadere-0', 0, 'Embarcadère Sud (fictif)',
     ST_SetSRID(ST_MakeLine(ARRAY[ST_MakePoint(-4.000, 2.010), ST_MakePoint(-3.995, 1.965)]), 4326), false, false)
on conflict (id) do nothing;

insert into network.route_pattern_stop (route_pattern_id, sequence, stop_id, city_id, is_fictional, distance_along_m) values
    ('00000000-0000-4000-8006-000000000001', 0, '00000000-0000-4000-8002-000000000001', '00000000-0000-4000-8000-000000000001', true, 0),
    ('00000000-0000-4000-8006-000000000001', 1, '00000000-0000-4000-8002-000000000003', '00000000-0000-4000-8000-000000000001', true, 2300),
    ('00000000-0000-4000-8006-000000000002', 0, '00000000-0000-4000-8002-000000000002', '00000000-0000-4000-8000-000000000001', true, 0),
    ('00000000-0000-4000-8006-000000000002', 1, '00000000-0000-4000-8002-000000000004', '00000000-0000-4000-8000-000000000001', true, 5000)
on conflict (route_pattern_id, sequence) do nothing;

insert into network.service_profile (city_id, is_fictional, route_pattern_id, stop_id, day_type, slot_start, active, headway_mean_s, departs_when_full, seats, n_obs) values
    ('00000000-0000-4000-8000-000000000001', true, '00000000-0000-4000-8006-000000000001',
     '00000000-0000-4000-8002-000000000001', 'ouvrable', '06:30', true, null, true, 18, 0),
    ('00000000-0000-4000-8000-000000000001', true, '00000000-0000-4000-8006-000000000002',
     '00000000-0000-4000-8002-000000000002', 'ouvrable', '06:30', true, 300, false, 4, 0)
on conflict (route_pattern_id, stop_id, day_type, slot_start) do nothing;

insert into ops.staff_account (id, display_name, email, role, mfa_enabled, is_fictional) values
    ('00000000-0000-4000-8007-000000000001', 'Curatrice (fictif)', 'curatrice@example.invalid', 'curateur', true, true),
    ('00000000-0000-4000-8007-000000000002', 'Modérateur (fictif)', 'moderateur@example.invalid', 'moderateur', true, true)
on conflict (id) do nothing;

insert into network.network_version (city_id, is_fictional, number, status, notes)
select '00000000-0000-4000-8000-000000000001', true, 1, 'brouillon', 'Réseau fictif de départ (I0.4)'
where not exists (
    select from network.network_version where city_id = '00000000-0000-4000-8000-000000000001' and number = 1);

commit;
