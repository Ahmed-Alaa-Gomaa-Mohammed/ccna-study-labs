#!/usr/bin/env python3
"""
Topology SVG generator using custom isometric icons from Icons.svg.
High-impact, compact, legible layout with reduced appliance spacing and enlarged visuals.
Layout:
  - Nevada DC: Top-Left (NV-PC -> NV-Switch -> R2-NV)
  - Florida Branch: Bottom-Left (FL-PC -> FL-Switch -> R3-FL)
  - Service Provider: Center Hub (Internet & MetroE)
  - Arizona HQ Campus: Right Half (R1-AZ -> Core1 & Core2 -> Access1 -> PC-10 & PC-20)
"""

import base64
import os
import math

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(SCRIPT_DIR, "isoflow-icons")

W, H = 1680, 950
BG = "#ffffff"
LABEL_FONT = "Inter, 'Segoe UI', Arial, sans-serif"
LABEL_COLOR = "#0f172a"

# Uniform 300x300 bounding box preserved for all icons so internal proportions from Icons.svg remain 1:1
ICON_BOX = 144
HALF_BOX = ICON_BOX / 2

def load_icon(filename):
    with open(os.path.join(ICON_DIR, filename), "rb") as f:
        data = f.read()
    return f"data:image/svg+xml;base64,{base64.b64encode(data).decode()}"

ICONS = {
    "router": load_icon("router.svg"),
    "switch": load_icon("switch.svg"),
    "l3switch": load_icon("l3switch.svg"),
    "pc": load_icon("pc.svg"),
    "cloud": load_icon("cloud.svg"),
}

# Node definitions: (id, label, type, cx, cy, sublabel, label_above)
NODES = [
    # NEVADA DC (top-left)
    ("NV-PC",     "NV-PC",         "pc",       135,  260, "",              False),
    ("NV-Switch", "NV-Switch",     "switch",   295,  260, "",              False),
    ("R2-NV",     "R2-NV",         "router",   455,  260, "",              False),

    # FLORIDA BRANCH (bottom-left)
    ("FL-PC",     "FL-PC",         "pc",       135,  770, "",              False),
    ("FL-Switch", "FL-Switch",     "switch",   295,  770, "",              False),
    ("R3-FL",     "R3-FL",         "router",   455,  770, "",              False),

    # SERVICE PROVIDER (center hub)
    ("Internet",  "Internet",      "cloud",    680,  285, "",              False),
    ("MetroE",    "MetroE",        "cloud",    680,  565, "",              False),

    # ARIZONA HQ CAMPUS (right half)
    ("R1-AZ",     "R1-AZ",         "router",   920,  510, "10.16.0.2/24", False),
    ("Core1",     "Core1",         "l3switch", 1125, 330, "10.16.0.1/24", True),
    ("Core2",     "Core2",         "l3switch", 1125, 690, "",              False),
    ("Access1",   "Access1",       "switch",   1325,  510, "",              False),
    ("PC-10",     "PC-10",         "pc",       1515, 365, "10.1.1.10/24", False),
    ("PC-20",     "PC-20",         "pc",       1515, 665, "10.1.1.11/24", False),
]

NODE_POS = {n[0]: (n[3], n[4]) for n in NODES}
NODE_TYPES = {n[0]: n[2] for n in NODES}

# All 15 links from ccna.clab.yml
LINKS = [
    # Nevada DC links
    ("NV-PC",     "NV-Switch", "#64748b", 0),
    ("NV-Switch", "R2-NV",     "#7c3aed", 0),

    # Florida Branch links
    ("FL-PC",     "FL-Switch", "#64748b", 0),
    ("FL-Switch", "R3-FL",     "#e11d48", 0),

    # WAN links
    ("MetroE",    "R2-NV",     "#d97706", 0),
    ("MetroE",    "R3-FL",     "#d97706", 0),
    ("MetroE",    "R1-AZ",     "#d97706", 0),
    ("Internet",  "R1-AZ",     "#d97706", 0),

    # Arizona HQ links
    ("R1-AZ",     "Core1",     "#0284c7", 0),
    # Dual parallel links between Core1 and Core2
    ("Core1",     "Core2",     "#0284c7", -13),
    ("Core1",     "Core2",     "#0284c7", 13),
    ("Core1",     "Access1",   "#059669", 0),
    ("Core2",     "Access1",   "#059669", 0),
    ("Access1",   "PC-10",     "#64748b", 0),
    ("Access1",   "PC-20",     "#64748b", 0),
]

ZONES = [
    {"label": "NEVADA DC",         "color": "#7c3aed",
     "nodes": ["R2-NV", "NV-Switch", "NV-PC"]},
    {"label": "FLORIDA BRANCH",    "color": "#e11d48",
     "nodes": ["R3-FL", "FL-Switch", "FL-PC"]},
    {"label": "SERVICE PROVIDER",  "color": "#d97706",
     "nodes": ["Internet", "MetroE"]},
    {"label": "ARIZONA HQ CAMPUS", "color": "#0284c7",
     "nodes": ["R1-AZ", "Core1", "Core2", "Access1", "PC-10", "PC-20"]},
]

