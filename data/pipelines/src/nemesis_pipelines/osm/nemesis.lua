-- Style osm2pgsql (sortie « flex ») de nemesis, incrément I0.7.
-- Écrit pour osm2pgsql 1.11 (paquet Ubuntu 24.04) ; tables dans le schéma staging_osm.
--
--   road           voirie et chemins, avec ce qui se marche et ce qui se roule
--   poi            points d'intérêt nommés, classés dans les catégories de network.place
--   transit_stop   arrêts, quais, gares routières, embarcadères
--   route          relations de lignes (gbakas, wôrô-wôrôs, bus, bateaux…)
--   route_master   relations « route_master » qui regroupent les sens d'une ligne
--   route_member   membres ordonnés des relations de lignes
--   boundary       limites administratives
--
-- Rien n'est corrigé : les valeurs des tags sont copiées telles quelles.

local schema = 'staging_osm'
local tables = {}

tables.road = osm2pgsql.define_way_table('road', {
    { column = 'highway', type = 'text', not_null = true },
    { column = 'name', type = 'text' },
    { column = 'ref', type = 'text' },
    { column = 'oneway', type = 'text' },
    { column = 'surface', type = 'text' },
    { column = 'walkable', type = 'boolean', not_null = true },
    { column = 'drivable', type = 'boolean', not_null = true },
    { column = 'geom', type = 'linestring', projection = 4326, not_null = true },
}, { schema = schema })

tables.poi = osm2pgsql.define_table({
    name = 'poi',
    schema = schema,
    ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
    columns = {
        { column = 'category', type = 'text', not_null = true },
        { column = 'name', type = 'text', not_null = true },
        { column = 'names', type = 'jsonb', not_null = true },
        { column = 'tags', type = 'jsonb', not_null = true },
        { column = 'geom', type = 'point', projection = 4326, not_null = true },
    },
})

tables.transit_stop = osm2pgsql.define_table({
    name = 'transit_stop',
    schema = schema,
    ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
    columns = {
        { column = 'kind', type = 'text', not_null = true },
        { column = 'name', type = 'text' },
        { column = 'names', type = 'jsonb', not_null = true },
        { column = 'tags', type = 'jsonb', not_null = true },
        { column = 'geom', type = 'point', projection = 4326, not_null = true },
    },
})

tables.route = osm2pgsql.define_relation_table('route', {
    { column = 'route', type = 'text', not_null = true },
    { column = 'ref', type = 'text' },
    { column = 'name', type = 'text' },
    { column = 'from_name', type = 'text' },
    { column = 'to_name', type = 'text' },
    { column = 'network', type = 'text' },
    { column = 'operator', type = 'text' },
    { column = 'colour', type = 'text' },
    { column = 'tags', type = 'jsonb', not_null = true },
    { column = 'way_count', type = 'int4', not_null = true },
    { column = 'stop_count', type = 'int4', not_null = true },
    { column = 'geom', type = 'multilinestring', projection = 4326 },
}, { schema = schema })

tables.route_master = osm2pgsql.define_relation_table('route_master', {
    { column = 'route_master', type = 'text' },
    { column = 'ref', type = 'text' },
    { column = 'name', type = 'text' },
    { column = 'network', type = 'text' },
    { column = 'operator', type = 'text' },
    { column = 'tags', type = 'jsonb', not_null = true },
}, { schema = schema })

tables.route_member = osm2pgsql.define_relation_table('route_member', {
    { column = 'sequence', type = 'int4', not_null = true },
    { column = 'member_type', type = 'text', not_null = true },
    { column = 'member_id', type = 'int8', not_null = true },
    { column = 'role', type = 'text', not_null = true },
}, { schema = schema })

tables.boundary = osm2pgsql.define_relation_table('boundary', {
    { column = 'admin_level', type = 'int4' },
    { column = 'name', type = 'text' },
    { column = 'names', type = 'jsonb', not_null = true },
    { column = 'geom', type = 'multipolygon', projection = 4326, not_null = true },
}, { schema = schema })

