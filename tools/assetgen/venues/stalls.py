"""Market stalls — the eight traders in Hearthmere's square.

The square is the town's living room, and these eight booths are what make it
read as *busy* rather than as an empty plaza. They carry most of its colour and
almost all of its life-per-triangle. The fountain is the anchor; the stalls are
the proof that people are here.

Design rules this module follows:

  - **Every stall is a person's business.** The potter stacks in graded rows;
    the fishmonger's boards are wet and gutted-on; the baker is dusted in
    flour; the charm seller hangs everything on strings. The arrangement, not
    the label, has to tell you who runs it (Art Bible §7 "Function").
  - **Nothing repeats.** Each stall has its own asset_id, its own frame
    proportions, its own awning sag, patch count and stripe treatment, and its
    own hand-written goods layout. There is no `for i in range(8)`.
  - **Residue everywhere** (Art Bible §7): produce spilled under a table, a cat
    stalking the fish, flour on the ground, straw from the pottery packing,
    crates stacked behind, a stool, scales and weights, a chalked tally board,
    rope-tied bundles, a cloak left over a rail.
  - **Two loose rows, not a grid** (World Bible): the rows funnel in from the
    north road mouth where the footfall is, and thin out toward the south. Each
    stall is angled toward the arriving traffic — traders face the money.

Scale is fixed by Art Bible §3: counter 0.90 m, awning clearance 2.20 m.
Everything is checked against the 1.75 m reference figure in the renders.
"""

from __future__ import annotations

import numpy as np

from core import mesh as M
from core import kit as K
from core.mathx import rng_for, jitter
from core.venue import VenueContext

NAME = "stalls"
CELLS = ["C3", "D3", "C4", "D4"]

# Art Bible §3 — never hardcode these anywhere else in the file.
COUNTER_H = 0.90
AWNING_CLEAR = 2.20

CH_PROP = 0.008     # furniture / prop chamfer
CH_SMALL = 0.003    # handheld and small metal


# ---------------------------------------------------------------------------
# Geometry helpers (venue-local; core/ is owned by other agents this pass)
# ---------------------------------------------------------------------------

def _tex(m, su=1.0, sv=None, ou=0.0, ov=0.0):
    """Rescale/offset a mesh's UVs.

    Two jobs. First, texel density: a 6 cm apple and a 2 m counter cannot share
    a UV scale or one of them samples a single texel. Second — and this is the
    important one — every library material carries its own internal variance
    (per-tile firing colour in terracotta, per-board grain in oak). Offsetting
    each instance into a different region of the same texture is how twelve
    lathed pots come out twelve different shades of fired clay without adding a
    material or breaking the locked palette.
    """
    sv = su if sv is None else sv
    if len(m.uv):
        m.uv = (m.uv * np.array([su, sv], np.float32)
                + np.array([ou, ov], np.float32)).astype(np.float32)
    return m


def _prism(profile, depth, mat, chamfer=0.005, uv_scale=1.0):
    """Extruded 2D profile with a true chamfer on every edge.

    `mesh.prism` accepts a chamfer argument and ignores it, so cut-out signage
    built with it comes out with razor CAD edges — the first thing review
    rejects (Art Bible §6). This does the real thing: the profile corners are
    mitred in-plane, and the two end caps are inset so the perimeter gets a
    bevel band that catches the sun.
    """
    pts = [np.asarray(p, np.float64) for p in profile]
    n = len(pts)
    c = float(chamfer)
    if c <= 1e-6 or n < 3:
        return M.prism(profile, depth, mat, uv_scale=uv_scale)

    # -- 1. mitre the in-plane corners ------------------------------------
    cut = []
    for i in range(n):
        p, a, b = pts[i], pts[i - 1], pts[(i + 1) % n]
        din, dout = p - a, b - p
        lin, lout = np.linalg.norm(din), np.linalg.norm(dout)
        if lin < 1e-9 or lout < 1e-9:
            cut.append(p)
            continue
        k = min(c, lin * 0.4, lout * 0.4)
        cut.append(p - din / lin * k)
        cut.append(p + dout / lout * k)
    cut = np.array(cut)

    # -- 2. inset copy for the end caps -----------------------------------
    cen = cut.mean(axis=0)
    off = cut - cen
    ln = np.linalg.norm(off, axis=1, keepdims=True)
    ins = cut - off / np.maximum(ln, 1e-9) * np.minimum(c, ln * 0.4)

    hd = depth * 0.5
    b = M._Builder()
    f_out = [np.array([p[0], p[1], hd - c], np.float32) for p in cut]
    b_out = [np.array([p[0], p[1], -hd + c], np.float32) for p in cut]
    f_in = [np.array([p[0], p[1], hd], np.float32) for p in ins]
    b_in = [np.array([p[0], p[1], -hd], np.float32) for p in ins]

    b.poly(f_in, None, np.array([0, 0, 1], np.float32))
    b.poly(b_in[::-1], None, np.array([0, 0, -1], np.float32))
    m = len(cut)
    for i in range(m):
        j = (i + 1) % m
        for quad in ([f_out[i], f_out[j], b_out[j], b_out[i]],     # side wall
                     [f_in[i], f_in[j], f_out[j], f_out[i]],       # front bevel
                     [b_out[i], b_out[j], b_in[j], b_in[i]]):      # back bevel
            nrm = np.cross(quad[1] - quad[0], quad[2] - quad[0])
            if np.linalg.norm(nrm) < 1e-12:
                continue
            b.poly(quad, M._planar_uv(quad, nrm / np.linalg.norm(nrm), uv_scale))
    return b.build(mat)


def _globe(r, mat, seg=8, rings=4, sx=1.0, sy=1.0, sz=1.0, uv=1.0, ou=0.0, ov=0.0):
    """Low-poly sphere centred on the origin. Fruit, loaves, heads, floats."""
    prof = []
    for i in range(rings + 1):
        a = np.pi * i / rings
        prof.append((r * np.sin(a) * 1.0, r - r * np.cos(a)))
    m = M.lathe(prof, seg, mat, close_bottom=False, close_top=False)
    m.translate(0, -r, 0)
    if (sx, sy, sz) != (1.0, 1.0, 1.0):
        m.scale(sx, sy, sz)
    return _tex(m, uv, uv, ou, ov)


def _cone(r, h, mat, seg=7, uv=1.0, ou=0.0, ov=0.0):
    """Tapered root vegetable / bundle. Tip at the bottom, base at +h."""
    m = M.lathe([(0.0, 0.0), (r * 0.45, h * 0.28), (r * 0.82, h * 0.62),
                 (r, h * 0.92), (r * 0.93, h)], seg, mat, close_bottom=False)
    return _tex(m, uv, uv, ou, ov)


def _link(p0, p1, r, mat, seg=5, chamfer=0.0015):
    """A cylinder spanning two points. Ropes, chains, spits, skewers, legs."""
    p0 = np.asarray(p0, np.float64)
    p1 = np.asarray(p1, np.float64)
    d = p1 - p0
    L = float(np.linalg.norm(d))
    if L < 1e-6:
        return None
    c = M.cylinder(r, L, seg, min(chamfer, r * 0.4), mat)
    dn = d / L
    a = float(np.arccos(np.clip(dn[1], -1.0, 1.0)))
    if abs(np.sin(a)) > 1e-6:
        c.rotate_x(a)
        c.rotate_y(float(np.arctan2(dn[0], dn[2])))
    elif dn[1] < 0:
        c.rotate_x(np.pi)
    c.translate(*p0)
    return c


def _cord(p0, p1, sag, mat="canvas", r=0.008, segs=6, seg_faces=4):
    """A hanging line as a real catenary of short links.

    Used for awning guys, hanging strings of charms, the sausage rack and every
    tie-down. A straight cylinder between two points reads as a steel rod; the
    droop is what makes it read as rope.
    """
    out = M.Group()
    p0 = np.asarray(p0, np.float64)
    p1 = np.asarray(p1, np.float64)
    prev = None
    for i in range(segs + 1):
        t = i / segs
        p = p0 + (p1 - p0) * t
        p = p + np.array([0.0, -sag * 4.0 * t * (1.0 - t), 0.0])
        if prev is not None:
            out.add(_link(prev, p, r, mat, seg_faces))
        prev = p
    return out


def _ring(r, section, mat, seg=10, tilt=0.0):
    """A torus-ish band: rope lashing, barrel hoop, bracelet, pot rim."""
    m = M.lathe([(r - section * 0.5, -section * 0.35), (r + section * 0.4, 0.0),
                 (r - section * 0.5, section * 0.35)], seg, mat,
                close_bottom=False, close_top=False)
    if tilt:
        m.rotate_x(tilt)
    return m


def _sheet(w, d, hf, uv_fn, nx=12, nz=8, mat="canvas"):
    """A smooth-shaded hanging cloth surface.

    v = 0 at the back edge (+Z), v = 1 at the front edge (-Z), so a stall's
    awning is authored front-facing like everything else. Normals come from the
    analytic height field rather than face normals: cloth is the one thing in
    this town that must NOT be faceted, or it reads as folded cardboard.
    """
    vs, ns, uvs, idx = [], [], [], []
    e = 1e-3
    for j in range(nz + 1):
        for i in range(nx + 1):
            u, v = i / nx, j / nz
            x = -w * 0.5 + u * w
            z = d * 0.5 - v * d
            y = hf(u, v)
            u0, u1 = max(0.0, u - e), min(1.0, u + e)
            v0, v1 = max(0.0, v - e), min(1.0, v + e)
            dydx = (hf(u1, v) - hf(u0, v)) / ((u1 - u0) * w)
            dydz = -(hf(u, v1) - hf(u, v0)) / ((v1 - v0) * d)
            n = np.array([-dydx, 1.0, -dydz], np.float64)
            n /= np.linalg.norm(n)
            vs.append((x, y, z))
            ns.append(n)
            uvs.append(uv_fn(x, z))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            b, c, dd = a + 1, a + nx + 2, a + nx + 1
            idx += [a, c, b, a, dd, c]
    return M.Mesh(np.array(vs, np.float32), np.array(ns, np.float32),
                  np.array(uvs, np.float32), np.array(idx, np.uint32), mat=mat)


# Stripe treatments. The canvas material is authored striped (6 bands per UV),
# so the stripe *pitch* is a UV scale and a "plain" awning is one whose UV span
# is compressed into a single cream band. That is how eight awnings get five
# different looks out of one locked-palette texture: Art Bible §4 wants roughly
# 40% of stalls striped, not 100%.
STRIPE = {
    "wide":   dict(su=0.38, sv=0.45, ou=0.02, axis="x"),
    "narrow": dict(su=0.62, sv=0.50, ou=0.30, axis="x"),
    "cross":  dict(su=0.46, sv=0.42, ou=0.11, axis="z"),
    "cream":  dict(su=0.055, sv=0.60, ou=0.128, axis="x"),
    "russet": dict(su=0.050, sv=0.60, ou=0.045, axis="x"),
}


def _stripe_uv(kind, ou_extra=0.0, ov=0.0):
    s = STRIPE[kind]
    if s["axis"] == "x":
        return lambda x, z: (x * s["su"] + s["ou"] + ou_extra, z * s["sv"] + ov)
    return lambda x, z: (z * s["su"] + s["ou"] + ou_extra, x * s["sv"] + ov)


# ---------------------------------------------------------------------------
# The stall shell: frame, counter, awning
# ---------------------------------------------------------------------------

def _post(h, sec, mat, rng, lean=0.0):
    """A hand-cut upright. Slightly out of plumb, because they all are."""
    p = M.box(sec, h, sec * jitter(rng, 1.0, 0.10), CH_PROP, mat)
    p.uv = np.stack([p.v[:, 0] * 2.2, p.v[:, 1] * 0.55], axis=1).astype(np.float32)
    p.translate(0, h * 0.5, 0)
    if lean:
        p.rotate_z(lean)
    return p


