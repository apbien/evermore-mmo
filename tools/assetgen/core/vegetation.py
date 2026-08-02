"""The natural layer: everything that grows, and everything that divides a plot.

Hearthmere had 576 m of ground and not one tree on it. From the air the town
read as a brown blob on green felt whose edge followed nothing, because the two
things that give a real settlement its plan — planting inside the wall and
hedged field boundaries outside it — were both missing.

This module owns the *geometry*. `venues/landscape.py` owns the *placement*.
The split matters: a tree is one shape used four hundred times, so it has to be
built once, instanced, and given an LOD chain, while where it stands is a
question about the town plan and belongs next to the plan.

Three rules run through everything here.

**Foliage is cut-out cards, never opaque cones.** `core/materials.py` ships four
alpha leaf atlases (`leaf_oak`, `leaf_ash`, `leaf_apple`, `leaf_willow`), each a
4x4 sheet of individual leaves. A card maps a whole sheet — sixteen leaves for
two triangles — which is the only way a canopy of real leaves at real scale
(an oak leaf is 120 mm) fits in a prop budget. A lathed green cone is what v1
produced and it reads as a low-poly crystal.

**Card normals are spherical, not planar.** A flat quad's true normal makes the
canopy shade as a heap of shingles: every card facing the sun blows out, every
card facing away goes black, and the tree reads as tinfoil. Blending each
vertex's normal toward the direction from the canopy CENTRE makes the whole
canopy shade as one soft mass, which is what foliage actually does. The leaf
materials are double-sided, so the back faces get the flipped normal for free.

**Everything sways.** Art Bible §7 lists vegetation under required motion.
`SWAY_MATERIALS` is the contract with `client/src/ambient.js`: any primitive
whose material name is in that set gets a vertex-shader wind, amplitude scaled
by height above the primitive's own base. That is why a trunk is `timber_grey`
and a canopy is `leaf_*` even where one material would have been cheaper — the
split IS the rig.
"""

from __future__ import annotations

import math

import numpy as np

from . import kit as K
from . import mesh as M
from .mathx import rng_for
from . import materials as MATS

# ---------------------------------------------------------------------------
# The contract with the client
# ---------------------------------------------------------------------------
# `client/src/ambient.js` keys wind sway off the glTF material NAME, which is
# the library key (see core/gltf.material_from_set). Nothing else is shared, so
# a venue can add a swaying surface by using one of these materials and gets the
# motion with no client edit.
SWAY_MATERIALS = (
    "leaf_oak", "leaf_ash", "leaf_apple", "leaf_willow", "leaf_yew",
    "hedge", "ivy", "weeds", "foliage", "foliage_flower", "reed",
)

# The season, as a COLOR_0 multiplier rather than as pixels in the albedo.
#
# `materials.leaf_atlas` used to bake four of its sixteen leaves bright orange,
# and because 72 % of cards map the whole 4x4 sheet, every canopy in the town
# drew a quarter autumn leaves in high summer with no parameter that could turn
# it off. COLOR_0 multiplies into base colour, so it can only darken and warm —
# which is exactly what a turning leaf does to a green one, and exactly why the
# season belongs here and not in the texture. `AUTUMN` on HERB_GREEN lands on a
# russet, not on the candy orange section 1 lists under "Not this".
AUTUMN = (1.00, 0.62, 0.33)

# Leaf atlas geometry, mirrored from materials.leaf_cards(rows=4, cols=4).
# A card that maps the full sheet shows sixteen leaves; a 2x2 sub-rect shows
# four and is used at the canopy's silhouette edge where a big card's empty
# corners would read as a square hole.
ATLAS_ROWS = 4
ATLAS_COLS = 4

# One atlas cell is one leaf, so a full-sheet card is four leaves across, and
# this is the number that decides whether a canopy reads at the right scale.
#
# A leaf does NOT fill its atlas cell: `materials.leaf_cards` gives a blade
# about 0.4 of the cell across and 0.9 of it along, so a card sized for 0.13 m
# leaves actually draws 50 mm ones. The orchard's first render showed exactly
# that — green confetti rather than foliage. 1.05 m puts a cell at 0.26 m and
# an oak leaf at roughly 0.10 x 0.23 m, which is life size.
CARD_M = 1.05

SPECIES = {
    # leaf material, bark material, card scale, canopy shape (rx, ry ratios),
    # droop (radians the card pitches down), autumn card share
    "oak":      dict(leaf="leaf_oak",    bark="timber_grey",   card=1.00,
                     crown=(1.00, 0.72), droop=0.22),
    "ash":      dict(leaf="leaf_ash",    bark="timber_grey",   card=1.15,
                     crown=(0.82, 1.00), droop=0.30),
    "apple":    dict(leaf="leaf_apple",  bark="oak_weathered", card=0.78,
                     crown=(1.10, 0.60), droop=0.34),
    "willow":   dict(leaf="leaf_willow", bark="timber_grey",   card=1.30,
                     crown=(1.05, 0.80), droop=0.95),
    # The churchyard yew: dense, dark, and the one tree in Hearthmere older than
    # the church.
    #
    # It used to be a MASS — `blob_canopy` on the `hedge` material — on the
    # argument that a yew reads as a mass at any distance. It does, at every
    # distance except the one that matters. These two stand at ~9 m diameter on
    # both flanks of the church, where a four-ring seven-segment lathe has
    # facets three to four metres across; they rendered as flat dark-green
    # angular slabs cropping both aisles off the west front in the frame every
    # player looks at ten seconds after spawning. A yew is a conifer, so it gets
    # a needle sheet rather than a broadleaf one — `materials.needle_atlas`.
    "yew":      dict(leaf="leaf_yew",    bark="oak_weathered", card=0.86,
                     crown=(0.92, 0.86), droop=0.14),
}


# ---------------------------------------------------------------------------
# Card primitives
# ---------------------------------------------------------------------------

def _quad(b, pts, uvs, nrm, col=None, normals=None):
    """Append one quad to a `mesh._Builder` with explicit UVs.

    Deliberately not `b.poly`: that projects planar UVs in metres, which is
    right for a wall and wrong for an atlas card, whose UVs address a rect in
    texture space and have nothing to do with its size in the world.

    `col` is the card's COLOR_0 tint — season and crown-depth shade. It has to
    go through the builder's own colour list or the attribute ends up shorter
    than POSITION, which glTF accepts and the renderer then reads off the end of.
    """
    base = len(b.v)
    c = (1.0, 1.0, 1.0, 1.0) if col is None else (
        tuple(float(x) for x in col) + ((1.0,) if len(col) == 3 else ()))
    if col is not None:
        b._coloured = True
    ns = normals if normals is not None else [nrm] * len(pts)
    for p, t, n in zip(pts, uvs, ns):
        b.v.append(np.asarray(p, np.float32))
        b.n.append(np.asarray(n, np.float32))
        b.uv.append(t)
        b.col.append(c)
    b.idx += [base, base + 1, base + 2, base, base + 2, base + 3]


def _atlas_rect(rng, big=0.55):
    """A UV rect on the leaf sheet, in one of eight orientations.

    Returns (uv00, uv10, uv11, uv01, cells_across) — the four corner UVs in the
    card's own winding order, not a min/max box, because the box is exactly what
    made the grid.

    **Why this is not just a rect.** `review/reports/ad-town-04.md` §4 read the
    canopy off the screen as *"regular rectangular grids of dark-green squares"*
    across 40 % of `approach-s`. Two lattices produce that and both had to go.
    The sheet's own — sixteen sprays at sixteen identical stations — is broken in
    `materials.leaf_cards`. This is the other one: **every card mapped the sheet
    the same way up.** Seven hundred cards in a crown, all showing the same
    sixteen sprays in the same order at the same phase, is a repeated tile, and
    the eye finds a repeated tile in a canopy instantly however good the tile is.

    The eight orientations are the square's own symmetries — flip in u, flip in
    v, transpose — and they are the only transforms that map the 4x4 cell grid
    onto itself. That matters: `materials.leaf_cards` guarantees no blade
    crosses a cell boundary, so a card cut on cell lines never shows a severed
    leaf, and an arbitrary rotation in UV space would show one on every edge.
    Eight orientations times nine sub-rect origins is 72 distinct cards from one
    sheet, which is past the count at which a canopy stops repeating.

    Petiole-at-v0 is the sheet's own convention (`materials.leaf_cards` puts
    `along = 0` at the top of each cell), so a card hung from its v0 edge hangs
    by its stalks — and a flipped card hangs by them just as well, because a
    spray upside down in a canopy is a spray on the underside of a branch.
    """
    if rng.random() < big:
        u0, v0, u1, v1, across = 0.0, 0.0, 1.0, 1.0, ATLAS_COLS
    else:
        c = int(rng.integers(0, ATLAS_COLS - 1))
        r = int(rng.integers(0, ATLAS_ROWS - 1))
        u0, v0 = c / ATLAS_COLS, r / ATLAS_ROWS
        u1, v1 = (c + 2) / ATLAS_COLS, (r + 2) / ATLAS_ROWS
        across = 2
    if rng.random() < 0.5:
        u0, u1 = u1, u0
    if rng.random() < 0.5:
        v0, v1 = v1, v0
    corners = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    if rng.random() < 0.5:                      # transpose: the 90 degree turn
        corners = [(v, u) for (u, v) in corners]
    return corners, across


def _spherify(m, centre, amount=0.85):
    """Blend every normal toward the outward radial from `centre`.

    The single highest-impact line in this file. Without it a canopy is a heap
    of independently-lit quads; with it the whole crown shades as one volume and
    the anime rim light (Art Bible §1) actually wraps it.
    """
    if not len(m.v):
        return m
    d = m.v - np.asarray(centre, np.float32)
    ln = np.linalg.norm(d, axis=1, keepdims=True)
    rad = d / np.where(ln < 1e-6, 1.0, ln)
    n = m.n * (1.0 - amount) + rad * amount
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    m.n = (n / np.where(ln < 1e-6, 1.0, ln)).astype(np.float32)
    return m


