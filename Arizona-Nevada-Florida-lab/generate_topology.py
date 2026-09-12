#!/usr/bin/env python3
"""
Topology SVG: isoflow icons at direct pixel positions.
Layout: SP center, AZ right, NV bottom-left, FL bottom-right.
Draw order: zones → links → icons → labels (text always on top).
Links support optional explicit waypoints for clean routing.
"""

import base64, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(SCRIPT_DIR, "isoflow-icons")

W, H = 2000, 1100
BG = "#ffffff"
LABEL_FONT = "Inter, 'Segoe UI', Arial, sans-serif"
LABEL_COLOR = "#1e293b"
ICON_W, ICON_H = 120, 111   # bigger icons (~518:477 ratio)
HALF_W, HALF_H = ICON_W // 2, ICON_H // 2

# ── icon loader ──────────────────────────────────────────────────────────────
def load_icon(filename):
    with open(os.path.join(ICON_DIR, filename), "rb") as f:
        data = f.read()
    return f"data:image/svg+xml;base64,{base64.b64encode(data).decode()}"

ICONS = {
    "router": load_icon("router.svg"),
    "switch": load_icon("L2-switch.svg"),
    "pc":     load_icon("desktop.svg"),
    "cloud":  load_icon("cloud.svg"),
}

# ── node definitions (cx, cy = icon center) ──────────────────────────────────
#   id, label, type, cx, cy, sublabel
NODES = [
    # ── SERVICE PROVIDER (center) ──
    ("internet", "Internet",      "cloud",  800, 230, ""),
    ("metroe",   "MetroE Bridge", "cloud",  800, 490, ""),

    # ── ARIZONA HQ CAMPUS (right) — IPs from IP Addressing Table only ──
    ("r1_az",   "R1-AZ",   "router", 1150, 350, "10.16.0.2/24"),
    ("core1",   "Core1",   "switch", 1370, 210, "10.16.0.1/24"),
    ("core2",   "Core2",   "switch", 1370, 490, ""),
    ("access1", "Access1", "switch", 1590, 210, ""),
    ("access2", "Access2", "switch", 1590, 490, ""),
    ("pc10",    "PC-10",   "pc",     1810, 210, "10.1.1.10/24"),
    ("pc20",    "PC-20",   "pc",     1810, 490, "10.1.1.11/24"),

    # ── NEVADA DC (bottom-left) ──
    ("r1_nv",   "R1-NV",   "router", 330,  800, ""),
    ("core_nv", "Core-NV", "switch", 590,  800, ""),
    ("srv_nv",  "SRV-NV",  "pc",     850,  800, ""),

    # ── FLORIDA BRANCH (bottom-right) ──
    ("r1_fl",   "R1-FL",   "router", 1150, 870, ""),
    ("core_fl", "Core-FL", "switch", 1410, 870, ""),
    ("pc_fl",   "PC-FL",   "pc",     1670, 870, ""),
]

NODE_POS = {n[0]: (n[3], n[4]) for n in NODES}

# ── links: (from, to, color, label, waypoints_or_None) ───────────────────────
# waypoints = list of (x,y) intermediate screen points the path must pass through
LINKS = [
    # WAN / provider — explicit routing to avoid zone crossings
    ("internet", "r1_az",   "#d97706", "", [(1150, 230)]),
    ("metroe",   "r1_az",   "#d97706", "", [(800, 350),(1000,350)]),
    ("metroe",   "r1_nv",   "#d97706", "", [(330, 490)]),
    ("metroe",   "r1_fl",   "#d97706", "", [(1000, 490),(1000, 870)]),

    # Arizona HQ internal
    ("r1_az",    "core1",   "#0284c7", "", None),
    ("r1_az",    "core2",   "#0284c7", "", None),
    ("core1",    "core2",   "#0284c7", "", None),
    ("core1",    "access1", "#059669", "", None),
    ("core2",    "access2", "#059669", "", None),
    ("access1",  "pc10",    "#64748b", "", None),
    ("access2",  "pc20",    "#64748b", "", None),

    # Nevada DC
    ("r1_nv",    "core_nv", "#7c3aed", "", None),
    ("core_nv",  "srv_nv",  "#64748b", "", None),

    # Florida Branch
    ("r1_fl",    "core_fl", "#e11d48", "", None),
    ("core_fl",  "pc_fl",   "#64748b", "", None),
]