def _shell(sid, rng, w, d, *, front_h=2.34, back_h=2.86, sagx=0.09, sagz=0.07,
           stripe="wide", valance=0.22, patches=2, timber="oak_weathered",
           awn_mat="canvas", over_f=0.30, over_s=0.17, torn=0.0,
           back_panel="boards", guys=2, nx=13, nz=8):
    """Frame + awning, in stall-local space (front faces -Z, origin on ground).

    Returns (group, info) where info carries the awning height field and the
    frame anchors so each stall can hang its own goods off them.
    """
    out = M.Group()
    sec = 0.088
    hw, hd = w * 0.5, d * 0.5

    # -- uprights ---------------------------------------------------------
    corners = {}
    for sx in (-1, 1):
        for sz in (-1, 1):
            h = front_h if sz < 0 else back_h
            lean = rng.uniform(-0.014, 0.014)
            p = _post(h, sec, timber, rng, lean)
            x, z = sx * hw, sz * hd
            p.translate(x, 0, z)
            out.add(p)
            corners[(sx, sz)] = (x, z, h)
            # A stone wedge under one foot — the square is not flat and every
            # trader in history has packed a post up with whatever was to hand.
            if rng.random() < 0.35:
                wg = M.box(0.15, 0.045, 0.13, 0.006, "stone")
                wg.rotate_y(rng.uniform(-0.4, 0.4))
                wg.translate(x + rng.uniform(-0.02, 0.02), 0.020, z)
                out.add(wg)

    # -- headers and rails ------------------------------------------------
    fh = M.plank(w + 0.16, 0.10, 0.075, CH_PROP, timber)
    fh.translate(0, front_h - 0.045, -hd)
    out.add(fh)
    bh = M.plank(w + 0.12, 0.10, 0.075, CH_PROP, timber)
    bh.translate(0, back_h - 0.045, hd)
    out.add(bh)
    for sx in (-1, 1):
        # Side rail slopes back-to-front; the awning lies on these.
        ln = float(np.hypot(d, back_h - front_h))
        r = M.plank(ln, 0.075, 0.06, CH_PROP, timber)
        r.rotate_z(0)
        r.rotate_y(np.pi * 0.5)
        r.rotate_x(-float(np.arctan2(back_h - front_h, d)))
        r.translate(sx * hw, (front_h + back_h) * 0.5 - 0.03, 0)
        out.add(r)
        # Knee brace at the back post — visible structure, and it is the piece
        # that tells you the frame is pegged rather than welded.
        if rng.random() < 0.75:
            br = M.plank(0.46, 0.05, 0.05, 0.004, timber)
            br.rotate_z(-np.pi * 0.25)
            br.rotate_y(np.pi * 0.5)
            br.translate(sx * hw, back_h - 0.30, hd - 0.16)
            out.add(br)

    # Rope lashings where members cross. Hand-built means tied, not bolted.
    for (sx, sz), (x, z, h) in corners.items():
        lash = _ring(sec * 0.86, 0.028, "canvas", 8)
        lash.translate(x, h - 0.05 + rng.uniform(-0.01, 0.01), z)
        out.add(lash)

    # -- awning -----------------------------------------------------------
    aw = w + 2 * over_s
    ad = d + over_f
    v_frame = d / ad
    ph = [rng.uniform(0, 6.28) for _ in range(3)]
    dip_corner = rng.integers(0, 4)

    def hf(u, v):
        t = min(1.0, v / v_frame)
        y = back_h + (front_h - back_h) * t
        # Sag between the two front posts, deepest at mid-span and mostly felt
        # near the free edge.
        y -= sagx * np.sin(np.pi * u) * (0.25 + 0.75 * v)
        # Sag between the back header and the front header.
        y -= sagz * np.sin(np.pi * min(v / v_frame, 1.0)) * (0.55 + 0.45 * np.sin(np.pi * u))
        # Cloth ripple — small, irregular, phase-randomised per stall.
        y += 0.016 * np.sin(u * 5.1 * np.pi + ph[0]) * np.sin(v * 2.3 * np.pi + ph[1])
        y += 0.009 * np.sin(u * 9.7 * np.pi + ph[2])
        # One corner pulled down harder than the others: nothing hangs level.
        cu = 1.0 - u if dip_corner % 2 else u
        cv = 1.0 - v if dip_corner < 2 else v
        y -= 0.055 * (cu ** 3) * (cv ** 2)
        return y

    uvf = _stripe_uv(stripe, rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4))
    sheet = _sheet(aw, ad, hf, uvf, nx, nz, awn_mat)
    sheet.translate(0, 0, (d * 0.5 + hd) * 0 + (hd - ad * 0.5) + (ad - d) * 0.0)
    # Sheet spans z from +hd (back) to -(hd+over_f) (front).
    sheet.translate(0, 0, hd - ad * 0.5 - (hd - ad * 0.5))
    out.add(sheet)

    def world(u, v):
        return np.array([-aw * 0.5 + u * aw, hf(u, v), hd - v * ad])

    # Rafters under the cloth — the reason it sags where it sags.
    for t in (0.5,) if w < 2.0 else (0.34, 0.68):
        x = -hw + t * w
        p0 = np.array([x, front_h - 0.055, -hd])
        p1 = np.array([x, back_h - 0.055, hd])
        out.add(_link(p0, p1, 0.026, timber, 6, 0.003))

    # Front valance: the scalloped skirt that says "market" from 40 m away.
    if valance > 0:
        vs, ns, uvs, idx = [], [], [], []
        nvx = nx
        zf = hd - ad
        for j in range(3):
            for i in range(nvx + 1):
                u = i / nvx
                top = hf(u, 1.0)
                # Scalloped hem, deeper in the middle of each swag.
                drop = valance * (0.62 + 0.38 * abs(np.sin(u * 3.0 * np.pi + ph[0])))
                y = top - drop * (j / 2.0)
                z = zf + 0.012 * np.sin(u * 6.0 * np.pi + ph[1]) * (j / 2.0)
                x = -aw * 0.5 + u * aw
                vs.append((x, y, z))
                ns.append((0.0, 0.10, -1.0))
                uvs.append(uvf(x, z - 0.30 * (j / 2.0)))
        for j in range(2):
            for i in range(nvx):
                a = j * (nvx + 1) + i
                idx += [a, a + 1, a + nvx + 2, a, a + nvx + 2, a + nvx + 1]
        nn = np.array(ns, np.float32)
        nn /= np.linalg.norm(nn, axis=1, keepdims=True)
        out.add(M.Mesh(np.array(vs, np.float32), nn, np.array(uvs, np.float32),
                       np.array(idx, np.uint32), mat=awn_mat))

    # Patches. Every awning in a real market has been repaired, and no two have
    # been repaired the same way.
    for k in range(patches):
        pu = rng.uniform(0.12, 0.88)
        pv = rng.uniform(0.12, 0.85)
        pw = rng.uniform(0.22, 0.42)
        pd = rng.uniform(0.18, 0.34)
        du, dv = pw / aw, pd / ad
        pts, nps, uvp, ip = [], [], [], []
        for j in range(2):
            for i in range(2):
                u = float(np.clip(pu + (i - 0.5) * du, 0, 1))
                v = float(np.clip(pv + (j - 0.5) * dv, 0, 1))
                p = world(u, v) + np.array([0, 0.008, 0])
                pts.append(p)
                nps.append((0, 1, 0))
                uvp.append(uvf(p[0] + rng.uniform(-1.5, 1.5), p[2] + 0.7))
        ip += [0, 2, 3, 0, 3, 1]
        out.add(M.Mesh(np.array(pts, np.float32), np.array(nps, np.float32),
                       np.array(uvp, np.float32), np.array(ip, np.uint32), mat=awn_mat))
        # Stitching: a dashed line of tiny dark pegs around two edges.
        for s in range(5):
            t = (s + 0.5) / 5
            q = world(float(np.clip(pu - du * 0.5 + du * t, 0, 1)),
                      float(np.clip(pv - dv * 0.5, 0, 1))) + np.array([0, 0.012, 0])
            st = M.box(0.012, 0.006, 0.02, 0.001, "oak_dark")
            st.translate(*q)
            out.add(st)

    # Guy ropes from the front corners to iron pegs in the ground. Silhouette,
    # and the single cheapest way to say "this is temporary and put up by hand".
    for gi in range(guys):
        sx = -1 if gi % 2 == 0 else 1
        top = np.array([sx * (hw + over_s * 0.7), hf(0.5 + sx * 0.44, 0.94), -hd - over_f * 0.7])
        peg = np.array([sx * (hw + rng.uniform(0.55, 0.85)), 0.0,
                        -hd - rng.uniform(0.35, 0.75)])
        out.add(_cord(top, peg, 0.03, "canvas", 0.011, 4))
        pin = M.cylinder(0.016, 0.20, 6, CH_SMALL, "iron")
        pin.rotate_x(rng.uniform(0.2, 0.4) * sx)
        pin.translate(peg[0], -0.03, peg[2])
        out.add(pin)

    # -- back screen ------------------------------------------------------
    # Without it you see straight through the stall to the ground plane, which
    # is the classic unfinished-blockout read. It also gives the goods a
    # backdrop to sit against, which is what makes them legible.
    if back_panel == "boards":
        nb = max(3, int(w / 0.34))
        for i in range(nb):
            bw = w / nb
            bd = M.box(bw * 0.95, back_h * rng.uniform(0.52, 0.66), 0.028, 0.005, timber)
            bd.uv = np.stack([bd.v[:, 0] * 1.6, bd.v[:, 1] * 0.6], axis=1).astype(np.float32)
            bd.translate(-hw + (i + 0.5) * bw, back_h * 0.42 + rng.uniform(-0.03, 0.03),
                         hd - 0.05)
            out.add(bd)
    elif back_panel == "cloth":
        def bhf(u, v):
            return back_h - 0.10 - v * (back_h - 0.62) + 0.03 * np.sin(u * 4.0 * np.pi + ph[0])
        bs = _sheet(w + 0.05, back_h - 0.5, bhf,
                    lambda x, z: (x * 0.42 + 0.3, z * 0.42), nx, 4, awn_mat)
        bs.rotate_x(np.pi * 0.5)
        bs.translate(0, 0, hd - 0.04)
        # rotate_x maps the sheet's z-extent onto y; rebuild by hand instead.
        out.add(_cloth_hang(w + 0.05, back_h - 0.12, 0.62, hd - 0.05, ph,
                            uvf, awn_mat, nxx=nx))

    info = dict(w=w, d=d, hw=hw, hd=hd, front_h=front_h, back_h=back_h,
                hf=hf, world=world, aw=aw, ad=ad, sec=sec, timber=timber)
    return out, info


def _cloth_hang(w, ytop, ybot, z, ph, uvf, mat="canvas", nxx=10, nyy=4, wave=0.05):
    """A cloth panel hanging from a rail: back screens, cloth-stall wares, a
    cloak left over a rail. Waves in Z so it never reads as a flat card."""
    vs, ns, uvs, idx = [], [], [], []
    for j in range(nyy + 1):
        for i in range(nxx + 1):
            u, v = i / nxx, j / nyy
            x = -w * 0.5 + u * w
            y = ytop + (ybot - ytop) * v
            off = wave * np.sin(u * 3.4 * np.pi + ph[0]) * (0.25 + 0.75 * v)
            vs.append((x, y, z + off))
            dz = wave * 3.4 * np.pi / w * np.cos(u * 3.4 * np.pi + ph[0]) * (0.25 + 0.75 * v)
            n = np.array([-dz, 0.12, -1.0])
            ns.append(n / np.linalg.norm(n))
            uvs.append(uvf(x, -y))
    for j in range(nyy):
        for i in range(nxx):
            a = j * (nxx + 1) + i
            idx += [a, a + 1, a + nxx + 2, a, a + nxx + 2, a + nxx + 1]
    return M.Mesh(np.array(vs, np.float32), np.array(ns, np.float32),
                  np.array(uvs, np.float32), np.array(idx, np.uint32), mat=mat)


def _counter(sid, rng, w, d, *, h=COUNTER_H, mat="oak_weathered", planks=4,
             fascia=True, shelf=0.34, front_z=None, depth=None, tilt=0.0):
    """The 0.90 m counter (Art Bible §3). Boards, not a slab: gaps between them
    catch shadow, and one board is always newer than the rest."""
    out = M.Group()
    dep = depth if depth is not None else d * 0.78
    zf = front_z if front_z is not None else -d * 0.5 + 0.04
    zc = zf + dep * 0.5
    for i in range(planks):
        pw = dep / planks
        p = M.plank(w * jitter(rng, 0.98, 0.02), pw * 0.94, 0.038, 0.005, mat)
        p.rotate_x(tilt)
        p.translate(rng.uniform(-0.012, 0.012), h + rng.uniform(-0.006, 0.004),
                    zf + (i + 0.5) * pw)
        _tex(p, 1.0, 1.0, rng.uniform(0, 3), rng.uniform(0, 3))
        out.add(p)
    if fascia:
        f = M.box(w * 1.01, 0.165, 0.032, 0.005, mat)
        f.uv = np.stack([f.v[:, 0] * 0.6, f.v[:, 1] * 1.8], axis=1).astype(np.float32)
        f.translate(0, h - 0.10, zf - 0.012)
        out.add(f)
    # Bearers and a pair of trestle legs, so the counter is held up by
    # something you can see.
    for sx in (-1, 1):
        br = M.plank(dep, 0.07, 0.055, 0.004, mat)
        br.rotate_y(np.pi * 0.5)
        br.translate(sx * w * 0.38, h - 0.055, zc)
        out.add(br)
        for sz in (-1, 1):
            lg = M.box(0.06, h - 0.09, 0.055, 0.005, mat)
            lg.translate(sx * w * 0.38, (h - 0.09) * 0.5, zc + sz * dep * 0.32)
            out.add(lg)
    if shelf:
        for i in range(2):
            sp = M.plank(w * 0.9, dep * 0.44, 0.030, 0.004, mat)
            sp.translate(0, shelf, zc + (i - 0.5) * dep * 0.46)
            out.add(sp)
        for sx in (-1, 1):
            rl = M.plank(dep * 0.9, 0.05, 0.04, 0.004, mat)
            rl.rotate_y(np.pi * 0.5)
            rl.translate(sx * w * 0.38, shelf - 0.035, zc)
            out.add(rl)
    return out


