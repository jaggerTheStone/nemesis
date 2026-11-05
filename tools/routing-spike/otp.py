"""Option A of the routing spike (I0.8): OpenTripPlanner 2 from its pinned image.

    python tools/routing-spike/otp.py run --image <image> --osm <x.osm.pbf> --gtfs <gtfs.zip>
        --work <dir> --pairs couples.csv --date 2023-06-13 --out otp.json
        [--times 06:30,11:00,18:30] [--repeat 5] [--service 2023-01-01:2023-12-31] [--heap 3g]

Builds the graph (time, peak memory, import issues), serves it, then sends every
origin-destination pair at every time through the GTFS GraphQL API, timing each
request. Only the standard library is used.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

PLAN = """{ plan(from: {lat: %(olat)f, lon: %(olon)f}, to: {lat: %(dlat)f, lon: %(dlon)f},
  date: "%(date)s", time: "%(time)s:00", numItineraries: %(n)d) {
  itineraries { startTime endTime duration walkDistance waitingTime
    legs { mode startTime endTime duration distance
      from { name lat lon stop { gtfsId } } to { name lat lon stop { gtfsId } }
      route { gtfsId shortName longName } trip { gtfsId } } } } }"""

_UNITS = {
    "B": 1,
    "KiB": 1024,
    "MiB": 1024**2,
    "GiB": 1024**3,
    "kB": 1000,
    "MB": 1000**2,
    "GB": 1000**3,
}


def parse_memory(text: str) -> float:
    """« 1.23GiB / 15.6GiB » → bytes used."""
    match = re.match(r"\s*([0-9.]+)\s*([A-Za-z]+)", text)
    if not match:
        return 0.0
    return float(match.group(1)) * _UNITS.get(match.group(2), 1)


class MemorySampler(threading.Thread):
    """Peak memory of a container, sampled with `docker stats` every second."""

    def __init__(self, container: str) -> None:
        super().__init__(daemon=True)
        self.container, self.peak, self._stop = container, 0.0, threading.Event()

    def run(self) -> None:
        while not self._stop.is_set():
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", self.container],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                self.peak = max(self.peak, parse_memory(result.stdout))
            self._stop.wait(1.0)

    def stop(self) -> float:
        self._stop.set()
        self.join(timeout=5)
        return self.peak


def prepare(osm: Path, gtfs: Path, work: Path, service: str | None) -> None:
    work.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(osm, work / "reseau.osm.pbf")
    shutil.copyfile(gtfs, work / "reseau-gtfs.zip")
    config: dict[str, Any] = {}
    if service:
        # OTP keeps by default one year back and three years ahead of today: an
        # older feed would lose all its service without these bounds.
        start, end = service.split(":")
        config.update(transitServiceStart=start, transitServiceEnd=end)
    (work / "build-config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def docker_base(image: str, work: Path, heap: str, name: str) -> list[str]:
    return [
        "docker",
        "run",
        "--name",
        name,
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "-e",
        f"JAVA_TOOL_OPTIONS=-Xmx{heap}",
        "-v",
        f"{work.resolve()}:/var/opentripplanner",
    ]


def build(image: str, work: Path, heap: str) -> dict[str, Any]:
    name = "otp-spike-build"
    subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
    sampler = MemorySampler(name)
    started = time.monotonic()
    process = subprocess.Popen(
        [*docker_base(image, work, heap, name), image, "--build", "--save"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(1)
    sampler.start()
    log = process.communicate()[0]
    seconds = time.monotonic() - started
    peak = sampler.stop()
    subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
    (work / "build.log").write_text(log, encoding="utf-8")
    if process.returncode != 0:
        sys.stderr.write(log[-5000:])
        raise SystemExit(f"construction du graphe OTP en échec ({process.returncode})")
    issues = dict(
        re.findall(r"^\S+ INFO .*?DataImportIssueSummary.*?-\s+(\w+)\s+(\d+)$", log, re.M)
    )
    keep = ("frequency-based", "Limiting transit service days", "Transit built", "Graph built")
    notes = [line.split(") ", 1)[-1] for line in log.splitlines() if any(k in line for k in keep)]
    return {
        "seconds": round(seconds, 1),
        "peak_memory_mib": round(peak / 1024**2),
        "graph_mib": round((work / "graph.obj").stat().st_size / 1024**2, 1),
        "issues": {k: int(v) for k, v in issues.items()},
        "notes": notes,
    }


def graphql(port: int, query: str, timeout: float = 120) -> dict[str, Any]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/otp/gtfs/v1",
        data=json.dumps({"query": query}).encode(),
        headers={"Content-Type": "application/json"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return json.load(response)


def serve(image: str, work: Path, heap: str, port: int) -> tuple[str, float]:
    name = "otp-spike-serve"
    subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
    base = docker_base(image, work, heap, name)
    subprocess.run(
        [*base[:2], "-d", *base[2:], "-p", f"127.0.0.1:{port}:8080", image, "--load", "--serve"],
        check=True,
        capture_output=True,
    )
    started = time.monotonic()
    while time.monotonic() - started < 600:
        try:
            graphql(port, "{ feeds { feedId } }", timeout=5)
            return name, time.monotonic() - started
        except OSError:
            time.sleep(1)
    logs = subprocess.run(["docker", "logs", name], capture_output=True, text=True, check=False)
    sys.stderr.write(logs.stdout[-5000:] + logs.stderr[-5000:])
    raise SystemExit("le serveur OTP n'a pas démarré en 10 minutes")


def run_queries(
    port: int, pairs: list[dict[str, str]], date: str, times: list[str], repeat: int
) -> list[dict[str, Any]]:
    results = []
    for pair in pairs:
        for clock in times:
            query = PLAN % {
                "olat": float(pair["origin_lat"]),
                "olon": float(pair["origin_lon"]),
                "dlat": float(pair["destination_lat"]),
                "dlon": float(pair["destination_lon"]),
                "date": date,
                "time": clock,
                "n": 5,
            }
            samples, response = [], {}
            for _ in range(repeat):
                started = time.perf_counter()
                response = graphql(port, query)
                samples.append((time.perf_counter() - started) * 1000)
            plan = (response.get("data") or {}).get("plan") or {}
            results.append(
                {
                    "pair_id": pair["pair_id"],
                    "band": pair["band"],
                    "time": clock,
                    "latency": latency(samples),
                    "errors": response.get("errors"),
                    "itineraries": plan.get("itineraries", []),
                }
            )
    return results


def latency(samples: list[float]) -> dict[str, float]:
    ordered = sorted(samples)
    pick = lambda q: ordered[round((len(ordered) - 1) * q)]  # noqa: E731
    return {
        "p50_ms": round(pick(0.5), 2),
        "p95_ms": round(pick(0.95), 2),
        "max_ms": round(ordered[-1], 2),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    for name in ("--image", "--osm", "--gtfs", "--work", "--pairs", "--date", "--out"):
        run.add_argument(name, required=True)
    run.add_argument("--times", default="06:30,11:00,18:30")
    run.add_argument("--repeat", type=int, default=5)
    run.add_argument("--service")
    run.add_argument("--heap", default="3g")
    run.add_argument("--port", type=int, default=18080)
    args = parser.parse_args(argv)

    work = Path(args.work)
    prepare(Path(args.osm), Path(args.gtfs), work, args.service)
    built = build(args.image, work, args.heap)
    print(
        f"Graphe OTP : {built['seconds']} s, {built['peak_memory_mib']} Mio au plus, "
        f"{built['graph_mib']} Mio sur disque"
    )
    name, startup = serve(args.image, work, args.heap, args.port)
    sampler = MemorySampler(name)
    sampler.start()
    try:
        with open(args.pairs, encoding="utf-8") as handle:
            pairs = list(csv.DictReader(handle))
        times = args.times.split(",")
        # One warm-up request: the first ones pay for the JIT compilation.
        run_queries(args.port, pairs[:1], args.date, times[:1], 3)
        results = run_queries(args.port, pairs, args.date, times, args.repeat)
    finally:
        peak = sampler.stop()
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
    all_p50 = [r["latency"]["p50_ms"] for r in results]
    report = {
        "engine": "OpenTripPlanner",
        "image": args.image,
        "date": args.date,
        "repeat": args.repeat,
        "build": built,
        "startup_seconds": round(startup, 1),
        "serve_peak_memory_mib": round(peak / 1024**2),
        "latency_p50_of_p50_ms": round(statistics.median(all_p50), 2),
        "latency_max_p50_ms": round(max(all_p50), 2),
        "queries_without_itinerary": sum(1 for r in results if not r["itineraries"]),
        "queries_with_errors": sum(1 for r in results if r["errors"]),
        "queries": results,
    }
    Path(args.out).write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(
        f"{len(results)} requêtes, latence médiane {report['latency_p50_of_p50_ms']} ms, "
        f"mémoire du serveur {report['serve_peak_memory_mib']} Mio au plus, "
        f"{report['queries_without_itinerary']} sans itinéraire"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