def leaf_cards(asset_id, mat, points, size=CARD_M, droop=0.25, centre=None,
               jitter=0.22, autumn=0.0, depth_shade=0.42, radius=None,
               puff=0.55, shell_face=0.62):
    """A cloud of leaf cards at the given points. One Mesh, one material.

    Each card is a single quad — two triangles for sixteen SPRAYS of leaves —
    turned on all three axes: its FACE toward the outside of the crown mixed
    with a free random direction (`shell_face`), its +Y hanging outward and down
    by `droop`, and a roll about its own normal. All three matter and the
    project has shipped two passes without the first two of them.

    Two things arrive on COLOR_0, and both are free:

    `depth_shade` darkens the cards that sit inside the crown toward the ones on
    its surface. A canopy lit by one directional light with no occlusion between
    its own leaves is a flat green cloud; half a stop of interior shade is what
    makes it a volume, and it is the same trick baked vertex AO plays everywhere
    else in this repo. `radius` is the crown's own half-extent — pass it and the
    ramp is measured against the tree rather than against whatever happens to be
    the furthest card.

    `autumn` is the share of cards that have turned, 0..1. It lives here rather
    than in the albedo because `materials.leaf_atlas` used to bake it and the
    result was a town where every canopy was multicoloured confetti in July with
    no parameter that could turn it off.
    """
    rng = rng_for(asset_id, "cards")
    b = M._Builder()
    pts = np.asarray(points, np.float32).reshape(-1, 3)
    if not len(pts):
        return M.Mesh(mat=mat)
    ctr = np.asarray(centre if centre is not None else pts.mean(axis=0),
                     np.float32)
    if radius is None:
        d = np.linalg.norm(pts - ctr, axis=1)
        radius = float(d.max()) if len(d) else 1.0
    radius = max(float(radius), 1e-3)
    splay = []
    DOWN = np.array([0.0, -1.0, 0.0], np.float32)
    # How hard the card's face is turned to the crown's own outward normal.
    # 1.0 would be a shell of billboards — correct coverage, wrong structure,
    # and it makes the crown a balloon. 0.0 is what shipped and it is worse: see
    # the note in the loop.
    face = float(np.clip(shell_face, 0.0, 1.0))
    for p in pts:
        d = p - ctr
        dl = float(np.linalg.norm(d))
        rad = d / dl if dl > 1e-4 else np.array([0.0, 1.0, 0.0], np.float32)
        t_r = min(1.0, dl / radius)
        # Small sub-rect cards at the crown's edge, whole sheets inside it.
        # A big card's empty corners read as a square hole on the silhouette,
        # and small cards are what makes an outline look bitten rather than cut.
        uvs, across = _atlas_rect(rng, big=0.72 - 0.52 * t_r)
        s = size * (across / ATLAS_COLS) * rng.uniform(1.0 - jitter, 1.0 + jitter)
        s *= 1.0 - 0.26 * max(0.0, t_r - 0.70) / 0.30

        # --- orientation ----------------------------------------------------
        #
        # THE BUG THIS REPLACES. The old frame was built from a yaw, a small
        # pitch and a small roll, which gave
        #     ay = (-sin yaw cos pitch, sin pitch, -cos yaw cos pitch)
        # and with every species' `droop` between 0.14 and 0.34, `sin pitch` is
        # about -0.2: **`ay` was 97 % horizontal and `ax` at most 47 % off
        # horizontal, so every leaf card in the town was a flat plate lying
        # face-up.** From a 1.62 m eye that is the worst orientation there is —
        # every card is edge-on, so it paints a streak instead of its 55 %
        # coverage and the crown never closes; the only cards seen face-on are
        # the ones overhead, seen from UNDERNEATH, where a double-sided flip
        # turns the normal away from a 38 deg sun and they render black. It is
        # the whole of `ad-town-05.md` §3's "rows and columns", the see-through
        # canopy and the black/white split, in one line of trigonometry.
        #
        # Now: the card faces OUTWARD from the crown centre, mixed with a free
        # random direction, and the mix is stronger at the crown's surface than
        # in its middle — the outside of a canopy is a wall of leaves presented
        # to the sky and the inside is a jumble.
        rnd = rng.normal(size=3).astype(np.float32)
        rnd /= (np.linalg.norm(rnd) or 1.0)
        mix = face * (0.42 + 0.58 * t_r)
        nz = rad * mix + rnd * (1.0 - mix)
        nz /= (np.linalg.norm(nz) or 1.0)
        # +Y of the card runs petiole -> tip, so it must hang outward and DOWN,
        # which is what `droop` means. A willow hangs straight down (droop 0.95)
        # and an oak spray reaches out (0.22).
        dw = float(np.clip(droop, 0.0, 1.0))
        hang = rad * (1.0 - dw) + DOWN * dw
        hang -= nz * float(np.dot(hang, nz))
        hl = float(np.linalg.norm(hang))
        if hl < 1e-3:
            hang = np.cross(nz, np.array([0.0, 1.0, 0.0], np.float32))
            hl = float(np.linalg.norm(hang)) or 1.0
        ay0 = hang / hl
        ax0 = np.cross(ay0, nz)
        # Roll about the card's own normal — the third axis. Mostly a hang, but
        # one card in six is turned right over, because a real spray on the
        # underside of a limb points any way at all.
        phi = (rng.uniform(-math.pi, math.pi) if rng.random() < 0.17
               else rng.uniform(-1.15, 1.15))
        cph, sph = math.cos(phi), math.sin(phi)
        ay = ay0 * cph + ax0 * sph
        ax = np.cross(ay, nz)
        hx = ax * (s * 0.5)
        # Mostly hung from the petiole edge, so the sheet's stalks meet the twig
        # instead of floating half a card away from it — but pulled back by a
        # fifth, because `ay` now points outward and a card hung entirely below
        # its point pushes the silhouette a whole card past the crown.
        v = ay * s
        c = p - v * 0.20
        pts4 = [c - hx, c + hx, c + hx + v, c - hx + v]
        # Crown-depth shade, plus a lift on the cards that sit high in the
        # crown: sky light reaches the top of a canopy and the underside of it
        # gets whatever bounces. One multiply, no cost, and it is most of the
        # difference between a tree and a green cloud.
        hi = float(np.clip((c[1] - ctr[1]) / radius, -1.0, 1.0))
        g = (1.0 - depth_shade) + depth_shade * (t_r ** 0.75)
        g *= 0.90 + 0.10 * hi
        g *= rng.uniform(0.93, 1.0)
        col = (g, g, g)
        if autumn > 0.0 and rng.random() < autumn:
            col = (g * AUTUMN[0], g * AUTUMN[1], g * AUTUMN[2])
        # The card's own curvature, as four corner normals fanned outward from
        # its centre. A quad with one normal is FLAT, and at five metres — which
        # is where `approach-s` puts the canopy — flat is exactly what it reads
        # as: a green cutout pasted on the sky. Splaying the corners makes the
        # card shade like a section of a sphere, so a clump of leaves catches the
        # light across itself instead of taking one value over its whole area.
        # It is the same trick as `_spherify` one level down, and the two
        # compose: `_spherify` makes the CROWN a volume, this makes each CLUMP
        # one. Costs nothing — the vertices already exist.
        splay.append([(ax * sx + ay * sy) * puff for sx, sy in
                      ((-1.0, -0.6), (1.0, -0.6), (1.0, 0.7), (-1.0, 0.7))])
        _quad(b, pts4, uvs, nz, col)
    m = b.build(mat)
    _spherify(m, ctr)
    if splay:
        n = m.n + np.asarray(splay, np.float32).reshape(-1, 3)
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        m.n = (n / np.where(ln < 1e-6, 1.0, ln)).astype(np.float32)
    return m


# ---------------------------------------------------------------------------
# Woody structure
# ---------------------------------------------------------------------------

def _limb(a, b, r0, r1, mat, segments=5):
    """A tapered tube from a to b. The whole of this module's branch geometry.

    Built by hand rather than by rotating a lathe: aiming a lathe needs a basis
    and a composed rotation, and every time that has been done by angle in this
    repo something has ended up 90 degrees out.
    """
    a = np.asarray(a, np.float32)
    b = np.asarray(b, np.float32)
    d = b - a
    ln = float(np.linalg.norm(d))
    if ln < 1e-4:
        return M.Mesh(mat=mat)
    d = d / ln
    up = np.array([0, 1, 0], np.float32)
    if abs(float(np.dot(d, up))) > 0.95:
        up = np.array([1, 0, 0], np.float32)
    ex = np.cross(up, d)
    ex /= (np.linalg.norm(ex) or 1.0)
    ez = np.cross(d, ex)
    bld = M._Builder()
    seg = max(3, int(segments))
    for i in range(seg):
        a0 = (i / seg) * math.tau
        a1 = ((i + 1) / seg) * math.tau
        p00 = a + ex * (math.cos(a0) * r0) + ez * (math.sin(a0) * r0)
        p10 = a + ex * (math.cos(a1) * r0) + ez * (math.sin(a1) * r0)
        p11 = b + ex * (math.cos(a1) * r1) + ez * (math.sin(a1) * r1)
        p01 = b + ex * (math.cos(a0) * r1) + ez * (math.sin(a0) * r1)
        # V runs along the limb in metres so the bark's grain runs with the
        # member, Art Bible §2.
        uvs = [(a0 * r0 * 0.5, 0.0), (a1 * r0 * 0.5, 0.0),
               (a1 * r1 * 0.5, ln * 0.5), (a0 * r1 * 0.5, ln * 0.5)]
        n0 = ex * math.cos(a0) + ez * math.sin(a0)
        n1 = ex * math.cos(a1) + ez * math.sin(a1)
        base = len(bld.v)
        for p, t, nn in ((p00, uvs[0], n0), (p10, uvs[1], n1),
                         (p11, uvs[2], n1), (p01, uvs[3], n0)):
            bld.v.append(np.asarray(p, np.float32))
            bld.n.append(np.asarray(nn, np.float32))
            bld.uv.append(t)
        bld.idx += [base, base + 1, base + 2, base, base + 2, base + 3]
    return bld.build(mat)


def _trunk(asset_id, height, r_base, r_top, mat, lean=0.0, bend=0.10, flare=1.6):
    """A bole with a root flare and a bend. Never a cylinder.

    `flare` is why: a tree meets the ground in a spreading buttress, and a
    straight-sided cylinder pushed into turf is the most common tell in a
    procedural forest.
    """
    rng = rng_for(asset_id, "trunk")
    out = M.Mesh(mat=mat)
    N = 5
    prev = np.array([0.0, 0.0, 0.0], np.float32)
    lean_dir = rng.uniform(0.0, math.tau)
    for i in range(N):
        t0, t1 = i / N, (i + 1) / N
        # Radius: a flared foot, then a steady taper.
        r0 = r_base * ((flare - 1.0) * (1.0 - t0) ** 3 + 1.0) * (1.0 - t0) + r_top * t0
        r1 = r_base * ((flare - 1.0) * (1.0 - t1) ** 3 + 1.0) * (1.0 - t1) + r_top * t1
        sway = bend * height * (t1 ** 1.6) + lean * height * t1
        nxt = np.array([math.cos(lean_dir) * sway + rng.uniform(-0.02, 0.02) * height,
                        height * t1,
                        math.sin(lean_dir) * sway + rng.uniform(-0.02, 0.02) * height],
                       np.float32)
        out.merge(_limb(prev, nxt, r0, r1, mat, segments=7 if i < 2 else 5))
        prev = nxt
    return out, prev, lean_dir


def crown_shape(rng, spread=1.0):
    """A seeded description of ONE crown. Two trees of a species differ by this.

    Returns a dict consumed by `_crown_points`. It is drawn from the tree's own
    RNG, so `oak_great` and `oak` are different individuals rather than the same
    individual at two scales — and a caller that wants a second individual of
    the same kind asks for it with a different asset id and gets one for free.

    A crown's readable identity is almost entirely its LOW frequencies: how many
    big masses it carries, whether it is lopsided, whether it leans, whether one
    flank has been cut back off a lane. Those are the four numbers here.
    """
    lobes = []
    for _ in range(int(rng.integers(3, 6))):
        lobes.append((rng.uniform(0.10, 0.26) * spread,       # amplitude
                      rng.uniform(0.0, math.tau),             # azimuth phase
                      float(rng.integers(2, 5)),              # azimuth order
                      rng.uniform(0.0, math.tau)))            # elevation phase
    return dict(
        lobes=lobes,
        # Lopsidedness: a hedgerow tree is drawn to the light and a street tree
        # is cut back off the carriageway. Both make the crown off-centre.
        lean=(rng.uniform(-0.20, 0.20) * spread,
              rng.uniform(-0.20, 0.20) * spread),
        # Aspect: the same species runs from squat to columnar.
        aspect=rng.uniform(0.88, 1.14),
        # How many discrete leaf masses hang on the limbs. Low numbers read as
        # an old, open, hard-pruned tree; high as a young dense one.
        clump_n=float(rng.uniform(0.75, 1.30)),
        clump_r=rng.uniform(0.20, 0.30),
    )