# ---------------------------------------------------------------------------
# Goods
# ---------------------------------------------------------------------------

def _heap(sid, rng, make, count, rx, rz, y0, drop=0.62, layers=3):
    """A pile of loose goods, stacked as they actually settle: a wide base
    course, fewer above, everything rolled slightly out of alignment."""
    out = M.Group()
    n_left = count
    for L in range(layers):
        k = max(1, int(round(count * (drop ** L) / max(1, sum(drop ** q for q in range(layers))) * layers * 0.5)))
        k = min(k, n_left)
        if k <= 0:
            break
        for i in range(k):
            a = (i / k) * 2 * np.pi + rng.uniform(-0.5, 0.5) + L * 1.1
            rr = (1.0 - L * 0.30)
            item, ih = make(rng)
            item.rotate_y(rng.uniform(0, 6.28))
            item.rotate_z(rng.uniform(-0.25, 0.25))
            item.translate(np.cos(a) * rx * rr * rng.uniform(0.35, 1.0),
                           y0 + L * ih * 0.72,
                           np.sin(a) * rz * rr * rng.uniform(0.35, 1.0))
            out.add(item)
        n_left -= k
    return out


def _crate_open(sid, w=0.46, d=0.34, h=0.20, mat="oak", slats=4):
    """A shallow slatted produce crate — the greengrocer's display unit. Open
    top, gappy sides, so what is in it reads at a glance."""
    rng = rng_for(sid, "crate_open")
    out = M.Group()
    t = 0.016
    for sz in (-1, 1):
        for i in range(2):
            b = M.box(w, h * 0.4, t, 0.003, mat)
            b.translate(0, h * (0.25 + i * 0.5), sz * d * 0.5)
            out.add(b)
    for sx in (-1, 1):
        b = M.box(t, h * 0.92, d, 0.003, mat)
        b.translate(sx * w * 0.5, h * 0.5, 0)
        out.add(b)
    for i in range(slats):
        b = M.box(w * 0.96, t, d / slats * 0.8, 0.003, mat)
        b.translate(0, t * 0.5, -d * 0.5 + (i + 0.5) * d / slats)
        out.add(b)
    for sx in (-1, 1):
        for sz in (-1, 1):
            c = M.box(0.028, h * 1.05, 0.028, 0.003, mat)
            c.translate(sx * w * 0.5, h * 0.52, sz * d * 0.5)
            out.add(c)
    return out


def _basket(sid, r=0.20, h=0.24, mat="thatch", bands=4, handle=False):
    """Woven withy basket. Bands of weave give it a real profile instead of a
    smooth bucket."""
    rng = rng_for(sid, "basket")
    out = M.Group()
    prof = [(r * 0.62, 0), (r * 0.80, h * 0.18), (r * 0.95, h * 0.55),
            (r, h * 0.92), (r * 1.03, h)]
    out.add(_tex(M.lathe(prof, 12, mat, close_top=False), 1.6, 1.6,
                 rng.uniform(0, 2), rng.uniform(0, 2)))
    for i in range(bands):
        y = h * (0.16 + i * 0.78 / max(1, bands - 1))
        rr = r * (0.78 + 0.24 * (y / h))
        out.add(_ring(rr, 0.020, mat, 12).translate(0, y, 0))
    if handle:
        for t in range(5):
            u = t / 4
            a = np.pi * u
            p = np.array([np.cos(a) * r * 0.9, h + np.sin(a) * r * 0.75, 0])
            if t:
                out.add(_link(prev, p, 0.012, mat, 4))
            prev = p
    return out


def _stool(sid, h=0.46, r=0.17, mat="oak_weathered"):
    """Three-legged stool — the only furniture a market trader owns."""
    rng = rng_for(sid, "stool")
    out = M.Group()
    top = M.lathe([(r * 0.94, 0), (r, 0.012), (r, 0.042), (r * 0.92, 0.052)], 10, mat)
    top.translate(0, h - 0.05, 0)
    out.add(_tex(top, 1.4, 1.4, rng.uniform(0, 2), 0))
    for i in range(3):
        a = i / 3 * 2 * np.pi + rng.uniform(-0.15, 0.15)
        top_p = np.array([np.cos(a) * r * 0.62, h - 0.055, np.sin(a) * r * 0.62])
        foot = np.array([np.cos(a) * r * 1.15, 0.0, np.sin(a) * r * 1.15])
        out.add(_link(foot, top_p, 0.022, mat, 6, 0.003))
    out.rotate_y(rng.uniform(0, 6.28))
    return out


def _tally_board(sid, w=0.40, h=0.30):
    """A trader's tally: chalk strokes in fives on a dark board.

    Art Bible §2 forbids readable lettering anywhere in the world. Tally marks
    are the period-correct answer — they are numerals that carry meaning with
    no alphabet, and they say "somebody is counting money here".
    """
    rng = rng_for(sid, "tally")
    out = M.Group()
    bd = M.box(w, h, 0.022, 0.004, "oak_dark")
    bd.uv = np.stack([bd.v[:, 0] * 1.4, bd.v[:, 1] * 1.4], axis=1).astype(np.float32)
    out.add(bd)
    groups = int(rng.integers(3, 6))
    for g in range(groups):
        row = g // 3
        col = g % 3
        gx = -w * 0.38 + col * w * 0.30
        gy = h * 0.26 - row * h * 0.34
        for k in range(4):
            s = M.box(0.008, h * 0.19 * rng.uniform(0.85, 1.1), 0.006, 0.001, "plaster")
            s.rotate_z(rng.uniform(-0.10, 0.10))
            s.translate(gx + k * 0.019, gy + rng.uniform(-0.006, 0.006), -0.013)
            out.add(s)
        d = M.box(0.008, h * 0.23, 0.006, 0.001, "plaster")
        d.rotate_z(1.05)
        d.translate(gx + 0.030, gy, -0.014)
        out.add(d)
    return out


def _scales(sid):
    """Beam balance with two pans, plus graduated weights. Every market on
    earth has exactly this object and it reads instantly as commerce."""
    rng = rng_for(sid, "scales")
    out = M.Group()
    col = M.box(0.035, 0.42, 0.035, CH_SMALL, "iron")
    col.translate(0, 0.21, 0)
    out.add(col)
    base = M.lathe([(0.10, 0), (0.105, 0.018), (0.06, 0.03)], 10, "iron")
    out.add(base)
    tilt = rng.uniform(-0.12, 0.12)     # never balanced
    beam = M.box(0.52, 0.020, 0.020, CH_SMALL, "iron")
    beam.rotate_z(tilt)
    beam.translate(0, 0.43, 0)
    out.add(beam)
    for sx in (-1, 1):
        ex = sx * 0.25
        ey = 0.43 + np.sin(tilt) * ex
        pan_y = ey - 0.155
        for k in range(3):
            lk = _ring(0.012, 0.006, "iron", 6)
            lk.rotate_x(np.pi * 0.5 if k % 2 else 0)
            lk.translate(ex, ey - 0.03 - k * 0.028, 0)
            out.add(lk)
        for a in (-0.06, 0.06):
            out.add(_cord((ex, ey - 0.02, 0), (ex + a, pan_y, a), 0.01, "iron", 0.004, 3))
        pan = M.lathe([(0.0, 0), (0.055, 0.004), (0.085, 0.020), (0.088, 0.026)],
                      12, "iron", close_top=False)
        pan.translate(ex, pan_y, 0)
        out.add(pan)
    # Weights, in a graded row: nobody keeps them in a jumble.
    for i, r in enumerate((0.034, 0.028, 0.023, 0.018)):
        wt = M.lathe([(r, 0), (r, 0.03 + r * 0.6), (r * 0.55, 0.045 + r * 0.6)],
                     8, "iron")
        wt.translate(0.17 + i * 0.072, 0.0, 0.14 + rng.uniform(-0.01, 0.01))
        out.add(wt)
        hd = _ring(r * 0.4, 0.008, "iron", 6)
        hd.rotate_x(np.pi * 0.5)
        hd.translate(0.17 + i * 0.072, 0.055 + r * 0.6, 0.14)
        out.add(hd)
    return out


def _sign(sid, shape, mat="oak_dark", depth=0.028, scale=1.0):
    """A pictorial trade sign, cut to its own silhouette.

    Art Bible §2: signage is pictorial, never typographic. A shaped board reads
    from across the square where a painted panel does not, and it solves
    localisation for free.
    """
    pts = [(x * scale, y * scale) for x, y in shape]
    return _prism(pts, depth, mat, 0.006)


# Trade-sign silhouettes. Deliberately bold and closed — these must read as
# black shapes at 30 m (Art Bible §6 "secondary").
SIGN_FISH = [(-0.30, 0.0), (-0.14, 0.11), (0.06, 0.115), (0.20, 0.06),
             (0.26, 0.0), (0.20, -0.06), (0.06, -0.115), (-0.14, -0.11)]
SIGN_FISH_TAIL = [(0.24, 0.0), (0.40, 0.13), (0.36, 0.0), (0.40, -0.13)]
SIGN_LOAF = [(-0.24, -0.10), (-0.20, 0.06), (-0.08, 0.13), (0.08, 0.13),
             (0.20, 0.06), (0.24, -0.10)]
SIGN_JUG = [(-0.10, -0.16), (-0.13, -0.02), (-0.10, 0.10), (-0.05, 0.16),
            (0.05, 0.16), (0.10, 0.10), (0.13, -0.02), (0.10, -0.16)]
SIGN_LEAF = [(0.0, 0.22), (0.09, 0.10), (0.11, -0.02), (0.05, -0.14),
             (0.0, -0.20), (-0.05, -0.14), (-0.11, -0.02), (-0.09, 0.10)]
SIGN_GOURD = [(0.0, 0.20), (0.08, 0.13), (0.13, 0.0), (0.10, -0.13),
              (0.0, -0.19), (-0.10, -0.13), (-0.13, 0.0), (-0.08, 0.13)]
SIGN_BOLT = [(-0.22, -0.09), (-0.22, 0.09), (0.22, 0.09), (0.22, -0.09)]
SIGN_STAR = [(0.0, 0.24), (0.06, 0.08), (0.22, 0.06), (0.10, -0.05),
             (0.14, -0.21), (0.0, -0.11), (-0.14, -0.21), (-0.10, -0.05),
             (-0.22, 0.06), (-0.06, 0.08)]
SIGN_HAM = [(-0.22, 0.02), (-0.16, 0.13), (-0.02, 0.16), (0.12, 0.10),
            (0.17, -0.02), (0.12, -0.13), (-0.02, -0.16), (-0.16, -0.10)]


def _hang_sign(sid, board, x, y, z, rng, drop=0.16, arm=0.0, mat="iron"):
    """Hang a shaped board off the awning header on two short chains."""
    out = M.Group()
    for sx in (-1, 1):
        hx = x + sx * 0.085
        out.add(_cord((hx, y, z), (hx, y - drop, z + 0.012), 0.006, mat, 0.006, 3))
    board.rotate_z(rng.uniform(-0.09, 0.09))
    board.translate(x, y - drop - 0.15, z + 0.02)
    out.add(board)
    return out


# ---------------------------------------------------------------------------
# Livestock and vermin — the cheapest life in the whole town
# ---------------------------------------------------------------------------

def _cat(sid, mat="oak_weathered", crouch=True):
    """A cat, mid-stalk, watching the fish. Art Bible §7 lists exactly this as
    the kind of residue that buys more life than another 10k triangles."""
    rng = rng_for(sid, "cat")
    out = M.Group()
    body = _globe(0.115, mat, 8, 4, sx=1.0, sy=0.86, sz=1.0, uv=2.2,
                  ou=rng.uniform(0, 2))
    body.scale(2.25, 1.0, 1.0)
    body.translate(0, 0.155, 0)
    out.add(body)
    head = _globe(0.068, mat, 8, 4, uv=3.0, ou=rng.uniform(0, 2))
    head.translate(-0.255, 0.20 if crouch else 0.26, 0)
    out.add(head)
    muz = _globe(0.036, mat, 6, 3, sx=1.2, uv=3.0)
    muz.translate(-0.305, 0.182 if crouch else 0.242, 0)
    out.add(muz)
    for sz in (-1, 1):
        ear = _prism([(0.0, 0.0), (0.045, 0.0), (0.018, 0.058)], 0.008, mat, 0.002)
        ear.rotate_y(np.pi * 0.5)
        ear.rotate_z(0.15)
        ear.translate(-0.245, 0.245 if crouch else 0.305, sz * 0.036)
        out.add(ear)
    for sx, sz in ((-0.16, -0.055), (-0.16, 0.055), (0.15, -0.06), (0.15, 0.06)):
        top = np.array([sx, 0.135, sz])
        foot = np.array([sx + (0.03 if sx < 0 else -0.02), 0.0, sz])
        out.add(_link(foot, top, 0.026, mat, 5, 0.002))
    # Tail, curled up and out — the readable part of the silhouette.
    prev = None
    for i in range(7):
        t = i / 6
        p = np.array([0.24 + t * 0.20, 0.16 + np.sin(t * 2.0) * 0.16, t * 0.04])
        if prev is not None:
            out.add(_link(prev, p, 0.020 - t * 0.007, mat, 5, 0.002))
        prev = p
    return out