def zone_rect(zone):
    color = zone["color"]
    label = zone["label"]
    xs, ys = [], []
    for nid in zone["nodes"]:
        cx, cy = NODE_POS[nid]
        xs += [cx - HALF_BOX, cx + HALF_BOX]
        ys += [cy - HALF_BOX - 28, cy + HALF_BOX + 48]

    pad = 26
    x0 = min(xs) - pad
    y0 = min(ys) - pad - 10
    x1 = max(xs) + pad
    y1 = max(ys) + pad
    rw, rh = x1 - x0, y1 - y0

    return (
        f'  <!-- zone: {label} -->\n'
        f'  <rect x="{x0:.1f}" y="{y0:.1f}" width="{rw:.1f}" height="{rh:.1f}" rx="16" ry="16" '
        f'fill="{color}" fill-opacity="0.06" stroke="{color}" stroke-width="2" '
        f'stroke-dasharray="10 6" opacity="0.85"/>\n'
        f'  <text x="{x0 + 16:.1f}" y="{y0 + 22:.1f}" '
        f'font-family="{LABEL_FONT}" font-size="15" font-weight="800" '
        f'letter-spacing="0.08em" fill="{color}" opacity="0.95">{label}</text>'
    )

def straight_link_svg(from_id, to_id, color, offset=0):
    x1, y1 = NODE_POS[from_id]
    x2, y2 = NODE_POS[to_id]

    if offset != 0:
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length > 0:
            px = -dy / length * offset
            py = dx / length * offset
            x1 += px
            y1 += py
            x2 += px
            y2 += py

    d = f"M {x1:.1f},{y1:.1f} L {x2:.1f},{y2:.1f}"

    lines = [
        f'  <path d="{d}" fill="none" stroke="{color}" stroke-width="2.8" '
        f'stroke-opacity="0.85" stroke-linecap="round"/>'
    ]
    for px, py in [(x1, y1), (x2, y2)]:
        lines.append(f'  <circle cx="{px:.1f}" cy="{py:.1f}" r="4.2" fill="{color}" opacity="0.95"/>')
    return "\n".join(lines)

def node_svg(nid, label, icon_type, cx, cy, sublabel, label_above=False):
    sx, sy = cx - HALF_BOX, cy - HALF_BOX
    icon_uri = ICONS[icon_type]

    if label_above:
        label_y1 = cy - HALF_BOX - 8          # sublabel baseline
        label_y2 = cy - HALF_BOX - 28         # name baseline (topmost)
    else:
        label_y1 = cy + HALF_BOX + 22         # name baseline
        label_y2 = cy + HALF_BOX + 42         # sublabel baseline

    lines = [
        f'  <!-- node: {nid} -->',
        f'  <image href="{icon_uri}" x="{sx:.1f}" y="{sy:.1f}" '
        f'width="{ICON_BOX}" height="{ICON_BOX}" image-rendering="optimizeQuality"/>',
    ]
    if label_above and sublabel:
        lines += [
            f'  <text x="{cx}" y="{label_y2:.1f}" text-anchor="middle" '
            f'font-family="{LABEL_FONT}" font-size="18" font-weight="700" '
            f'fill="{LABEL_COLOR}">{label}</text>',
            f'  <text x="{cx}" y="{label_y1:.1f}" text-anchor="middle" '
            f'font-family="{LABEL_FONT}" font-size="16" font-weight="600" '
            f'fill="{LABEL_COLOR}">{sublabel}</text>',
        ]
    else:
        lines += [
            f'  <text x="{cx}" y="{label_y1:.1f}" text-anchor="middle" '
            f'font-family="{LABEL_FONT}" font-size="18" font-weight="700" '
            f'fill="{LABEL_COLOR}">{label}</text>',
        ]
        if sublabel:
            lines += [
                f'  <text x="{cx}" y="{label_y2:.1f}" text-anchor="middle" '
                f'font-family="{LABEL_FONT}" font-size="16" font-weight="600" '
                f'fill="{LABEL_COLOR}">{sublabel}</text>',
            ]
    return "\n".join(lines)

def build():
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'shape-rendering="geometricPrecision" text-rendering="geometricPrecision">',
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        '',
        '<!-- title -->',
        f'<text x="40" y="52" font-family="{LABEL_FONT}" font-size="30" '
        f'font-weight="800" fill="#0f172a">Arizona / Nevada / Florida — Network Topology</text>',
        '',
        '<!-- 1. ZONE BORDERS -->',
    ]
    for z in ZONES:
        parts.append(zone_rect(z))

    parts.append('\n<!-- 2. STRAIGHT LINKS (Packet Tracer style) -->')
    for row in LINKS:
        from_id, to_id, color, offset = row[0], row[1], row[2], row[3]
        parts.append(straight_link_svg(from_id, to_id, color, offset))

    parts.append('\n<!-- 3. ICONS + LABELS (drawn on top) -->')
    for nid, label, icon_type, cx, cy, sublabel, label_above in NODES:
        parts.append(node_svg(nid, label, icon_type, cx, cy, sublabel, label_above))

    parts.append('</svg>')
    return "\n".join(parts)

if __name__ == "__main__":
    out = os.path.join(SCRIPT_DIR, "topology.svg")
    svg = build()
    with open(out, "w") as f:
        f.write(svg)
    print(f"Written: {out}  ({len(svg):,} bytes)")

    png = out.replace(".svg", ".png")
    export_w = W * 2
    os.system(
        f'inkscape --export-filename="{png}" --export-width={export_w} '
        f'--export-png-antialias=3 --export-background="{BG}" --export-background-opacity=1 "{out}" 2>/dev/null || '
        f'magick -density 300 "{out}" "{png}" 2>/dev/null'
    )
    if os.path.exists(png):
        sz = os.path.getsize(png)
        print(f"PNG:     {png}  ({sz:,} bytes)")