-- Modes de transport public suivis (relations type=route).
local ROUTE_MODES = {
    bus = true, minibus = true, share_taxi = true, trolleybus = true, coach = true,
    ferry = true, train = true, light_rail = true, subway = true, tram = true,
}

-- Voies interdites aux piétons, sauf mention contraire (foot=yes).
local NOT_WALKABLE = { motorway = true, motorway_link = true, trunk = true, trunk_link = true,
    construction = true, proposed = true, raceway = true, bus_guideway = true }
-- Voies réservées aux piétons ou aux deux-roues.
local NOT_DRIVABLE = { footway = true, path = true, pedestrian = true, steps = true,
    cycleway = true, bridleway = true, corridor = true, construction = true, proposed = true,
    platform = true, elevator = true }

-- Tags conservés dans la colonne jsonb « tags » (le reste est dans l'extrait source).
local KEPT_TAGS = { 'amenity', 'shop', 'office', 'religion', 'denomination', 'place',
    'public_transport', 'highway', 'railway', 'healthcare', 'tourism', 'leisure', 'junction',
    'brand', 'operator', 'network', 'ref', 'local_ref', 'bus', 'share_taxi', 'minibus',
    'ferry', 'shelter', 'bench', 'lit', 'wheelchair', 'route', 'route_master', 'type',
    'fictional' }

local function kept_tags(tags)
    local result = {}
    for _, key in ipairs(KEPT_TAGS) do
        if tags[key] then result[key] = tags[key] end
    end
    return result
end

-- Toutes les variantes de nom : name, alt_name, old_name, short_name, name:fr…
local function names(tags)
    local result = {}
    for key, value in pairs(tags) do
        if key == 'name' or key:find('_name$') or key:find('^name:') then
            result[key] = value
        end
    end
    return result
end

local function starts_with_ci(text, prefix)
    return text ~= nil and text:lower():sub(1, #prefix) == prefix
end

-- Catégorie de network.place ; nil si l'objet n'est pas un repère utile.
local function poi_category(tags)
    local amenity, name = tags.amenity, tags.name
    if starts_with_ci(name, 'carrefour') or (tags.junction and tags.junction ~= 'roundabout')
        or tags.highway == 'mini_roundabout' or tags.highway == 'traffic_signals' then
        return 'carrefour'
    end
    if amenity == 'pharmacy' or tags.healthcare == 'pharmacy' then return 'pharmacie' end
    if amenity == 'place_of_worship' then
        if tags.religion == 'muslim' then return 'mosquee' end
        if tags.religion == 'christian' then return 'eglise' end
        return 'autre'
    end
    if amenity == 'marketplace' then return 'marche' end
    if amenity == 'bus_station' or amenity == 'ferry_terminal' or tags.public_transport == 'station' then
        return 'gare'
    end
    if amenity == 'school' or amenity == 'college' or amenity == 'university'
        or amenity == 'kindergarten' then
        return 'ecole'
    end
    if amenity == 'townhall' or amenity == 'police' or amenity == 'post_office'
        or amenity == 'courthouse' or amenity == 'hospital' or amenity == 'clinic'
        or amenity == 'fire_station' or tags.office == 'government' then
        return 'batiment_public'
    end
    if amenity == 'restaurant' or amenity == 'bar' or amenity == 'fast_food'
        or amenity == 'food_court' or amenity == 'cafe' or amenity == 'nightclub' then
        -- « Maquis » seulement quand le nom le dit : pas de déduction.
        if name and name:lower():find('maquis') then return 'maquis' end
        return 'autre'
    end
    if tags.place == 'suburb' or tags.place == 'quarter' or tags.place == 'neighbourhood' then
        return 'quartier'
    end
    if tags.office == 'company' then return 'entreprise' end
    if amenity or tags.shop or tags.office or tags.tourism or tags.leisure
        or tags.healthcare or tags.place then
        return 'autre'
    end
    return nil
end

-- Nature d'un arrêt ; nil si l'objet n'en est pas un.
local function stop_kind(tags)
    if tags.amenity == 'ferry_terminal' then return 'ferry_terminal' end
    if tags.amenity == 'bus_station' then return 'bus_station' end
    local pt = tags.public_transport
    if pt == 'platform' then return 'platform' end
    if pt == 'station' then return 'station' end
    if pt == 'stop_position' then return 'stop_position' end
    if tags.highway == 'bus_stop' then return 'bus_stop' end
    if tags.railway == 'station' or tags.railway == 'halt' or tags.railway == 'tram_stop' then
        return 'rail_station'
    end
    return nil
end

local function add_point_features(tags, geom)
    if geom == nil or geom:is_null() then return end
    local kind = stop_kind(tags)
    if kind then
        tables.transit_stop:insert({ kind = kind, name = tags.name, names = names(tags),
            tags = kept_tags(tags), geom = geom })
    end
    if tags.name then
        local category = poi_category(tags)
        if category then
            tables.poi:insert({ category = category, name = tags.name, names = names(tags),
                tags = kept_tags(tags), geom = geom })
        end
    end
end

function osm2pgsql.process_node(object)
    add_point_features(object.tags, object:as_point())
end

function osm2pgsql.process_way(object)
    local tags = object.tags
    local highway = tags.highway
    -- Une voie fermée (rond-point) reste une ligne ; une place piétonne (area=yes) non.
    if highway and highway ~= 'platform' and tags.area ~= 'yes' then
        local geom = object:as_linestring()
        if not geom:is_null() then
            local walkable = (tags.foot == 'yes' or tags.foot == 'designated')
                or (not NOT_WALKABLE[highway] and tags.foot ~= 'no' and tags.access ~= 'no'
                    and tags.access ~= 'private')
            local drivable = not NOT_DRIVABLE[highway] and tags.access ~= 'no'
                and tags.motor_vehicle ~= 'no'
            tables.road:insert({ highway = highway, name = tags.name, ref = tags.ref,
                oneway = tags.oneway, surface = tags.surface, walkable = walkable,
                drivable = drivable, geom = geom })
        end
    end
    if object.is_closed and (stop_kind(tags) or (tags.name and poi_category(tags))) then
        add_point_features(tags, object:as_polygon():centroid())
    end
end

function osm2pgsql.process_relation(object)
    local tags = object.tags
    local kind = tags.type
    if kind == 'route' and ROUTE_MODES[tags.route] then
        local ways, stops = 0, 0
        for index, member in ipairs(object.members) do
            tables.route_member:insert({ sequence = index, member_type = member.type,
                member_id = member.ref, role = member.role or '' })
            if member.type == 'w' and (member.role == '' or member.role == nil) then
                ways = ways + 1
            elseif member.role and (member.role:find('^stop') or member.role:find('^platform')) then
                stops = stops + 1
            end
        end
        local geom = object:as_multilinestring()
        tables.route:insert({ route = tags.route, ref = tags.ref, name = tags.name,
            from_name = tags.from, to_name = tags.to, network = tags.network,
            operator = tags.operator, colour = tags.colour, tags = kept_tags(tags),
            way_count = ways, stop_count = stops,
            geom = (geom ~= nil and not geom:is_null()) and geom or nil })
    elseif kind == 'route_master' and ROUTE_MODES[tags.route_master] then
        for index, member in ipairs(object.members) do
            tables.route_member:insert({ sequence = index, member_type = member.type,
                member_id = member.ref, role = member.role or '' })
        end
        tables.route_master:insert({ route_master = tags.route_master, ref = tags.ref,
            name = tags.name, network = tags.network, operator = tags.operator,
            tags = kept_tags(tags) })
    elseif kind == 'boundary' and tags.boundary == 'administrative' then
        local geom = object:as_multipolygon()
        if not geom:is_null() then
            tables.boundary:insert({ admin_level = tonumber(tags.admin_level), name = tags.name,
                names = names(tags), geom = geom })
        end
    elseif kind == 'multipolygon' and (stop_kind(tags) or (tags.name and poi_category(tags))) then
        local geom = object:as_multipolygon()
        if not geom:is_null() then
            add_point_features(tags, geom:centroid())
        end
    end
end