def _shape_radius(shape, ux, uy, uz):
    """The crown's radius multiplier in the direction (ux, uy, uz), unit length.

    Smooth and low-frequency: this is the SILHOUETTE, and any high frequency put
    here is a frequency the eye can find and call a pattern.
    """
    az = math.atan2(uz, ux)
    r = 1.0
    for amp, ph, order, eph in shape["lobes"]:
        r += amp * math.sin(az * order + ph) * math.cos(uy * 2.1 + eph)
    return max(0.35, r)


def _blue_noise(rng, n, sampler, k=6):
    """Best-candidate sampling: n points, each the furthest of k candidates.

    **Why the scatter had to change at all.** The old crown sampler drew every
    card independently from a uniform spherical distribution, which is white
    noise — and white noise in two dimensions is not "random-looking", it is
    lumpy: it makes clusters and voids at every scale, and the eye reads the
    voids as holes and the clusters as a repeat. Poisson-disc/blue-noise spacing
    is what a real canopy has, because leaves compete for the same light and
    cannot occupy the same place.

    Mitchell's best-candidate rather than Bridson's dart-throwing: it takes an
    arbitrary `sampler` (so the crown can be clumped and lopsided rather than a
    ball), it never fails to place the count it was asked for, and it needs no
    radius to be chosen in advance — the spacing falls out of the count.
    """
    n = int(n)
    if n <= 0:
        return np.zeros((0, 3), np.float32)
    out = np.zeros((n, 3), np.float32)
    out[0] = sampler(1)[0]
    for i in range(1, n):
        cand = sampler(k)
        d = ((cand[:, None, :] - out[None, :i, :]) ** 2).sum(-1).min(axis=1)
        out[i] = cand[int(np.argmax(d))]
    return out


def _crown_points(rng, centre, rx, ry, n, shell=0.62, shape=None, ragged=0.30,
                  anchors=None):
    """Blue-noise points through a clumped, individually-shaped crown.

    Three things this has to do that the old uniform-shell sampler did not, all
    of them named in `ad-town-05.md` §3:

    **No detectable period at any range.** Blue noise, above.

    **Clumps, not a shell.** A canopy is a few dozen discrete leaf masses hung
    on the limbs, with sky between them — that is why you can see through a real
    tree in a way that has structure. `shell` used to push every card onto one
    surface, which gives a hollow green balloon: closed where you do not want it
    and empty where the branches are. Cards are now drawn from clump balls whose
    centres are themselves blue-noise-spaced through the volume, biased outward
    but not pinned to the surface.

    **A ragged silhouette.** Each clump's reach past the nominal crown surface
    is drawn per clump, so the outline is bitten into rather than being an
    offset of the shape function, and the density of cards inside a clump falls
    off toward its own edge. The alternative — one smooth surface with cards on
    it — is a shell, and a shell reads as a cut-out however good the sheet is.
    """
    n = int(n)
    if n <= 0:
        return np.zeros((0, 3), np.float32)
    shape = shape or crown_shape(rng)
    cx, cy, cz = float(centre[0]), float(centre[1]), float(centre[2])
    lean_x, lean_z = shape["lean"]
    ay = ry * shape["aspect"]

    def _unit(m):
        u = rng.normal(size=(m, 3))
        u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-6)
        return u

    # --- the clumps ---------------------------------------------------------
    n_clump = int(np.clip(round((n ** 0.62) * shape["clump_n"]), 3, 40))

    def _clump_sampler(m):
        u = _unit(m)
        # Biased outward — the leaf mass of a broadleaf hangs on the outer
        # third of the limbs — but nowhere near a shell.
        r = 0.34 + 0.62 * rng.random(m) ** 0.55
        out = np.empty((m, 3), np.float32)
        for j in range(m):
            g = _shape_radius(shape, u[j, 0], u[j, 1], u[j, 2])
            out[j] = (cx + lean_x * rx + u[j, 0] * rx * r[j] * g,
                      cy + u[j, 1] * ay * r[j] * g,
                      cz + lean_z * rx + u[j, 2] * rx * r[j] * g)
        return out

    # The leaf masses hang ON THE LIMBS. Seeding a clump at every branch tip
    # before filling the rest in is what stops the first render's defect: bare
    # secondary limbs projecting a metre and a half past the leaf mass with
    # nothing on them, which reads as a dead tree with a green cloud behind it.
    fixed = np.zeros((0, 3), np.float32)
    if anchors is not None and len(anchors):
        a = np.asarray(anchors, np.float32).reshape(-1, 3)
        if len(a) > n_clump:
            a = a[rng.choice(len(a), size=n_clump, replace=False)]
        # Pulled back along the limb a little: a spray sits around the last
        # third of a twig, not balanced on its point.
        fixed = a + (np.asarray(centre, np.float32) - a) * 0.12
        fixed = fixed + rng.normal(scale=rx * 0.06, size=fixed.shape).astype(np.float32)
    cl = _blue_noise(rng, max(0, n_clump - len(fixed)), _clump_sampler, k=5)
    cl = np.concatenate([fixed, cl], axis=0) if len(fixed) else cl
    n_clump = len(cl)
    # Per-clump radius, spread wide on purpose: equal-sized clumps at
    # blue-noise spacing is a lattice with the corners knocked off.
    clr = (rx * shape["clump_r"] *
           rng.uniform(0.55, 1.70, size=n_clump)).astype(np.float32)
    # Which clumps get how many cards. Equal shares would make every mass the
    # same visual weight; a real crown has two or three dominant masses.
    w = rng.uniform(0.35, 1.0, size=n_clump) ** 1.5
    w /= w.sum()

    def _card_sampler(m):
        j = rng.choice(n_clump, size=m, p=w)
        u = _unit(m)
        # Density falls off toward the clump's own edge — `**0.70` rather than
        # the `**(1/3)` that would fill the ball uniformly. That is what makes
        # the outer boundary of every mass soft, and the union of soft masses is
        # a ragged silhouette.
        r = rng.random(m) ** 0.70
        return (cl[j] + u * (clr[j] * (1.0 + ragged * (rng.random(m) - 0.5)) *
                             r)[:, None]).astype(np.float32)

    return _blue_noise(rng, n, _card_sampler, k=6)


def blob_canopy(asset_id, rx, ry, mat="hedge", rings=7, segments=16, lumps=0.22):
    """An opaque, irregular leaf mass. **LOD2 and LOD3 only.**

    Alpha-tested cards stop paying at about 60 m — the cutout dithers, the
    overdraw is real and the shape is all that survives. What survives is what
    this builds: a lumpy volume in one opaque material with no sorting.

    The defaults were `rings=4, segments=7`, which is a 28-facet lathe. That is
    fine at 60 m and a disaster at 6: it built the churchyard yews, and at their
    9 m diameter each facet was three to four metres across and hard-edged
    against the sky. **Nothing a player can stand under may use this.** The yew
    now has a card canopy; the distance wood has a billboard impostor; what is
    left here is LOD2, LOD3 and a hedge's end, all of which are beyond 40 m, and
    the defaults are raised so that even those never read as a polyhedron.
    """
    rng = rng_for(asset_id, "blob")
    b = M._Builder()
    R, S = max(2, rings), max(4, segments)
    # Per-vertex radial noise, shared around the seam so the blob closes. Two
    # frequencies: a low-order lobe that gives the mass a shape, and per-vertex
    # jitter on top of it. One frequency at one amplitude is what makes a lathe
    # read as a lathe however many segments it has — the facets stay in rings.
    amp = np.zeros((R + 1, S), np.float32)
    lobe_a = rng.uniform(0.0, math.tau)
    lobe_b = rng.uniform(0.0, math.tau)
    for i in range(R + 1):
        for j in range(S):
            th = (j / S) * math.tau
            phi = (i / R) * math.pi
            amp[i, j] = (1.0
                         + lumps * 0.85 * math.sin(th * 2.0 + lobe_a) * math.sin(phi)
                         + lumps * 0.55 * math.sin(th * 3.0 + phi * 2.0 + lobe_b)
                         + rng.uniform(-lumps * 0.45, lumps * 0.45))
    grid = []
    for i in range(R + 1):
        v = i / R
        phi = v * math.pi
        row = []
        for j in range(S):
            th = (j / S) * math.tau
            a = amp[i, j]
            row.append(np.array([math.sin(phi) * math.cos(th) * rx * a,
                                 math.cos(phi) * ry * a,
                                 math.sin(phi) * math.sin(th) * rx * a], np.float32))
        grid.append(row)
    for i in range(R):
        for j in range(S):
            k = (j + 1) % S
            p00, p10 = grid[i][j], grid[i][k]
            p11, p01 = grid[i + 1][k], grid[i + 1][j]
            for tri in ((p00, p11, p10), (p00, p01, p11)):
                b.poly(list(tri), [(p[0] * 0.5, p[1] * 0.5) for p in tri])
    m = b.build(mat)
    return _spherify(m, (0.0, 0.0, 0.0), 0.9)


# ---------------------------------------------------------------------------
# Trees
# ---------------------------------------------------------------------------