# ── zones ─────────────────────────────────────────────────────────────────────
ZONES = [
    {"label": "SERVICE PROVIDER",  "color": "#d97706",
     "nodes": ["internet", "metroe"]},
    {"label": "ARIZONA HQ CAMPUS", "color": "#0284c7",
     "nodes": ["r1_az","core1","core2","access1","access2","pc10","pc20"]},
    {"label": "NEVADA DC",         "color": "#7c3aed",
     "nodes": ["r1_nv","core_nv","srv_nv"]},
    {"label": "FLORIDA BRANCH",    "color": "#e11d48",
     "nodes": ["r1_fl","core_fl","pc_fl"]},
]

# ── SVG helpers ───────────────────────────────────────────────────────────────

def zone_rect(zone):
    color = zone["color"]
    label = zone["label"]
    xs, ys = [], []
    for nid in zone["nodes"]:
        cx, cy = NODE_POS[nid]
        xs += [cx - HALF_W, cx + HALF_W]
        ys += [cy - HALF_H, cy + HALF_H + 40]   # room for 2 label lines

    pad = 30
    x0 = min(xs) - pad
    y0 = min(ys) - pad - 24   # extra room above for zone label
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


def link_svg(from_id, to_id, color, lbl, waypoints):
    x1, y1 = NODE_POS[from_id]
    x2, y2 = NODE_POS[to_id]

    if waypoints:
        pts = [(x1, y1)] + list(waypoints) + [(x2, y2)]
        cmds = [f"M{pts[0][0]},{pts[0][1]}"]
        for px, py in pts[1:]:
            cmds.append(f"L{px},{py}")
        d = " ".join(cmds)
        mid_idx = len(pts) // 2
        mx, my = pts[mid_idx]
    else:
        if abs(y1 - y2) < 20:
            d = f"M{x1},{y1} L{x2},{y2}"
        else:
            mx_e = (x1 + x2) // 2
            d = f"M{x1},{y1} L{mx_e},{y1} L{mx_e},{y2} L{x2},{y2}"
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2

    lines = [
        f'  <path d="{d}" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-opacity="0.75" stroke-linecap="round" stroke-linejoin="round"/>'
    ]
    lines.append(
        f'  <circle cx="{x2}" cy="{y2}" r="4" fill="{color}" opacity="0.9"/>'
    )
    if lbl:
        lines += [
            f'  <rect x="{mx - 26}" y="{my - 12}" width="52" height="14" '
            f'rx="3" fill="{BG}" fill-opacity="0.8"/>',
            f'  <text x="{mx}" y="{my - 1}" text-anchor="middle" '
            f'font-family="{LABEL_FONT}" font-size="11" fill="{color}" opacity="0.95">{lbl}</text>',
        ]
    return "\n".join(lines)


def node_svg(nid, label, icon_type, cx, cy, sublabel):
    sx, sy = cx - HALF_W, cy - HALF_H
    icon_uri = ICONS[icon_type]
    label_y1 = cy + HALF_H + 18
    label_y2 = cy + HALF_H + 35
    lines = [
        f'  <!-- icon: {nid} -->',
        f'  <image href="{icon_uri}" x="{sx}" y="{sy}" '
        f'width="{ICON_W}" height="{ICON_H}" image-rendering="optimizeQuality"/>',
    ]
    lines += [
        f'  <rect x="{cx - 68}" y="{cy + HALF_H + 4}" width="136" height="19" '
        f'rx="3" fill="{BG}" fill-opacity="0.9"/>',
        f'  <text x="{cx}" y="{label_y1}" text-anchor="middle" '
        f'font-family="{LABEL_FONT}" font-size="16" font-weight="600" '
        f'fill="{LABEL_COLOR}">{label}</text>',
    ]
    if sublabel:
        lines += [
            f'  <rect x="{cx - 70}" y="{cy + HALF_H + 23}" width="140" height="17" '
            f'rx="3" fill="{BG}" fill-opacity="0.9"/>',
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
        '<!-- ═══ 1. ZONE BORDERS (drawn first, behind everything) ═══ -->',
    ]
    for z in ZONES:
        parts.append(zone_rect(z))

    parts.append('\n<!-- ═══ 2. LINKS (drawn before icons so text is always on top) ═══ -->')
    for row in LINKS:
        from_id, to_id, color, lbl = row[0], row[1], row[2], row[3]
        waypoints = row[4] if len(row) > 4 else None
        parts.append(link_svg(from_id, to_id, color, lbl, waypoints))

    parts.append('\n<!-- ═══ 3. ICONS + LABELS (drawn last, always on top) ═══ -->')
    for nid, label, icon_type, cx, cy, sublabel in NODES:
        parts.append(node_svg(nid, label, icon_type, cx, cy, sublabel))

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
