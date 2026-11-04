-- Comptes de connexion pour l'environnement de développement uniquement.
-- Mot de passe passé par la variable psql dev_password (docker-compose.yml).
-- En production, les comptes sont créés par l'exploitation, hors du dépôt.

select format('create role %I login password %L in role %I', login, :'dev_password', grp)
from (values
    ('nemesis_api_dev', 'nemesis_api'),
    ('nemesis_identity_dev', 'nemesis_identity'),
    ('nemesis_analyst_dev', 'nemesis_analyst'),
    ('nemesis_maintenance_dev', 'nemesis_maintenance')
) as accounts (login, grp)
where not exists (select from pg_roles where rolname = login)
\gexec
