"""Dessine les fonds de carte de la maquette, un par identité visuelle.

Usage : python dessiner.py <couches.json> <dossier de sortie> [identité…]
Chaque fond est un SVG rendu par Chromium (Playwright, via rasteriser.cjs) à deux fois la
taille du cadre, puis enregistré en WebP. Données © contributeurs OpenStreetMap, ODbL.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROAD_ORDER = ["minor", "tertiary", "secondary", "primary", "trunk", "motorway"]

# Widths in CSS pixels at zoom 14: (fill, casing).
WIDTHS = {
    "minor": (1.0, 1.8),
    "tertiary": (1.9, 3.1),
    "secondary": (2.5, 3.9),
    "primary": (3.2, 4.8),
    "trunk": (3.8, 5.6),
    "motorway": (4.2, 6.2),
}

THEMES: dict[str, dict] = {
    # Gbê : clair et précis, dans l'esprit des cartes routières claires.
    "gbe": {
        "sea": "#9CCDE6",
        "land": "#F4F2EE",
        "water": "#9CCDE6",
        "river": "#9CCDE6",
        "sand": "#F1E6C8",
        "green": "#D5EBCB",
        "forest": "#BFDFB1",
        "industrial": "#EEEBF1",
        "airport": "#EAE7F0",
        "runway": "#CDC8D8",
        "rail": "#B4AEA4",
        "ferry": "#5E9FC2",
        "roads": {
            "minor": ("#FFFFFF", "#DEDAD2"),
            "tertiary": ("#FFFFFF", "#D2CCC0"),
            "secondary": ("#FFFFFF", "#C9C2B4"),
            "primary": ("#FFE9A6", "#E2BC63"),
            "trunk": ("#FFDA85", "#D9A443"),
            "motorway": ("#FFC96B", "#CF9233"),
        },
    },
    # Yafohi : chaud et épuré, peu de détails, dans l'esprit des applis très simples.
    "yafohi": {
        "sea": "#A9DDD6",
        "land": "#FBF6EC",
        "water": "#A9DDD6",
        "river": "#A9DDD6",
        "sand": "#F6E9C9",
        "green": "#DDEDCB",
        "forest": "#CBE4B6",
        "industrial": "#F3ECE0",
        "airport": "#F1EADD",
        "runway": "#E2D7C4",
        "rail": "#D8CCB7",
        "ferry": "#4FA89C",
        "roads": {
            "minor": ("#FFFFFF", "#EFE5D3"),
            "tertiary": ("#FFFFFF", "#E8DBC4"),
            "secondary": ("#FFFFFF", "#E2D2B6"),
            "primary": ("#FFF0C2", "#EBCB80"),
            "trunk": ("#FFE39E", "#E5B95C"),
            "motorway": ("#FFD27A", "#DEA64A"),
        },
    },
    # Mon Kôrô : nuit, lisible et vivant, dans l'esprit des cartes communautaires de nuit.
    "koro": {
        "sea": "#0A1226",
        "land": "#161D35",
        "water": "#0A1226",
        "river": "#0D1730",
        "sand": "#1F2540",
        "green": "#18302F",
        "forest": "#152B2A",
        "industrial": "#1B2240",
        "airport": "#1C2443",
        "runway": "#2C3558",
        "rail": "#2F395E",
        "ferry": "#2E6C8F",
        "roads": {
            "minor": ("#252E4D", "#161D35"),
            "tertiary": ("#323C63", "#1A2140"),
            "secondary": ("#3B4772", "#1A2140"),
            "primary": ("#55639A", "#1E2547"),
            "trunk": ("#8C7A2E", "#1E2547"),
            "motorway": ("#B39A2B", "#1E2547"),
        },
    },
    # Vue satellite : seulement les grands axes, fins et clairs, par-dessus l'image.
    "sat": {
        "overlay": True,
        "roads": {
            "primary": ("rgba(255,255,255,.55)", None),
            "trunk": ("rgba(255,236,170,.75)", None),
            "motorway": ("rgba(255,214,120,.85)", None),
        },
    },
}


def path_rings(rings: list) -> str:
    return " ".join(
        "M" + " L".join(f"{x:g},{y:g}" for x, y in ring) + " Z" for ring in rings if len(ring) > 2
    )


def path_lines(lines: list) -> str:
    return " ".join("M" + " L".join(f"{x:g},{y:g}" for x, y in line) for line in lines)


def svg(layers: dict, theme: dict) -> str:
    w, h = layers["frame"]["width"], layers["frame"]["height"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
    ]
    line_attrs = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    if not theme.get("overlay"):
        parts.append(f'<rect width="{w}" height="{h}" fill="{theme["sea"]}"/>')
        for key in ("land", "sand", "green", "forest", "industrial", "airport", "water"):
            fill = theme["land"] if key == "land" else theme[key]
            parts.append(f'<path fill-rule="evenodd" fill="{fill}" d="{path_rings(layers[key])}"/>')
        parts.append(
            f'<path {line_attrs} stroke="{theme["river"]}" stroke-width="1.6" '
            f'd="{path_lines(layers["rivers"])}"/>'
        )
        parts.append(
            f'<path {line_attrs} stroke="{theme["runway"]}" stroke-width="7" '
            f'd="{path_lines(layers["runways"])}"/>'
        )
        parts.append(
            f'<path {line_attrs} stroke="{theme["ferry"]}" stroke-width="1.2" '
            f'stroke-dasharray="4 4" d="{path_lines(layers["ferry"])}"/>'
        )
    roads = layers["roads"]
    classes = [c for c in ROAD_ORDER if c in theme["roads"]]
    for cls in classes:
        casing = theme["roads"][cls][1]
        if casing:
            parts.append(
                f'<path {line_attrs} stroke="{casing}" stroke-width="{WIDTHS[cls][1]}" '
                f'd="{path_lines(roads.get(cls, []))}"/>'
            )
    for cls in classes:
        fill = theme["roads"][cls][0]
        width = WIDTHS[cls][0] if not theme.get("overlay") else WIDTHS[cls][0] * 0.55
        parts.append(
            f'<path {line_attrs} stroke="{fill}" stroke-width="{width}" '
            f'd="{path_lines(roads.get(cls, []))}"/>'
        )
    if not theme.get("overlay"):
        parts.append(
            f'<path {line_attrs} stroke="{theme["rail"]}" stroke-width="1.4" '
            f'stroke-dasharray="6 3" d="{path_lines(layers["rail"])}"/>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    layers = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    names = sys.argv[3:] or list(THEMES)
    w, h = layers["frame"]["width"], layers["frame"]["height"]
    jobs = []
    for name in names:
        theme = THEMES[name]
        (out / f"carte-{name}.svg").write_text(svg(layers, theme), encoding="utf-8")
        jobs += [
            str(out / f"carte-{name}.svg"),
            str(out / f"carte-{name}.png"),
            "1" if theme.get("overlay") else "0",
        ]
    node_path = subprocess.check_output(["npm", "root", "-g"], text=True).strip()
    env = {**os.environ, "NODE_PATH": node_path}
    here = Path(__file__).resolve().parent
    command = ["node", str(here / "rasteriser.cjs"), str(w), str(h), *jobs]
    subprocess.run(command, check=True, env=env)
    for name in names:
        image = Image.open(out / f"carte-{name}.png")
        target = out / f"carte-{name}.webp"
        if THEMES[name].get("overlay"):
            image.save(target, "WEBP", quality=88, method=6)
        else:
            image.convert("RGB").save(target, "WEBP", quality=86, method=6)
        print(name, image.size, target.stat().st_size)


if __name__ == "__main__":
    main()