def tree(asset_id, species="oak", height=8.0, density=1.0, detail=1.0,
         bare=False, autumn=0.0):
    """One tree, origin at the base of the bole, +Y up.

    `detail` drives the LOD level: 1.0 is LOD0, 0.45 is LOD1, 0.16 is LOD2.
    Everything below that is `blob_canopy` and does not come through here.

    `autumn` is the share of this tree's cards that have turned, 0..1. It is 0
    by default and Hearthmere ships at 09:30 in high summer, so nothing in the
    town uses it yet — but it is the ONLY place a season may be set. The sheet
    itself is green in every season on purpose (see `materials.leaf_atlas`), so
    a seasonal pass is a value on a call here and never a texture rebuild.
    """
    S = SPECIES.get(species, SPECIES["oak"])
    rng = rng_for(asset_id, "tree", species)
    out = M.Group()

    h = float(height)
    crown_rx, crown_ry = S["crown"]
    # Clear bole: an orchard apple is pruned to 1.4 m, a churchyard yew forks at
    # the ground, a hedgerow ash runs a third of its height clean.
    fork = h * {"apple": 0.26, "yew": 0.16, "willow": 0.30}.get(species, 0.34)
    r_base = h * 0.038 * (1.25 if species in ("oak", "yew") else 1.0)

    bole, top, lean_dir = _trunk(f"{asset_id}.bole", fork, r_base, r_base * 0.55,
                                 S["bark"], bend=0.06 if species != "willow" else 0.12)
    out.add(bole)

    # Primary limbs. They all start at the fork, spread on a cone, and end
    # inside the crown volume — which is what makes the crown look supported
    # rather than balanced on a stick.
    #
    # The crown is sized so its TOP lands on `height`. Deriving `ry` from a
    # species ratio instead put an 8 m oak's highest leaf at 6.5 m, which is a
    # 19% scale error on the most scale-sensitive object in an outdoor scene —
    # and one that only shows up beside the 1.75 m figure.
    crown_h = h - fork
    ry = crown_h * 0.55 * (1.0 if species != "apple" else 0.86)
    rx = ry * (crown_rx / crown_ry)
    centre = np.array([top[0], h - ry, top[2]], np.float32)
    n_limb = max(2, int(round((7 if detail > 0.6 else 4) * (1.0 if species != "apple" else 1.2))))
    tips = []
    for i in range(n_limb):
        a = (i / n_limb) * math.tau + rng.uniform(-0.4, 0.4)
        reach = rx * rng.uniform(0.45, 0.85)
        tip = np.array([centre[0] + math.cos(a) * reach,
                        centre[1] + ry * rng.uniform(-0.45, 0.45),
                        centre[2] + math.sin(a) * reach], np.float32)
        out.add(_limb(top, tip, r_base * 0.42, r_base * 0.13, S["bark"],
                      segments=5 if detail > 0.6 else 4))
        tips.append(tip)
        # Secondaries, LOD0 only. They are what stops a bare winter silhouette
        # reading as a hand of bananas.
        if detail > 0.6:
            for _ in range(3):
                b = a + rng.uniform(-0.9, 0.9)
                t2 = np.array([tip[0] + math.cos(b) * rx * 0.42,
                               tip[1] + rng.uniform(-0.10, 0.35) * ry,
                               tip[2] + math.sin(b) * rx * 0.42], np.float32)
                out.add(_limb(tip, t2, r_base * 0.14, r_base * 0.05, S["bark"], 4))
                tips.append(t2)

    if bare:
        return out

    # Cards. Count scales with crown VOLUME, so a 12 m ash is not given the same
    # canopy as a 4 m apple and then stretched.
    #
    # The multiplier used to be 9.0 and was chasing the wrong term. At 13 %
    # opaque coverage a card painted 0.13 m2 of leaf through a full quad of
    # overdraw, so no achievable card count could close a crown: the market oak
    # took 694 cards, painted ~90 m2 through a 110 m3 crown, and still rendered
    # as bare antlers hung with confetti. `materials.leaf_cards` now ships
    # sprays at 45-58 % coverage — 3.5x the leaf per card — so the SAME opacity
    # costs roughly a third of the geometry. That is the whole trade: coverage
    # is the term, card count never was.
    vol = rx * rx * ry
    # A yew is the densest thing that grows here — you cannot see through one —
    # and an old apple is the sparsest, because it is pruned open to let light
    # at the fruit. That is a real difference between the two trees and it is
    # worth the two constants.
    dens = {"yew": 1.60, "apple": 0.85, "willow": 1.15}.get(species, 1.0)
    n_card = int(np.clip(vol * 6.0 * dens * density * detail, 12, 780))
    # The individual. Drawn from THIS tree's rng before any card is placed, so
    # two oaks built from two asset ids are two different oaks — different
    # number of masses, different lopsidedness, different aspect — rather than
    # one oak at two scales. `landscape.TreeField` plants several variants of
    # the high-count kinds off this.
    shape = crown_shape(rng, spread=0.75 if species == "yew" else 1.0)
    pts = _crown_points(rng, centre, rx, ry, n_card, shape=shape, anchors=tips)
    # Anchor a share of the cards on the limb tips so the crown is attached.
    for i, t in enumerate(tips[:len(pts) // 6]):
        pts[i] = t
    # A big tree gets bigger sprays, not just more of them: one card's worth of
    # 100 mm leaves is the right density for an apple and would need four
    # thousand cards to clothe a 12 m oak.
    # Gently, and clamped by the jitter above. Card size sets LEAF size, and a
    # 12 m oak whose leaves are 400 mm long is a more obvious error than one
    # whose canopy costs 200 extra cards.
    size = CARD_M * S["card"] * (1.0 + rx / 26.0)
    # LOD card inflation. It was 1.9x, which put 2.1 m cards on a LOD1 oak —
    # and a 2.1 m alpha-masked quad is exactly the black lozenge `ad-town-05.md`
    # §3 found on the paving in `craft-walk-04`, because at that size one card
    # covers a metre and a half of ground on its own and the sheet's holes are
    # spread too thin to read as dapple. 1.35x still buys most of the fill rate
    # back; the rest comes off the card COUNT, which is the term that is
    # supposed to carry an LOD anyway.
    out.add(leaf_cards(f"{asset_id}.cards", S["leaf"], pts,
                       size=size * (1.0 if detail > 0.5 else 1.35),
                       droop=S["droop"], centre=centre,
                       depth_shade=0.24 if species == "yew" else 0.32,
                       radius=max(rx, ry), autumn=autumn,
                       # A yew presents a near-solid wall of needle; an old
                       # apple is pruned open and its sprays point every way.
                       shell_face=0.74 if species == "yew" else
                                  (0.48 if species == "apple" else 0.62)))
    return out


def tree_lods(asset_id, species="oak", height=8.0, density=1.0, autumn=0.0):
    """The four-step chain for one tree. Feed straight to `ctx.lod`.

    LOD3 is a blob and no trunk at all: at 100 m a bole is under two pixels and
    a second material for it costs a whole draw call per cell for nothing.
    """
    S = SPECIES.get(species, SPECIES["oak"])
    fork = height * {"apple": 0.26, "yew": 0.16, "willow": 0.30}.get(species, 0.34)
    ry = (height - fork) * 0.55 * (1.0 if species != "apple" else 0.86)
    rx = ry * (S["crown"][0] / S["crown"][1])
    # The impostor REACHES THE GROUND. An ellipsoid sized to the crown alone
    # hangs two and a half metres clear of the turf with no trunk under it —
    # which at LOD3 range is twenty-odd pixels of daylight beneath every distant
    # tree, and reads as a field of floating green lollipops. Directive §6.1
    # says nothing floats, and an impostor is not exempt from it.
    iry = (height - 0.4) * 0.5
    l3 = blob_canopy(f"{asset_id}.imp", rx * 0.92, iry, "hedge",
                     rings=3, segments=6)
    l3.translate(0.0, iry + 0.4, 0.0)
    return [
        tree(asset_id, species, height, density, detail=1.00, autumn=autumn),
        tree(asset_id, species, height, density, detail=0.45, autumn=autumn),
        tree(asset_id, species, height, density, detail=0.16, autumn=autumn),
        l3,
    ]


def distance_tree(asset_id, height=9.0, mat="tree_far"):
    """The wooded ring: a crossed-billboard impostor. Eight triangles.

    Only ever seen past 140 m, where the job is silhouette and hiding the world
    edge, and where a tree is fifteen pixels wide.

    It was a 90-triangle lathe. Two thousand three hundred of them is 207,000
    triangles, and it is a large part of why `landscape` carried 83 % of the
    town's geometry; worse, at rings=5 segments=9 the facets are legible even at
    that range, and across the Mere the ring read as a row of green crystals.
    A silhouette is what a billboard is for, so this is what it is now: three
    quads crossed at 60 degrees on `materials.tree_impostor`'s 2x2 sheet, plus
    one near-horizontal cap so the wood does not vanish edge-on in the aerials —
    which is the one failure mode crossed billboards have and the reason people
    who skip the cap ship a bald ring.

    Normals are spherified about the tree's own centre, so the four cards shade
    as one soft volume rather than as four independently-lit flats.
    """
    rng = rng_for(asset_id, "distant")
    h = height * rng.uniform(0.78, 1.24)
    w = h * rng.uniform(0.62, 0.86)
    # One of four silhouettes on the sheet. A single outline repeated two
    # thousand times along a horizon is legible AS a repeat.
    ci = int(rng.integers(0, 2))
    ri = int(rng.integers(0, 2))
    u0, u1 = ci * 0.5, (ci + 1) * 0.5
    v0, v1 = ri * 0.5, (ri + 1) * 0.5
    b = M._Builder()
    centre = np.array([0.0, h * 0.60, 0.0], np.float32)
    n_card = 3
    for i in range(n_card):
        a = (i / n_card) * math.pi + rng.uniform(-0.12, 0.12)
        ex = np.array([math.cos(a), 0.0, math.sin(a)], np.float32) * (w * 0.5)
        nz = np.array([-math.sin(a), 0.0, math.cos(a)], np.float32)
        # v0 is the top of the sheet and the top of the tree; the card stands
        # ON the ground, so nothing floats (directive 6.1).
        top, bot = np.array([0.0, h, 0.0], np.float32), np.zeros(3, np.float32)
        pts = [top - ex, top + ex, bot + ex, bot - ex]
        _quad(b, pts, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], nz)
    # The cap. Tilted rather than flat so it still catches the sun at 38 deg
    # and does not read as a lid.
    cy = h * 0.70
    ca = rng.uniform(0.0, math.pi)
    ex = np.array([math.cos(ca), 0.0, math.sin(ca)], np.float32) * (w * 0.44)
    # 45 degrees off horizontal: still most of a plan-view crown in the aerials,
    # and never edge-on from a 1.62 m eye. A near-flat lid in a wood of two
    # thousand reads as a field of glowing horizontal slashes, which is exactly
    # what the first render of this showed.
    ez = np.array([-math.sin(ca) * 0.71, 0.71, math.cos(ca) * 0.71], np.float32) * (w * 0.44)
    up = np.array([-math.sin(ca) * -0.71, 0.71, math.cos(ca) * -0.71], np.float32)
    up = up / (np.linalg.norm(up) or 1.0)
    c0 = np.array([0.0, cy, 0.0], np.float32)
    pts = [c0 - ex - ez, c0 + ex - ez, c0 + ex + ez, c0 - ex + ez]
    # The cap maps the crown only — the bottom third of the tile is bole.
    _quad(b, pts, [(u0, v0), (u1, v0), (u1, v0 + 0.32), (u0, v0 + 0.32)], up)
    m = b.build(mat)
    return _spherify(m, centre, 0.72)


def shrub(asset_id, radius=0.9, height=1.1, leaf="leaf_oak"):
    """Scrub, a bramble, an unclipped bush in a corner nobody weeds.

    Cards over a few stems, NOT a blob. A shrub in a back yard is seen from two
    metres, and a six-segment lathe at that range reads as a faceted emerald —
    which is exactly what the first pass put in thirty back plots. The blob form
    is right for a distance tree and wrong for anything a player can walk up to.
    """
    rng = rng_for(asset_id, "shrub")
    out = M.Group()
    stems = []
    for i in range(int(rng.integers(3, 6))):
        a = (i / 3.0) * math.tau + rng.uniform(-0.5, 0.5)
        tip = np.array([math.cos(a) * radius * rng.uniform(0.3, 0.7),
                        height * rng.uniform(0.55, 0.95),
                        math.sin(a) * radius * rng.uniform(0.3, 0.7)], np.float32)
        out.add(_limb((0.0, 0.0, 0.0), tip, 0.028, 0.012, "timber_grey", 4))
        stems.append(tip)
    pts = []
    # A third of the cards for the same opacity — see `tree`. At 46 a back-yard
    # bramble cost 90 quads to look like wire netting.
    n = int(np.clip(radius * radius * height * 15, 8, 34))
    for _ in range(n):
        a = rng.uniform(0, math.tau)
        v = math.acos(rng.uniform(-1, 1))
        r = 0.55 + 0.45 * rng.random() ** 0.5
        pts.append((math.sin(v) * math.cos(a) * radius * r,
                    height * 0.62 + math.cos(v) * height * 0.42 * r,
                    math.sin(v) * math.sin(a) * radius * r))
    out.add(leaf_cards(f"{asset_id}.cards", leaf, np.array(pts, np.float32),
                       size=CARD_M * 0.72, droop=0.45,
                       centre=(0.0, height * 0.62, 0.0)))
    return out


# ---------------------------------------------------------------------------
# Boundaries — hedge, wattle, dry stone, gate
# ---------------------------------------------------------------------------

def hedge_run(asset_id, path, height=1.35, width=0.75, gaps=(), base_mat="hedge",
              sprigs="leaf_oak"):
    """A clipped hedge along a polyline, laid as a lofted mass.

    Not instanced bushes: a hedge is continuous, and the moment it is a row of
    discrete blobs it reads as a row of discrete blobs. The section is a
    trapezoid — hedges are cut battered so light reaches the bottom — and both
    the top line and the face wander, because a hand-cut hedge has no straight
    edge anywhere on it.

    `gaps` is a list of (t0, t1) in 0..1 along the run: a gateway, a gap-stopped
    stretch, the place the cows got through.
    """
    rng = rng_for(asset_id, "hedge")
    pts = [np.asarray((float(p[0]), 0.0, float(p[-1])), np.float32) for p in path]
    if len(pts) < 2:
        return M.Mesh(mat=base_mat)

    # Resample to ~0.8 m so the wander has somewhere to live.
    poly = []
    total = 0.0
    for i in range(len(pts) - 1):
        seg = float(np.linalg.norm(pts[i + 1] - pts[i]))
        total += seg
        n = max(1, int(round(seg / 0.8)))
        for k in range(n):
            poly.append(pts[i] + (pts[i + 1] - pts[i]) * (k / n))
    poly.append(pts[-1])
    if total < 0.5:
        return M.Mesh(mat=base_mat)

    b = M._Builder()
    run = 0.0
    prev = None
    tops = []
    for i, p in enumerate(poly):
        if i:
            run += float(np.linalg.norm(p - poly[i - 1]))
        t = run / total
        if any(g0 <= t <= g1 for g0, g1 in gaps):
            prev = None
            continue
        d = (poly[min(i + 1, len(poly) - 1)] - poly[max(i - 1, 0)])
        ln = float(np.linalg.norm(d)) or 1.0
        d = d / ln
        nrm = np.array([-d[2], 0.0, d[0]], np.float32)
        # Height and width wander together; ends taper so a run does not stop
        # against thin air.
        endfade = min(1.0, min(run, total - run) / 1.2)
        hh = height * (0.86 + 0.20 * math.sin(run * 0.9 + rng.uniform(0, 0.1))) * \
            (0.35 + 0.65 * endfade)
        ww = width * (0.90 + 0.18 * math.sin(run * 1.7))
        sect = [
            p + nrm * (ww * 0.55) + np.array([0, 0.02, 0], np.float32),
            p + nrm * (ww * 0.40) + np.array([0, hh * 0.72, 0], np.float32),
            p + nrm * (ww * 0.16) + np.array([0, hh, 0], np.float32),
            p - nrm * (ww * 0.16) + np.array([0, hh * 0.99, 0], np.float32),
            p - nrm * (ww * 0.40) + np.array([0, hh * 0.70, 0], np.float32),
            p - nrm * (ww * 0.55) + np.array([0, 0.02, 0], np.float32),
        ]
        if prev is not None:
            for k in range(len(sect) - 1):
                quad = [prev[k], prev[k + 1], sect[k + 1], sect[k]]
                # UVs from world XZ + height, not from run length. Running U off
                # the distance along the hedge makes the mass texture's clump
                # shadow into a set of bands perpendicular to the run, and a
                # 40 m hedge reads as corrugated curtain.
                b.poly(quad, [((q[0] + q[2]) * 0.5, q[1] * 0.5) for q in quad])
            # Cap the top ridge closed.
            cap = (prev[2], sect[2], sect[3], prev[3])
            b.poly(list(cap), [((q[0] + q[2]) * 0.5, q[1] * 0.5) for q in cap])
        prev = sect
        if hh > height * 0.5:
            tops.append((p, hh, ww))

    out = M.Group()
    m = b.build(base_mat)
    # Normals lifted toward the sky rather than spherified about a point below
    # the run: a hedge is a long object and has no centre to shade around, but
    # its top does catch the sky and its sides do not.
    if len(m.v):
        n = m.n.copy()
        n[:, 1] += 0.55
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        m.n = (n / np.where(ln < 1e-6, 1.0, ln)).astype(np.float32)
    out.add(m)

    # Sprigs breaking the clipped line. A hedge that has been cut is still a
    # hedge that has grown since, and the ragged top is the difference between
    # a hedge and an extruded green wall — which is exactly what the first
    # render of the orchard boundary showed.
    if sprigs:
        pts = []
        for p, hh, ww in tops:
            for _ in range(2):
                pts.append((p[0] + rng.uniform(-ww, ww) * 0.6,
                            hh + rng.uniform(-0.10, 0.28),
                            p[2] + rng.uniform(-ww, ww) * 0.6))
        if pts:
            out.add(leaf_cards(f"{asset_id}.sprig", sprigs,
                               np.array(pts, np.float32), size=CARD_M * 0.44,
                               droop=0.15,
                               centre=(float(np.mean([q[0] for q in pts])), -4.0,
                                       float(np.mean([q[2] for q in pts])))))
    return out


def ridge_and_furrow(asset_id, centre, u, half_u, half_v, pitch=5.5, rise=0.22,
                     mat="grass_dry"):
    """Corrugated arable: the plough ridges of one close.

    Three things at once for four triangles a metre. It gives a field a
    DIRECTION, which is what tells the eye that land is worked rather than
    mown; it gives it a second green, which is what stops the ring outside the
    wall being one flat colour; and the shadow in each furrow at a 38-degree sun
    is the only shading the open ground gets at all.

    `u` is the ploughing direction — always the long axis of the close, because
    an ox team turns as few times as it can.
    """
    rng = rng_for(asset_id, "ridgefurrow")
    u = np.asarray(u, np.float64)
    u = u / (np.linalg.norm(u) or 1.0)
    v = np.array([-u[1], u[0]])
    c = np.asarray(centre, np.float64)
    b = M._Builder()
    n = max(1, int((half_v * 2.0) / pitch))
    for i in range(n):
        off = -half_v + (i + 0.5) * (half_v * 2.0 / n)
        w = pitch * rng.uniform(0.40, 0.48)
        h = rise * rng.uniform(0.75, 1.25)
        steps = max(2, int(half_u * 2.0 / 6.0))
        prev = None
        for s in range(steps + 1):
            t = -half_u + s * (half_u * 2.0 / steps)
            # The classic reverse-S: an ox team drifts left as it approaches the
            # headland, so a ridge is never straight.
            bend = math.sin(t / max(half_u, 1e-3) * math.pi * 0.5) * pitch * 0.16
            p = c + u * t + v * (off + bend)
            sect = [p - v * w, p + np.array([0.0, 0.0]) * 0, p + v * w]
            ys = [0.0, h, 0.0]
            cur = [(sect[k], ys[k]) for k in range(3)]
            if prev is not None:
                for k in range(2):
                    quad = [
                        np.array([prev[k][0][0], prev[k][1], prev[k][0][1]], np.float32),
                        np.array([prev[k + 1][0][0], prev[k + 1][1], prev[k + 1][0][1]], np.float32),
                        np.array([cur[k + 1][0][0], cur[k + 1][1], cur[k + 1][0][1]], np.float32),
                        np.array([cur[k][0][0], cur[k][1], cur[k][0][1]], np.float32),
                    ]
                    b.poly(quad, [(q[0] * 0.17, q[2] * 0.17) for q in quad])
            prev = cur
    return b.build(mat)


def wattle_fence(asset_id, path, height=1.05, mat="timber_grey"):
    """Woven hazel hurdles: sails, zales and the twisted end stake.

    The commonest boundary in a poor quarter, and the one that most obviously
    reads as hand-made, because no two rods are the same and the whole run
    leans.
    """
    rng = rng_for(asset_id, "wattle")
    out = M.Mesh(mat=mat)
    pts = [np.asarray((float(p[0]), 0.0, float(p[-1])), np.float32) for p in path]
    for i in range(len(pts) - 1):
        a, bb = pts[i], pts[i + 1]
        d = bb - a
        ln = float(np.linalg.norm(d))
        if ln < 0.2:
            continue
        d = d / ln
        nrm = np.array([-d[2], 0.0, d[0]], np.float32)
        n_stake = max(2, int(round(ln / 0.72)))
        for s in range(n_stake + 1):
            c = a + d * (ln * s / n_stake)
            hh = height * rng.uniform(0.94, 1.10)
            st = M.cylinder(0.026, hh, 4, 0.004, mat)
            st.rotate_z(rng.uniform(-0.05, 0.05))
            st.translate(c[0], 0.0, c[2])
            out.merge(st)
        # Woven rods: each course crosses the stakes on alternate sides, which
        # is the whole visual of a hurdle. Course spacing and the zig-zag step
        # are the two numbers that decide whether a boundary fence costs 100 or
        # 200 triangles a metre, and a town has hundreds of metres of it.
        n_rod = max(2, int(height / 0.18))
        for r in range(n_rod):
            y = 0.07 + r * (height * 0.88 / n_rod)
            side = 1 if r % 2 else -1
            steps = max(2, int(ln / 0.7))
            for k in range(steps):
                t0, t1 = k / steps, (k + 1) / steps
                c0 = a + d * (ln * t0) + nrm * (side * 0.022)
                c1 = a + d * (ln * t1) + nrm * (-side * 0.022)
                rod = _limb((c0[0], y + rng.uniform(-0.006, 0.006), c0[2]),
                            (c1[0], y + rng.uniform(-0.006, 0.006), c1[2]),
                            0.016, 0.014, mat, segments=3)
                out.merge(rod)
                side = -side
    return out


def dry_stone_wall(asset_id, path, height=1.05, width=0.52, mat="rubble"):
    """A battered body under a coping course set on edge.

    The coping is the identifying feature and the reason a dry stone wall reads
    at 40 m: a saw-tooth line along the top that no other boundary in the town
    has. It is therefore the only part built as individual stones.

    The body below is a lofted prism with the `rubble` set on it, NOT a stack of
    boxes. Modelling every stone measured 550 triangles a metre, and Hearthmere
    has several hundred metres of walling — that one decision would have cost
    more triangles than every building inside the wall put together, to be
    indistinguishable past four metres.
    """
    rng = rng_for(asset_id, "drystone")
    out = M.Mesh(mat=mat)
    pts = [np.asarray((float(p[0]), 0.0, float(p[-1])), np.float32) for p in path]
    b = M._Builder()
    for i in range(len(pts) - 1):
        a, bb = pts[i], pts[i + 1]
        d = bb - a
        ln = float(np.linalg.norm(d))
        if ln < 0.25:
            continue
        d = d / ln
        nrm = np.array([-d[2], 0.0, d[0]], np.float32)
        yaw = float(math.atan2(d[0], d[2]))
        steps = max(1, int(ln / 1.4))
        top = height - 0.17
        prev = None
        for k in range(steps + 1):
            c0 = a + d * (ln * k / steps)
            wob = rng.uniform(-0.03, 0.03)
            sect = [
                c0 + nrm * (width * 0.5) + np.array([0, 0.0, 0], np.float32),
                c0 + nrm * (width * 0.40) + np.array([0, top + wob, 0], np.float32),
                c0 - nrm * (width * 0.40) + np.array([0, top + wob, 0], np.float32),
                c0 - nrm * (width * 0.5) + np.array([0, 0.0, 0], np.float32),
            ]
            if prev is not None:
                for j in range(3):
                    quad = [prev[j], prev[j + 1], sect[j + 1], sect[j]]
                    b.poly(quad, [(q[0] * 0.5 + q[2] * 0.5, q[1] * 0.5) for q in quad])
            prev = sect
        # Coping: flat stones stood on edge and leaned, alternately.
        n = max(1, int(ln / 0.40))
        for k in range(n):
            t = (k + 0.5) / n
            c0 = a + d * (ln * t)
            s = M.box(0.155, 0.26 * rng.uniform(0.85, 1.15), width * 0.78, 0.016,
                      mat)
            s.rotate_y(yaw)
            s.rotate_x(rng.uniform(-0.18, 0.18))
            s.translate(c0[0], top + 0.09, c0[2])
            out.merge(s)
    out.merge(b.build(mat))
    return out


def field_gate(asset_id, width=2.9, height=1.25, mat="timber_grey"):
    """A five-bar gate hung on a heel post, sagging on its bottom hinge.

    Origin at the heel post's foot; the gate hangs toward +X.
    """
    rng = rng_for(asset_id, "gate")
    out = M.Group()
    for x, hh in ((0.0, height + 0.55), (width, height + 0.42)):
        post = M.box(0.15, hh, 0.15, 0.012, "oak_weathered")
        post.rotate_y(rng.uniform(-0.03, 0.03))
        post.translate(x, hh * 0.5, 0.0)
        out.add(post)
    sag = 0.06
    for i in range(5):
        y = 0.16 + i * (height - 0.16) / 4.0
        bar = M.plank(width - 0.20, 0.075, 0.032, 0.005, mat)
        bar.rotate_z(-sag * 0.10)
        bar.translate(width * 0.5, y - sag * (i / 4.0), 0.0)
        out.add(bar)
    # Diagonal brace, hanging stile and head — the bit that stops it being a
    # ladder lying on its side.
    brace = M.plank(float(np.hypot(width - 0.24, height - 0.20)), 0.07, 0.03, 0.005, mat)
    brace.rotate_z(float(math.atan2(height - 0.20, width - 0.24)))
    brace.translate(width * 0.5, height * 0.5, 0.0)
    out.add(brace)
    for x in (0.14, width - 0.14, width * 0.52):
        stile = M.plank(height + 0.02, 0.075, 0.03, 0.005, mat)
        stile.rotate_z(math.pi * 0.5)
        stile.translate(x, height * 0.52, 0.0)
        out.add(stile)
    for y in (0.24, height - 0.10):
        strap = M.box(0.30, 0.035, 0.022, 0.004, "iron")
        strap.translate(0.16, y, 0.055)
        out.add(strap)
    return out


def stile(asset_id, mat="oak_weathered"):
    """Two steps and a rail over a wall — a footpath crossing a boundary."""
    out = M.Group()
    for i, (h, w) in enumerate(((0.34, 0.62), (0.70, 0.52))):
        tread = M.plank(w, 0.30, 0.06, 0.006, mat)
        tread.translate(0.0, h, -0.16 + i * 0.32)
        out.add(tread)
        for sx in (-1, 1):
            leg = M.box(0.09, h, 0.09, 0.008, mat)
            leg.translate(sx * w * 0.38, h * 0.5, -0.16 + i * 0.32)
            out.add(leg)
    rail = M.cylinder(0.032, 1.15, 6, 0.005, mat)
    rail.translate(0.0, 0.0, 0.24)
    out.add(rail)
    return out


# ---------------------------------------------------------------------------
# The kitchen garden
# ---------------------------------------------------------------------------

def dug_bed(asset_id, width, depth, mat="earth", ridges=True):
    """A worked bed: turned earth, proud of the path, ridged along its length.

    A garden without beds is a lawn with vegetables standing in it. The bed IS
    the read, and it costs eight triangles.
    """
    rng = rng_for(asset_id, "bed")
    out = M.Mesh(mat=mat)
    slab = M.box(width, 0.13, depth, 0.03, mat)
    slab.translate(0, 0.065, 0)
    out.merge(slab)
    if ridges:
        n = max(1, int(width / 0.42))
        for i in range(n):
            x = -width * 0.5 + (i + 0.5) * (width / n)
            r = M.box(width / n * 0.72, 0.075, depth * rng.uniform(0.94, 1.0), 0.02,
                      mat)
            r.translate(x + rng.uniform(-0.02, 0.02), 0.15, rng.uniform(-0.05, 0.05))
            out.merge(r)
    return out


def crop_row(asset_id, length, kind="cabbage", spacing=0.42, mat="foliage"):
    """A row of one crop at ITS OWN real spacing, along local +X.

    Spacing is the whole point: cabbages at 450 mm, leeks at 150 mm, beans at
    200 mm up poles. Planting everything on one grid is what makes a procedural
    garden read as a chessboard.
    """
    rng = rng_for(asset_id, "crop", kind)
    out = M.Group()
    n = max(1, int(length / spacing))
    for i in range(n):
        x = -length * 0.5 + (i + 0.5) * spacing + rng.uniform(-0.03, 0.03)
        z = rng.uniform(-0.05, 0.05)
        if rng.random() < 0.07:
            continue                      # a gap where one failed. Always some.
        if kind == "cabbage":
            r = rng.uniform(0.13, 0.20)
            head = M.lathe([(r * 0.30, 0.0), (r, r * 0.55), (r * 0.72, r * 1.15),
                            (0.0, r * 1.30)], 7, mat)
            head.translate(x, 0.02, z)
            out.add(head)
            out.add(K.leaf_cluster(f"{asset_id}.{i}", radius=r * 0.95, count=4,
                                   mat=mat, droop=0.85).translate(x, 0.01, z))
        elif kind == "leek":
            c = K.leaf_cluster(f"{asset_id}.{i}", radius=0.055, count=5, mat=mat,
                               droop=0.14)
            c.scale(1.0, rng.uniform(1.5, 2.3), 1.0)
            c.translate(x, 0.03, z)
            out.add(c)
        elif kind == "herb":
            c = K.leaf_cluster(f"{asset_id}.{i}", radius=rng.uniform(0.07, 0.11),
                               count=6, mat="foliage_flower", droop=0.55)
            c.translate(x, 0.02, z)
            out.add(c)
        else:                              # root crop: tops only, as it should be
            c = K.leaf_cluster(f"{asset_id}.{i}", radius=rng.uniform(0.08, 0.13),
                               count=7, mat=mat, droop=0.75)
            c.translate(x, 0.02, z)
            out.add(c)
    return out


def bean_poles(asset_id, length, height=2.1, spacing=0.55, mat="timber_grey"):
    """A double row of hazel rods crossed and tied, with the crop climbing it.

    The tallest thing in a kitchen garden and the one that gives a flat plot a
    silhouette, which is why every garden here gets one.
    """
    rng = rng_for(asset_id, "beans")
    out = M.Group()
    n = max(2, int(length / spacing))
    ridge = []
    for i in range(n):
        x = -length * 0.5 + (i + 0.5) * spacing
        h = height * rng.uniform(0.92, 1.06)
        top = np.array([x + rng.uniform(-0.04, 0.04), h * 0.94, 0.0], np.float32)
        ridge.append(top)
        for side in (-1, 1):
            foot = np.array([x + rng.uniform(-0.04, 0.04), 0.0,
                             side * 0.42 * rng.uniform(0.9, 1.1)], np.float32)
            out.add(_limb(foot, top + np.array([0, h * 0.06, 0], np.float32),
                          0.019, 0.010, mat, segments=4))
            # The crop: cards climbing the rod.
            pts = np.array([foot + (top - foot) * t + np.array(
                [rng.uniform(-0.09, 0.09), 0.0, rng.uniform(-0.09, 0.09)], np.float32)
                for t in np.linspace(0.12, 0.98, 4)], np.float32)
            # 0.20 m across a whole 4x4 sheet put a bean leaf at 12 mm. A card
            # sizes the LEAF, not the plant.
            out.add(leaf_cards(f"{asset_id}.{i}.{side}", "leaf_apple", pts,
                               size=0.46, droop=0.55, centre=(x, h * 0.5, 0.0),
                               depth_shade=0.22))
    # The ridge rod tying every pair together.
    for i in range(len(ridge) - 1):
        out.add(_limb(ridge[i], ridge[i + 1], 0.014, 0.014, mat, segments=4))
    return out


def cloche(asset_id, mat="straw"):
    """A woven straw forcing cloche over early seedlings.

    Glass bell cloches are the obvious choice and are wrong here: blown glass at
    that size is a 17th-century industry. A straw cloche is what a pre-industrial
    gardener actually used, and it reads better anyway.
    """
    rng = rng_for(asset_id, "cloche")
    r = rng.uniform(0.20, 0.27)
    h = r * rng.uniform(1.5, 1.9)
    m = M.lathe([(r, 0.0), (r * 0.98, h * 0.42), (r * 0.72, h * 0.78),
                 (r * 0.30, h * 0.96), (0.0, h)], 9, mat, close_bottom=False)
    m.rotate_y(rng.uniform(0, math.tau))
    return m


def scarecrow(asset_id):
    """Two poles, a sack head, a coat and a hat. Residue at its cheapest."""
    rng = rng_for(asset_id, "scarecrow")
    out = M.Group()
    post = M.cylinder(0.038, 1.72, 6, 0.006, "timber_grey")
    post.rotate_z(rng.uniform(-0.06, 0.06))
    out.add(post)
    arm = M.cylinder(0.030, 1.26, 6, 0.006, "timber_grey")
    arm.rotate_z(math.pi * 0.5)
    arm.rotate_x(rng.uniform(-0.1, 0.1))
    arm.translate(0.63, 1.26, 0.0)
    out.add(arm)
    # Coat: a slack sheet over the crosspiece, gathered at the waist.
    coat = M.box(1.04, 0.72, 0.16, 0.02, "cloth_brown")
    coat.rotate_z(rng.uniform(-0.05, 0.05))
    coat.translate(0.0, 0.94, 0.0)
    out.add(coat)
    for sx in (-1, 1):
        sleeve = M.box(0.30, 0.16, 0.14, 0.015, "cloth_brown")
        sleeve.translate(sx * 0.50, 1.22, 0.0)
        out.add(sleeve)
    head = M.lathe([(0.0, 0.0), (0.13, 0.06), (0.14, 0.20), (0.06, 0.27)], 9, "sacking")
    head.translate(0.0, 1.30, 0.0)
    out.add(head)
    hat = M.lathe([(0.28, 0.0), (0.26, 0.03), (0.12, 0.05), (0.115, 0.16),
                   (0.0, 0.19)], 10, "straw")
    hat.rotate_x(rng.uniform(0.10, 0.28))
    hat.translate(0.0, 1.52, 0.0)
    out.add(hat)
    return out


def compost_heap(asset_id, radius=0.95):
    """A muck heap, half rotted down, with a fork left in it."""
    rng = rng_for(asset_id, "compost")
    out = M.Group()
    h = radius * rng.uniform(0.55, 0.78)
    heap = M.lathe([(radius, 0.0), (radius * 0.92, h * 0.45),
                    (radius * 0.55, h * 0.85), (0.0, h)], 9, "yard")
    heap.scale(1.0, 1.0, rng.uniform(0.75, 1.05))
    out.add(heap)
    straw = M.lathe([(radius * 0.72, h * 0.40), (radius * 0.42, h * 0.88),
                     (0.0, h * 1.04)], 8, "straw", close_bottom=False)
    out.add(straw)
    fork = M.cylinder(0.022, 1.3, 5, 0.004, "timber_grey")
    fork.rotate_x(rng.uniform(0.25, 0.45))
    fork.translate(radius * 0.35, h * 0.7, radius * 0.1)
    out.add(fork)
    return out


def beehive(asset_id):
    """A coiled straw skep on a stone. Every walled garden in the plan has one."""
    rng = rng_for(asset_id, "skep")
    out = M.Group()
    stone = M.box(0.46, 0.11, 0.46, 0.02, "rubble")
    stone.translate(0, 0.055, 0)
    out.add(stone)
    skep = M.lathe([(0.30, 0.11), (0.31, 0.20), (0.29, 0.36), (0.20, 0.50),
                    (0.0, 0.56)], 11, "straw")
    skep.rotate_y(rng.uniform(0, math.tau))
    out.add(skep)
    return out


# ---------------------------------------------------------------------------
# The churchyard
# ---------------------------------------------------------------------------

def grave_marker(asset_id, kind=None, mat="sandstone"):
    """A headstone, carved and never lettered (Art Bible §2).

    Four forms, because a churchyard where every stone is the same slab is a
    prop. The carving is a sunk roundel, a wheel head or an incised cross — all
    pictorial, all period, none of them readable text.
    """
    rng = rng_for(asset_id, "grave")
    kind = kind or ["slab", "wheel", "coped", "post"][int(rng.integers(0, 4))]
    out = M.Mesh(mat=mat)
    if kind == "wheel":
        h = rng.uniform(0.62, 0.92)
        shaft = M.box(0.30, h, 0.11, 0.02, mat)
        shaft.translate(0, h * 0.5, 0)
        out.merge(shaft)
        head = M.lathe([(0.0, 0.0), (0.24, 0.012), (0.24, 0.10), (0.0, 0.11)], 12, mat)
        head.rotate_x(math.pi * 0.5)
        head.translate(0, h + 0.16, 0)
        out.merge(head)
        boss = M.lathe([(0.07, 0.0), (0.05, 0.05)], 8, mat)
        boss.rotate_x(math.pi * 0.5)
        boss.translate(0, h + 0.16, -0.06)
        out.merge(boss)
    elif kind == "coped":
        # A body stone: a low ridged slab over the grave itself.
        L = rng.uniform(1.5, 1.95)
        body = M.prism([(-0.30, 0.0), (0.30, 0.0), (0.22, 0.20), (0.0, 0.32),
                        (-0.22, 0.20)], L, chamfer=0.0)
        body.rotate_y(math.pi * 0.5)
        out.merge(body.with_material(mat))
    elif kind == "post":
        h = rng.uniform(0.45, 0.68)
        p = M.box(0.16, h, 0.16, 0.025, mat)
        p.translate(0, h * 0.5, 0)
        out.merge(p)
        cap = M.lathe([(0.11, 0.0), (0.10, 0.05), (0.0, 0.11)], 8, mat)
        cap.translate(0, h, 0)
        out.merge(cap)
    else:
        w = rng.uniform(0.42, 0.62)
        h = rng.uniform(0.55, 1.05)
        slab = M.box(w, h, 0.09, 0.022, mat)
        slab.translate(0, h * 0.5, 0)
        out.merge(slab)
        # Round-headed, with a sunk roundel.
        head = M.lathe([(0.0, 0.0), (w * 0.5, 0.012), (w * 0.5, 0.085), (0.0, 0.09)],
                       11, mat)
        head.rotate_x(math.pi * 0.5)
        head.translate(0, h, 0)
        out.merge(head)
        ring = M.lathe([(w * 0.20, 0.0), (w * 0.26, 0.006), (w * 0.26, 0.02),
                        (w * 0.20, 0.024)], 12, mat)
        ring.rotate_x(math.pi * 0.5)
        ring.translate(0, h * 0.72, -0.048)
        out.merge(ring)
    # Every stone in a real churchyard has settled. This is the read from 20 m.
    out.rotate_x(rng.uniform(-0.16, 0.16))
    out.rotate_z(rng.uniform(-0.13, 0.13))
    out.rotate_y(rng.uniform(0, 0.35))
    return out


def lych_gate(asset_id, span=2.2, depth=2.4, post_h=2.05):
    """The roofed gate a coffin waits under. Oak, half-hipped, a coffin stool.

    The churchyard's anchor: the one piece of architecture on a boundary, and
    the thing that tells the player the ground beyond it is different.
    """
    rng = rng_for(asset_id, "lych")
    out = M.Group()
    for sx in (-1, 1):
        for sz in (-1, 1):
            post = M.box(0.17, post_h, 0.17, 0.015, "oak_dark")
            post.rotate_y(rng.uniform(-0.02, 0.02))
            post.translate(sx * span * 0.5, post_h * 0.5, sz * depth * 0.5)
            out.add(post)
            # Sill stone under each post — oak never touches the ground here.
            s = M.box(0.30, 0.16, 0.30, 0.02, "rubble")
            s.translate(sx * span * 0.5, 0.08, sz * depth * 0.5)
            out.add(s)
    for sz in (-1, 1):
        tie = M.plank(span + 0.34, 0.16, 0.14, 0.008, "oak_dark")
        tie.translate(0, post_h + 0.07, sz * depth * 0.5)
        out.add(tie)
        # Braces, which is what stops it racking and what makes it read as oak.
        for sx in (-1, 1):
            br = M.plank(0.62, 0.10, 0.09, 0.006, "oak_dark")
            br.rotate_z(sx * math.pi * 0.25)
            br.translate(sx * (span * 0.5 - 0.22), post_h - 0.22, sz * depth * 0.5)
            out.add(br)
    roof = K.gable_roof(span + 0.5, depth + 0.5, f"{asset_id}.roof", pitch=1.05,
                        overhang=0.36, tile_mat="terracotta", timber_mat="oak_dark")
    roof.rotate_y(math.pi * 0.5)
    roof.translate(0, post_h + 0.14, 0)
    out.add(roof)
    # The coffin stool the gate exists for.
    stool = M.box(1.85, 0.13, 0.44, 0.012, "oak_weathered")
    stool.rotate_y(math.pi * 0.5)
    stool.translate(span * 0.5 - 0.28, 0.56, 0)
    out.add(stool)
    for sz in (-1, 1):
        leg = M.box(0.11, 0.50, 0.11, 0.008, "oak_weathered")
        leg.translate(span * 0.5 - 0.28, 0.25, sz * 0.68)
        out.add(leg)
    return out


# ---------------------------------------------------------------------------
# Water margin
# ---------------------------------------------------------------------------

def reed_tuft(asset_id, height=1.5, blades=9, mat="reed"):
    """A stand of reed: tall tapered blades with a seed head on some.

    Instanced by the thousand along the Emberflow, so it is deliberately eight
    triangles a blade and nothing else.
    """
    rng = rng_for(asset_id, "reed")
    out = M.Mesh(mat=mat)
    for i in range(blades):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.0, 0.13)
        h = height * rng.uniform(0.55, 1.15)
        w = rng.uniform(0.012, 0.024)
        lean = rng.uniform(0.06, 0.30)
        blade = M.prism([(-w, 0.0), (w, 0.0), (w * 0.75, h * 0.55),
                         (0.0, h)], 0.004, chamfer=0.0)
        blade.rotate_x(lean * math.cos(a))
        blade.rotate_z(-lean * math.sin(a))
        blade.rotate_y(a)
        blade.translate(math.cos(a) * r, 0.0, math.sin(a) * r)
        out.merge(blade.with_material(mat))
        if rng.random() < 0.30:
            head = M.lathe([(0.0, 0.0), (0.016, 0.03), (0.016, 0.14), (0.0, 0.17)],
                           6, mat)
            head.translate(math.cos(a) * (r + lean * h * 0.5), h * 0.97,
                           math.sin(a) * (r + lean * h * 0.5))
            out.merge(head)
    return out


