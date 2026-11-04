"""Promotes named OSM points of interest to network.place, with their aliases (F-01).

Each place keeps its OSM reference (`node/123`) and the import run it came from, so
that the next import updates it instead of duplicating it. Places that disappeared
from OSM are counted, never deleted silently: a moderator decides.
"""

from __future__ import annotations

import json
from typing import Any

from nemesis_pipelines.sources import City, Source

# OSM name keys → alias kinds of network.place_alias. Anything else is « autre ».
ALIAS_KINDS = {"name": "nom", "old_name": "ancien_nom", "short_name": "abreviation"}

ENSURE_CITY = """
insert into network.city (code, name, timezone, metric_srid, bbox, is_fictional)
values (%s, %s, %s, %s, st_makeenvelope(%s, %s, %s, %s, 4326), %s)
on conflict (code) do nothing
"""

UPSERT_PLACES = """
with candidate as (
    select case p.osm_type when 'N' then 'node' when 'W' then 'way' else 'relation' end
               || '/' || p.osm_id as external_ref,
           p.category, p.name, p.geom
    from staging_osm.poi p
    where st_intersects(p.geom, (select bbox from network.city where id = %s::uuid))
)
insert into network.place (city_id, is_fictional, category, name, geom, source_id,
                           external_ref, import_run_id)
select %s::uuid, %s, c.category, c.name, c.geom, %s, c.external_ref, %s::uuid
from candidate c
on conflict (city_id, source_id, external_ref) where external_ref is not null
do update set category = excluded.category, name = excluded.name, geom = excluded.geom,
              import_run_id = excluded.import_run_id
returning (xmax = 0) as inserted
"""

INSERT_ALIASES = """
insert into network.place_alias (place_id, city_id, is_fictional, alias, alias_kind, language)
select pl.id, pl.city_id, pl.is_fictional, btrim(alias.value),
       coalesce(%s::jsonb ->> n.key, 'autre'),
       case when n.key like 'name:%%' then substr(n.key, 6) else 'fr' end
from network.place pl
join staging_osm.poi p
  on pl.external_ref = case p.osm_type when 'N' then 'node' when 'W' then 'way'
                       else 'relation' end || '/' || p.osm_id
cross join lateral jsonb_each_text(p.names) as n (key, value)
cross join lateral regexp_split_to_table(n.value, ';') as alias (value)
where pl.city_id = %s::uuid and pl.source_id = %s and pl.import_run_id = %s::uuid
  and btrim(alias.value) <> ''
  and (n.key not like 'name:%%' or substr(n.key, 6) ~ '^[a-z]{2,3}$')
on conflict (place_id, alias) do nothing
"""


def ensure_city(cursor: Any, city: City) -> str:
    lon_min, lat_min, lon_max, lat_max = city.bbox
    cursor.execute(
        ENSURE_CITY,
        (
            city.code,
            city.name,
            city.timezone,
            city.metric_srid,
            lon_min,
            lat_min,
            lon_max,
            lat_max,
            city.is_fictional,
        ),
    )
    cursor.execute("select id::text, is_fictional from network.city where code = %s", (city.code,))
    city_id, fictional = cursor.fetchone()
    if fictional != city.is_fictional:
        raise ValueError(f"{city.code} : statut fictif différent en base et dans sources.toml")
    return city_id


def promote_places(connection: Any, source: Source, city: City, run_id: str) -> dict[str, int]:
    """Upserts the POIs of the last OSM import inside the city's bounding box."""
    if source.is_fictional != city.is_fictional:
        raise ValueError("source et ville doivent être toutes deux fictives ou toutes deux réelles")
    cursor = connection.cursor()
    try:
        city_id = ensure_city(cursor, city)
        cursor.execute(UPSERT_PLACES, (city_id, city_id, city.is_fictional, source.id, run_id))
        flags = [row[0] for row in cursor.fetchall()]
        cursor.execute(INSERT_ALIASES, (json.dumps(ALIAS_KINDS), city_id, source.id, run_id))
        aliases = cursor.rowcount
        cursor.execute(
            """
            select count(*) from network.place
             where city_id = %s::uuid and source_id = %s and import_run_id <> %s::uuid
            """,
            (city_id, source.id, run_id),
        )
        stale = cursor.fetchone()[0]
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    return {
        "lieux_crees": sum(flags),
        "lieux_mis_a_jour": len(flags) - sum(flags),
        "alias_ajoutes": aliases,
        "lieux_absents_du_dernier_import": stale,
    }
