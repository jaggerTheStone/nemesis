#!/usr/bin/env bash
# Spike du moteur d'itinéraires (I0.8) : options A et B sur les mêmes couples.
#   tools/routing-spike/run.sh <extrait.osm.pbf> <gtfs.zip> <dossier de sortie> [date AAAA-MM-JJ]
# Prérequis : osmium, Docker, cargo, python3. L'extrait est découpé sur l'emprise de la
# ville (H-029) ; la date doit tomber dans le calendrier du GTFS (2023 pour « Abidjan 2023 »).
set -euo pipefail

osm=$1
gtfs=$2
out=$3
date=${4:-2023-06-13}
root=$(cd "$(dirname "$0")/../.." && pwd)
manifest="$root/data/pipelines/sources.toml"
read_manifest() { python3 -c "import tomllib,sys; d=tomllib.load(open('$manifest','rb')); print($1)"; }
image=$(read_manifest 'd["tools"]["opentripplanner"]')
bbox=$(read_manifest '",".join(str(v) for v in d["cities"]["abidjan"]["bbox"])')
year=${date%%-*}
seed=2026
pairs="$root/tools/routing-spike/couples.csv"

mkdir -p "$out"
echo "== Extrait OSM de l'emprise $bbox"
osmium extract --bbox "$bbox" --overwrite -o "$out/abidjan.osm.pbf" "$osm"
rm -rf "$out/gtfs" && mkdir -p "$out/gtfs"
python3 -I -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$gtfs" "$out/gtfs"

echo "== Option B : RAPTOR à fréquences (Rust)"
(cd "$root/services/routing" && cargo build --release --locked --quiet)
routing="$root/services/routing/target/release/routing"
common=(--gtfs "$out/gtfs" --pairs "$pairs" --date "$date" --repeat 20)
"$routing" spike "${common[@]}" --out "$out/b-base.json"
"$routing" spike "${common[@]}" --simulated-waits "$seed" --out "$out/b-sim.json"
"$routing" spike "${common[@]}" --virtual-spacing 250 --out "$out/b-virtuels.json"

echo "== Option A : OpenTripPlanner ($image)"
python3 -I "$root/tools/routing-spike/otp.py" run --image "$image" --osm "$out/abidjan.osm.pbf" \
  --gtfs "$gtfs" --work "$out/otp" --pairs "$pairs" --date "$date" \
  --service "$year-01-01:$year-12-31" --repeat 5 --heap 4g --out "$out/otp.json"

echo "== Comparaison"
python3 -I "$root/tools/routing-spike/compare.py" --gtfs "$out/gtfs" --otp "$out/otp.json" \
  --b-base "$out/b-base.json" --b-sim "$out/b-sim.json" --b-virtual "$out/b-virtuels.json" \
  --seed "$seed" --out-json "$out/comparaison.json" --out-md "$out/comparaison.md"