def tussock(asset_id, radius=0.30, height=0.42, mat="weeds", blades=11,
            blade_w=0.011):
    """A grass tussock: the thing that makes turf stop being a texture.

    Used for meadow, verge, the untrodden joints of paving, and the long grass
    under an orchard. Cheap enough to instance in the thousands.

    `blade_w` is in METRES and is fixed, not a fraction of the tussock radius.
    A grass blade is 5-12 mm wide whatever the clump is; deriving the width from
    the radius made the orchard's long grass 80 mm across, which renders as a
    field of leeks and was the first thing wrong with that shot.
    """
    rng = rng_for(asset_id, "tussock")
    out = M.Mesh(mat=mat)
    for i in range(blades):
        a = rng.uniform(0, math.tau)
        h = height * rng.uniform(0.5, 1.25)
        w = blade_w * rng.uniform(0.7, 1.5)
        droop = rng.uniform(0.35, 1.05)
        blade = M.prism([(-w, 0.0), (w, 0.0), (w * 0.55, h * 0.6), (0.0, h)],
                        0.004, chamfer=0.0)
        blade.rotate_x(droop * 0.6)
        blade.rotate_y(a)
        blade.translate(math.cos(a) * radius * 0.25, 0.0, math.sin(a) * radius * 0.25)
        out.merge(blade.with_material(mat))
    return out


