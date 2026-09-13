#!/usr/bin/env python3
"""
Topology SVG generator using custom isometric icons from Icons.svg.
Layout: Service Provider center, Arizona HQ right, Nevada DC bottom-left, Florida Branch bottom-right.
Links: Clean direct straight lines (Packet Tracer / GNS3 style), no 90-degree elbows.
Dual links between Core1 and Core2 drawn as parallel straight lines.
Links are mapped 1:1 from ccna.clab.yml (all 15 links).
"""

import base64
import os
import math

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(SCRIPT_DIR, "isoflow-icons")

W, H = 2000, 1100
BG = "#ffffff"
LABEL_FONT = "Inter, 'Segoe UI', Arial, sans-serif"
LABEL_COLOR = "#1e293b"
ICON_W, ICON_H = 120, 111
HALF_W, HALF_H = ICON_W // 2, ICON_H // 2

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
# Official IPs only: Core1 (10.16.0.1/24), R1-AZ (10.16.0.2/24), PC-10 (10.1.1.10/24), PC-20 (10.1.1.11/24)
NODES = [
    # SERVICE PROVIDER (center)
    ("Internet",  "Internet",      "cloud",     800, 210, "",              False),
    ("MetroE",    "MetroE",        "cloud",     800, 480, "",              False),

    # ARIZONA HQ CAMPUS (right)
    ("R1-AZ",     "R1-AZ",         "router",   1150, 360, "10.16.0.2/24", False),
    ("Core1",     "Core1",         "l3switch", 1370, 210, "10.16.0.1/24", True),
    ("Core2",     "Core2",         "l3switch", 1370, 510, "",              False),
    ("Access1",   "Access1",       "switch",   1590, 360, "",              False),
    ("PC-10",     "PC-10",         "pc",       1810, 210, "10.1.1.10/24", False),
    ("PC-20",     "PC-20",         "pc",       1810, 510, "10.1.1.11/24", False),

    # NEVADA DC (bottom-left)
    ("R2-NV",     "R2-NV",         "router",   330,  830, "",             False),
    ("NV-Switch", "NV-Switch",     "switch",   590,  830, "",             False),
    ("NV-PC",     "NV-PC",         "pc",       850,  830, "",             False),

    # FLORIDA BRANCH (bottom-right)
    ("R3-FL",     "R3-FL",         "router",  1150, 850, "",              False),
    ("FL-Switch", "FL-Switch",     "switch",  1410, 850, "",              False),
    ("FL-PC",     "FL-PC",         "pc",      1670, 850, "",              False),
]

NODE_POS = {n[0]: (n[3], n[4]) for n in NODES}

# All 15 links from ccna.clab.yml
LINKS = [
    # WAN links (direct straight lines)
    ("Internet",  "R1-AZ",     "#d97706", 0),
    ("MetroE",    "R1-AZ",     "#d97706", 0),
    ("MetroE",    "R2-NV",     "#d97706", 0),
    ("MetroE",    "R3-FL",     "#d97706", 0),

    # Arizona HQ links (direct straight lines)
    ("R1-AZ",     "Core1",     "#0284c7", 0),
    # Dual links between Core1 and Core2 (parallel lines offset by +/- 12px)
    ("Core1",     "Core2",     "#0284c7", -12),
    ("Core1",     "Core2",     "#0284c7", 12),
    ("Core1",     "Access1",   "#059669", 0),
    ("Core2",     "Access1",   "#059669", 0),
    ("Access1",   "PC-10",     "#64748b", 0),
    ("Access1",   "PC-20",     "#64748b", 0),

    # Nevada DC links
    ("R2-NV",     "NV-Switch", "#7c3aed", 0),
    ("NV-Switch", "NV-PC",     "#64748b", 0),

    # Florida Branch links
    ("R3-FL",     "FL-Switch", "#e11d48", 0),
    ("FL-Switch", "FL-PC",     "#64748b", 0),
]

