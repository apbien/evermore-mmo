"""Procedural PBR material generation.

Art Bible §5: every material ships albedo + roughness + metalness + normal + AO,
and roughness must vary from at least two noise scales. A surface with uniform
roughness reads as painted cardboard under any lighting, and it is the single
most common reason procedural art looks like a prototype.

Every builder here also applies *wear logic* — where water runs, where hands
touch, where the ground splashes. Wear that is physically motivated reads as
real; wear scattered as generic noise reads as dirt-overlay filter.
"""

from __future__ import annotations

import os
import numpy as np
from PIL import Image

from . import palette as P
from .mathx import fbm, worley, ridged, normalize01, smoothstep, gradient_v, seed_from


class MaterialSet:
    """A complete PBR channel set, written as PNGs."""

    def __init__(self, name, size=1024):
        self.name = name
        self.size = size
        s = (size, size)
        self.albedo = np.ones(s + (3,), np.float32) * 0.5
        self.roughness = np.ones(s, np.float32) * 0.8
        self.metalness = np.zeros(s, np.float32)
        self.normal = None          # derived from height at write time
        self.height = np.zeros(s, np.float32)
        self.ao = np.ones(s, np.float32)
        self.emissive = None

    # -- channel helpers ----------------------------------------------------

    def set_base(self, hex_color):
        self.albedo[:] = P.rgb(hex_color)
        return self

    def tint(self, hex_color, mask):
        """Blend a colour in using a 0..1 mask."""
        m = np.clip(mask, 0, 1)[..., None]
        self.albedo = self.albedo * (1 - m) + P.rgb(hex_color) * m
        return self

    def darken(self, mask, amount=0.4):
        m = np.clip(mask, 0, 1)[..., None] * amount
        self.albedo *= (1.0 - m)
        return self

    def lighten(self, mask, amount=0.3):
        m = np.clip(mask, 0, 1)[..., None] * amount
        self.albedo = self.albedo + (1.0 - self.albedo) * m
        return self

    def rough(self, base, broad_amp=0.12, fine_amp=0.06, seed=0, broad_freq=3, fine_freq=28):
        """Roughness with the two mandated noise scales.

        Broad (0.5-2m) reads as weathering and dampness; fine (1-5cm) reads as
        surface microstructure. Together they break up specular so highlights
        travel across a surface instead of sitting on it as a uniform sheen.
        """
        s = (self.size, self.size)
        broad = fbm(s, broad_freq, seed + 11, octaves=4)
        fine = fbm(s, fine_freq, seed + 29, octaves=3)
        self.roughness = np.clip(base + broad * broad_amp + fine * fine_amp, 0.03, 1.0)
        return self

    def add_height(self, h, amp=1.0):
        self.height = self.height + h * amp
        return self

    # -- wear logic ---------------------------------------------------------

    def ground_splash(self, height_m, splash_m=0.15, seed=0):
        """Dirt on the bottom 15cm of a wall. Art Bible §5."""
        g = gradient_v((self.size, self.size), invert=True)  # 1 at bottom
        band = smoothstep(1.0 - splash_m / max(height_m, 1e-3) * 1.6, 1.0, g)
        noisy = band * (0.6 + 0.4 * normalize01(fbm((self.size,) * 2, 14, seed + 5)))
        self.darken(noisy, 0.45)
        self.roughness = np.clip(self.roughness + noisy * 0.22, 0.03, 1.0)
        return self

    def water_streak(self, seed=0, strength=0.35, count=18):
        """Vertical runs below sills and ledges."""
        s = (self.size, self.size)
        cols = np.abs(fbm(s, count, seed + 71, octaves=2))
        # Stretch vertically so streaks run down, and fade with distance.
        streak = np.clip(cols * 2.2 - 0.8, 0, 1) * gradient_v(s)
        streak *= (0.5 + 0.5 * normalize01(fbm(s, 5, seed + 91)))
        self.darken(streak, strength)
        self.roughness = np.clip(self.roughness + streak * 0.15, 0.03, 1.0)
        return self

    def touch_polish(self, mask, amount=0.5):
        """Where hands go: smoother and slightly darker from skin oils."""
        m = np.clip(mask, 0, 1)
        self.roughness = np.clip(self.roughness - m * amount, 0.03, 1.0)
        self.darken(m, 0.12)
        return self

    def cavity_dirt(self, cavity, strength=0.5):
        """Dirt settles in crevices; drive with an inverted-curvature mask."""
        c = np.clip(cavity, 0, 1)
        self.albedo = self.albedo * (1 - c[..., None] * strength) + \
            P.rgb(P.AO_TINT) * (c[..., None] * strength)
        self.ao = np.clip(self.ao - c * 0.5, 0.0, 1.0)
        self.roughness = np.clip(self.roughness + c * 0.18, 0.03, 1.0)
        return self

    def edge_wear(self, edges, hex_substrate, strength=0.6):
        """Protruding edges rub back to substrate and smooth off."""
        e = np.clip(edges, 0, 1) * strength
        self.albedo = self.albedo * (1 - e[..., None]) + P.rgb(hex_substrate) * e[..., None]
        self.roughness = np.clip(self.roughness - e * 0.25, 0.03, 1.0)
        return self

    # -- export -------------------------------------------------------------

    def _normal_from_height(self, strength=2.0):
        h = self.height.astype(np.float32)
        # Sobel-ish central difference, wrapped so tiling materials stay seamless.
        dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
        dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
        n = np.stack([-dx, -dy, np.ones_like(h)], axis=-1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        return (n * 0.5 + 0.5).astype(np.float32)   # OpenGL +Y convention

    def write(self, outdir, normal_strength=2.0):
        os.makedirs(outdir, exist_ok=True)
        base = os.path.join(outdir, self.name)

        alb = P.linear_to_srgb(np.clip(self.albedo, 0, 1))
        _png(base + "_albedo.png", alb)

        # Channel-packed ORM: R=AO, G=roughness, B=metalness.
        # This is the packing both Unreal and Unity expect, so the port is free.
        orm = np.stack([np.clip(self.ao, 0, 1),
                        np.clip(self.roughness, 0, 1),
                        np.clip(self.metalness, 0, 1)], axis=-1)
        _png(base + "_orm.png", orm)

        _png(base + "_normal.png", self._normal_from_height(normal_strength))

        if self.emissive is not None:
            _png(base + "_emissive.png", P.linear_to_srgb(np.clip(self.emissive, 0, 1)))
        return base


def _png(path, arr):
    a = np.clip(arr, 0.0, 1.0)
    if a.ndim == 2:
        Image.fromarray((a * 255).astype(np.uint8), "L").save(path, optimize=True)
    else:
        Image.fromarray((a * 255).astype(np.uint8), "RGB").save(path, optimize=True)


# ---------------------------------------------------------------------------
# Material library
# ---------------------------------------------------------------------------
# Each returns a finished MaterialSet. Builders call these rather than authoring
# textures inline, so the whole town shares one material vocabulary.

def lime_plaster(name="plaster", size=1024, seed=0, wall_height=3.0, shaded=False):
    """Hand-applied lime plaster over daub. Trowel swirl, crackle, patch repairs."""
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(P.PLASTER_SHADE if shaded else P.PLASTER)

    # Trowel texture: broad swirl + fine tooth.
    swirl = fbm(s, 6, seed + 1, octaves=4)
    tooth = fbm(s, 40, seed + 2, octaves=3)
    m.add_height(swirl * 0.55 + tooth * 0.12)

    # Colour variance so it never reads as flat paint.
    m.darken(normalize01(swirl) * 0.5, 0.10)
    m.lighten(normalize01(fbm(s, 11, seed + 3)) * 0.5, 0.08)

    # Crackle network. Lime render crazes at 2-5cm with HAIRLINE cracks — at
    # a 2m tile that is ~50 cells, not 9. Coarse, deeply-embossed cells read as
    # crazy-paving stone and were the single worst defect in the first pass.
    # It lives almost entirely in height; albedo barely registers it.
    crack = 1.0 - smoothstep(0.0, 0.055, worley(s, 52, seed + 4, metric="f2f1"))
    m.add_height(-crack * 0.06)
    m.cavity_dirt(crack * 0.22, 0.10)

    # A few real structural cracks. Thresholded ridged noise makes continuous
    # meandering "worm trails"; gating it by a sparse mask keeps only short
    # isolated runs, which is how settlement cracking actually appears.
    sparse = smoothstep(0.80, 0.93, normalize01(fbm(s, 3, seed + 7, octaves=2)))
    major = smoothstep(0.955, 0.995, normalize01(ridged(s, 24, seed + 5, octaves=2))) * sparse
    m.add_height(-major * 0.16)
    m.cavity_dirt(major * 0.5, 0.25)

    # Patch repairs: a few regions of newer, brighter plaster.
    patch = smoothstep(0.55, 0.72, normalize01(fbm(s, 4, seed + 6, octaves=2)))
    m.lighten(patch, 0.14)

    m.rough(0.86, 0.09, 0.06, seed)
    # NOTE: no ground_splash / water_streak here. Those are world-position
    # effects, but this texture tiles — baking them in would repeat a "bottom
    # of the wall" dirt band at every tile seam. Position-dependent wear is
    # applied per-vertex at assembly time instead (see mesh.apply_ground_wear).
    return m


def oak_timber(name="oak", size=1024, seed=0, tone=P.OAK, weathered=0.4):
    """Sawn/hewn oak. Grain runs along V (see mesh.plank)."""
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(tone)

    # Grain. A pure sine produces hard repeating bands that alias badly against
    # the plank UV scale and read as painted stripes rather than wood. Warping
    # the phase with multi-octave noise gives grain lines that wander, split,
    # and vary in spacing the way sawn timber actually does.
    gx = np.linspace(0, 1, size, endpoint=False)[None, :].repeat(size, 0)
    warp = fbm(s, 3, seed + 12, octaves=4) * 0.55 + fbm(s, 9, seed + 19, octaves=3) * 0.18
    grain = np.sin((gx * 26.0 + warp * 26.0) * np.pi) * 0.5 + 0.5
    # Sharpen into fibres rather than a smooth wave, then break up amplitude so
    # some lines are strong and others barely there.
    grain = grain ** 1.8
    grain = grain * (0.35 + 0.65 * normalize01(fbm(s, 14, seed + 13, octaves=3)))
    m.add_height(grain * 0.16 + fbm(s, 70, seed + 14) * 0.06)
    m.darken(grain * 0.55, 0.16)

    # Growth-ring colour banding.
    rings = normalize01(np.abs(fbm(s, 3, seed + 15, octaves=2)))
    m.tint(P.OAK_DARK, rings * 0.25)

    # Knots — a couple per board, with grain deflection around them.
    knot = 1.0 - smoothstep(0.0, 0.13, worley(s, 3, seed + 16))
    m.darken(knot, 0.55)
    m.add_height(-knot * 0.4)

    # Weathering: silvering on exposed faces, splits opening along the grain.
    if weathered > 0:
        silver = normalize01(fbm(s, 7, seed + 17)) * weathered
        m.lighten(silver, 0.18)
        splits = smoothstep(0.86, 0.98, grain) * smoothstep(0.4, 0.9, normalize01(fbm(s, 2, seed + 18)))
        m.add_height(-splits * 0.5)
        m.cavity_dirt(splits * weathered, 0.5)

    m.rough(0.74, 0.13, 0.07, seed + 20)
    return m


def terracotta_tile(name="terracotta", size=1024, seed=0):
    """Fired clay pan-tiles with per-tile colour variance and lichen."""
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(P.TERRACOTTA)

    # Tile grid: 0.16m exposure per Art Bible §3, on a 2m tile => ~12 rows.
    rows, cols = 12, 8
    gy = np.linspace(0, rows, size, endpoint=False)[:, None].repeat(size, 1)
    gx = np.linspace(0, cols, size, endpoint=False)[None, :].repeat(size, 0)
    # Running bond offset per row.
    gx = gx + (np.floor(gy) % 2) * 0.5
    ty, tx = gy % 1.0, gx % 1.0

    # Barrel curvature across each tile — this is what catches the sun.
    m.add_height(np.sin(tx * np.pi) * 0.55)
    # Lap shadow at the head of each course.
    lap = smoothstep(0.0, 0.14, ty)
    m.add_height((lap - 1.0) * 0.5)
    m.ao = np.clip(m.ao - (1.0 - lap) * 0.55, 0, 1)

    # Per-tile firing variance: no two tiles from a wood kiln match.
    tile_id = np.floor(gy) * 31.0 + np.floor(gx) * 17.0
    var = ((tile_id * 0.6180339887) % 1.0).astype(np.float32)
    m.tint(P.TERRACOTTA_AGED, smoothstep(0.35, 1.0, var) * 0.55)
    m.darken(var * 0.4, 0.10)

    # Lichen and moss in the shaded laps, moisture-driven.
    moss = smoothstep(0.55, 0.85, normalize01(fbm(s, 6, seed + 31))) * (1.0 - lap * 0.6)
    m.tint(P.HERB_GREEN, moss * 0.5)
    m.roughness = np.ones(s, np.float32)
    m.rough(0.68, 0.14, 0.08, seed + 33)
    m.roughness = np.clip(m.roughness + moss * 0.2, 0.03, 1.0)
    m.cavity_dirt((1.0 - lap) * 0.6, 0.3)
    return m


def cobblestone(name="cobble", size=1024, seed=0, wetness=0.0):
    """Street paving. Worn smooth on desire paths, mossy where nobody walks."""
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(P.COBBLE)

    cells = worley(s, 12, seed + 41)
    edges = 1.0 - smoothstep(0.0, 0.22, worley(s, 12, seed + 41, metric="f2f1"))
    m.add_height((1.0 - cells) * 0.5 - edges * 0.6)

    # Per-stone colour. Granite paving is never one colour, and weak stone-to-
    # stone variance is why a cobbled street reads as flat grey mud at any
    # distance past a few metres — the normal map alone mips away, so the
    # ALBEDO has to carry the read. Keyed off the cell id so variance is
    # per-stone rather than a smooth blur across stones.
    # Per-stone value. Quantising the Worley f1 DISTANCE field produces
    # concentric rings inside every cell rather than one flat value per stone,
    # which tiled across a street as a field of visible bullseyes. Blobby
    # noise at the stone frequency gives per-region variance with no rings.
    per_stone = normalize01(fbm(s, 26, seed + 48, octaves=2))
    per_stone = np.floor(per_stone * 7.0) / 7.0
    m.darken(per_stone * 0.9, 0.34)
    m.lighten(smoothstep(0.62, 1.0, per_stone), 0.20)
    m.tint(P.FOUNDATION, smoothstep(0.30, 0.75, per_stone) * 0.50)
    m.tint("#6B6358", smoothstep(0.28, 0.0, per_stone) * 0.45)

    # Desire path: a diagonal band of polished, darker stone.
    gx = np.linspace(-1, 1, size)[None, :].repeat(size, 0)
    gy = np.linspace(-1, 1, size)[:, None].repeat(size, 1)
    path = 1.0 - smoothstep(0.0, 0.55, np.abs(gx * 0.7 + gy * 0.7))
    path *= (0.7 + 0.3 * normalize01(fbm(s, 4, seed + 44)))
    m.darken(path, 0.16)

    m.rough(0.72, 0.12, 0.07, seed + 45)
    m.roughness = np.clip(m.roughness - path * 0.30, 0.03, 1.0)   # polished by boots

    # Moss in the joints, only away from traffic.
    moss = edges * (1.0 - path) * smoothstep(0.4, 0.8, normalize01(fbm(s, 7, seed + 46)))
    m.tint(P.HERB_GREEN, moss * 0.55)

    if wetness > 0:
        pud = smoothstep(0.6, 0.85, normalize01(fbm(s, 5, seed + 47))) * wetness
        m.roughness = np.clip(m.roughness - pud * 0.55, 0.03, 1.0)
        m.darken(pud, 0.3)

    m.cavity_dirt(edges * 0.8, 0.45)
    return m


def wrought_iron(name="iron", size=1024, seed=0, rust=0.35):
    """Hand-forged iron: hammer facets, scale, rust blooming from crevices."""
    m = MaterialSet(name, size)
    s = (size, size)
    # Lifted off the palette value: a fully-metallic surface at #3A3632 has
    # almost no diffuse and, without a bright environment, renders as a flat
    # black cutout. Real wrought iron reads dark but always shows its form.
    m.set_base("#575047")
    r, _ = P.METAL_SPEC["iron"]
    # Deliberately below 1.0: aged wrought iron carries scale and oxide that
    # scatter diffusely, and a pure-metal surface renders as a black cutout
    # wherever the environment is dim. This keeps hammer facets readable.
    m.metalness[:] = 0.55

    # Hammer facets — Art Bible §2: iron is never smooth-extruded. These are
    # what make the highlight travel and break across the surface.
    facets = worley(s, 22, seed + 51, metric="f2f1")
    planish = normalize01(fbm(s, 11, seed + 55, octaves=3))
    m.add_height(facets * 0.55 + planish * 0.30 + fbm(s, 55, seed + 52) * 0.08)
    m.darken(normalize01(facets) * 0.6, 0.18)
    m.lighten(smoothstep(0.55, 0.95, planish), 0.16)   # burnished high spots

    # Strong roughness contrast is what separates forged iron from plastic.
    m.rough(r, 0.22, 0.10, seed + 53)
    m.roughness = np.clip(m.roughness - smoothstep(0.6, 1.0, planish) * 0.28, 0.05, 1.0)

    # Rust: blooms from low areas, and kills metalness where it forms.
    if rust > 0:
        bloom = smoothstep(0.45, 0.8, normalize01(fbm(s, 8, seed + 54, octaves=4))) * rust
        bloom = np.clip(bloom + facets * rust * 0.3, 0, 1)
        m.tint("#7A3B1E", bloom * 0.8)
        m.metalness = np.clip(m.metalness - bloom * 0.85, 0, 1)
        m.roughness = np.clip(m.roughness + bloom * 0.35, 0.03, 1.0)
        m.add_height(bloom * 0.12)
    return m


def canvas_awning(name="canvas", size=1024, seed=0, stripe=True,
                  base=P.CANVAS_CREAM, accent=P.CANVAS_STRIPE):
    """Oiled canvas. Woven thread, sun-bleaching, patches, and stripes."""
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(base)

    # Woven structure: two perpendicular thread sets.
    gx = np.linspace(0, 1, size, endpoint=False)[None, :].repeat(size, 0)
    gy = np.linspace(0, 1, size, endpoint=False)[:, None].repeat(size, 1)
    weave = (np.sin(gx * 260 * np.pi) * np.sin(gy * 260 * np.pi)) * 0.5 + 0.5
    m.add_height(weave * 0.12 + fbm(s, 30, seed + 61) * 0.06)

    if stripe:
        # Hand-dyed stripes: edges wander, width varies.
        wob = fbm(s, 3, seed + 62, octaves=2) * 0.035
        band = ((gx + wob) * 6.0) % 1.0
        mask = smoothstep(0.03, 0.09, band) * (1.0 - smoothstep(0.44, 0.50, band))
        m.tint(accent, mask)

    # Sun bleaching on the upper surface, dirt where rain collects.
    bleach = smoothstep(0.3, 1.0, gradient_v(s, invert=True)) * 0.5
    m.lighten(bleach * normalize01(fbm(s, 4, seed + 63)), 0.22)
    m.darken(smoothstep(0.6, 1.0, gradient_v(s)) * 0.6, 0.18)

    # Patches and a small tear — every awning in a real market is repaired.
    patch = smoothstep(0.72, 0.80, normalize01(fbm(s, 9, seed + 64)))
    m.darken(patch, 0.16)
    m.add_height(patch * 0.18)

    m.rough(0.88, 0.08, 0.05, seed + 65)
    return m


def thatch(name="thatch", size=1024, seed=0):
    """Reed thatch — dense directional straw, darker and mossy at the eaves."""
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base("#B9975B")
    straw = ridged(s, 90, seed + 71, octaves=2)
    m.add_height(straw * 0.4 + fbm(s, 25, seed + 72) * 0.2)
    m.darken(normalize01(fbm(s, 18, seed + 73)) * 0.8, 0.3)
    m.tint("#6B5638", smoothstep(0.5, 1.0, gradient_v(s)) * 0.5)
    moss = smoothstep(0.6, 0.9, normalize01(fbm(s, 6, seed + 74))) * gradient_v(s)
    m.tint(P.HERB_GREEN, moss * 0.45)
    m.rough(0.93, 0.06, 0.04, seed + 75)
    return m


def foundation_stone(name="stone", size=1024, seed=0):
    """Coursed rubble plinth. Big irregular blocks, deep mortar joints."""
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(P.FOUNDATION)

    blocks = worley(s, 6, seed + 81)
    joints = 1.0 - smoothstep(0.0, 0.14, worley(s, 6, seed + 81, metric="f2f1"))
    m.add_height((1.0 - blocks) * 0.45 - joints * 0.8)
    m.darken(normalize01(fbm(s, 12, seed + 82)) * 0.7, 0.16)
    m.tint(P.COBBLE_WORN, normalize01(fbm(s, 9, seed + 83)) * 0.4)
    m.rough(0.80, 0.12, 0.07, seed + 84)
    m.cavity_dirt(joints, 0.5)
    m.ground_splash(1.0, 0.25, seed + 85)
    return m


def forge_coal(name="coal", size=1024, seed=0):
    """Live forge fire — the town's only significant emissive surface."""
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base("#1A1512")
    lumps = worley(s, 14, seed + 91)
    m.add_height(lumps * 0.4)

    # Heat, distributed across the whole tile rather than as one central
    # hotspot. The fire bed is built from dozens of small scattered coal
    # pieces, each sampling world-position UVs — with a radial gradient most
    # of them land in the cold corners and render as black rock, which is
    # exactly what killed the forge glow in the first pass.
    ember = normalize01(fbm(s, 7, seed + 92, octaves=4))
    veins = normalize01(ridged(s, 13, seed + 95, octaves=3))
    heat = np.clip(0.30 + ember * 0.55 + veins * 0.35 - lumps * 0.45, 0, 1)

    m.emissive = (P.rgb(P.IRON_HOT)[None, None, :] * (heat ** 1.6)[..., None] * 3.0 +
                  P.rgb("#FFD98A")[None, None, :] * (heat ** 5.0)[..., None] * 2.0)
    m.tint(P.IRON_HOT, heat * 0.7)
    m.rough(0.85, 0.10, 0.06, seed + 93)
    m.metalness[:] = 0.0
    return m


def painted_wood(name="painted", size=1024, seed=0, colour=P.INN_GREEN):
    """Painted joinery — shutters, doors, signboards. Paint fails at edges."""
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(colour)

    grain = np.sin((np.linspace(0, 1, size)[None, :].repeat(size, 0) * 40.0 +
                    fbm(s, 4, seed + 101, octaves=3) * 6.0) * np.pi) * 0.5 + 0.5
    m.add_height(grain * 0.16)

    # Paint flakes off, exposing weathered timber beneath.
    flake = smoothstep(0.60, 0.78, normalize01(fbm(s, 13, seed + 102, octaves=4)))
    m.edge_wear(flake, P.OAK_WEATHERED, 0.75)
    m.add_height(-flake * 0.1)

    # Uneven brush coverage — hand-painted, thin over the grain.
    m.darken(grain * flake, 0.2)
    m.lighten(normalize01(fbm(s, 7, seed + 103)) * 0.4, 0.07)

    m.rough(0.45, 0.16, 0.09, seed + 104)
    m.roughness = np.clip(m.roughness + flake * 0.35, 0.03, 1.0)
    return m


def leaded_glass(name="glass", size=512, seed=0, lit=False):
    """Hand-blown crown glass in leaded cames — small panes only per §2.

    Rendered with an emissive interior spill rather than true transmission:
    from outside, a lit window reads as a warm glowing pane, and that glow is
    what makes a town look inhabited at any hour. Flat white opaque panes read
    as paper, which was the first-pass defect.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base("#2E3C44")
    gx = np.linspace(0, 5, size, endpoint=False)[None, :].repeat(size, 0)
    gy = np.linspace(0, 6, size, endpoint=False)[:, None].repeat(size, 1)
    came = np.minimum(np.minimum(gx % 1.0, 1 - gx % 1.0), np.minimum(gy % 1.0, 1 - gy % 1.0))
    lead = 1.0 - smoothstep(0.0, 0.055, came)
    m.tint(P.IRON, lead)
    m.metalness = lead * 0.9
    # Crown glass is never flat — the waviness is why old windows sparkle.
    m.add_height(-lead * 0.6 + fbm(s, 9, seed + 111) * 0.45 + fbm(s, 30, seed + 113) * 0.10)
    m.rough(0.10, 0.06, 0.03, seed + 112)
    m.roughness = np.clip(m.roughness + lead * 0.6, 0.03, 1.0)
    # Per-pane brightness variance: real leaded lights are never uniform.
    pane = 0.55 + 0.45 * ((np.floor(gx) * 13.0 + np.floor(gy) * 7.0) * 0.6180339887 % 1.0)
    # Daylight windows are dark glass with a hint of interior warmth; a strong
    # emissive reads as backlit paper, not glass. A LIT window is a different
    # thing entirely — there is a hearth behind it, and it should read warm and
    # occupied from across the square.
    if lit:
        m.set_base("#4A3A28")
        m.tint(P.IRON, lead)
        m.emissive = (P.rgb(P.WINDOW_SPILL)[None, None, :]
                      * ((1.0 - lead) * pane)[..., None] * 2.4)
        # Uneven glow: firelight is not a lightbox.
        flick = 0.65 + 0.35 * normalize01(fbm(s, 4, seed + 114, octaves=3))
        m.emissive = m.emissive * flick[..., None]
    else:
        m.emissive = (P.rgb(P.WINDOW_SPILL)[None, None, :]
                      * ((1.0 - lead) * pane)[..., None] * 0.28)
    return m


def foliage(name="foliage", size=512, seed=0, tone=P.HERB_GREEN, flowers=False):
    """Leaf material for window boxes, planters, herbs, and vines.

    Needed because the alternative is reusing striped market canvas on plants,
    which produced candy-striped cones in the first cottage pass. Foliage has
    its own colour logic: strong hue variance leaf-to-leaf, translucent-looking
    highlights, and darker undersides.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(tone)

    # Leaf-to-leaf colour variance — uniform green is the tell of fake plants.
    var = normalize01(fbm(s, 7, seed + 121, octaves=3))
    m.tint("#8FA854", smoothstep(0.5, 1.0, var) * 0.7)      # sun-yellowed
    m.tint("#3E5C33", smoothstep(0.5, 0.0, var) * 0.6)      # shaded depth

    # Venation and leaf surface.
    veins = ridged(s, 26, seed + 122, octaves=2)
    m.add_height(veins * 0.30 + fbm(s, 60, seed + 123) * 0.10)
    m.darken(veins * 0.5, 0.14)

    if flowers:
        blooms = smoothstep(0.86, 0.95, normalize01(worley(s, 14, seed + 124, metric="f2f1")))
        m.tint("#C4574F", blooms * 0.85)
        m.lighten(blooms, 0.15)

    # Waxy leaves are glossier than they look, and that sheen sells them.
    m.rough(0.52, 0.16, 0.09, seed + 125)
    return m


def ashlar(name="ashlar", size=1024, seed=0):
    """Dressed ashlar — squared blocks, fine joints, tooled faces.

    Distinct from `foundation_stone` (coursed rubble) on purpose. The guild is
    the only building in Hearthmere built by outside money to outside
    standards, and regular ashlar against everyone else's rubble-and-plaster is
    what carries that story without a word of exposition.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base("#B3A894")

    # Regular courses: wide blocks, running bond, thin joints.
    rows, cols = 7, 4
    gy = np.linspace(0, rows, size, endpoint=False)[:, None].repeat(size, 1)
    gx = np.linspace(0, cols, size, endpoint=False)[None, :].repeat(size, 0)
    gx = gx + (np.floor(gy) % 2) * 0.5
    ty, tx = gy % 1.0, gx % 1.0
    joint = np.minimum(np.minimum(tx, 1 - tx) * cols, np.minimum(ty, 1 - ty) * rows)
    jm = 1.0 - smoothstep(0.0, 0.055, joint)
    m.add_height(-jm * 0.55)

    # Tooled face: fine chisel marks, plus a slightly raised centre per block.
    m.add_height(ridged(s, 64, seed + 131, octaves=2) * 0.10)
    m.add_height((1.0 - jm) * 0.06)

    # Per-block colour: quarried stone varies bed to bed.
    blk = ((np.floor(gy) * 19.0 + np.floor(gx) * 7.0) * 0.6180339887) % 1.0
    m.darken(blk * 0.8, 0.13)
    m.tint(P.FOUNDATION, smoothstep(0.4, 1.0, blk) * 0.35)

    m.rough(0.68, 0.11, 0.06, seed + 132)
    m.cavity_dirt(jm * 0.8, 0.35)
    return m


def banner_cloth(name="banner", size=512, seed=0, colour=P.GUILD_CRIMSON):
    """Heavy dyed wool for banners. Uneven dye, sun-fade, frayed lower edge."""
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(colour)

    gx = np.linspace(0, 1, size, endpoint=False)[None, :].repeat(size, 0)
    gy = np.linspace(0, 1, size, endpoint=False)[:, None].repeat(size, 1)
    weave = (np.sin(gx * 200 * np.pi) * np.sin(gy * 200 * np.pi)) * 0.5 + 0.5
    m.add_height(weave * 0.14 + fbm(s, 22, seed + 141) * 0.08)

    # Vat-dyed wool is never even; the blotching is what stops it reading as
    # a flat colour swatch.
    blotch = normalize01(fbm(s, 5, seed + 142, octaves=3))
    m.darken(blotch * 0.8, 0.22)
    m.lighten(smoothstep(0.6, 1.0, blotch), 0.14)

    # Sun-bleached toward the hanging edge, dirt at the bottom.
    m.lighten(smoothstep(0.45, 0.0, gy) * 0.7, 0.20)
    m.darken(smoothstep(0.82, 1.0, gy), 0.30)

    m.rough(0.90, 0.07, 0.05, seed + 143)
    return m


def beaten_earth(name="dirt", size=1024, seed=0):
    """Trodden earth with cinder and scale worked into it.

    The blacksmith's yard is not paved — using the rubble-stone material there
    made a working floor read as crazy-paving. Beaten earth needs no cell
    structure at all: it is scuffs, ruts, embedded grit and scattered dark
    cinder.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base("#6E5C46")

    # Broad rutting and scuffing from feet and barrow wheels.
    ruts = fbm(s, 5, seed + 151, octaves=4)
    m.add_height(ruts * 0.35 + fbm(s, 34, seed + 152, octaves=3) * 0.14)
    m.darken(normalize01(ruts) * 0.8, 0.22)
    m.lighten(smoothstep(0.55, 1.0, normalize01(fbm(s, 12, seed + 153))), 0.14)

    # Embedded grit and cinder — the smithy's signature on the ground.
    grit = smoothstep(0.72, 0.90, normalize01(worley(s, 46, seed + 154, metric="f2f1")))
    m.add_height(grit * 0.22)
    cinder = smoothstep(0.80, 0.95, normalize01(fbm(s, 26, seed + 155, octaves=3)))
    m.tint("#241E1A", cinder * 0.85)

    m.rough(0.93, 0.07, 0.05, seed + 156)
    return m


def skin_tone(name="skin", size=256, seed=0, colour="#C08A62"):
    """Skin. Kept deliberately simple and matte — at gameplay distance the
    silhouette and clothing do the work, and a glossy or heavily-detailed skin
    reads worse, not better."""
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(colour)
    m.add_height(fbm(s, 40, seed + 161) * 0.05)
    m.darken(normalize01(fbm(s, 9, seed + 162)) * 0.5, 0.06)
    m.rough(0.72, 0.07, 0.04, seed + 163)
    return m


def hair(name="hair", size=256, seed=0, colour="#3A2A1E"):
    """Hair — directional strand detail and a gloss band."""
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(colour)
    strands = ridged(s, 70, seed + 171, octaves=2)
    m.add_height(strands * 0.30)
    m.darken(strands * 0.7, 0.25)
    m.lighten(smoothstep(0.55, 0.9, normalize01(fbm(s, 14, seed + 172))), 0.16)
    m.rough(0.42, 0.14, 0.08, seed + 173)
    return m


def parchment(name="parchment", size=512, seed=0):
    """Parchment for notices, maps and posted bills.

    There was no parchment in the registry, so the quest board — the single
    most important interactable in Hearthmere — requested "canvas" and got the
    STRIPED MARKET AWNING. Seventeen candy-striped cards on a rack of poles
    read as laundry, not as posted work.

    Real parchment: warm off-white, blotchy from the skin it came from, with
    fibre grain, foxing spots, and darkened handled edges.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base("#DCCFAE")

    # Skin blotching — parchment is never even.
    blotch = normalize01(fbm(s, 6, seed + 181, octaves=4))
    m.darken(blotch * 0.8, 0.16)
    m.lighten(smoothstep(0.6, 1.0, blotch), 0.12)

    # Fibre grain and surface tooth.
    m.add_height(ridged(s, 45, seed + 182, octaves=2) * 0.14 +
                 fbm(s, 90, seed + 183) * 0.06)

    # Foxing — the brown age spots that make old paper read as old.
    fox = smoothstep(0.80, 0.94, normalize01(worley(s, 20, seed + 184, metric="f2f1")))
    m.tint("#9C7B4A", fox * 0.55)

    # Handled edges darken and soften.
    gx = np.abs(np.linspace(-1, 1, size))[None, :].repeat(size, 0)
    gy = np.abs(np.linspace(-1, 1, size))[:, None].repeat(size, 1)
    edge = smoothstep(0.72, 1.0, np.maximum(gx, gy))
    m.darken(edge, 0.28)

    m.rough(0.86, 0.09, 0.05, seed + 185)
    return m


def sealing_wax(name="wax", size=256, seed=0, colour="#8E2B2B"):
    """Sealing wax — glossy, deep, and the only high-spec thing on a notice."""
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(colour)
    m.add_height(fbm(s, 18, seed + 191) * 0.25)
    m.darken(normalize01(fbm(s, 10, seed + 192)) * 0.7, 0.20)
    m.rough(0.22, 0.10, 0.06, seed + 193)
    return m


# Registry so venue modules and the build script agree on names.
LIBRARY = {
    "plaster":      lambda **k: lime_plaster(**k),
    "plaster_shade": lambda **k: lime_plaster(shaded=True, **k),
    "oak":          lambda **k: oak_timber(**k),
    "oak_dark":     lambda **k: oak_timber(tone=P.OAK_DARK, weathered=0.2, **k),
    "oak_weathered": lambda **k: oak_timber(tone=P.OAK_WEATHERED, weathered=0.8, **k),
    "terracotta":   lambda **k: terracotta_tile(**k),
    "cobble":       lambda **k: cobblestone(**k),
    "iron":         lambda **k: wrought_iron(**k),
    "canvas":       lambda **k: canvas_awning(**k),
    "thatch":       lambda **k: thatch(**k),
    "stone":        lambda **k: foundation_stone(**k),
    "coal":         lambda **k: forge_coal(**k),
    "painted":      lambda **k: painted_wood(**k),
    "glass":        lambda **k: leaded_glass(**k),
    "foliage":      lambda **k: foliage(**k),
    "foliage_flower": lambda **k: foliage(flowers=True, **k),
    "ashlar":       lambda **k: ashlar(**k),
    "banner":       lambda **k: banner_cloth(**k),
    "dirt":         lambda **k: beaten_earth(**k),
    # Clothing. Townsfolk need several distinct dyes or a crowd reads as
    # uniformed. All palette-compliant per Art Bible section 4.
    "cloth_blue":   lambda **k: banner_cloth(colour="#4A5C7A", **k),
    "cloth_green":  lambda **k: banner_cloth(colour=P.INN_GREEN, **k),
    "cloth_rust":   lambda **k: banner_cloth(colour="#9C5A3C", **k),
    "cloth_cream":  lambda **k: banner_cloth(colour=P.CANVAS_CREAM, **k),
    "cloth_brown":  lambda **k: banner_cloth(colour="#6B5638", **k),
    "skin":         lambda **k: skin_tone(**k),
    "hair_dark":    lambda **k: hair(colour="#3A2A1E", **k),
    "hair_fair":    lambda **k: hair(colour="#9C7B4A", **k),
    "parchment":    lambda **k: parchment(**k),
    # Lit glass. The inn's brief calls it "the most inviting thing in the
    # frame", and warm light behind glass is what actually delivers that —
    # daylight-neutral windows read as a building nobody is home in.
    "glass_lit":    lambda **k: leaded_glass(lit=True, **k),
    "wax":          lambda **k: sealing_wax(**k),
    "leather":      lambda **k: canvas_awning(stripe=False, base="#6B4A2E",
                                              accent="#6B4A2E", **k),
}