def willow_pollard(asset_id, height=4.6):
    """A pollarded willow: a fat stump and a burst of one-year rods.

    Every willow at a working watercourse is cut for withies, so a naturally
    grown weeping willow is the wrong tree here. The pollard head is also a far
    better silhouette.
    """
    rng = rng_for(asset_id, "pollard")
    out = M.Group()
    h = height * rng.uniform(0.7, 1.05)
    bole_h = h * 0.46
    bole, top, _ = _trunk(f"{asset_id}.bole", bole_h, h * 0.075, h * 0.062,
                          "timber_grey", bend=0.13, flare=1.9)
    out.add(bole)
    knuckle = M.lathe([(h * 0.062, 0.0), (h * 0.105, h * 0.05),
                       (h * 0.10, h * 0.11), (h * 0.05, h * 0.14)], 9, "timber_grey")
    knuckle.translate(top[0], bole_h, top[2])
    out.add(knuckle)
    rods = []
    for i in range(9):
        a = (i / 9) * math.tau + rng.uniform(-0.3, 0.3)
        reach = h * rng.uniform(0.16, 0.30)
        tip = np.array([top[0] + math.cos(a) * reach, bole_h + h * rng.uniform(0.34, 0.56),
                        top[2] + math.sin(a) * reach], np.float32)
        out.add(_limb((top[0], bole_h + h * 0.10, top[2]), tip,
                      h * 0.016, h * 0.006, "timber_grey", 4))
        rods.append(tip)
    # A pollard head is a dense mop, not nine leaves on a stick. Eighty-one
    # cards read as confetti round bare rods in the first meadow render.
    pts = []
    for t in rods:
        for _ in range(9):
            pts.append(t + np.array([rng.uniform(-0.8, 0.8), rng.uniform(-1.3, 0.4),
                                     rng.uniform(-0.8, 0.8)], np.float32))
    out.add(leaf_cards(f"{asset_id}.withy", "leaf_willow", np.array(pts, np.float32),
                       size=CARD_M * 1.3, droop=0.95,
                       centre=(top[0], bole_h + h * 0.42, top[2])))
    return out