def _pigeon(sid, mat="stone"):
    """Pecking pigeon. Two of these near the spilled grain and a plaza stops
    being a diorama."""
    rng = rng_for(sid, "pigeon")
    out = M.Group()
    body = _globe(0.070, mat, 7, 4, uv=3.5, ou=rng.uniform(0, 2), ov=rng.uniform(0, 2))
    body.scale(1.7, 1.0, 1.0)
    body.translate(0, 0.085, 0)
    out.add(body)
    head = _globe(0.033, mat, 6, 3, uv=4.0, ou=rng.uniform(0, 2))
    head.translate(-0.085, 0.115 + rng.uniform(-0.05, 0.03), 0)
    out.add(head)
    tail = _prism([(0.0, 0.0), (0.10, 0.035), (0.11, -0.012)], 0.05, mat, 0.002)
    tail.rotate_y(np.pi * 0.5)
    tail.translate(0.095, 0.075, 0)
    out.add(tail)
    for sz in (-1, 1):
        out.add(_link((0.0, 0.035, sz * 0.018), (0.0, 0.0, sz * 0.02), 0.007, "iron", 4))
    out.rotate_y(rng.uniform(0, 6.28))
    return out


# ---------------------------------------------------------------------------
# Per-stall builders. Eight hand-written arrangements — no shared loop, because
# eight identical stalls with different props is exactly what this venue must
# not be.
# ---------------------------------------------------------------------------

def _stall_produce(sid):
    """Nearest the road mouth and the loudest: the greengrocer takes the best
    pitch in the market. Crates tilted to the customer, everything spilling."""
    rng = rng_for(sid, "produce")
    out = M.Group()
    w, d = 2.75, 1.95
    shell, I = _shell(sid, rng, w, d, front_h=2.36, back_h=2.90, sagx=0.11,
                      sagz=0.075, stripe="wide", valance=0.26, patches=3, guys=2)
    out.add(shell)
    out.add(_counter(sid, rng, w, d, planks=4, shelf=0.36))

    def gourd(r):
        def mk(rg):
            g = _globe(r * rg.uniform(0.85, 1.15), "terracotta", 8, 4, sy=0.80,
                       uv=0.7, ou=rg.uniform(0, 6), ov=rg.uniform(0, 6))
            st = M.cylinder(0.012, 0.045, 5, 0.002, "foliage")
            st.rotate_z(rg.uniform(-0.3, 0.3))
            st.translate(0, r * 0.62, 0)
            return M.Group().add(g).add(st), r * 1.5
        return mk

    def apple(rg):
        return _globe(0.042 * rg.uniform(0.85, 1.1), "terracotta", 7, 3, sy=0.9,
                      uv=1.6, ou=rg.uniform(0, 6), ov=rg.uniform(0, 6)), 0.078

    def cabbage(rg):
        g = M.Group()
        g.add(_globe(0.085 * rg.uniform(0.9, 1.1), "foliage", 8, 4, sy=0.86,
                     uv=1.1, ou=rg.uniform(0, 4)))
        g.add(K.leaf_cluster(f"{sid}.cab{rg.integers(0,999)}", 0.075, 5,
                             "foliage", 0.9).translate(0, 0.02, 0))
        return g, 0.16

    # Front counter: tilted crates, angled at the customer. The greengrocer's
    # signature move, and it gets the goods into the player's eyeline.
    for i, (cx, kind) in enumerate([(-0.86, "apple"), (-0.02, "gourd"), (0.84, "apple")]):
        cr = _crate_open(f"{sid}.crate{i}", 0.62, 0.40, 0.19)
        cr.rotate_x(-0.30)
        cr.rotate_y(rng.uniform(-0.14, 0.14))
        cr.translate(cx, COUNTER_H + 0.05, -d * 0.5 + 0.34)
        out.add(cr)
        if kind == "apple":
            fill = _heap(f"{sid}.h{i}", rng, apple, 13, 0.22, 0.13, 0.02, layers=2)
        else:
            fill = _heap(f"{sid}.h{i}", rng, gourd(0.085), 6, 0.19, 0.11, 0.04, layers=2)
        fill.rotate_x(-0.30)
        fill.translate(cx, COUNTER_H + 0.14, -d * 0.5 + 0.31)
        out.add(fill)

    # Back shelf: the big stuff, stacked where it will not roll off.
    out.add(_heap(f"{sid}.pump", rng, gourd(0.145), 5, 0.62, 0.16,
                  COUNTER_H + 0.11, layers=1).translate(-0.35, 0, 0.22))
    out.add(_heap(f"{sid}.cab", rng, cabbage, 5, 0.42, 0.14,
                  COUNTER_H + 0.10, layers=1).translate(0.82, 0, 0.20))

    # Carrots and leeks, bundled and tied — rope-tied bundles per the brief.
    for i in range(3):
        bx = -w * 0.5 + 0.30 + i * 0.24
        bun = M.Group()
        for k in range(6):
            c = _cone(0.020, 0.26, "terracotta", 6, 1.4, rng.uniform(0, 5))
            c.rotate_z(rng.uniform(-0.10, 0.10))
            c.translate(rng.uniform(-0.035, 0.035), 0, rng.uniform(-0.03, 0.03))
            bun.add(c)
            lf = K.leaf_cluster(f"{sid}.car{i}{k}", 0.05, 3, "foliage", 1.2)
            lf.translate(0, 0.26, 0)
            bun.add(lf)
        bun.add(_ring(0.055, 0.018, "canvas", 8).translate(0, 0.15, 0))
        bun.rotate_z(-0.42)
        bun.rotate_y(rng.uniform(-0.2, 0.2))
        bun.translate(bx, COUNTER_H + 0.02, 0.30)
        out.add(bun)

    # Spilled produce under the table — Art Bible §7 residue, and the single
    # cheapest cue that this stall has been trading all morning.
    for i in range(6):
        a = rng.uniform(0, 6.28)
        r = rng.uniform(0.15, 0.95)
        g = _globe(rng.uniform(0.035, 0.055), "terracotta", 7, 3, sy=0.85,
                   uv=1.5, ou=rng.uniform(0, 6), ov=rng.uniform(0, 6))
        g.translate(np.cos(a) * r, 0.038, -d * 0.5 - abs(np.sin(a)) * 0.55 + 0.15)
        out.add(g)
    squash = _globe(0.09, "terracotta", 8, 4, sy=0.42, uv=0.9, ou=rng.uniform(0, 5))
    squash.rotate_z(0.3)
    squash.translate(0.55, 0.028, -d * 0.5 - 0.42)
    out.add(squash)

    # A tipped-over empty crate and the day's tally board.
    tip = _crate_open(f"{sid}.tip", 0.55, 0.38, 0.20)
    tip.rotate_z(1.45)
    tip.rotate_y(0.5)
    tip.translate(-w * 0.5 - 0.34, 0.19, 0.42)
    out.add(tip)
    tb = _tally_board(f"{sid}.tally", 0.36, 0.28)
    tb.rotate_y(0.10)
    tb.translate(w * 0.5 - 0.22, 1.62, -d * 0.5 + 0.10)
    out.add(tb)

    # Stock in reserve, stacked behind where the trader can reach it.
    for i, (cx, cz) in enumerate([(-w * 0.5 + 0.30, d * 0.5 + 0.42),
                                  (-w * 0.5 + 0.34, d * 0.5 + 0.46)]):
        c = K.crate(f"{sid}.stack{i}")
        c.translate(cx + i * 0.03, i * 0.56, cz)
        out.add(c)
    out.add(_basket(f"{sid}.bask", 0.20, 0.24, handle=True)
            .translate(w * 0.5 - 0.10, 0.0, d * 0.5 + 0.30))

    sg = _sign(f"{sid}.sign", SIGN_GOURD, "oak_dark", 0.03, 1.25)
    out.add(_hang_sign(f"{sid}.sign", sg, -w * 0.5 + 0.24, I["front_h"] - 0.10,
                       -d * 0.5 - 0.03, rng, 0.14))
    return out, dict(w=w, d=d, front_h=I["front_h"])