ZONES = [
    {"label": "SERVICE PROVIDER",  "color": "#d97706",
     "nodes": ["Internet", "MetroE"]},
    {"label": "ARIZONA HQ CAMPUS", "color": "#0284c7",
     "nodes": ["R1-AZ", "Core1", "Core2", "Access1", "PC-10", "PC-20"]},
    {"label": "NEVADA DC",         "color": "#7c3aed",
     "nodes": ["R2-NV", "NV-Switch", "NV-PC"]},
    {"label": "FLORIDA BRANCH",    "color": "#e11d48",
     "nodes": ["R3-FL", "FL-Switch", "FL-PC"]},
]

def zone_rect(zone):
    color = zone["color"]
    label = zone["label"]
    xs, ys = [], []
    for nid in zone["nodes"]:
        cx, cy = NODE_POS[nid]
        xs += [cx - HALF_W, cx + HALF_W]
        ys += [cy - HALF_H, cy + HALF_H + 40]

    pad = 30
    x0 = min(xs) - pad
    y0 = min(ys) - pad - 24
    x1 = max(xs) + pad
    y1 = max(ys) + pad
    rw, rh = x1 - x0, y1 - y0

    return (
        f'  <!-- zone: {label} -->\n'
        f'  <rect x="{x0}" y="{y0}" width="{rw}" height="{rh}" rx="16" ry="16" '
        f'fill="{color}" fill-opacity="0.07" stroke="{color}" stroke-width="1.8" '
        f'stroke-dasharray="10 5" opacity="0.80"/>\n'
        f'  <text x="{x0 + 14}" y="{y0 + 20}" '
        f'font-family="{LABEL_FONT}" font-size="14" font-weight="700" '
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
        f'  <path d="{d}" fill="none" stroke="{color}" stroke-width="2.2" '
        f'stroke-opacity="0.8" stroke-linecap="round"/>'
    ]
    for px, py in [(x1, y1), (x2, y2)]:
        lines.append(f'  <circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{color}" opacity="0.9"/>')
    return "\n".join(lines)

def node_svg(nid, label, icon_type, cx, cy, sublabel, label_above=False):
    sx, sy = cx - HALF_W, cy - HALF_H
    icon_uri = ICONS[icon_type]
    if label_above:
        # sublabel (IP) on top, name just below it, both above the icon
        label_y1 = cy - HALF_H - 8          # name baseline
        label_y2 = cy - HALF_H - 24         # sublabel (IP) baseline (higher)
    else:
        label_y1 = cy + HALF_H + 18         # name baseline
        label_y2 = cy + HALF_H + 35         # sublabel (IP) baseline
    lines = [
        f'  <!-- node: {nid} -->',
        f'  <image href="{icon_uri}" x="{sx}" y="{sy}" '
        f'width="{ICON_W}" height="{ICON_H}" image-rendering="optimizeQuality"/>',
    ]
    if label_above and sublabel:
        # Draw name first (top), then IP below it — both above the icon
        lines += [
            f'  <text x="{cx}" y="{label_y2}" text-anchor="middle" '
            f'font-family="{LABEL_FONT}" font-size="16" font-weight="600" '
            f'fill="{LABEL_COLOR}">{label}</text>',
            f'  <text x="{cx}" y="{label_y1}" text-anchor="middle" '
            f'font-family="{LABEL_FONT}" font-size="14" fill="#64748b">{sublabel}</text>',
        ]
    else:
        lines += [
            f'  <text x="{cx}" y="{label_y1}" text-anchor="middle" '
            f'font-family="{LABEL_FONT}" font-size="16" font-weight="600" '
            f'fill="{LABEL_COLOR}">{label}</text>',
        ]
        if sublabel:
            lines += [
                f'  <text x="{cx}" y="{label_y2}" text-anchor="middle" '
                f'font-family="{LABEL_FONT}" font-size="14" fill="#64748b">{sublabel}</text>',
            ]
    return "\n".join(lines)

def build():
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        '',
        '<!-- title -->',
        f'<text x="36" y="50" font-family="{LABEL_FONT}" font-size="26" '
        f'font-weight="700" fill="#1e293b">Arizona / Nevada / Florida — Network Topology</text>',
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
    os.system(
        f'inkscape --export-filename="{png}" --export-width=2000 "{out}" 2>/dev/null || '
        f'convert -density 150 "{out}" "{png}" 2>/dev/null'
    )
    if os.path.exists(png):
        sz = os.path.getsize(png)
        print(f"PNG:     {png}  ({sz:,} bytes)")