# ---------------------------------------------------------------------------
# Attached to buildings and paving
# ---------------------------------------------------------------------------

def ivy_panel(asset_id, width, height, mat="ivy", ragged=0.35):
    """A sheet of ivy clinging to a wall, in the wall's own local +Z face.

    The cheapest "this building is old" signal there is: one quad grid, standing
    2 cm off the wall, with a ragged upper edge so it does not read as wallpaper
    cut to size.
    """
    rng = rng_for(asset_id, "ivy")
    b = M._Builder()
    nx = max(2, int(width / 0.55))
    ny = max(2, int(height / 0.55))
    for i in range(nx):
        for j in range(ny):
            u0, u1 = i / nx, (i + 1) / nx
            v0, v1 = j / ny, (j + 1) / ny
            # Ragged top: the coverage thins toward the head of the wall.
            cover = 1.0 - (v1 ** 1.5) * ragged * rng.uniform(0.6, 1.6)
            if rng.random() > cover:
                continue
            x0, x1 = (u0 - 0.5) * width, (u1 - 0.5) * width
            y0, y1 = v0 * height, v1 * height
            z = 0.02 + rng.uniform(0.0, 0.05)
            pts = [(x0, y0, z), (x1, y0, z), (x1, y1, z + 0.02), (x0, y1, z + 0.02)]
            uvs = [(x0 * 0.5, y0 * 0.5), (x1 * 0.5, y0 * 0.5),
                   (x1 * 0.5, y1 * 0.5), (x0 * 0.5, y1 * 0.5)]
            _quad(b, pts, uvs, np.array([0, 0, 1], np.float32))
    m = b.build(mat)
    # Bow the normals outward from the wall plane so a flat sheet still catches
    # a rolling highlight instead of one uniform value.
    if len(m.v):
        n = m.n.copy()
        n[:, 0] += np.clip(m.v[:, 0] / max(width, 0.1), -1, 1) * 0.45
        n[:, 1] += 0.25
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        m.n = (n / np.where(ln < 1e-6, 1.0, ln)).astype(np.float32)
    return m