def _stall_fish(sid):
    """Fresh from the mere. Wet boards sloped to a drip channel, fish hung by
    the gills, and a cat who has been thrown out of here twice already."""
    rng = rng_for(sid, "fish")
    out = M.Group()
    w, d = 2.45, 1.85
    shell, I = _shell(sid, rng, w, d, front_h=2.31, back_h=2.78, sagx=0.13,
                      sagz=0.06, stripe="narrow", valance=0.19, patches=2,
                      guys=1, timber="oak_weathered")
    out.add(shell)
    # The slab: thick boards tilted forward so the water runs off the front,
    # into a plank gutter. That tilt is the whole reason a fish stall looks
    # like a fish stall.
    out.add(_counter(sid, rng, w, d, planks=3, shelf=0.32, tilt=-0.055))
    gut = M.box(w * 0.98, 0.055, 0.10, 0.005, "oak_dark")
    gut.translate(0, COUNTER_H - 0.055, -d * 0.5 + 0.02)
    out.add(gut)

    def fish(sid2, ln, mat="stone", fat=0.20, ou=0.0):
        g = M.Group()
        prof = [(0.0, 0.0), (ln * fat * 0.55, ln * 0.10), (ln * fat, ln * 0.36),
                (ln * fat * 0.92, ln * 0.62), (ln * fat * 0.45, ln * 0.88),
                (ln * fat * 0.16, ln)]
        b = M.lathe(prof, 8, mat, close_bottom=False, close_top=False)
        b.scale(1.0, 1.0, 0.46)
        g.add(_tex(b, 2.2, 2.2, ou, ou * 0.7))
        tail = _prism([(0.0, 0.0), (ln * 0.17, ln * 0.11), (ln * 0.13, 0.0),
                       (ln * 0.17, -ln * 0.11)], 0.008, mat, 0.002)
        tail.rotate_z(np.pi * 0.5)
        tail.translate(0, ln * 0.99, 0)
        g.add(tail)
        dor = _prism([(0.0, 0.0), (ln * 0.16, ln * 0.055), (ln * 0.30, 0.0)],
                     0.006, mat, 0.002)
        dor.rotate_y(np.pi * 0.5)
        dor.rotate_z(np.pi * 0.5)
        dor.translate(0, ln * 0.40, ln * fat * 0.35)
        g.add(dor)
        eye = _globe(ln * 0.028, "iron", 5, 3)
        eye.translate(ln * fat * 0.42, ln * 0.13, ln * fat * 0.22)
        g.add(eye)
        return g

    # Laid out in rows on the slab, all facing the same way, overlapping the way
    # a fishmonger actually lays them.
    for i in range(7):
        f = fish(f"{sid}.f{i}", rng.uniform(0.24, 0.33), "stone", 0.22,
                 rng.uniform(0, 4))
        f.rotate_x(np.pi * 0.5)
        f.rotate_y(rng.uniform(-0.16, 0.16))
        f.rotate_z(rng.uniform(-0.05, 0.05))
        f.translate(-w * 0.42 + (i % 4) * 0.30 + (i // 4) * 0.16,
                    COUNTER_H + 0.055 + (i // 4) * 0.045,
                    -d * 0.5 + 0.30 + (i // 4) * 0.34)
        out.add(f)
    # A big pike laid diagonally across the corner — the day's best catch, and
    # it breaks the row rhythm.
    pike = fish(f"{sid}.pike", 0.60, "stone", 0.17, 2.4)
    pike.rotate_x(np.pi * 0.5)
    pike.rotate_y(0.55)
    pike.translate(w * 0.5 - 0.52, COUNTER_H + 0.06, -d * 0.5 + 0.44)
    out.add(pike)

    # Hung by the gills from an iron rod under the awning: goods at eye level,
    # which is what the player actually sees walking past.
    rod = M.cylinder(0.014, w * 0.86, 8, CH_SMALL, "iron")
    rod.rotate_z(np.pi * 0.5)
    rod.translate(-w * 0.43, 1.86, -d * 0.5 + 0.30)
    out.add(rod)
    for i in range(4):
        hx = -w * 0.34 + i * 0.23 + rng.uniform(-0.02, 0.02)
        hook = _cord((hx, 1.86, -d * 0.5 + 0.30), (hx, 1.72, -d * 0.5 + 0.30),
                     0.0, "iron", 0.006, 2)
        out.add(hook)
        f = fish(f"{sid}.hang{i}", rng.uniform(0.30, 0.42), "stone", 0.20,
                 rng.uniform(0, 4))
        f.rotate_x(np.pi)
        f.rotate_y(rng.uniform(0, 6.28))
        f.rotate_z(rng.uniform(-0.07, 0.07))
        f.translate(hx, 1.72, -d * 0.5 + 0.30)
        out.add(f)

    # A tub of water with eels, a gutting knife left on the board, a whetstone.
    tub = M.lathe([(0.20, 0), (0.225, 0.10), (0.23, 0.28), (0.235, 0.30)], 14,
                  "oak_weathered", close_top=False)
    tub.translate(w * 0.5 - 0.26, 0.0, d * 0.5 - 0.42)
    out.add(tub)
    out.add(_ring(0.235, 0.03, "iron", 14).translate(w * 0.5 - 0.26, 0.22, d * 0.5 - 0.42))
    water = M.lathe([(0.0, 0.24), (0.215, 0.243)], 14, "glass")
    water.translate(w * 0.5 - 0.26, 0, d * 0.5 - 0.42)
    out.add(water)
    for i in range(3):
        prev = None
        for k in range(6):
            t = k / 5
            a = t * 5.0 + i * 2.1
            p = np.array([w * 0.5 - 0.26 + np.cos(a) * 0.13 * (1 - t * 0.3),
                          0.245 + (0.01 if k % 2 else 0.0),
                          d * 0.5 - 0.42 + np.sin(a) * 0.13 * (1 - t * 0.3)])
            if prev is not None:
                out.add(_link(prev, p, 0.017 - t * 0.006, "oak_dark", 5, 0.002))
            prev = p

    knife = M.Group()
    bl = _prism([(0.0, -0.018), (0.17, -0.030), (0.20, 0.0), (0.0, 0.020)],
                0.004, "iron", 0.0015)
    knife.add(bl)
    hl = M.box(0.10, 0.026, 0.022, CH_SMALL, "oak_dark")
    hl.translate(-0.055, 0.0, 0)
    knife.add(hl)
    knife.rotate_x(np.pi * 0.5)
    knife.rotate_y(0.7)
    knife.translate(-w * 0.5 + 0.30, COUNTER_H + 0.055, -d * 0.5 + 0.62)
    out.add(knife)
    ws = M.box(0.20, 0.035, 0.07, 0.006, "stone")
    ws.rotate_y(0.3)
    ws.translate(-w * 0.5 + 0.52, COUNTER_H + 0.05, 0.10)
    out.add(ws)

    # Wet ground: a shallow puddle under the drip line, and scattered offcuts.
    pud = M.lathe([(0.0, 0.004), (0.34, 0.006), (0.42, 0.003)], 12, "glass")
    pud.scale(1.3, 1.0, 0.8)
    pud.translate(-0.10, 0, -d * 0.5 - 0.36)
    out.add(pud)
    for i in range(4):
        sc = _globe(rng.uniform(0.022, 0.034), "stone", 6, 3, sy=0.5, uv=3.0,
                    ou=rng.uniform(0, 4))
        sc.translate(rng.uniform(-0.6, 0.6), 0.012, -d * 0.5 - rng.uniform(0.20, 0.60))
        out.add(sc)

    # The cat. Crouched at the corner of the stall, eyes on the slab.
    cat = _cat(f"{sid}.cat")
    cat.rotate_y(-0.55)
    cat.translate(-w * 0.5 - 0.50, 0.0, -d * 0.5 - 0.30)
    out.add(cat)

    # Reserve stock and a barrel of salt for what does not sell.
    out.add(K.barrel(f"{sid}.barrel").translate(w * 0.5 + 0.30, 0, d * 0.5 - 0.10))
    out.add(_basket(f"{sid}.b1", 0.22, 0.20).translate(-w * 0.5 - 0.34, 0, d * 0.5 - 0.24))

    fs = _sign(f"{sid}.sign", SIGN_FISH, "iron", 0.022, 1.15)
    fs.add(_prism([(x * 1.15, y * 1.15) for x, y in SIGN_FISH_TAIL], 0.022, "iron", 0.005)) \
        if isinstance(fs, M.Group) else None
    grp = M.Group().add(fs)
    grp.add(_prism([(x * 1.15, y * 1.15) for x, y in SIGN_FISH_TAIL], 0.022, "iron", 0.005))
    out.add(_hang_sign(f"{sid}.sign", grp, w * 0.5 - 0.30, I["front_h"] - 0.10,
                       -d * 0.5 - 0.03, rng, 0.13))
    return out, dict(w=w, d=d, front_h=I["front_h"])


def _stall_bread(sid):
    """The baker's: stepped shelves, everything dusted in flour, and a spilled
    sack she has not swept up because she has been serving since dawn."""
    rng = rng_for(sid, "bread")
    out = M.Group()
    w, d = 2.35, 1.80
    shell, I = _shell(sid, rng, w, d, front_h=2.40, back_h=2.84, sagx=0.07,
                      sagz=0.09, stripe="cream", valance=0.24, patches=1,
                      guys=2, timber="oak")
    out.add(shell)
    out.add(_counter(sid, rng, w, d, planks=4, shelf=0.35, mat="oak"))

    # Stepped display shelves — the baker's rack, rising toward the back.
    for s, (sy, sz) in enumerate([(1.19, 0.18), (1.46, 0.46)]):
        sh = M.plank(w * 0.92, 0.34, 0.034, 0.005, "oak")
        sh.translate(0, sy, sz)
        out.add(sh)
        for sx in (-1, 1):
            leg = M.box(0.05, sy - COUNTER_H, 0.05, 0.004, "oak")
            leg.translate(sx * w * 0.40, COUNTER_H + (sy - COUNTER_H) * 0.5, sz)
            out.add(leg)

    def boule(rg, r=0.085):
        g = M.Group()
        b = _globe(r * rg.uniform(0.9, 1.1), "oak", 8, 4, sy=0.62, uv=1.9,
                   ou=rg.uniform(0, 6), ov=rg.uniform(0, 6))
        g.add(b)
        # Scored crust: three raised slash ridges across the top.
        for k in range(3):
            sl = M.box(r * 1.25, 0.010, 0.012, 0.002, "oak")
            sl.rotate_y(0.5)
            sl.translate((k - 1) * r * 0.34, r * 0.55, 0)
            g.add(sl)
        return g, r * 1.3

    def miche(rg, ln=0.30):
        g = M.Group()
        prof = [(0.0, 0), (0.048, 0.02), (0.058, ln * 0.35), (0.058, ln * 0.65),
                (0.048, ln - 0.02), (0.0, ln)]
        b = M.lathe(prof, 8, "oak", close_bottom=False, close_top=False)
        b.rotate_z(np.pi * 0.5)
        b.scale(1.0, 0.78, 1.0)
        g.add(_tex(b, 1.7, 1.7, rg.uniform(0, 6), rg.uniform(0, 6)))
        for k in range(4):
            sl = M.box(0.014, 0.012, 0.075, 0.002, "oak_weathered")
            sl.rotate_y(0.42)
            sl.translate(-ln * 0.5 + 0.06 + k * (ln - 0.12) / 3, 0.036, 0)
            g.add(sl)
        return g, 0.09

    # Top shelf: big round boules in a careful row. Middle: long miches.
    for i in range(5):
        b, _ = boule(rng, 0.082)
        b.rotate_y(rng.uniform(0, 6.28))
        b.translate(-w * 0.36 + i * (w * 0.72 / 4) + rng.uniform(-0.02, 0.02),
                    1.46 + 0.05, 0.46 + rng.uniform(-0.02, 0.02))
        out.add(b)
    for i in range(4):
        m2, _ = miche(rng, rng.uniform(0.26, 0.34))
        m2.rotate_y(rng.uniform(-0.10, 0.10))
        m2.translate(-w * 0.32 + i * 0.22, 1.19 + 0.05, 0.18 + rng.uniform(-0.03, 0.03))
        out.add(m2)

    # Counter: a plaited loaf, a basket of rolls under a cloth, a flat rye disc.
    plait = M.Group()
    for k in range(3):
        prev = None
        for t in range(7):
            u = t / 6
            p = np.array([-0.13 + u * 0.26,
                          0.028 + 0.014 * np.sin(u * 3.2 * np.pi + k * 2.1),
                          0.035 * np.sin(u * 3.2 * np.pi + k * 2.1)])
            if prev is not None:
                plait.add(_link(prev, p, 0.028, "oak", 6, 0.003))
            prev = p
    plait.rotate_y(0.2)
    plait.translate(-w * 0.5 + 0.45, COUNTER_H + 0.02, -d * 0.5 + 0.42)
    out.add(plait)

    bask = _basket(f"{sid}.rolls", 0.19, 0.15)
    bask.translate(0.30, COUNTER_H + 0.02, -d * 0.5 + 0.40)
    out.add(bask)
    out.add(_heap(f"{sid}.rolls2", rng,
                  lambda rg: (_globe(0.038, "oak", 6, 3, sy=0.7, uv=2.6,
                                     ou=rg.uniform(0, 6), ov=rg.uniform(0, 6)), 0.06),
                  7, 0.13, 0.11, COUNTER_H + 0.12).translate(0.30, 0, -d * 0.5 + 0.40))
    # The cloth over half the basket — bakers keep rolls covered.
    ph = [rng.uniform(0, 6.28) for _ in range(2)]
    cl = _cloth_hang(0.34, COUNTER_H + 0.21, COUNTER_H + 0.02, -d * 0.5 + 0.30, ph,
                     lambda x, z: (x * 0.9 + 3.1, z * 0.9), "canvas", 6, 3, 0.02)
    cl.translate(0.30, 0, 0)
    out.add(cl)

    rye = _globe(0.13, "oak_weathered", 9, 4, sy=0.30, uv=1.3, ou=rng.uniform(0, 5))
    rye.translate(w * 0.5 - 0.36, COUNTER_H + 0.06, -d * 0.5 + 0.36)
    out.add(rye)

    # THE flour. A tipped sack, a cone of spill, a dusting on the boards and on
    # the ground — this is the one detail that names the trade without a sign.
    sack = K.sack(f"{sid}.flour", 0.52, "canvas")
    sack.rotate_z(1.28)
    sack.translate(-w * 0.5 - 0.16, 0.20, d * 0.5 - 0.30)
    out.add(sack)
    spill = M.lathe([(0.0, 0.055), (0.14, 0.012), (0.24, 0.0)], 12, "plaster")
    spill.scale(1.4, 1.0, 0.9)
    spill.translate(-w * 0.5 - 0.44, 0, d * 0.5 - 0.34)
    out.add(spill)
    for i in range(7):
        du = M.lathe([(0.0, 0.004), (rng.uniform(0.05, 0.16), 0.001)], 8, "plaster")
        du.scale(rng.uniform(0.8, 1.5), 1.0, rng.uniform(0.7, 1.3))
        du.translate(-w * 0.5 - rng.uniform(-0.2, 0.9), 0.002,
                     d * 0.5 - rng.uniform(-0.3, 0.9))
        out.add(du)
    for i in range(4):
        du = M.lathe([(0.0, 0.003), (rng.uniform(0.04, 0.10), 0.001)], 8, "plaster")
        du.translate(rng.uniform(-w * 0.4, w * 0.4), COUNTER_H + 0.042,
                     -d * 0.5 + rng.uniform(0.15, 0.7))
        out.add(du)
    # A wooden peel leaning on the frame, still floury.
    peel = M.Group()
    bl = M.box(0.30, 0.020, 0.34, 0.004, "oak_weathered")
    peel.add(bl)
    peel.add(_link((0, 0, 0.16), (0, 0, 1.35), 0.022, "oak_weathered", 6, 0.003))
    peel.rotate_x(-1.30)
    peel.rotate_y(0.35)
    peel.translate(w * 0.5 - 0.06, 0.02, d * 0.5 - 0.55)
    out.add(peel)

    # Pigeons on the flour. Cheapest life in the market.
    out.add(_pigeon(f"{sid}.pig1").translate(-w * 0.5 - 0.72, 0, d * 0.5 - 0.05))
    out.add(_pigeon(f"{sid}.pig2").translate(-w * 0.5 - 0.30, 0, d * 0.5 + 0.52))

    out.add(_stool(f"{sid}.stool").translate(w * 0.5 - 0.42, 0, d * 0.5 + 0.30))

    sg = _sign(f"{sid}.sign", SIGN_LOAF, "oak_dark", 0.03, 1.3)
    out.add(_hang_sign(f"{sid}.sign", sg, w * 0.5 - 0.26, I["front_h"] - 0.10,
                       -d * 0.5 - 0.03, rng, 0.15))
    return out, dict(w=w, d=d, front_h=I["front_h"])


def _stall_cloth(sid):
    """The draper: the tidiest stall in the market. Bolts graded by size,
    lengths hung to show the drape, everything squared up."""
    rng = rng_for(sid, "cloth")
    out = M.Group()
    w, d = 2.55, 1.75
    shell, I = _shell(sid, rng, w, d, front_h=2.42, back_h=2.92, sagx=0.055,
                      sagz=0.05, stripe="wide", valance=0.30, patches=1,
                      guys=2, timber="oak")
    out.add(shell)
    out.add(_counter(sid, rng, w, d, planks=5, shelf=0.38, mat="oak"))

    def bolt(mat, ln, r, uvs=1.0):
        g = M.Group()
        core = M.cylinder(r, ln, 12, 0.004, mat)
        core.rotate_z(np.pi * 0.5)
        core.translate(ln * 0.5, 0, 0)
        g.add(_tex(core, uvs, uvs, rng.uniform(0, 3), rng.uniform(0, 3)))
        # The loose end flap: without it a bolt is just a log.
        flap = M.box(ln * 0.34, 0.006, r * 2.05, 0.002, mat)
        flap.rotate_z(-0.16)
        flap.translate(ln * 0.34, r * 0.94, 0)
        g.add(_tex(flap, uvs, uvs, rng.uniform(0, 3), rng.uniform(0, 3)))
        g.translate(-ln * 0.5, 0, 0)
        return g

    # Pyramid of bolts on the counter, biggest at the bottom. A careful person.
    rows = [(3, 0.058, ["canvas", "plaster", "painted"]),
            (2, 0.052, ["plaster_shade", "canvas"]),
            (1, 0.048, ["painted"])]
    y = COUNTER_H + 0.06
    for n, r, mats in rows:
        for i in range(n):
            b = bolt(mats[i % len(mats)], 0.78, r, 0.8)
            b.rotate_y(rng.uniform(-0.03, 0.03))
            b.translate(-0.10 + rng.uniform(-0.012, 0.012), y,
                        -d * 0.5 + 0.30 + (i - (n - 1) * 0.5) * (r * 2.25))
            out.add(b)
        y += r * 1.85

    # Bolts stood on end against the back screen — vertical rhythm, and it
    # fills the back of the booth with colour.
    for i, mat in enumerate(["canvas", "painted", "plaster", "canvas", "plaster_shade"]):
        h = rng.uniform(1.05, 1.35)
        r = rng.uniform(0.048, 0.062)
        st = M.cylinder(r, h, 10, 0.004, mat)
        _tex(st, 0.9, 0.9, rng.uniform(0, 3), rng.uniform(0, 3))
        st.rotate_z(rng.uniform(-0.10, 0.10))
        st.translate(-w * 0.5 + 0.22 + i * (w - 0.44) / 4, 0.34, d * 0.5 - 0.20)
        out.add(st)

    # Hung lengths showing the drape — the draper's whole sales pitch.
    ph = [rng.uniform(0, 6.28) for _ in range(2)]
    rail_y = I["front_h"] - 0.30
    rail = M.cylinder(0.020, w * 0.86, 8, CH_SMALL, "iron")
    rail.rotate_z(np.pi * 0.5)
    rail.translate(-w * 0.43, rail_y, -d * 0.5 + 0.14)
    out.add(rail)
    for i, (cx, cw, mat, uvs) in enumerate([(-0.72, 0.52, "canvas", 0.44),
                                            (-0.10, 0.46, "painted", 0.5),
                                            (0.52, 0.50, "plaster", 0.5)]):
        drop = rng.uniform(0.62, 0.86)
        hang = _cloth_hang(cw, rail_y - 0.02, rail_y - drop, -d * 0.5 + 0.14,
                           [ph[0] + i, ph[1]],
                           lambda x, z, s=uvs: (x * s + i * 2.0, z * s),
                           mat, 8, 5, 0.045)
        hang.translate(cx, 0, 0)
        out.add(hang)
        for sx in (-1, 1):
            r2 = _ring(0.026, 0.008, "iron", 6)
            r2.rotate_x(np.pi * 0.5)
            r2.translate(cx + sx * cw * 0.42, rail_y, -d * 0.5 + 0.14)
            out.add(r2)

    # Shears, a notched measuring stick (no numerals — Art Bible §2), a
    # pincushion, and the cloak she takes off when the sun comes round.
    sh = M.Group()
    for sx in (-1, 1):
        bl = _prism([(0.0, 0.0), (0.16, sx * 0.014), (0.155, sx * 0.030),
                     (0.0, 0.016)], 0.004, "iron", 0.0015)
        sh.add(bl)
        hd = _ring(0.030, 0.010, "iron", 8)
        hd.rotate_x(np.pi * 0.5)
        hd.translate(-0.055, sx * 0.022, 0)
        sh.add(hd)
    sh.rotate_x(np.pi * 0.5)
    sh.rotate_y(0.9)
    sh.translate(w * 0.5 - 0.42, COUNTER_H + 0.045, -d * 0.5 + 0.52)
    out.add(sh)

    stick = M.box(0.92, 0.022, 0.030, 0.003, "oak_dark")
    for k in range(7):
        nk = M.box(0.006, 0.008, 0.032, 0.001, "plaster")
        nk.translate(-0.40 + k * 0.13, 0.013, 0)
        out.add(nk.translate(w * 0.5 - 0.22, COUNTER_H + 0.045, -d * 0.5 + 0.66))
    stick.rotate_y(0.06)
    stick.translate(w * 0.5 - 0.22, COUNTER_H + 0.05, -d * 0.5 + 0.66)
    out.add(stick)

    cloak = _cloth_hang(0.46, I["back_h"] - 0.42, 0.92, d * 0.5 - 0.10,
                        [ph[1], ph[0]], lambda x, z: (x * 0.5 + 5.0, z * 0.5),
                        "painted", 7, 5, 0.055)
    cloak.translate(-w * 0.5 + 0.16, 0, 0)
    out.add(cloak)

    out.add(K.crate(f"{sid}.crate").translate(w * 0.5 + 0.28, 0, d * 0.5 + 0.10))
    out.add(K.rope_coil(f"{sid}.rope").translate(w * 0.5 + 0.30, 0.56, d * 0.5 + 0.10))

    sg = _sign(f"{sid}.sign", SIGN_BOLT, "oak_dark", 0.03, 1.2)
    out.add(_hang_sign(f"{sid}.sign", sg, -w * 0.5 + 0.28, I["front_h"] - 0.10,
                       -d * 0.5 - 0.03, rng, 0.16))
    return out, dict(w=w, d=d, front_h=I["front_h"])


def _stall_pottery(sid):
    """The potter stacks carefully — graded rows, nested bowls, nothing where
    it can be knocked. Straw packing everywhere, and one pot that did get
    knocked, swept into a corner."""
    rng = rng_for(sid, "pottery")
    out = M.Group()
    w, d = 2.60, 1.90
    shell, I = _shell(sid, rng, w, d, front_h=2.33, back_h=2.80, sagx=0.085,
                      sagz=0.065, stripe="russet", valance=0.20, patches=2,
                      guys=2, timber="oak_weathered")
    out.add(shell)
    out.add(_counter(sid, rng, w, d, planks=4, shelf=0.33))

    def pot(kind, s=1.0, ou=0.0):
        if kind == "jug":
            prof = [(0.0, 0), (0.075, 0.01), (0.095, 0.09), (0.075, 0.20),
                    (0.048, 0.25), (0.055, 0.28), (0.048, 0.30)]
        elif kind == "bowl":
            prof = [(0.0, 0), (0.045, 0.005), (0.095, 0.05), (0.115, 0.09),
                    (0.118, 0.10)]
        elif kind == "jar":
            prof = [(0.0, 0), (0.085, 0.015), (0.115, 0.12), (0.105, 0.26),
                    (0.070, 0.33), (0.078, 0.36)]
        elif kind == "pan":
            prof = [(0.0, 0), (0.10, 0.008), (0.155, 0.045), (0.165, 0.075),
                    (0.170, 0.082)]
        else:  # amphora
            prof = [(0.0, 0), (0.055, 0.02), (0.145, 0.22), (0.130, 0.44),
                    (0.070, 0.56), (0.062, 0.62), (0.075, 0.66)]
        m = M.lathe([(r * s, y * s) for r, y in prof], 14, "terracotta",
                    close_top=(kind in ()))
        # Small UV window per pot: the terracotta map carries per-tile firing
        # variance, so a different window is a different kiln batch.
        return _tex(m, 0.055, 0.055, ou, ou * 0.37)

    # Counter: graded rows, largest at the back. Precision is the character.
    for i in range(5):
        j = pot("jug", 1.0 + i * 0.03, rng.uniform(0, 1))
        j.rotate_y(rng.uniform(-0.05, 0.05))
        j.translate(-w * 0.38 + i * (w * 0.76 / 4), COUNTER_H + 0.02,
                    -d * 0.5 + 0.32 + rng.uniform(-0.012, 0.012))
        out.add(j)
    for i in range(4):
        p = pot("pan", 0.95, rng.uniform(0, 1))
        p.translate(-w * 0.30 + i * 0.21, COUNTER_H + 0.02, 0.14)
        out.add(p)
    # Nested stacks of bowls, inverted — how a potter actually transports them.
    for sxi, cx in enumerate((-w * 0.42, w * 0.30)):
        n = int(rng.integers(4, 7))
        for k in range(n):
            b = pot("bowl", 1.0, rng.uniform(0, 1))
            b.rotate_y(rng.uniform(0, 6.28))
            b.translate(cx + rng.uniform(-0.006, 0.006),
                        COUNTER_H + 0.02 + k * 0.038, 0.36)
            out.add(b)

    # Big storage jars on the ground beside the stall, straw-packed in a crate.
    for i, (cx, cz, s) in enumerate([(-w * 0.5 - 0.36, -0.30, 1.0),
                                     (-w * 0.5 - 0.30, 0.16, 0.86),
                                     (w * 0.5 + 0.34, 0.02, 0.94)]):
        a = pot("amphora", s, rng.uniform(0, 1))
        a.rotate_y(rng.uniform(0, 6.28))
        a.rotate_z(rng.uniform(-0.05, 0.05))
        a.translate(cx, 0, cz)
        out.add(a)
    crate = K.crate(f"{sid}.crate")
    crate.translate(w * 0.5 + 0.34, 0, d * 0.5 + 0.20)
    out.add(crate)
    for i in range(3):
        j = pot("jar", 0.85, rng.uniform(0, 1))
        j.rotate_y(rng.uniform(0, 6.28))
        j.translate(w * 0.5 + 0.34 + rng.uniform(-0.12, 0.12), 0.50,
                    d * 0.5 + 0.20 + rng.uniform(-0.10, 0.10))
        out.add(j)
    # Straw packing spilling out of the crate and trodden around the pitch.
    for i in range(22):
        st = M.box(rng.uniform(0.10, 0.22), 0.006, 0.012, 0.001, "thatch")
        st.rotate_y(rng.uniform(0, 3.14))
        st.rotate_z(rng.uniform(-0.1, 0.1))
        st.translate(w * 0.5 + rng.uniform(-0.2, 0.9), rng.uniform(0.004, 0.60),
                     d * 0.5 + rng.uniform(-0.5, 0.6))
        out.add(st)

    # The pot that did get knocked: shards swept into a tidy pile, because of
    # course this trader swept them up.
    for i in range(7):
        a = rng.uniform(0, 6.28)
        r = rng.uniform(0.02, 0.16)
        sh = _prism([(0.0, 0.0), (rng.uniform(0.04, 0.09), rng.uniform(0.01, 0.03)),
                     (rng.uniform(0.03, 0.07), rng.uniform(-0.03, -0.01))],
                    0.008, "terracotta", 0.002)
        sh.rotate_x(np.pi * 0.5)
        sh.rotate_y(rng.uniform(0, 6.28))
        sh.rotate_z(rng.uniform(-0.4, 0.4))
        sh.translate(-w * 0.5 - 0.55 + np.cos(a) * r, 0.012, d * 0.5 - 0.15 + np.sin(a) * r)
        out.add(sh)

    out.add(_stool(f"{sid}.stool", 0.44).translate(-w * 0.5 + 0.30, 0, d * 0.5 - 0.34))
    tb = _tally_board(f"{sid}.tally", 0.30, 0.24)
    tb.rotate_y(-0.06)
    tb.translate(-w * 0.5 + 0.26, 1.58, -d * 0.5 + 0.08)
    out.add(tb)

    sg = _sign(f"{sid}.sign", SIGN_JUG, "oak_dark", 0.03, 1.4)
    out.add(_hang_sign(f"{sid}.sign", sg, w * 0.5 - 0.26, I["front_h"] - 0.10,
                       -d * 0.5 - 0.03, rng, 0.14))
    return out, dict(w=w, d=d, front_h=I["front_h"])


def _stall_charms(sid):
    """The charm seller: the smallest, darkest, most cluttered pitch. Half a
    curtain drawn, everything hung on strings, and one lamp lit in daylight
    because glass beads do not glint on their own."""
    rng = rng_for(sid, "charms")
    out = M.Group()
    w, d = 1.95, 1.60
    shell, I = _shell(sid, rng, w, d, front_h=2.30, back_h=2.68, sagx=0.10,
                      sagz=0.08, stripe="cream", valance=0.17, patches=3,
                      guys=1, timber="oak_dark", awn_mat="painted",
                      back_panel="cloth")
    out.add(shell)
    out.add(_counter(sid, rng, w, d, planks=3, shelf=0.30, mat="oak_dark"))

    ph = [rng.uniform(0, 6.28) for _ in range(2)]
    # Dark cloth over the counter — jewellers have always done this, and it
    # makes the metal read.
    drape = _cloth_hang(w * 0.98, COUNTER_H + 0.02, COUNTER_H - 0.20,
                        -d * 0.5 + 0.06, ph,
                        lambda x, z: (x * 0.45 + 1.7, z * 0.45), "painted", 9, 3, 0.02)
    out.add(drape)
    top = _sheet(w * 0.98, d * 0.62,
                 lambda u, v: COUNTER_H + 0.045 + 0.006 * np.sin(u * 4 * np.pi + ph[0]),
                 lambda x, z: (x * 0.45 + 1.7, z * 0.45), 8, 4, "painted")
    top.translate(0, 0, -d * 0.5 + 0.06 + d * 0.31)
    out.add(top)

    # Rows of small goods laid out on the cloth: pendants, rings, glass beads.
    for i in range(9):
        cx = -w * 0.40 + (i % 5) * (w * 0.80 / 4)
        cz = -d * 0.5 + 0.28 + (i // 5) * 0.22
        kind = i % 3
        if kind == 0:
            p = _ring(0.032, 0.010, "iron", 8)
            p.rotate_x(np.pi * 0.5)
            p.rotate_z(rng.uniform(0, 3))
            p.translate(cx, COUNTER_H + 0.055, cz)
        elif kind == 1:
            p = _prism([(-0.026, 0.0), (0.0, 0.038), (0.026, 0.0), (0.0, -0.030)],
                       0.006, "iron", 0.0015)
            p.rotate_x(np.pi * 0.5)
            p.rotate_y(rng.uniform(0, 3))
            p.translate(cx, COUNTER_H + 0.052, cz)
        else:
            p = M.Group()
            for k in range(5):
                bd = _globe(0.014, "glass", 6, 3)
                bd.translate(cx + (k - 2) * 0.030, COUNTER_H + 0.058,
                             cz + rng.uniform(-0.012, 0.012))
                p.add(bd)
        out.add(p)

    # Hanging strings of beads and charms from the front header — the thing the
    # player walks under and the thing that catches the sun.
    for i in range(6):
        hx = -w * 0.42 + i * (w * 0.84 / 5) + rng.uniform(-0.02, 0.02)
        y0 = I["front_h"] - 0.16
        drop = rng.uniform(0.28, 0.55)
        out.add(_cord((hx, y0, -d * 0.5 + 0.10), (hx + rng.uniform(-0.02, 0.02),
                                                  y0 - drop, -d * 0.5 + 0.10),
                      0.0, "iron", 0.004, 3))
        n = int(rng.integers(3, 6))
        for k in range(n):
            bd = _globe(rng.uniform(0.013, 0.020), "glass", 6, 3)
            bd.translate(hx, y0 - drop * (k + 1) / (n + 1), -d * 0.5 + 0.10)
            out.add(bd)
        ch = _prism([(-0.022, 0.0), (0.0, 0.034), (0.022, 0.0), (0.0, -0.026)],
                    0.005, "iron", 0.0015)
        ch.rotate_y(rng.uniform(0, 3))
        ch.translate(hx, y0 - drop - 0.03, -d * 0.5 + 0.10)
        out.add(ch)

    # A rack of rings on a turned rod, and a lamp so they glint.
    rod = M.cylinder(0.014, 0.34, 8, CH_SMALL, "oak_dark")
    rod.rotate_z(np.pi * 0.5)
    rod.translate(-0.17, COUNTER_H + 0.20, 0.16)
    out.add(rod)
    for sx in (-1, 1):
        up = M.box(0.028, 0.22, 0.028, 0.004, "oak_dark")
        up.translate(sx * 0.17, COUNTER_H + 0.10, 0.16)
        out.add(up)
    for k in range(7):
        r2 = _ring(0.022, 0.007, "iron", 8)
        r2.rotate_z(np.pi * 0.5)
        r2.rotate_x(rng.uniform(-0.1, 0.1))
        r2.translate(-0.14 + k * 0.045, COUNTER_H + 0.20, 0.16)
        out.add(r2)

    lamp = K.lantern(f"{sid}.lamp", scale=0.85)
    lamp.translate(w * 0.5 - 0.24, COUNTER_H + 0.045, 0.24)
    out.add(lamp)

    # Side curtain half-drawn against the sun — the stall's asymmetry.
    cur = _cloth_hang(d * 0.86, I["front_h"] - 0.06, 0.55, 0.0, ph,
                      lambda x, z: (x * 0.42 + 4.0, z * 0.42), "canvas", 8, 6, 0.07)
    cur.rotate_y(np.pi * 0.5)
    cur.translate(-w * 0.5 - 0.01, 0, 0.02)
    out.add(cur)

    # A little iron-bound coffer on the shelf and a mug on the counter rail.
    box = M.box(0.26, 0.16, 0.18, 0.006, "oak_dark")
    box.translate(w * 0.5 - 0.30, 0.30 + 0.08, 0.20)
    out.add(box)
    for sy in (-1, 1):
        bd = M.box(0.27, 0.022, 0.19, 0.002, "iron")
        bd.translate(w * 0.5 - 0.30, 0.38 + sy * 0.06, 0.20)
        out.add(bd)
    mug = M.lathe([(0.036, 0), (0.040, 0.02), (0.042, 0.085), (0.038, 0.095)],
                  10, "terracotta", close_top=False)
    mug.translate(-w * 0.5 + 0.16, COUNTER_H + 0.045, 0.30)
    out.add(mug)

    out.add(_stool(f"{sid}.stool", 0.42).translate(0.30, 0, d * 0.5 - 0.30))

    sg = _sign(f"{sid}.sign", SIGN_STAR, "iron", 0.02, 1.0)
    out.add(_hang_sign(f"{sid}.sign", sg, w * 0.5 - 0.22, I["front_h"] - 0.10,
                       -d * 0.5 - 0.03, rng, 0.13))
    return out, dict(w=w, d=d, front_h=I["front_h"])


def _stall_herbs(sid):
    """The herb woman: a drying rack of tied bundles overhead, live plants
    below, and the market's only set of scales — she sells by weight."""
    rng = rng_for(sid, "herbs")
    out = M.Group()
    w, d = 2.30, 1.85
    shell, I = _shell(sid, rng, w, d, front_h=2.38, back_h=2.86, sagx=0.075,
                      sagz=0.085, stripe="cross", valance=0.23, patches=2,
                      guys=2, timber="oak_weathered")
    out.add(shell)
    out.add(_counter(sid, rng, w, d, planks=4, shelf=0.34))

    # Drying rack: two rails under the awning, hung with tied bundles. This is
    # the stall's silhouette and it reads from right across the square.
    for ri, rz in enumerate((-d * 0.5 + 0.34, 0.14)):
        ry = 1.92 + ri * 0.10
        rail = M.cylinder(0.022, w * 0.90, 8, 0.003, "oak_weathered")
        rail.rotate_z(np.pi * 0.5)
        rail.translate(-w * 0.45, ry, rz)
        out.add(rail)
        n = 6 if ri == 0 else 5
        for i in range(n):
            hx = -w * 0.40 + i * (w * 0.80 / (n - 1)) + rng.uniform(-0.025, 0.025)
            ln = rng.uniform(0.26, 0.42)
            mat = "thatch" if rng.random() < 0.62 else "foliage"
            bun = M.Group()
            for k in range(int(rng.integers(6, 10))):
                a = rng.uniform(0, 6.28)
                rr = rng.uniform(0.0, 0.032)
                st = _link((np.cos(a) * rr * 0.35, 0, np.sin(a) * rr * 0.35),
                           (np.cos(a) * rr, -ln * rng.uniform(0.8, 1.0),
                            np.sin(a) * rr), 0.010, mat, 4, 0.001)
                bun.add(st)
                if mat == "foliage":
                    lf = K.leaf_cluster(f"{sid}.lf{ri}{i}{k}", 0.045, 3, "foliage", 1.3)
                    lf.rotate_x(np.pi)
                    lf.translate(np.cos(a) * rr, -ln * 0.86, np.sin(a) * rr)
                    bun.add(lf)
            bun.add(_ring(0.036, 0.016, "canvas", 8).translate(0, -0.05, 0))
            bun.rotate_y(rng.uniform(0, 6.28))
            bun.rotate_z(rng.uniform(-0.14, 0.14))
            bun.translate(hx, ry - 0.03, rz + rng.uniform(-0.02, 0.02))
            out.add(bun)

    # Counter: open boxes of loose dried herb, stoppered jars, mortar, scales.
    for i, (cx, mat) in enumerate([(-w * 0.5 + 0.34, "thatch"),
                                   (-w * 0.5 + 0.72, "foliage")]):
        bx = _crate_open(f"{sid}.box{i}", 0.30, 0.26, 0.10, "oak_weathered", 3)
        bx.translate(cx, COUNTER_H + 0.02, -d * 0.5 + 0.30)
        out.add(bx)
        fill = _heap(f"{sid}.fill{i}", rng,
                     lambda rg, m=mat: (_globe(rg.uniform(0.022, 0.034), m, 6, 3,
                                               sy=0.6, uv=2.4, ou=rg.uniform(0, 4)),
                                        0.035),
                     9, 0.10, 0.09, COUNTER_H + 0.10, layers=2)
        fill.translate(cx, 0, -d * 0.5 + 0.30)
        out.add(fill)

    for i in range(4):
        jr = M.lathe([(0.0, 0), (0.038, 0.008), (0.046, 0.05), (0.040, 0.11),
                      (0.028, 0.13), (0.032, 0.145)], 10, "terracotta")
        _tex(jr, 0.06, 0.06, rng.uniform(0, 1), rng.uniform(0, 1))
        jr.translate(0.10 + i * 0.115, COUNTER_H + 0.02, 0.18 + rng.uniform(-0.02, 0.02))
        out.add(jr)
        cork = M.lathe([(0.026, 0.145), (0.030, 0.155), (0.024, 0.175)], 8, "thatch")
        cork.translate(0.10 + i * 0.115, COUNTER_H + 0.02, 0.18)
        out.add(cork)

    mortar = M.lathe([(0.0, 0), (0.055, 0.006), (0.070, 0.045), (0.078, 0.085),
                      (0.070, 0.092)], 12, "stone")
    mortar.translate(w * 0.5 - 0.28, COUNTER_H + 0.02, -d * 0.5 + 0.34)
    out.add(mortar)
    pest = M.lathe([(0.020, 0), (0.024, 0.03), (0.016, 0.10), (0.026, 0.13)], 8, "stone")
    pest.rotate_z(0.9)
    pest.translate(w * 0.5 - 0.30, COUNTER_H + 0.09, -d * 0.5 + 0.34)
    out.add(pest)

    sc = _scales(f"{sid}.scales")
    sc.rotate_y(-0.25)
    sc.translate(w * 0.5 - 0.62, COUNTER_H + 0.02, 0.16)
    out.add(sc)

    # Living plants: potted on the ground and on the counter, so the stall has
    # something genuinely green in it.
    for i, (cx, cz, s) in enumerate([(-w * 0.5 - 0.34, -0.20, 1.0),
                                     (-w * 0.5 - 0.28, 0.24, 0.8),
                                     (w * 0.5 + 0.30, -0.10, 0.9),
                                     (w * 0.5 + 0.36, 0.34, 1.1)]):
        p = M.lathe([(0.09 * s, 0), (0.105 * s, 0.02), (0.125 * s, 0.16 * s),
                     (0.135 * s, 0.18 * s)], 12, "terracotta", close_top=False)
        _tex(p, 0.06, 0.06, rng.uniform(0, 1), rng.uniform(0, 1))
        p.translate(cx, 0, cz)
        out.add(p)
        lf = K.leaf_cluster(f"{sid}.pot{i}", 0.11 * s, int(rng.integers(7, 10)),
                            "foliage_flower" if i % 2 else "foliage", 0.55)
        lf.translate(cx, 0.16 * s, cz)
        out.add(lf)

    out.add(_basket(f"{sid}.b", 0.19, 0.22, handle=True)
            .translate(-w * 0.5 - 0.05, 0, d * 0.5 + 0.34))
    out.add(_stool(f"{sid}.stool", 0.45).translate(w * 0.5 - 0.50, 0, d * 0.5 + 0.20))

    sg = _sign(f"{sid}.sign", SIGN_LEAF, "oak_dark", 0.028, 1.35)
    out.add(_hang_sign(f"{sid}.sign", sg, -w * 0.5 + 0.24, I["front_h"] - 0.10,
                       -d * 0.5 - 0.03, rng, 0.15))
    return out, dict(w=w, d=d, front_h=I["front_h"])


def _stall_roast(sid):
    """The roast-meat pitch, at the south end where the smoke blows away from
    everyone else. Live charcoal, a joint on a spit, a chopping block scarred
    to a dish, and the darkest timber in the market from twenty years of smoke.
    """
    rng = rng_for(sid, "roast")
    out = M.Group()
    w, d = 2.50, 2.00
    # Awning is set high and stops short of the fire: you do not hang oiled
    # canvas over live coals, and the gap is a genuine structural asymmetry.
    shell, I = _shell(sid, rng, w, d, front_h=2.44, back_h=2.94, sagx=0.09,
                      sagz=0.07, stripe="cream", valance=0.18, patches=2,
                      guys=1, timber="oak_dark", over_f=0.18, over_s=0.10)
    out.add(shell)
    out.add(_counter(sid, rng, w * 0.62, d, planks=3, shelf=0.36, mat="oak_dark",
                     front_z=-d * 0.5 + 0.06).translate(-w * 0.19, 0, 0))

    # The brazier: iron firebox on splayed legs, standing on a stone slab
    # because you do not light a fire on somebody else's cobbles.
    bx, bz = w * 0.26, -d * 0.5 + 0.44
    slab = M.box(0.90, 0.06, 0.72, 0.012, "cobble")
    slab.rotate_y(0.06)
    slab.translate(bx, 0.03, bz)
    out.add(slab)
    fire = M.box(0.72, 0.20, 0.46, 0.010, "iron")
    fire.translate(bx, 0.66, bz)
    out.add(fire)
    for sx in (-1, 1):
        for sz in (-1, 1):
            out.add(_link((bx + sx * 0.40, 0.06, bz + sz * 0.26),
                          (bx + sx * 0.31, 0.58, bz + sz * 0.19), 0.020, "iron", 5))
    # Coal bed. The `coal` map is hottest at the centre of its UV space, so the
    # lumps near the middle of the bed are placed on the hot region and the ones
    # at the rim on the char — the glow falls off outward without a gradient.
    for i in range(16):
        a = rng.uniform(0, 6.28)
        r = rng.uniform(0.0, 1.0) ** 0.6
        lx = np.cos(a) * r * 0.30
        lz = np.sin(a) * r * 0.18
        lump = M.box(rng.uniform(0.06, 0.11), rng.uniform(0.04, 0.07),
                     rng.uniform(0.05, 0.09), 0.006, "coal")
        _tex(lump, 0.9, 0.9, 0.5 - lx * 1.2 - 0.45, 0.5 - lz * 1.6 - 0.45)
        lump.rotate_y(rng.uniform(0, 3))
        lump.translate(bx + lx, 0.74 + rng.uniform(-0.01, 0.02), bz + lz)
        out.add(lump)

    # Spit across the fire with a joint on it, and a crank at one end.
    spit_y = 0.94
    out.add(_link((bx - 0.52, spit_y, bz), (bx + 0.52, spit_y, bz), 0.014, "iron", 6))
    joint = M.lathe([(0.0, 0), (0.075, 0.03), (0.115, 0.12), (0.105, 0.26),
                     (0.055, 0.34), (0.020, 0.38)], 10, "terracotta")
    _tex(joint, 0.4, 0.4, rng.uniform(0, 2), rng.uniform(0, 2))
    joint.rotate_z(np.pi * 0.5)
    joint.translate(bx - 0.19, spit_y, bz)
    out.add(joint)
    joint2 = M.lathe([(0.0, 0), (0.06, 0.025), (0.085, 0.10), (0.075, 0.19),
                      (0.030, 0.24)], 10, "oak_dark")
    joint2.rotate_z(np.pi * 0.5)
    joint2.translate(bx + 0.12, spit_y, bz)
    out.add(joint2)
    # Crank handle — bent bar, no gears, no springs (Art Bible §2).
    out.add(_link((bx + 0.52, spit_y, bz), (bx + 0.60, spit_y, bz), 0.012, "iron", 5))
    out.add(_link((bx + 0.60, spit_y, bz), (bx + 0.60, spit_y - 0.13, bz), 0.012, "iron", 5))
    hnd = M.cylinder(0.018, 0.10, 6, 0.003, "oak_dark")
    hnd.rotate_z(np.pi * 0.5)
    hnd.translate(bx + 0.60, spit_y - 0.13, bz)
    out.add(hnd)
    # Skewers resting across the bars.
    for i in range(3):
        sy = bz - 0.13 + i * 0.13
        out.add(_link((bx - 0.34, 0.87, sy), (bx + 0.30, 0.87, sy), 0.007, "iron", 4))
        for k in range(4):
            ch = _globe(0.030, "terracotta", 6, 3, sx=1.5, uv=1.4,
                        ou=rng.uniform(0, 4), ov=rng.uniform(0, 4))
            ch.translate(bx - 0.26 + k * 0.15, 0.895, sy)
            out.add(ch)

    # Sausages hung on a rack above — silhouette, and unmistakable.
    rky = 1.86
    out.add(_link((-w * 0.5 + 0.14, rky, -d * 0.5 + 0.36),
                  (w * 0.5 - 0.14, rky, -d * 0.5 + 0.36), 0.020, "oak_dark", 6, 0.003))
    for i in range(4):
        hx = -w * 0.34 + i * 0.24
        n = 7
        for k in range(n):
            t = k / (n - 1)
            a = np.pi * t
            p = np.array([hx + np.sin(a) * 0.075, rky - 0.06 - t * 0.30 - np.sin(a) * 0.05,
                          -d * 0.5 + 0.36])
            s = _globe(0.032, "terracotta", 6, 3, sx=1.0, sy=1.35, uv=1.6,
                       ou=rng.uniform(0, 4), ov=rng.uniform(0, 4))
            s.rotate_z(a * 0.4)
            s.translate(*p)
            out.add(s)

    # Chopping block: an oak stump worn to a dish, with a cleaver in it.
    blk = M.lathe([(0.20, 0), (0.215, 0.04), (0.215, 0.34), (0.205, 0.36),
                   (0.16, 0.355)], 12, "oak_dark")
    _tex(blk, 1.2, 1.2, rng.uniform(0, 2), 0)
    blk.translate(-w * 0.5 + 0.42, COUNTER_H - 0.34, -d * 0.5 + 0.44)
    out.add(blk)
    cl = M.Group()
    cl.add(_prism([(0.0, 0.0), (0.15, 0.0), (0.15, 0.09), (0.0, 0.095)],
                  0.005, "iron", 0.0015))
    hl = M.box(0.11, 0.026, 0.024, CH_SMALL, "oak_dark")
    hl.translate(-0.06, 0.045, 0)
    cl.add(hl)
    cl.rotate_z(-1.15)
    cl.rotate_y(0.5)
    cl.translate(-w * 0.5 + 0.40, COUNTER_H + 0.03, -d * 0.5 + 0.42)
    out.add(cl)
    # Trenchers stacked ready to serve on.
    for k in range(5):
        tr = M.lathe([(0.0, 0), (0.085, 0.004), (0.095, 0.014), (0.090, 0.018)],
                     10, "oak_weathered")
        tr.rotate_y(rng.uniform(0, 3))
        tr.translate(-w * 0.5 + 0.78 + rng.uniform(-0.01, 0.01),
                     COUNTER_H + 0.02 + k * 0.017, -d * 0.5 + 0.38)
        out.add(tr)

    # Residue: ash and cinder trodden into the ground, a water bucket kept
    # close (fire discipline), a mug on the rail, a stool.
    for i in range(14):
        a = rng.uniform(0, 6.28)
        r = rng.uniform(0.3, 1.15)
        cd = M.box(rng.uniform(0.03, 0.07), 0.012, rng.uniform(0.03, 0.06),
                   0.002, "cobble")
        cd.rotate_y(rng.uniform(0, 3))
        cd.translate(bx + np.cos(a) * r, 0.006, bz + np.sin(a) * r * 0.8)
        out.add(cd)
    buck = M.lathe([(0.125, 0), (0.145, 0.26)], 12, "oak_weathered", close_top=False)
    buck.translate(bx + 0.62, 0, bz + 0.52)
    out.add(buck)
    out.add(_ring(0.146, 0.026, "iron", 12).translate(bx + 0.62, 0.20, bz + 0.52))
    wtr = M.lathe([(0.0, 0.21), (0.138, 0.212)], 12, "glass")
    wtr.translate(bx + 0.62, 0, bz + 0.52)
    out.add(wtr)
    mug = M.lathe([(0.040, 0), (0.044, 0.02), (0.046, 0.095), (0.042, 0.105)],
                  10, "terracotta", close_top=False)
    mug.translate(-w * 0.5 + 0.20, COUNTER_H + 0.045, 0.10)
    out.add(mug)
    out.add(_stool(f"{sid}.stool", 0.44).translate(-w * 0.5 - 0.30, 0, d * 0.5 - 0.20))
    out.add(K.barrel(f"{sid}.barrel").translate(w * 0.5 + 0.32, 0, d * 0.5 + 0.06))
    # Firewood, stacked where it stays dry under the awning's back corner.
    for row in range(3):
        for i in range(4):
            lg = M.cylinder(rng.uniform(0.045, 0.070), rng.uniform(0.30, 0.38),
                            6, 0.004, "oak_weathered")
            lg.rotate_z(np.pi * 0.5)
            lg.rotate_y(rng.uniform(-0.05, 0.05))
            lg.translate(w * 0.5 - 0.28, 0.06 + row * 0.115,
                         d * 0.5 - 0.58 + i * 0.14)
            out.add(lg)

    sg = _sign(f"{sid}.sign", SIGN_HAM, "oak_dark", 0.03, 1.3)
    out.add(_hang_sign(f"{sid}.sign", sg, -w * 0.5 + 0.26, I["front_h"] - 0.10,
                       -d * 0.5 - 0.03, rng, 0.16))
    return out, dict(w=w, d=d, front_h=I["front_h"])


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
# Two loose rows flanking the Ford Road, funnelling in from the north gate and
# thinning toward the south (World Bible). Traders arrange for footfall, so the
# best pitches are at the road mouth and everything is angled at the arriving
# traffic rather than squared to a grid. The 4 m around the origin is left clear
# for the fountain, which another agent owns.

LAYOUT = [
    # key         x      z    yaw°   builder
    ("produce", -4.30, -11.70, -19, _stall_produce),
    ("fish",     3.95, -12.55,  25, _stall_fish),
    ("bread",   -5.70,  -8.25, -11, _stall_bread),
    ("cloth",    5.35,  -9.05,  15, _stall_cloth),
    ("herbs",   -6.85,  -4.85, -30, _stall_herbs),
    ("charms",   6.45,  -5.30,  33, _stall_charms),
    ("pottery", -7.55,   1.70,  -8, _stall_pottery),
    ("roast",    7.15,   1.25,   6, _stall_roast),
]


def _cell_for(x, z):
    return ("C" if x < 0 else "D") + ("3" if z < 0 else "4")


def build(ctx: VenueContext, only=None):
    """Emit the eight stalls. `only` builds a single stall for close-up review."""
    for key, x, z, yaw_deg, fn in LAYOUT:
        if only and key != only:
            continue
        sid = f"hm.market.stall.{key}.01"
        group, info = fn(sid)
        yaw = np.radians(yaw_deg)
        group.rotate_y(yaw)
        group.translate(x, 0, z)
        ctx.emit(group)

        # The customer stands in front of the counter; that is where the
        # interaction volume belongs, not at the stall's centroid.
        fx, fz = 0.0, -(info["d"] * 0.5 + 0.55)
        wx = x + fx * np.cos(yaw) + fz * np.sin(yaw)
        wz = z - fx * np.sin(yaw) + fz * np.cos(yaw)
        ctx.entity(sid, f"vendor.{key}", (wx, 0.0, wz),
                   cell=_cell_for(x, z), verbs=["browse", "trade"],
                   rot=[0.0, float(np.sin(yaw * 0.5)), 0.0, float(np.cos(yaw * 0.5))],
                   vendor={"trade": key, "hours": [7, 17]},
                   collider={"shape": "box",
                             "half": [info["w"] * 0.5 + 0.2, 1.2, info["d"] * 0.5 + 0.2]})