def window_box(asset_id, width=0.86):
    """A planted window box: a boarded trough with real plants in it.

    Art Bible §7 lists a window box under "vertical interest every 8-10 m", and
    it is the single cheapest thing that makes a plaster wall look lived in.
    """
    rng = rng_for(asset_id, "wbox")
    out = M.Group()
    trough = M.box(width, 0.17, 0.20, 0.008, "timber_grey")
    trough.translate(0, 0.085, 0)
    out.add(trough)
    for sx in (-1, 1):
        brk = M.box(0.05, 0.17, 0.16, 0.006, "iron")
        brk.rotate_z(sx * 0.22)
        brk.translate(sx * width * 0.42, 0.02, -0.09)
        out.add(brk)
    soil = M.box(width - 0.06, 0.03, 0.16, 0.004, "earth")
    soil.translate(0, 0.165, 0)
    out.add(soil)
    out.add(K.planter_plants(f"{asset_id}.p", width - 0.10,
                             count=int(rng.integers(4, 7)),
                             mat="foliage_flower", height=0.17))
    return out


def wall_moss(asset_id, width, height, mat="moss"):
    """Moss where nobody walks: a wall's shaded foot, a north face, a step nose.

    Art Bible §7's rule, made geometry — "worn smooth where everyone walks,
    mossy where nobody does". Emitted as a thin skin so it has silhouette at a
    grazing angle rather than being a decal.
    """
    rng = rng_for(asset_id, "wallmoss")
    b = M._Builder()
    n = max(1, int(width / 0.5))
    for i in range(n):
        if rng.random() < 0.3:
            continue
        x0 = -width * 0.5 + i * (width / n)
        x1 = x0 + (width / n) * rng.uniform(0.7, 1.0)
        h = height * rng.uniform(0.35, 1.0)
        z = 0.012
        pts = [(x0, 0.0, z), (x1, 0.0, z), (x1, h, z * 0.6), (x0, h, z * 0.6)]
        b.poly(pts, [(p[0] * 0.5, p[1] * 0.5) for p in pts],
               np.array([0, 0.35, 0.94], np.float32))
    return b.build(mat)


def joint_weeds(asset_id, count=6, mat="weeds"):
    """The weeds in a paving joint. Prototype for instancing — five triangles."""
    rng = rng_for(asset_id, "weeds")
    out = M.Mesh(mat=mat)
    for i in range(max(2, count)):
        a = rng.uniform(0, math.tau)
        h = rng.uniform(0.05, 0.15)
        w = rng.uniform(0.010, 0.022)
        blade = M.prism([(-w, 0.0), (w, 0.0), (0.0, h)], 0.003, chamfer=0.0)
        blade.rotate_x(rng.uniform(0.3, 1.0))
        blade.rotate_y(a)
        blade.translate(math.cos(a) * 0.03, 0.0, math.sin(a) * 0.03)
        out.merge(blade.with_material(mat))
    return out


# ---------------------------------------------------------------------------
# The road out
# ---------------------------------------------------------------------------

def milestone(asset_id, mat="sandstone"):
    """A wayside stone with a cut hand pointing, never a legend.

    Art Bible §2 forbids readable lettering, which is also why a real early
    milestone is a pointing hand and a notch count.
    """
    rng = rng_for(asset_id, "milestone")
    out = M.Mesh(mat=mat)
    h = rng.uniform(0.78, 0.95)
    body = M.box(0.34, h, 0.20, 0.028, mat)
    body.translate(0, h * 0.5, 0)
    out.merge(body)
    cap = M.lathe([(0.0, 0.0), (0.17, 0.014), (0.17, 0.06), (0.0, 0.07)], 10, mat)
    cap.rotate_x(math.pi * 0.5)
    cap.translate(0, h, 0)
    out.merge(cap)
    # The cut hand: a sunk palm and a finger.
    palm = M.box(0.10, 0.08, 0.02, 0.006, mat)
    palm.translate(-0.02, h * 0.62, -0.10)
    out.merge(palm)
    finger = M.box(0.11, 0.028, 0.018, 0.005, mat)
    finger.translate(0.08, h * 0.62, -0.10)
    out.merge(finger)
    for i in range(int(rng.integers(2, 5))):
        notch = M.box(0.055, 0.018, 0.016, 0.004, mat)
        notch.translate(-0.06 + i * 0.045, h * 0.38, -0.10)
        out.merge(notch)
    out.rotate_y(rng.uniform(-0.25, 0.25))
    return out


def wayside_shrine(asset_id):
    """A niche shrine on the approach road: stone base, hood, a light in it.

    Every road into a town in this world has one, and it does the same job as a
    waymarker plus the job Art Bible §7 calls "every street must terminate in
    something worth walking toward".
    """
    rng = rng_for(asset_id, "shrine")
    out = M.Group()
    for i, (w, y, h) in enumerate(((1.15, 0.0, 0.26), (0.95, 0.26, 0.20))):
        step = M.box(w, h, w * 0.85, 0.025, "rubble")
        step.translate(0, y + h * 0.5, 0)
        out.add(step)
    shaft = M.box(0.62, 1.30, 0.52, 0.03, "sandstone")
    shaft.translate(0, 0.46 + 0.65, 0)
    out.add(shaft)
    # The niche: a recess and the back of it, so it reads hollow.
    back = M.box(0.36, 0.52, 0.06, 0.012, "sandstone", uv_scale=MATS.uv_detail("sandstone", 1, why="0.52 m member; the library's 2 m tile shows 26% of one tile here and reads as flat colour"))
    back.translate(0, 1.42, 0.20)
    out.add(back)
    for sx in (-1, 1):
        jamb = M.box(0.11, 0.56, 0.30, 0.012, "sandstone", uv_scale=MATS.uv_detail("sandstone", 1, why="0.56 m member; the library's 2 m tile shows 28% of one tile here and reads as flat colour"))
        jamb.translate(sx * 0.24, 1.42, -0.09)
        out.add(jamb)
    hood = M.prism([(-0.40, 0.0), (0.40, 0.0), (0.0, 0.34)], 0.60, chamfer=0.02)
    hood.translate(0, 1.72, 0.0)
    out.add(hood.with_material("sandstone"))
    lamp = K.lantern(f"{asset_id}.lamp", scale=0.75)
    lamp.translate(0, 1.26, -0.02)
    out.add(lamp)
    # Offerings: somebody left flowers, and somebody else left them a while ago.
    for i in range(3):
        c = K.leaf_cluster(f"{asset_id}.off.{i}", radius=0.07, count=5,
                           mat="foliage_flower", droop=0.8)
        c.translate(rng.uniform(-0.30, 0.30), 0.46, rng.uniform(-0.34, -0.18))
        out.add(c)
    return out


def verge_ditch(asset_id, path, width=1.1, depth=0.30, mat="grass_lush"):
    """The ditch and bank that edges every made road out of a town.

    Two triangles per metre, and it is what stops the road/field junction being
    a straight painted line — which is the single most artificial thing in an
    aerial of a procedural landscape.
    """
    rng = rng_for(asset_id, "verge")
    b = M._Builder()
    pts = [np.asarray((float(p[0]), 0.0, float(p[-1])), np.float32) for p in path]
    for i in range(len(pts) - 1):
        a, bb = pts[i], pts[i + 1]
        d = bb - a
        ln = float(np.linalg.norm(d))
        if ln < 0.5:
            continue
        d = d / ln
        nrm = np.array([-d[2], 0.0, d[0]], np.float32)
        steps = max(1, int(ln / 2.5))
        for k in range(steps):
            for side in (-1, 1):
                p0 = a + d * (ln * k / steps)
                p1 = a + d * (ln * (k + 1) / steps)
                o0 = width * rng.uniform(0.85, 1.15)
                prof = [(0.0, 0.02), (o0 * 0.45, -depth), (o0, 0.06), (o0 * 1.35, 0.0)]
                for j in range(len(prof) - 1):
                    (d0, y0), (d1, y1) = prof[j], prof[j + 1]
                    q = [p0 + nrm * (side * d0) + np.array([0, y0, 0], np.float32),
                         p1 + nrm * (side * d0) + np.array([0, y0, 0], np.float32),
                         p1 + nrm * (side * d1) + np.array([0, y1, 0], np.float32),
                         p0 + nrm * (side * d1) + np.array([0, y1, 0], np.float32)]
                    if side < 0:
                        q.reverse()
                    b.poly(q, [(v[0] * 0.17, v[2] * 0.17) for v in q])
    return b.build(mat)
