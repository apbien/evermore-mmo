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

# Converts an `fbm` field to nominal +-1 so that an amplitude argument is
# expressed in the units of the channel it modulates.
#
# `fbm` sums Perlin octaves and divides by the amplitude sum, which leaves a
# field with a standard deviation near 0.13 and 1st/99th percentiles near
# +-0.32 — it is emphatically NOT a [-1,1] field, and every caller in this file
# assumed it was. Dividing by that percentile makes `broad_amp=0.12` mean "this
# band swings roughness by about 0.12", which is what the call sites were
# written to say. Measured, not guessed: see the band statistics in
# `tools/render/swatches.mjs`'s companion audit.
#
# Fixed constant rather than a per-image `normalize01`, on purpose. Normalising
# each field by its own extremes makes a material's contrast depend on the
# luckiest pixel in its own noise draw, so two seeds of the same builder get
# different amounts of wear — and `normalize01` also destroys the zero mean,
# which is what lets `albedo_break` leave the §4 mean where it found it.
_BAND_GAIN = 1.0 / 0.32


# ---------------------------------------------------------------------------
# Exposure-correct albedo
# ---------------------------------------------------------------------------
# Art Bible §4 gives APPEARANCE targets — "this is what lime plaster should
# look like". The library was pasting them straight into the albedo channel as
# if they were REFLECTANCES, and those are not the same quantity. `#E8DCC4` is
# a linear reflectance of 0.71, which is fresh snow. Lit by §4's own rig — sun
# 3.2 plus hemisphere 1.35 plus ambient 0.55 plus rim — a 0.71 wall leaves the
# ACES shoulder at the top and clips, so in `town-aerial-sw.png` whole
# buildings render as featureless white with the roof and the wall merged into
# one shape.
#
# Measured, before this existed: plaster 0.861 mean sRGB luminance (p95 0.881),
# limewash 0.779, linen 0.848, alabaster 0.833 — against terracotta 0.421,
# slate 0.375, thatch_old 0.416 inside the same library. The dark half of the
# library is physically right and the light half is a stop and a half hot.
#
# The fix is here rather than on the sun, because dimming the key would darken
# the correct materials to fix the incorrect ones. Two stages:
#
#   1. A shoulder on the material's MEAN luminance, applied as a SCALAR gain.
#      Scalar is the whole point: it moves the family value and leaves every
#      ratio inside the image untouched, so all the `albedo_break` and wear
#      variance survives exactly. A per-pixel shoulder crushes the top end —
#      measured, it took plaster's p95/mean contrast from 1.21 to 1.04.
#   2. A per-pixel backstop at REFLECTANCE_MAX, which nothing should reach.
#      Fresh snow is the brightest diffuse surface on Earth at ~0.8 linear.
#
# The shoulder is monotone, so the ORDERING of §4's values is preserved: lime
# plaster stays the brightest wall in the town, it just stops being snow.
REFLECTANCE_KNEE = 0.16     # linear luminance. Below this a material is untouched.
REFLECTANCE_CEIL = 0.42     # linear luminance the mean asymptotes to (sRGB 0.68)
REFLECTANCE_MAX = 0.62      # per-pixel backstop (sRGB 0.81)


def _luma(rgb):
    a = np.asarray(rgb, np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def _shoulder(l, knee=REFLECTANCE_KNEE, ceil=REFLECTANCE_CEIL):
    """Monotone soft ceiling on a linear luminance. Identity below `knee`."""
    l = np.asarray(l, np.float32)
    span = max(ceil - knee, 1e-6)
    over = np.maximum(l - knee, 0.0)
    return np.where(l <= knee, l, knee + span * (1.0 - np.exp(-over / span)))


def expose(albedo, alpha=None):
    """Map an authored §4 appearance colour to a physical reflectance.

    Used on every albedo at write time and on the §4 reference colours in
    `tools/validate.py`, so the palette checker and the shipped texture are
    measured in the same space.
    """
    a = np.clip(np.asarray(albedo, np.float32), 0.0, 1.0)
    lum = _luma(a)
    if a.ndim == 1:
        mean = float(lum)
    elif alpha is not None and float(np.max(alpha)) > 0.02:
        w = np.clip(alpha, 0, 1)
        mean = float((lum * w).sum() / max(float(w.sum()), 1e-6))
    else:
        mean = float(lum.mean())
    if mean > 1e-5:
        a = a * float(_shoulder(np.float32(mean)) / mean)
    # Per-pixel backstop, rolled rather than clipped so a highlight keeps its
    # shape instead of turning into a flat plateau.
    lum2 = _luma(a)
    hot = lum2 > REFLECTANCE_MAX * 0.8
    if bool(np.any(hot)):
        rolled = _shoulder(lum2, REFLECTANCE_MAX * 0.8, REFLECTANCE_MAX)
        a = a * (rolled / np.maximum(lum2, 1e-5))[..., None]
    return np.clip(a, 0.0, 1.0)


def reflectance(colour):
    """The exposure-mapped form of a single palette colour, linear triple."""
    return expose(P.as_rgb(colour))


class MaterialSet:
    """A complete PBR channel set, written as PNGs."""

    def __init__(self, name, size=1024, coverage=2.0, klass="standard"):
        self.name = name
        self.size = size
        # World metres spanned by one tile of this texture (Art Bible §5: "2 m x
        # 2 m per tile unless noted"). It is not decoration: texel density is
        # size/coverage, which is a done-criterion, and it is also the UV scale
        # a generator must use — see `uv_scale` below.
        self.coverage = float(coverage)
        self.klass = klass
        s = (size, size)
        self.albedo = np.ones(s + (3,), np.float32) * 0.5
        self.roughness = np.ones(s, np.float32) * 0.8
        self.metalness = np.zeros(s, np.float32)
        self.normal = None          # derived from height at write time
        self.height = np.zeros(s, np.float32)
        self.ao = np.ones(s, np.float32)
        self.emissive = None
        # Alpha for cut-out sheets: leaf cards, netting, hanging fleece. Kept
        # separate from albedo so a builder can author coverage independently of
        # colour, and so the writer knows whether an RGBA albedo is warranted.
        self.alpha = None

    # -- channel helpers ----------------------------------------------------

    def set_base(self, colour):
        """Base colour. Accepts a palette hex or a derived linear triple."""
        self.albedo[:] = P.as_rgb(colour)
        return self

    def tint(self, colour, mask):
        """Blend a colour in using a 0..1 mask."""
        m = np.clip(mask, 0, 1)[..., None]
        self.albedo = self.albedo * (1 - m) + P.as_rgb(colour) * m
        return self

    def darken(self, mask, amount=0.4):
        m = np.clip(mask, 0, 1)[..., None] * amount
        self.albedo *= (1.0 - m)
        return self

    def lighten(self, mask, amount=0.3):
        m = np.clip(mask, 0, 1)[..., None] * amount
        self.albedo = self.albedo + (1.0 - self.albedo) * m
        return self

    def rough(self, base, broad_amp=0.12, fine_amp=0.06, seed=0, broad_freq=3,
              fine_freq=28, mid_amp=None, mid_freq=9):
        """Roughness with the mandated noise scales, at the amplitude asked for.

        Broad (0.5-2m) reads as weathering and dampness; fine (1-5cm) reads as
        surface microstructure. A mid band (~0.3 m) sits between them because
        two octaves three and a half decades apart leave a hole exactly at the
        scale a player standing on a surface actually resolves — without it a
        material reads as one soft blob per metre with static on top.

        **Each band is normalised before the amplitude is applied**, and that
        is the whole point of this function. `fbm` returns a field whose 1st and
        99th percentiles are about +-0.32, so the previous version multiplied
        the raw field and delivered `broad_amp * 0.32` of actual swing — a
        `rough(0.90, 0.07, 0.05)` shipped a roughness standard deviation of
        0.011. Every one of the hundred-odd call sites below is written as
        though the amplitude meant roughness units, the docstring above claimed
        it did, and it did not: twelve materials measured under 0.013 and the
        cloth family rendered as flat vinyl. Art Bible §5 calls uniform
        roughness "the single biggest tell of amateur work" and the library was
        failing its own rule by an order of magnitude, silently, everywhere.

        Normalising here rather than editing the call sites is deliberate: the
        amplitudes those builders chose encode each material's intended
        *relative* character — sailcloth rougher-varying than blued steel — and
        that judgement is worth keeping. Only the units were wrong.
        """
        s = (self.size, self.size)
        broad = fbm(s, broad_freq, seed + 11, octaves=4) * _BAND_GAIN
        fine = fbm(s, fine_freq, seed + 29, octaves=3) * _BAND_GAIN
        r = base + broad * broad_amp + fine * fine_amp
        if mid_amp is None:
            mid_amp = 0.5 * (broad_amp + fine_amp)
        if mid_amp > 0:
            r = r + fbm(s, mid_freq, seed + 47, octaves=3) * _BAND_GAIN * mid_amp
        self.roughness = np.clip(r, 0.03, 1.0)
        return self

    def albedo_break(self, broad_amp=0.10, fine_amp=0.05, seed=0, broad_freq=4,
                     fine_freq=30, warm=0.30):
        """The albedo twin of `rough`: two-scale VALUE variance, mean preserved.

        Art Bible §5 writes the two-noise-source rule against roughness only,
        and the library obeyed it there and nowhere else — so the surfaces whose
        story lived entirely in `add_height` shipped a flat albedo. That is a
        worse defect than uniform roughness for one reason: **a normal map mips
        away and an albedo does not.** `oak` carries beautiful warped grain in
        its height and a 1.7-unit spread in L*; by the 15 m LOD the grain is
        gone and what is left is a tan rectangle. The same failure put `plaster`
        — the town's primary wall, on more square metres than anything else — at
        an L* standard deviation of 0.76, which is flat paint.

        Multiplicative and zero-mean, so every wear pass above it survives and
        the §4 mean does not move (which is what keeps `hold_to` and the palette
        checker honest). `warm` splits temperature with value the way real
        weathering does — the parts the sun has bleached go warm as well as
        light — because a pure value multiply reads as a greyscale overlay.
        """
        s = (self.size, self.size)
        broad = fbm(s, broad_freq, seed + 811, octaves=4) * _BAND_GAIN
        fine = fbm(s, fine_freq, seed + 812, octaves=3) * _BAND_GAIN
        n = np.clip(broad * broad_amp + fine * fine_amp, -0.85, 0.85)
        gain = (1.0 + n)[..., None]
        if warm > 0:
            # Warm the highs, cool the lows: R rides the variance harder than B.
            tilt = np.stack([n * warm, np.zeros_like(n), -n * warm], -1)
            gain = gain * (1.0 + tilt)
        self.albedo = np.clip(self.albedo * gain, 0, 1)
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

    def edge_wear(self, edges, substrate, strength=0.6):
        """Protruding edges rub back to substrate and smooth off."""
        e = np.clip(edges, 0, 1) * strength
        self.albedo = self.albedo * (1 - e[..., None]) + P.as_rgb(substrate) * e[..., None]
        self.roughness = np.clip(self.roughness - e * 0.25, 0.03, 1.0)
        return self

    def cut(self, mask, feather=0.0):
        """Cut the sheet out: `mask` 1 keeps, 0 is empty.

        Alpha-MASK rather than BLEND, so leaf cards sort correctly against each
        other and against everything behind them. A blended leaf atlas in a
        hedge is the classic transparent-foliage sorting failure, and it is
        visible from every angle at once.
        """
        a = np.clip(mask, 0, 1).astype(np.float32)
        if feather > 0:
            a = smoothstep(0.5 - feather, 0.5 + feather, a)
        self.alpha = a if self.alpha is None else np.minimum(self.alpha, a)
        return self

    def glow(self, colour, mask, gain=1.0):
        """Add to the emissive channel from a palette colour and a mask."""
        e = P.as_rgb(colour)[None, None, :] * np.clip(mask, 0, 1)[..., None] * gain
        self.emissive = e if self.emissive is None else self.emissive + e
        return self

    def hold_to(self, colour, strength=1.0, mask=None):
        """Pull the finished albedo mean back onto a palette colour.

        Every darken/lighten/tint/cavity pass moves the mean, and they all move
        it the same way — down and toward the AO tint — so a builder that ends
        with a dozen wear passes ships a surface whose *family* is no longer
        the one it was authored from. `cobblestone` had drifted a full dE 37 to
        COBBLE_WORN, which meant the town's paving shipped as its own gutter
        tone; `banner` and `water` were the same failure at 6.3 and 8.6 against
        the §4 checker in tools/validate.py.

        Multiplicative, per channel, so all the variation built above survives:
        this rescales the family without flattening the story.

        `mask` restricts BOTH the measurement and the correction to one region,
        which is what a surface with two populations needs. A leaf atlas is
        green leaves plus turned ones; held globally to the green, the gain
        that fixes the overall mean drags every turned leaf toward an olive
        that belongs to no §4 family — measured 11.7 on the oak atlas against
        4.4 when each population is held to its own colour.
        """
        target = P.as_rgb(colour)
        if mask is None:
            cur = self.albedo.reshape(-1, 3).mean(0)
            sel = None
        else:
            w = np.clip(mask, 0, 1)
            tot = float(w.sum())
            if tot < 1e-3:
                return self
            cur = (self.albedo * w[..., None]).reshape(-1, 3).sum(0) / tot
            sel = w[..., None]
        gain = target / np.maximum(cur, 1e-5)
        gain = 1.0 + (gain - 1.0) * float(strength)
        if sel is None:
            self.albedo = np.clip(self.albedo * gain, 0, 1)
        else:
            self.albedo = np.clip(self.albedo * (1.0 + (gain - 1.0) * sel), 0, 1)
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

    @property
    def texel_density(self):
        """px per world metre — the Art Bible §5 done-criterion."""
        return self.size / max(self.coverage, 1e-6)

    def mean_luminance(self, srgb=True):
        """Rec.709 luminance of the finished albedo, alpha-weighted.

        Reported by the build and gated by `tools/validate.py`. `srgb=True`
        gives the number you would read off the PNG with an eyedropper, which
        is the one worth arguing about.
        """
        a = np.clip(expose(self.albedo, self.alpha), 0, 1)
        lin = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
        if self.alpha is not None and float(self.alpha.max()) > 0.02:
            w = np.clip(self.alpha, 0, 1)
            lin = float((lin * w).sum() / max(float(w.sum()), 1e-6))
        else:
            lin = float(lin.mean())
        return float(P.linear_to_srgb(np.array([lin]))[0]) if srgb else lin

    def write(self, outdir, normal_strength=2.0):
        os.makedirs(outdir, exist_ok=True)
        base = os.path.join(outdir, self.name)

        albedo = expose(self.albedo, self.alpha)
        if self.alpha is not None:
            albedo = _dilate(albedo, self.alpha)
        alb = P.linear_to_srgb(np.clip(albedo, 0, 1))
        if self.alpha is not None:
            # Alpha rides in the albedo's fourth channel, which is where glTF's
            # alphaMode expects it.
            alb = np.concatenate([alb, np.clip(self.alpha, 0, 1)[..., None]], axis=-1)
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


def _dilate(colour, alpha):
    """Push the sheet's colour outward under its own cut-out (push-pull).

    Mandatory for every alpha-MASK material and routinely forgotten. A mip
    level averages neighbouring texels REGARDLESS of alpha, so whatever colour
    sits in the empty space between the leaves bleeds into the leaves at
    distance. Leave it black and every hedge in the town grows a dark halo by
    15 m; leave it as whatever the tint passes happened to paint there — which
    is what this file did before — and the halo is an arbitrary colour instead.

    Push-pull rather than an iterated blur. An iterated 4-neighbour blur
    propagates one texel per pass, so filling the 40-texel gaps in a leaf atlas
    needs forty passes; capping it lower leaves most of the empty area at a
    single global mean, and on a sheet holding both green and turning leaves
    that mean is a khaki belonging to no §4 family at all. Averaging DOWN a
    pyramid and filling UP from it reaches everywhere in log(size) steps and
    gives every hole the colour of its own neighbourhood, which is also the
    only answer that is locally correct.
    """
    a = (np.clip(alpha, 0, 1) > 0.02).astype(np.float32)
    if a.max() < 1e-6:
        return colour
    # Push: successively halve, carrying alpha-weighted colour sums.
    pyr = [(colour * a[..., None], a)]
    while min(pyr[-1][1].shape) > 2:
        c, w = pyr[-1]
        h2, w2 = c.shape[0] // 2, c.shape[1] // 2
        cc = (c[0:2 * h2:2, 0:2 * w2:2] + c[1:2 * h2:2, 0:2 * w2:2] +
              c[0:2 * h2:2, 1:2 * w2:2] + c[1:2 * h2:2, 1:2 * w2:2])
        ww = (w[0:2 * h2:2, 0:2 * w2:2] + w[1:2 * h2:2, 0:2 * w2:2] +
              w[0:2 * h2:2, 1:2 * w2:2] + w[1:2 * h2:2, 1:2 * w2:2])
        pyr.append((cc, ww))
    # Pull: fill each level's holes from the level above it.
    c, w = pyr[-1]
    up = c / np.maximum(w, 1e-6)[..., None]
    for c, w in reversed(pyr[:-1]):
        big = np.repeat(np.repeat(up, 2, axis=0), 2, axis=1)
        big = big[:c.shape[0], :c.shape[1]]
        have = (w > 1e-6)[..., None]
        up = np.where(have, c / np.maximum(w, 1e-6)[..., None], big)
    inside = (np.clip(alpha, 0, 1) > 0.02)[..., None]
    return np.where(inside, colour, up).astype(np.float32)


def _png(path, arr):
    a = np.clip(arr, 0.0, 1.0)
    mode = {2: "L", 3: "RGB", 4: "RGBA"}[a.ndim if a.ndim == 2 else a.shape[-1]]
    Image.fromarray((a * 255).astype(np.uint8), mode).save(path, optimize=True)


# ---------------------------------------------------------------------------
# Shared pattern helpers
# ---------------------------------------------------------------------------
# Sixty-odd builders live below this line and most of them are some
# arrangement of: a bond pattern, a per-unit value, a weave, or a stripe. Every
# one of those was hand-rolled inline in the first twenty builders, and by the
# fifth copy the copies had already diverged — two of them quantised the Worley
# *distance* field for per-stone colour, which draws concentric bullseyes
# inside every cell. Shared helpers are how that class of drift stops.


def _uv(size):
    """Normalised (v, u) ramps in [0,1). Row-major, so v is the first axis."""
    u = np.linspace(0, 1, size, endpoint=False, dtype=np.float32)[None, :].repeat(size, 0)
    v = np.linspace(0, 1, size, endpoint=False, dtype=np.float32)[:, None].repeat(size, 1)
    return v, u


def _course_hash(idx, seed, k):
    """A stable 0..1 value per COURSE index. Deterministic, no allocation."""
    return np.abs(np.sin(idx * k + float(int(seed) % 9973) * 0.0173)
                  * 43758.5453).astype(np.float32) % 1.0


def coursed(size, rows, cols, bond=0.5, joint=0.05, wobble=0.0, seed=0,
            wobble_u=0.0, stagger=0.0, vary=0.0, hash_unit=False):
    """A laid bond: brick, ashlar, tile, sett, plank.

    Returns `(joint, unit, ty, tx)`:
      joint  1 inside the mortar/lap line, 0 on the face
      unit   a stable 0..1 value per unit, for per-unit colour and firing
             variance (Art Bible §2: hand-made means nothing repeats)
      ty,tx  0..1 coordinates within the unit, for chamfers and cambers

    `wobble` warps the course lines with low-frequency noise, which is the
    difference between a hand-laid wall and a tiled texture. `bond` is the
    fraction of a unit each course is offset by — 0.5 is running bond, 0 is
    stack bond, 0.25 reads as a rubble course.

    `joint` is the mortar half-width **as a fraction of the shorter unit side**,
    so it is a physical width and it is the same on the bed and on the perpend.

    ## The joint was sub-pixel, and that is why no bond has ever been visible

    This line used to read

        d = min(min(tx, 1-tx) * cols, min(ty, 1-ty) * rows)

    which multiplies where it has to divide. `tx` is already unit-local, so the
    tile-fraction distance to a perpend is `tx / cols`, not `tx * cols` — the
    old form scaled the joint down by `cols²`. On `rubble` (6 x 8 on a 2 m tile
    at 512 px) that put the mortar at **3.4 mm, or 0.9 of one texel**, so it
    filtered away to nothing in the albedo and to nothing in the normal. It was
    also *inverted*: the axis with the shorter unit got the narrower joint, so
    beds and perpends came out different widths in the wrong direction.

    That single error is most of `ad-town-03` §1. `rubble_weathered` was
    correctly rebuilt on this function last wave and still shipped as crazy
    paving, because the bond it laid had no mortar the eye could find; the
    art director read the sheet and saw stones bleeding into each other. The
    joint shadow is roughly 80 % of what makes stone read as stone, and there
    was none.

    Fixed, `joint=0.055` on a 6 x 8 rubble tile is 27 mm of mortar — which is
    what a rubble wall has. Every caller's number was re-derived against a
    real width in millimetres; see the comment at each call site.

    ## `wobble` is measured in LATTICE widths, and that is why it dissolves

    The two lines above scale the warp by `rows` and `cols`, so the amplitude
    the eye sees — the warp in UNITS — grows with the lattice. `fbm` runs about
    +/-0.7, so the peak-to-peak warp along x is `wobble * cols * 0.18 * 1.4`
    units. `rubble` (0.62, 8 cols) is **1.25 units**; `cobble_wall` (0.52, 11
    cols) is **1.44 units**.

    Past about half a unit the perpends of neighbouring stones cross each other
    and two units merge into one amorphous polygon. Past a whole unit the bond
    is gone and what is left is a field of irregular polygons with wandering
    boundaries meeting at three-way junctions — **which is a Worley
    tessellation reconstructed out of a regular lattice.** `ad-town-05` §1 and
    §5 (the "inflated foam" church interior, the "cracked mud" enceinte) are
    both this, and it is why removing the Worley fields did not remove the
    crazy paving.

    So the masonry family does not use `wobble`. It uses:

      `wobble_u`  the same warp measured in **units**, at a noise frequency
                  tied to the lattice so it varies over ~3 stones rather than
                  over the whole tile. 0.18 is a hand-laid wall; 0.35 is rough
                  rubble; anything past 0.45 starts merging units again.
      `stagger`   a per-COURSE random phase, in units. This is what actually
                  makes a wall read as hand-laid: no perpend runs through two
                  courses, and no two courses share a rhythm. A fixed `bond`
                  alone gives a repeating brick pattern.
      `vary`      a per-COURSE unit-width scale, +/-`vary`. Real courses are
                  laid from whatever stone came off the cart, so one course is
                  long stones and the next is short ones. Varies stone SIZE
                  without touching the straightness of any joint.

    `wobble` is kept, and kept exact, because brick, slate, sett, plank and
    tile call it and their numbers were tuned against it.
    """
    s = (size, size)
    gy = np.linspace(0, rows, size, endpoint=False, dtype=np.float32)[:, None].repeat(size, 1)
    gx = np.linspace(0, cols, size, endpoint=False, dtype=np.float32)[None, :].repeat(size, 0)
    if wobble > 0:
        gy = gy + fbm(s, 3, seed + 401, octaves=2) * wobble * rows * 0.12
        gx = gx + fbm(s, 4, seed + 402, octaves=2) * wobble * cols * 0.18
    if wobble_u > 0:
        # Frequency tied to the lattice: ~3 units per cycle, so the joint
        # between two stones bends but the two stones stay two stones.
        gy = gy + fbm(s, max(2, int(round(rows / 3.0))), seed + 405,
                      octaves=2) * wobble_u * 0.55
        gx = gx + fbm(s, max(2, int(round(cols / 3.0))), seed + 406,
                      octaves=2) * wobble_u
    crow = np.floor(gy)
    if vary > 0.0:
        gx = gx / (1.0 + vary * (_course_hash(crow, seed + 407, 37.0) - 0.5) * 2.0)
    if stagger > 0.0:
        gx = gx + _course_hash(crow, seed + 408, 91.0) * stagger
    gx = gx + (crow % 2.0) * bond
    ty, tx = gy % 1.0, gx % 1.0
    # Distance to the nearest unit boundary, measured in units of the SHORTER
    # side so a joint on a long thin brick is the same physical width top and
    # end. `tx` spans one unit, so `tx * unit_w` is the tile fraction; dividing
    # by the shorter side puts both axes on a common footing.
    uh, uw = 1.0 / max(rows, 1e-6), 1.0 / max(cols, 1e-6)
    short = min(uh, uw)
    d = np.minimum(np.minimum(tx, 1 - tx) * (uw / short),
                   np.minimum(ty, 1 - ty) * (uh / short))
    jm = 1.0 - smoothstep(0.0, max(joint, 1e-4), d)
    if hash_unit:
        # `(19*row + 7*col) * phi % 1` is a low-discrepancy SEQUENCE, not a
        # hash: neighbouring units differ by exactly `7*phi mod 1` = 0.326
        # along a course and `19*phi mod 1` = 0.740 up a wall. Both are near
        # rational, so the field repeats on a ~3 x 4 unit block and any value
        # keyed to it walks light-mid-dark-light-mid-dark. That is invisible
        # while a `tint` pass is flattening the per-unit spread, and it is the
        # first thing the eye finds once the spread survives — which is what
        # the masonry family rebuild changed. Permuting the sequence does not
        # help; the periodicity is spatial, so the fix has to be a real 2-D
        # hash of the unit index.
        #
        # Opt-in, because brick, slate, sett, tile and plank were all tuned
        # against the sequence and their numbers should not move under them.
        unit = (np.abs(np.sin(np.floor(gy) * 127.1 + np.floor(gx) * 311.7 +
                              float(int(seed) % 9973) * 0.0173) * 43758.5453)
                % 1.0)
    else:
        unit = ((np.floor(gy) * 19.0 + np.floor(gx) * 7.0) * 0.6180339887) % 1.0
    return jm.astype(np.float32), unit.astype(np.float32), ty, tx


def per_unit(size, freq, seed, steps=6):
    """Quantised blobby noise: one value per region, no rings.

    The obvious way to get per-stone colour is to quantise a Worley distance
    field, and it is wrong — the field is a *distance*, so quantising it draws
    concentric rings inside every cell and tiles across a street as a field of
    bullseyes. Both `cobblestone` and `river_gravel` shipped that defect.
    Blobby fbm at the unit frequency gives per-region variance instead.
    """
    return np.floor(normalize01(fbm((size, size), freq, seed, octaves=2))
                    * float(steps)) / float(steps)


# The tile-repeat rule, stated once here because it is the commonest defect in
# the whole file and `ad-town-03` §4/§15 rejected on it:
#
#   A tiling material may not contain a feature the size of its own tile.
#
# Two things break it, and both were everywhere:
#
#   1. **A gradient in u or v.** `ground_splash` darkens the bottom of the
#      sheet; `limewashed_stone` banded its last coat across the lower third;
#      `rubble_weathered` ramped its moss up from the bottom edge. Every one of
#      those is a hard horizontal stripe every 2 m up a wall — four of them on a
#      24 m curtain, which is exactly what the art director counted. A material
#      cannot know where the ground is. Ground proximity is the *venue's* job
#      (`vegetation.wall_moss`, `props.spill`, a splash decal), never the tile's.
#   2. **One low-frequency blob per tile.** `fbm(s, 3)` puts about one feature
#      across the sheet, so it repeats as a lattice of identical light and dark
#      patches — the "obvious light/dark chequerboard" on `sett` at 2-8 m.
#
# `mottle` is the safe form: several features per tile, so the eye reads
# variation and cannot find the module. Anything below `FREQ_FLOOR` is a tile
# landmark, not variation.
FREQ_FLOOR = 6


def mottle(size, seed, freq=8, octaves=3):
    """Large-scale variation that cannot read as one blob per tile.

    Use instead of `fbm(s, 3)` wherever the result modulates a whole surface.
    Frequency is clamped at `FREQ_FLOOR` so the largest feature is a sixth of
    the tile — big enough to break a flat colour, small enough that repeating it
    does not draw a grid. Returns 0..1.
    """
    return normalize01(fbm((size, size), max(FREQ_FLOOR, int(freq)), seed,
                           octaves=octaves)).astype(np.float32)


def weave(size, threads, seed=0, slub=0.35):
    """Woven cloth height: two perpendicular thread sets, unevenly spun.

    A pure product of sines is a perfect machine weave and reads as nylon. Real
    hand-spun yarn varies in thickness along its length (slubs), which is what
    catches light unevenly and sells the cloth.
    """
    s = (size, size)
    v, u = _uv(size)
    warp = np.sin(u * threads * np.pi) * 0.5 + 0.5
    weft = np.sin(v * threads * np.pi) * 0.5 + 0.5
    thick = 1.0 + slub * (fbm(s, 9, seed + 411, octaves=3) +
                          fbm(s, 26, seed + 412, octaves=2))
    return ((warp * weft) * thick).astype(np.float32)


def stripes(size, count, seed=0, duty=0.5, wander=0.035, axis="u"):
    """Hand-dyed stripe mask. Edges wander and widths vary."""
    s = (size, size)
    v, u = _uv(size)
    g = u if axis == "u" else v
    wob = fbm(s, 3, seed + 421, octaves=2) * wander
    band = ((g + wob) * float(count)) % 1.0
    return (smoothstep(0.02, 0.07, band) *
            (1.0 - smoothstep(duty - 0.06, duty, band))).astype(np.float32)


def runs(size, seed, count=9, length=0.75, start=0.0, sharpness=2.4):
    """Vertical streaks that start somewhere and run DOWN, fading as they go.

    Verdigris off a copper roof, tar down a post, tallow down a candle, rust
    below an iron fixing, lime bloom under a sill. `water_streak` on MaterialSet
    is the wear-pass version of this; this one is the raw mask, so a builder can
    tint with it rather than only darken.

    `start` is where in V the run begins (0 = top edge), which is what makes a
    streak read as coming from a specific fixing rather than from the sky.
    """
    s = (size, size)
    v, _u = _uv(size)
    cols = normalize01(np.abs(fbm(s, count, seed + 451, octaves=2)))
    seeded = np.clip(cols * sharpness - (sharpness - 1.0), 0, 1)
    reach = start + length * (0.45 + 0.55 * normalize01(fbm(s, max(2, count // 3),
                                                            seed + 452, octaves=2)))
    down = np.clip((v - start) / np.maximum(reach - start, 1e-3), 0, 1)
    fade = (1.0 - down) * smoothstep(-0.02, 0.03, v - start)
    return (seeded * fade * (0.55 + 0.45 * normalize01(fbm(s, 22, seed + 453)))
            ).astype(np.float32)


def bedding(size, seed, beds=7, tilt=0.06, roughness=0.35):
    """Sedimentary bedding planes: near-horizontal bands of differing hardness.

    This is the whole read of sandstone and the reason it is not just "beige
    ashlar". The bands must be slightly non-parallel and vary in thickness, or
    they alias into a corduroy pattern.
    """
    s = (size, size)
    v, u = _uv(size)
    warp = fbm(s, 3, seed + 461, octaves=3) * roughness
    g = (v + u * tilt + warp * 0.12) * float(beds)
    band = np.floor(g)
    within = g % 1.0
    hard = ((band * 0.6180339887 * 13.0) % 1.0).astype(np.float32)
    seam = 1.0 - smoothstep(0.0, 0.035, np.minimum(within, 1.0 - within))
    return hard.astype(np.float32), seam.astype(np.float32), within.astype(np.float32)


def flakes(size, freq, seed, elong=1.0, overlap=0.35):
    """Overlapping scale-like plates: fish scales, pine cones, fleece locks.

    Worley cells stretched along one axis, with a lap shadow on the leading
    edge so the plates read as lying ON each other rather than tiled beside
    each other.
    """
    s = (size, size)
    d = worley(s, max(2, int(freq)), seed + 471)
    e = worley(s, max(2, int(freq)), seed + 471, metric="f2f1")
    if elong != 1.0:
        d2 = worley(s, max(2, int(freq / max(elong, 0.2))), seed + 472)
        d = d * (1.0 - overlap) + d2 * overlap
    lap = 1.0 - smoothstep(0.0, 0.18, e)
    return (1.0 - d).astype(np.float32), lap.astype(np.float32)


# ---------------------------------------------------------------------------
# The Hearthmere masonry family
# ---------------------------------------------------------------------------
# `ad-town-05` §7: "Two, three, four, five, **seven**. ... This is the one thing
# in the build that has got monotonically worse every single pass." Seven
# masonry treatments in one town, four of them on one wall.
#
# A town is built out of the stone in its own ground. Hearthmere stands on one
# bed of pale warm-grey limestone, and every wall in it — church, curtain,
# gatehouse, plinth, quay, bridge, cottage footing — is that stone. What differs
# between them is **dressing, age and wealth**, never geology:
#
#   dressing  how square the stone was cut and how fine the joint is. Fine
#             ashlar and random rubble are the same rock through two levels of
#             mason's wages.
#   age       how far the mortar has weathered back, how much lichen, how much
#             soot and rain patina.
#   wealth    whether it was limewashed, whether the quoins are dressed, whether
#             anyone came back and repointed it.
#
# So there is ONE colour set and ONE relief/colour engine below, and every
# masonry key is a short parameter list against it. Two keys that look different
# must differ in a number here, not in a body of their own — that is what stops
# the count climbing to eight next pass.

# The quarry. One body colour; three beds within it, close enough in hue that
# they read as one rock and far enough apart that a wall is not one grey.
# Warm. Hearthmere's stone is a honey limestone, not a granite: Art Bible §1
# wants the foreground warm against a cool distance, and the church interior is
# lit almost entirely by sky ambient, so a neutral body goes blue in the one
# frame `BUILD_DIRECTIVE` §3 calls the most important in the build. `ashlar`
# used to carry that warmth alone (#B3A894, R-B +0.12) and everything else was
# grey; the family sits at ashlar's old temperature, not at `stone`'s.
MASON_BODY   = P.mix(P.FOUNDATION, P.CANVAS_CREAM, 0.34)
MASON_WARM   = P.mix(MASON_BODY, P.PRODUCE_ACCENT, 0.17)  # the iron-stained bed
MASON_COOL   = P.mix(MASON_BODY, P.SLATE, 0.11)           # the hard blue bed
MASON_DEEP   = P.mix(MASON_BODY, P.OAK_DARK, 0.26)        # rain patina and soot
# The two ends of the ONE axis the family is allowed to differ on.
#
# `ad-town-06` §5: "widen the family spread back to ~0.04-0.05 of warmth so
# `ashlar` (church, civic), `sandstone` (gates) and `rubble`/`cobble_wall`
# (quay, revetment) are recognisably different stones from the same quarry
# district — which is what 'one family' means. Cohesion is not one colour."
# Wave 06 collapsed the whole family's warmth span to 0.013 and every key
# became the same grey; the collapse was the right move made one step too far.
#
# These are not two more rocks. They are the SAME limestone at two ages of
# face. A freshly worked face shows the unweathered interior of the bed: paler,
# and warmer, because the iron in it has not yet gone to a grey-green skin. A
# face two hundred years out of the mason's hands is case-hardened, sooted and
# lichened, and it goes cool and dark. Every mason's yard in England has both
# lying next to each other and nobody mistakes them for different quarries.
#
# So one key differs from another by TWO NUMBERS — how well it was dressed and
# how long ago — and never by a colour of its own. `masonry_body` is the only
# sanctioned way to get a base colour into a masonry key: a new key that calls
# `set_base` with anything else has left the family, which is how the count
# went to seven last time.
MASON_FRESH  = P.mix(MASON_BODY, P.CANVAS_CREAM, 0.40)
MASON_WORN   = P.mix(P.mix(MASON_BODY, P.COBBLE_WORN, 0.34), P.SLATE, 0.11)
# One mortar. A weathered lime-and-river-sand bed, warm grey, and always DARKER
# than the stone it beds — a pale mortar draws a grid and the wall reads as
# tiling. Every key in the family points at this constant.
MASON_MORTAR = P.mix(P.PLASTER_SHADE, P.COBBLE_WORN, 0.52)
# One biology. Grey-green crustose lichen, never `HERB_GREEN` neat — the town
# already has five greens and `ad-town-05` §6 wants none of them here.
MASON_LICHEN = P.mix(P.HERB_GREEN, P.PLASTER, 0.68)
MASON_DAMP   = P.mix(P.HERB_GREEN, P.COBBLE_WORN, 0.62)


def masonry_body(dressing=0.0, weathered=0.0):
    """The family body colour for one grade of work, as a linear triple.

    `dressing` 0..1  — how well the stone was cut and how recently anyone
                       scoured it. 1 is the guild's fine ashlar; 0 is what came
                       out of a field.
    `weathered` 0..1 — how long the face has been out in the weather with
                       nobody spending money on it. 1 is a robbed garden wall.

    The two are independent on purpose: a finely dressed wall nobody has
    touched since 1400 is both, and that is the town's own church.

    Measured across the seven keys this gives a warmth (R-B) span of about
    0.05 and a value span of about 0.09, which is the range `ad-town-06` §5
    asks for. Below ~0.03 of warmth the family reads as one grey and the
    dressing story is invisible (wave 06, span 0.013); above ~0.07 the eye
    starts reading two quarries and the cohesion win is lost.
    """
    d = float(np.clip(dressing, 0.0, 1.0))
    w = float(np.clip(weathered, 0.0, 1.0))
    return P.mix(P.mix(MASON_BODY, MASON_FRESH, d), MASON_WORN, w)


def masonry_bond(m, size, seed, *, coverage=2.0, course_m=0.22, stone_m=0.42,
                 joint_mm=22.0, arris_mm=25.0, wobble_u=0.16, stagger=0.34,
                 vary=0.16, bond=0.5, relief=1.0, camber=0.05, sneck=0.0,
                 dome=0.0):
    """Lay one wall of the family, in metres, and cut its relief.

    Returns `(joint, ident, face, arris)`.

    Three things this does that every hand-rolled masonry body in the file was
    getting wrong, and which are the whole of `ad-town-05` §1:

    **The module is stated in metres.** `coursed` takes a row and column count
    against an unstated tile size, so every call site had to do the division in
    its head, and `rubble`'s coarse patch lattice — 3 x 4 on a 2 m tile — put
    0.67 x 0.50 m megaliths on a parish church arcade. Nothing in the family
    lays a stone bigger than a mason can lift onto a scaffold: 0.20-0.55 m for
    walling, 0.75 m for civic ashlar, and it is *visible in the call* now.

    **The joint is stated in millimetres, and floored at three texels.**
    `ashlar` and `ashlar_civic` authored a physically-correct 4.6 mm joint at
    256 px/m, which is 1.2 texels: it filters away in the first mip and the
    wall ships with no bond at all. That is the "smeared cloudy mottle with no
    courses" on the drum towers and the "blank pale slab" on the guild tower.
    A joint you cannot see is not a fine joint, it is a missing one, so the
    width is clamped up to 3 texels at the shipped density and the material
    stops lying about what it is.

    **The face is flat with an arris, not a pillow.** Every masonry body in the
    file shaped its stone as `sin(unit_local * pi) ** k` — a half-sine across
    the *whole stone*. On a 0.5 m unit that is a 0.5 m dome, which is exactly
    the "~10 cm rounded arrises / inflated foam / reptile hide" the review has
    rejected twice. A dressed or even a roughly-squared stone is **flat**, with
    a 20-30 mm chamfer where the mason's hammer knocked the edge off, and it is
    the crispness of that arris that makes stone read as stone. `arris_mm` is a
    real width and it is a small number.

    `sneck` mixes in a course of half-height snecks — the small squaring stones
    a rubble mason drops in to bring a lift back to level. It is what stops a
    coursed rubble wall reading as very rough brickwork.
    """
    rows = max(2, int(round(coverage / max(course_m, 1e-3))))
    cols = max(2, int(round(coverage / max(stone_m, 1e-3))))
    uh, uw = coverage / rows, coverage / cols          # metres per unit
    short = min(uh, uw)
    px_per_m = float(size) / coverage
    # Half the mortar width, in metres, never under 1.5 texels (3 texels full).
    half_m = max(joint_mm * 0.0005, 1.5 / px_per_m)
    joint, ident, ty, tx = coursed(size, rows, cols, bond=bond,
                                   joint=half_m / short, wobble=0.0, seed=seed,
                                   wobble_u=wobble_u, stagger=stagger, vary=vary,
                                   hash_unit=True)
    if sneck > 0.0:
        # A second, shallower lattice on the same geology, selected per LIFT by
        # `mottle` — never `fbm(s, 3)`, which is one blob per tile and is how
        # `rubble` came to lay half its sheet in megaliths (FREQ_FLOOR).
        j2, i2, ty2, tx2 = coursed(size, rows * 2, int(round(cols * 1.15)),
                                   bond=0.5, joint=(half_m / short) * 1.7,
                                   wobble=0.0, seed=seed + 17,
                                   wobble_u=wobble_u, stagger=stagger,
                                   vary=vary * 0.7, hash_unit=True)
        pick = mottle(size, seed + 18, freq=8, octaves=2) > (1.0 - sneck)
        joint = np.where(pick, j2, joint)
        ident = np.where(pick, i2 * 0.97 + 0.015, ident)
        ty, tx = np.where(pick, ty2, ty), np.where(pick, tx2, tx)
        uh, uw = uh * 0.5, uw / 1.15

    if dome > 0.0:
        # The ONE case where a rounded face is correct: a whole river cobble,
        # which is a 0.2 m water-worn boulder and not a dressed block.
        # Legitimate at that size and nowhere near a 0.5 m church voussoir.
        #
        # A round stone needs a round FOOTPRINT as well as a round profile. The
        # previous form domed a rectangular cell, so the mortar stayed a
        # rectangular grid and the stones read as square blocks with soft tops.
        # Cutting the footprint radially puts mortar in the corners, which is
        # what a cobble wall actually looks like and where its enormous bed
        # comes from.
        # Size and shape per stone, or the field reads as bubble wrap: a
        # river bed is graded, not sorted to one gauge, and the mortar around
        # a small stone is wider than the mortar around a big one.
        rad = 0.78 + 0.34 * ident
        ell = 0.82 + 0.36 * ((ident * 7.3) % 1.0)
        rr = np.sqrt(np.square((tx - 0.5) * 2.0 / np.maximum(ell, 0.3)) +
                     np.square((ty - 0.5) * 2.0 * (uw / max(uh, 1e-6)) * ell))
        rr = rr / np.maximum(rad, 0.4)
        cut = smoothstep(1.04, 0.84, rr)
        joint = np.clip(joint + (1.0 - cut), 0.0, 1.0)
        face = (1.0 - joint).astype(np.float32)
        d = (np.sqrt(np.clip(1.0 - np.square(np.clip(rr / 1.04, 0, 1)), 0, 1))
             * face).astype(np.float32)
        m.add_height((d * 0.95 * dome + (ident - 0.5) * 0.26 * d
                      - joint * 0.95) * relief)
        arris = np.clip(d / max(dome, 1e-3), 0, 1).astype(np.float32)
    else:
        face = (1.0 - joint).astype(np.float32)
        # The chamfer, in unit-local fractions, from a width in millimetres.
        aw_x = float(np.clip(max(arris_mm * 0.001, half_m) / uw, 0.02, 0.40))
        aw_y = float(np.clip(max(arris_mm * 0.001, half_m) / uh, 0.02, 0.40))
        arris = np.minimum(smoothstep(0.0, aw_x, np.minimum(tx, 1.0 - tx)),
                           smoothstep(0.0, aw_y, np.minimum(ty, 1.0 - ty))
                           ).astype(np.float32)
        cam = (np.sin(np.clip(ty, 0, 1) * np.pi) *
               np.sin(np.clip(tx, 0, 1) * np.pi)).astype(np.float32)
        # Flat face, chamfered edge, recessed bed. Nothing domes.
        m.add_height((arris * 0.15 + cam * camber - joint * 0.62) * relief)
    return joint.astype(np.float32), ident.astype(np.float32), face, arris


def masonry_colour(m, size, seed, joint, ident, face, *, spread=0.26,
                   warm=0.34, cool=0.26, patina=0.13, grain=0.11,
                   lichen=0.34, damp=0.0, mortar=0.55, tool=0.0):
    """Colour one wall of the family, in the one order that survives.

    `cobble_walling` worked out the rule last wave and applied it to itself
    alone; this is that rule, applied once, for everybody:

        establish the stone FAMILY first (every `tint`), and apply the
        per-stone VALUE last, where nothing can paint over it.

    `tint` is a lerp toward a colour. `rubble`, `stone` and `limewash` all
    authored a +/-18-21 % per-stone spread and then ran two `tint(..., 0.45)`
    calls through overlapping masks on top of it, which throws away most of the
    spread — and "adjacent blocks differing by only a few luminance levels" is
    the third of `ad-town-05` §1's three symptoms.

    Everything above the value pass is the geology and the weather, and it is
    the SAME geology and the same weather for every key in the town. What each
    key is allowed to change is how much of each.
    """
    s = (size, size)
    # (1) the beds of one quarry, keyed to the stone and to nothing else.
    m.tint(MASON_WARM, face * smoothstep(0.62, 0.94, ident) * warm)
    m.tint(MASON_COOL, face * smoothstep(0.36, 0.06, ident) * cool)
    # (2) within the stone: freestone weathers in patches across a face
    #     regardless of where the joints fall, and this is the part that
    #     survives to 25 m after the normal map has mipped away.
    #
    #     Audited against Art Bible §5 in wave 07 and it was failing the rule
    #     it was written for. §5 wants two sources, BROAD (0.5-2 m) and FINE
    #     (1-5 cm); this call ran at freq 15 and 54 on a 2 m tile, which is
    #     0.13 m and 0.037 m — two fine sources and nothing broad. Moved to
    #     freq 8 (0.25 m) and 48 (0.042 m), which is the widest legal split on
    #     a 2 m tile: `FREQ_FLOOR` is 6, so 0.33 m is the largest feature a
    #     tiling material may carry, and anything in §5's true broad band is
    #     the size of the tile and therefore a tile landmark. The 0.5-2 m band
    #     on a masonry wall has to come from the VENUE — see the note on
    #     building-scale weathering in `review/reports/masonry-tune.md`.
    m.albedo_break(grain * 1.5, grain, seed + 811, broad_freq=8, fine_freq=48,
                   warm=0.22)
    if tool > 0.0:
        # Boaster runs: the mason's chisel across the face.
        m.darken((normalize01(fibre(size, 34.0, seed + 812, along="u",
                                    warp_amp=0.35)) - 0.5) * face + 0.5, tool)
    # (3) the weather: rain patina and soot, several patches per tile so the
    #     module never reads (FREQ_FLOOR, and the tile-repeat rule above).
    #
    #     Two scales, because Art Bible §5's two-noise rule is not only about
    #     roughness and because one scale of weather is a haze rather than a
    #     history. `ad-town-06` §5: "`t-gate-south`'s 1,600 px of curtain wall
    #     is one flat value with no weathering ... the `patina`, `lichen` and
    #     `damp` terms are being applied at a strength that does not survive to
    #     12 m." They were not too coarse — 0.29 m at freq 7 is 40 px at 12 m —
    #     they were too WEAK: a tint of 0.12 toward `MASON_DEEP` moves a face
    #     by about two luminance levels and the eye does not find it.
    #
    #     A weathered wall is not uniformly dirtier. It is dirty where the rain
    #     runs and SCOURED where it beats, so the honest form is a dark pass and
    #     a bleach pass out of the same field, which doubles the visible range
    #     for the same mean. `hold_to` on the key puts the mean back.
    lift = mottle(size, seed + 813, freq=7, octaves=2)
    soot = mottle(size, seed + 817, freq=18, octaves=3)
    grime = np.clip(smoothstep(0.66, 0.04, lift) +
                    smoothstep(0.74, 0.24, soot) * 0.55, 0.0, 1.0)
    m.tint(MASON_DEEP, grime * face * patina * 1.55)
    m.lighten(smoothstep(0.60, 0.97, lift) * face, patina * 1.05)
    # (4) the mortar. One mortar, darker than the stone, weathered back.
    m.tint(MASON_MORTAR, joint * mortar)
    m.darken(joint, 0.15)
    grit = smoothstep(0.62, 0.90, normalize01(worley(s, 88, seed + 814,
                                                     metric="f2f1")))
    m.lighten(grit * joint, 0.15)
    m.add_height(grit * joint * 0.10)
    # (5) PER-STONE VALUE, LAST. Nothing below this line may `tint` the face.
    st = (ident - 0.5) * 2.0
    m.darken(np.clip(-st, 0.0, 1.0) * face, spread)
    m.lighten(np.clip(st, 0.0, 1.0) * face, spread * 0.90)
    # (6) biology. Patchy, never a `v` ramp — a tile has no up (see `mottle`).
    bio = np.zeros(s, np.float32)
    if lichen > 0.0:
        li = smoothstep(0.70, 0.94, mottle(size, seed + 815, freq=12, octaves=3))
        m.tint(MASON_LICHEN, li * face * lichen)
        bio = bio + li * lichen
    if damp > 0.0:
        dm = smoothstep(0.56, 0.88, mottle(size, seed + 816, freq=9, octaves=3))
        m.tint(MASON_DAMP, np.clip(dm * (0.18 + joint * 0.34) * damp, 0, 1))
        bio = bio + dm * damp
    return bio


def _cell_hash(ix, iy, k, seed, salt=0.0):
    """A stable 0..1 hash per (atlas cell, leaflet index). Deterministic."""
    h = (ix * 127.1 + iy * 311.7 + k * 74.7 +
         float((int(seed) % 9973) * 0.0179) + salt)
    return np.abs(np.sin(h) * 43758.5453) % 1.0


def leaf_cards(size, seed, rows=4, cols=4, lobes=5, elong=1.5, stem=0.10,
               leaflets=(3, 6), spread=0.62, reach=0.86, fatten=1.0):
    """An alpha atlas of SPRAYS — a shoot of leaves per cell, not one blade.

    Returns `(alpha, along, across, blade_id)`:
      alpha     1 inside a leaf
      along     0 at each leaflet's petiole, 1 at its tip (midrib and colour)
      across    -1..1 across the blade (lateral veins and the fold)
      blade_id  a stable 0..1 per LEAFLET, so no two leaves match

    **One leaf per cell does not make a tree, and the arithmetic is not close.**
    A single blade in a 256 px cell covered 7-18 % of the sheet, which at
    `vegetation.CARD_M` paints about 0.13 m2 of leaf for two triangles and a
    full quad of overdraw. The market oak needed 694 cards to clothe a 110 m3
    crown with that and still rendered as bare antlers hung with confetti: the
    cards were transparent, so the branches showed through, so the fix looked
    like "more cards" — and more cards is the one thing that cannot work, since
    every card added is another full quad of overdraw buying another 13 % of
    nothing. Coverage per card is the term that has to move, and the only way to
    move it is to put more leaf in the cell. Every shipped foliage atlas does
    this: the unit is a SPRAY, not a leaf.

    So each cell here carries two or three shoots rising from one node just
    inside the cell's own bottom edge, each with alternate leaves that stand
    more upright the higher up the shoot they sit — which is what a real shoot
    does, and what fills a square cell instead of fanning into a semicircle and
    leaving the corners empty. Measured coverage goes from 7-18 % to 45-58 %,
    which lets the card count fall by two thirds for a canopy that is finally
    opaque. It also fixes the atlas's third defect for free: every stalk
    converges INSIDE its cell, so a 2x2 sub-rect card can no longer draw the
    severed stalks that are the loose brown sticks in every canopy in the build.

    `leaflets` is the (min, max) leaf count per shoot, `spread` the divergence
    between shoots in radians, `reach` how far up the cell they go, and `elong`
    the blade's length-to-width ratio — which is what makes a willow a willow
    and an oak an oak, since section 4 has exactly one green and species must
    therefore read from SHAPE, never from hue.
    """
    v, u = _uv(size)
    gy, gx = v * rows, u * cols
    iy, ix = np.floor(gy), np.floor(gx)
    ty, tx = gy % 1.0, gx % 1.0

    # --- the lattice, broken ------------------------------------------------
    #
    # Sixteen sprays, every one of them rising from the bottom edge of its own
    # cell at the same size — that is a regular 4x4 grid of near-identical
    # objects, and `review/reports/ad-town-04.md` §4 read it off the screen as
    # what it is: *"leaves are regular grids of green squares"*, 40 % of the
    # canonical return camera. Coverage was fixed last wave and the ARRANGEMENT
    # was not.
    #
    # Each cell now turns its whole spray by a quarter turn drawn from its own
    # hash, plus a small free tilt, plus a size change. The quarter turn is the
    # part that costs nothing: a square rotated by 90 degrees is the same
    # square, so a spray built to fit its cell still fits it and the invariant
    # this sheet is built on — no blade is ever cut by a cell boundary — holds
    # exactly. `zoom` pays for the free tilt by pulling the spray in by the
    # extra reach the tilt needs, which is why the tilt is small.
    _turn = np.floor(_cell_hash(ix, iy, 903.0, seed) * 4.0)
    _tilt = (_cell_hash(ix, iy, 917.0, seed) - 0.5) * 0.52
    _zoom = ((0.92 + 0.20 * _cell_hash(ix, iy, 931.0, seed)) *
             (1.0 + 0.42 * np.abs(_tilt)))
    _ang = _turn * (np.pi * 0.5) + _tilt
    _cs, _sn = np.cos(_ang), np.sin(_ang)
    _px, _py = (tx - 0.5) * _zoom, (ty - 0.5) * _zoom
    tx = 0.5 + _px * _cs - _py * _sn
    ty = 0.5 + _px * _sn + _py * _cs

    # The node: where the whole spray meets the twig. Inside its own cell, so
    # nothing a sub-rect card cuts is ever a blade.
    NODE_Y = 0.085
    kmin, kmax = int(leaflets[0]), int(leaflets[1])
    NBR = 3

    alpha = np.zeros_like(ty)
    along = np.zeros_like(ty)
    across = np.zeros_like(ty)
    ident = np.zeros_like(ty)
    best = np.zeros_like(ty)

    # Two shoots on most cells, three on some. One shoot is a twig, not a spray.
    nbr = 2.0 + np.floor(_cell_hash(ix, iy, 55.0, seed) * 1.7)

    for br in range(NBR):
        bl = (nbr > br).astype(np.float32)
        if not bl.any():
            break
        hb0 = _cell_hash(ix, iy, 200.0 + br, seed)
        hb1 = _cell_hash(ix, iy, 200.0 + br, seed, 29.3)
        hb2 = _cell_hash(ix, iy, 200.0 + br, seed, 71.9)
        # Shoot direction, measured off the cell's long axis, so the spray is a
        # V from one node rather than a bundle of parallel sticks.
        bang = (br - (nbr - 1.0) * 0.5) * spread + (hb0 - 0.5) * 0.26
        bx, by = np.sin(bang) * 0.70, np.cos(bang)
        bn = np.sqrt(bx * bx + by * by) + 1e-6
        bx, by = bx / bn, by / bn
        rlen = reach * (0.32 + 0.15 * hb1) * np.where(br == 0, 1.10, 0.86)
        base_x = 0.5 + (hb2 - 0.5) * 0.06
        nlf = np.clip(kmin + np.floor(_cell_hash(ix, iy, 91.0 + br, seed) *
                                      (kmax - kmin + 1)), kmin, kmax)

        if stem > 0:
            # The shoot itself, running from the cell's own bottom edge — and
            # that edge IS the twig, so a stub cut there is correct. What is not
            # correct, and was the atlas's third defect, is a BLADE cut off by a
            # cell boundary.
            sp_ = ((tx - base_x) * bx + (ty - NODE_Y) * by) / np.maximum(rlen, 1e-3)
            tp_ = (tx - base_x) * (-by) + (ty - NODE_Y) * bx
            rach = (smoothstep(0.019, 0.010, np.abs(tp_)) *
                    smoothstep(-0.08, -0.01, sp_) * smoothstep(1.02, 0.92, sp_)) * bl
            alpha = np.maximum(alpha, rach)

        for k in range(kmax):
            live = bl * (nlf > k)
            if not live.any():
                continue
            h_a = _cell_hash(ix, iy, k + br * 17.0, seed, 0.0)
            h_b = _cell_hash(ix, iy, k + br * 17.0, seed, 13.7)
            h_c = _cell_hash(ix, iy, k + br * 17.0, seed, 41.3)
            # Leaves alternate along the shoot, and the higher one sits the more
            # upright it stands. `r` is its rank up the rachis.
            pairs = np.maximum(np.ceil(nlf * 0.5) - 1.0, 1.0)
            side = 1.0 if (k % 2 == 0) else -1.0
            r = np.clip((k // 2) / pairs, 0.0, 1.0)
            term = (k + 1) >= nlf                      # the terminal leaflet
            off = np.where(term, (h_a - 0.5) * 0.34,
                           side * (0.98 - 0.50 * r + (h_a - 0.5) * 0.24))
            ang = bang + off
            p = np.where(term, 1.0, 0.08 + 0.88 * r)
            ox = base_x + bx * rlen * p
            oy = NODE_Y + by * rlen * p
            L = reach * np.where(term, 0.54, 0.70 - 0.15 * r) * (0.84 + 0.30 * h_b)
            # Elliptical envelope: sideways reach is compressed so a
            # near-horizontal low leaf still ends inside its own cell.
            dx = np.sin(ang) * L * 0.55
            dy = np.cos(ang) * L * 0.80
            ln = np.sqrt(dx * dx + dy * dy) + 1e-6
            ux, uy = dx / ln, dy / ln
            px, py = tx - ox, ty - oy
            s = (px * ux + py * uy) / ln                   # 0 at node, 1 at tip
            t = (px * (-uy) + py * ux)                     # across, cell units
            # Blade half-width: widest a third of the way up, pinched at the
            # petiole, drawn to a point. Clamped before the power — sin(pi)
            # lands a hair below zero in float32 and a fractional power of a
            # negative is NaN, which propagates into the albedo as a black card.
            sc = np.clip(s, 0.0, 1.0)
            prof = np.clip(np.sin(sc ** 0.72 * np.pi), 0.0, None) ** 0.85
            lob = 1.0 + 0.15 * np.sin(sc * lobes * np.pi * 2.0 + h_c * 6.283)
            half = (ln / (2.0 * max(elong, 0.35))) * fatten * prof * lob
            blade = smoothstep(0.012, 0.0, np.abs(t) - half) * \
                smoothstep(-0.01, 0.02, s) * smoothstep(1.06, 0.98, s)
            # The leaflet's own petiole, from the shoot to where its blade opens.
            pet = (smoothstep(0.010, 0.005, np.abs(t)) *
                   smoothstep(-0.01, 0.01, s) * smoothstep(0.18, 0.11, s))
            a_k = np.clip(np.maximum(blade, pet * float(stem > 0)), 0, 1) * live
            # The winning leaflet owns the pixel's vein and colour data. Without
            # an explicit owner the overlaps average two midribs into a smear.
            win = a_k > best
            best = np.where(win, a_k, best)
            along = np.where(win, sc, along)
            across = np.where(win, np.clip(t / np.maximum(half, 1e-3), -1.5, 1.5),
                              across)
            ident = np.where(win, (h_a * 0.5 + h_c * 0.3 + br * 0.2) % 1.0, ident)
            alpha = np.maximum(alpha, a_k)

    return (alpha.astype(np.float32), along.astype(np.float32),
            across.astype(np.float32), ident.astype(np.float32))


def shingle_leaves(size, seed, cells=26, radius=0.034, lobes=5, sinus=0.55,
                   elong=1.12, aspect=1.0):
    """A TILING mat of overlapping cut-out leaves. Returns an alpha sheet.

    `leaf_cards` builds an ATLAS — sixteen discrete sprays on a 4x4 sheet, each
    addressed by one card of tree geometry. That is the wrong unit for anything
    that clothes a *surface*: ivy on a wall, ground cover between paving, the
    skin of a hedge. Those tile, they have no cell boundaries, and their
    identity is the shingle — leaves lying ON each other, each casting a little
    shadow on the one below, with the substrate showing through the gaps.

    Returns `(alpha, radial, angle, ident, lap)`:
      alpha   1 inside a leaf, 0 where the wall/ground shows through
      radial  0 at the owning leaf's petiole, 1 at its margin
      angle   -pi..pi round the owning leaf, 0 at its apex (palmate venation)
      ident   a stable 0..1 per leaf, so no two are the same green
      lap     how many further leaves lie under this pixel — the shingle shadow

    Leaves are scattered on a jittered lattice and resolved over the 3x3
    neighbourhood, Worley-style, so the cost is nine evaluations per pixel
    whatever the leaf count and the sheet wraps exactly. `radius` and `cells`
    are both in tile fractions, so at the library's 2 m coverage `cells=26,
    radius=0.034` is a 14 cm leaf on a 7.7 cm lattice — ivy at the top of its
    size range, deliberately, because a botanically correct 6 cm leaf is one
    and a half texels of silhouette at gameplay range and reads as noise.

    `lobes` is the palmate lobe count (5 for ivy — an apex, two laterals and
    two basals), `sinus` how deeply the base is cut away toward the petiole,
    and `elong` the reach toward the apex.
    """
    v, u = _uv(size)
    N = int(cells)
    gy, gx = v * N, u * N
    iy, ix = np.floor(gy), np.floor(gx)

    alpha = np.zeros_like(gy)
    best = np.full(gy.shape, -1.0, np.float32)
    radial = np.zeros_like(gy)
    angle = np.zeros_like(gy)
    ident = np.zeros_like(gy)
    cover = np.zeros_like(gy)

    for dy in (-1.0, 0.0, 1.0):
        for dx in (-1.0, 0.0, 1.0):
            cy, cx = iy + dy, ix + dx
            # Hash on the WRAPPED index so the sheet tiles exactly.
            wy, wx = np.mod(cy, N), np.mod(cx, N)
            jx = _cell_hash(wx, wy, 3.0, seed)
            jy = _cell_hash(wx, wy, 7.0, seed, 11.3)
            phi = _cell_hash(wx, wy, 13.0, seed, 23.7) * 6.2831853
            scl = 0.72 + 0.62 * _cell_hash(wx, wy, 19.0, seed, 37.1)
            z = _cell_hash(wx, wy, 29.0, seed, 53.9)
            idn = _cell_hash(wx, wy, 41.0, seed, 71.3)

            # Delta from the leaf's petiole, in tile units.
            px = (gx - (cx + 0.15 + jx * 0.70)) / N
            py = (gy - (cy + 0.15 + jy * 0.70)) / N * aspect
            ca, sa = np.cos(phi), np.sin(phi)
            rx = px * ca + py * sa
            ry = -px * sa + py * ca
            rr = np.sqrt(rx * rx + ry * ry) + 1e-7
            a = np.arctan2(rx, ry)                      # 0 at the apex (+y)

            # Palmate outline. cos(lobes*a) peaks at the apex and at the
            # lateral lobes and troughs at the base, which is the shape.
            R = radius * scl * (0.70 + 0.30 * np.cos(lobes * a))
            R *= (1.0 + (elong - 1.0) * np.clip(np.cos(a), 0.0, 1.0))
            # Cordate sinus: the leaf is cut away either side of its own stalk.
            R *= 1.0 - sinus * smoothstep(0.45, 1.0, -np.cos(a))
            edge = radius * 0.16
            a_k = smoothstep(edge, 0.0, rr - R)

            cover = cover + a_k
            alpha = np.maximum(alpha, a_k)
            win = (a_k > 0.35) & (z > best)
            best = np.where(win, z, best)
            radial = np.where(win, np.clip(rr / np.maximum(R, 1e-6), 0, 1), radial)
            angle = np.where(win, a, angle)
            ident = np.where(win, idn, ident)

    lap = np.clip(cover - alpha, 0.0, 2.0) * 0.5
    return (alpha.astype(np.float32), radial.astype(np.float32),
            angle.astype(np.float32), ident.astype(np.float32),
            lap.astype(np.float32))


def fibre(size, freq, seed, along="u", warp_amp=0.5):
    """Directional fibre: wood grain, straw, reed, rope, fleece.

    A sine sharpened into fibres and phase-warped by noise, so lines wander,
    split and vary in spacing. A clean sine aliases against the UV scale and
    reads as painted stripes — that was `oak_timber`'s first-pass defect and
    the fix is the only version of this anyone should be writing.
    """
    s = (size, size)
    v, u = _uv(size)
    g = u if along == "u" else v
    w = (fbm(s, 3, seed + 431, octaves=4) * warp_amp +
         fbm(s, 9, seed + 432, octaves=3) * warp_amp * 0.33)
    f = np.sin((g * freq + w * freq) * np.pi) * 0.5 + 0.5
    f = f ** 1.8
    return (f * (0.35 + 0.65 * normalize01(fbm(s, freq * 0.5 + 2, seed + 433,
                                               octaves=3)))).astype(np.float32)


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
    sparse = smoothstep(0.80, 0.93, mottle(size, seed + 7, freq=6, octaves=2))
    major = smoothstep(0.955, 0.995, normalize01(ridged(s, 24, seed + 5, octaves=2))) * sparse
    m.add_height(-major * 0.16)
    m.cavity_dirt(major * 0.5, 0.25)

    # Patch repairs: a few regions of newer, brighter plaster.
    #
    # This and `sparse` and `albedo_break`'s broad octave were all at frequency
    # 3-4, which is about ONE blob per tile each — three overlapping tile-sized
    # patches in three slightly different creams, repeating on a 2 m lattice.
    # `ad-town-03` §1 read the result as "a blurry blue-grey/cream mottle with
    # no structure" and §(c) as a camouflage gable. All three are now above
    # FREQ_FLOOR, so the variation is at trowel scale where it belongs.
    patch = smoothstep(0.55, 0.72, mottle(size, seed + 6, freq=7, octaves=2))
    m.lighten(patch, 0.14)

    # Trowel arcs, in ALBEDO as well as height. A float leaves a fan of shallow
    # arcs where the plasterer's wrist pivoted, and they are the one directional
    # feature on the surface — without them lime render has no structure at all
    # and can only read as a mottle, however much value variation it carries.
    arc = normalize01(fibre(size, 5.0, seed + 9, along="u", warp_amp=1.6))
    m.darken(smoothstep(0.30, 0.72, arc), 0.045)
    m.lighten(smoothstep(0.74, 0.98, arc), 0.05)
    m.add_height((arc - 0.5) * 0.16)

    # Lime render is mixed by the barrow, applied by the day, and carbonates at
    # a rate that depends on which way the wall faces — so no two square metres
    # of it are the same value. Everything above lives in HEIGHT, which mips
    # away, and this wall covers more of Hearthmere than any other surface: at
    # L* sigma 0.76 it was the flattest material in the library and the town
    # read as poured concrete from 20 m out.
    # `warm=0.12`, well below the 0.30 default. The default cools the LOWS
    # toward blue as it warms the highs, which on a cream lime render is the
    # blue-grey/cream duality the art director read as a camouflage gable
    # (`ad-town-03` §1, §(c): `craft-walk-04`, `spine-walk-03`). Lime plaster
    # weathers within ONE warm family — it goes grey-cream, never blue — so the
    # temperature swing that makes oak and stone read has to be dialled back
    # here or the wall reads as two colours rather than one surface.
    m.albedo_break(0.25, 0.11, seed + 8, broad_freq=7, fine_freq=26, warm=0.12)

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

    # Board-to-board and along-the-board value. The grain above is 80% height
    # and 16% albedo, so at the 15 m LOD — where half the town's timber is
    # seen — every frame member flattened to one tan rectangle. Oak converted
    # from a log varies hugely between heartwood and sapwood and between one
    # board and the next out of the same tree; this is that, and it is the part
    # that survives the mip chain.
    m.albedo_break(0.30, 0.14, seed + 21, broad_freq=4, fine_freq=22)

    m.rough(0.74, 0.13, 0.07, seed + 20)
    return m


def terracotta_tile(name="terracotta", size=1024, seed=0):
    """Fired clay pan-tiles with per-tile colour variance and lichen."""
    m = MaterialSet(name, size)
    s = (size, size)
    # ## The aerial is one orange, and the base is why (`ad-town-05` p02-21)
    #
    # The three kiln batches exist and `COLOR_0` carries them, but a vertex
    # colour can only **multiply**, so from a base as saturated as
    # `TERRACOTTA` (#B5603E) every building can go darker and browner and none
    # can go paler, greyer or pinker. `t-plan` and `t-aerial-sw` come out ~70 %
    # one saturated orange with the variation reading as shading rather than as
    # different clay.
    #
    # Desaturated 22 % toward a neutral of the SAME luminance, so the roofs do
    # not go darker — they go from one orange to a population with room either
    # side of it. #757575 is the neutral that matches #B5603E's luma (117).
    m.set_base(P.mix(P.TERRACOTTA, "#757575", 0.22))

    # Tile grid: 0.16 m exposure per Art Bible §3. The tile covers 4 m (see the
    # registry), so that is 25 rows, not the 12 this had — which put the courses
    # at 0.33 m, twice the specified exposure, on every roof in the town. A
    # scale error inside a repeating pattern is the hardest kind to see and the
    # most damaging, because there is nothing in frame to measure it against.
    rows, cols = 25, 16
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
    #
    # Art Bible §4 asks for TERRACOTTA_AGED on "~30% of tiles", and that is a
    # POPULATION, not a gradient. The smoothstep this had ramped 65% of tiles
    # through a continuous blend, which averages out to a uniform mid-tone at
    # any distance past a few metres — the aged tiles have to be individually
    # countable or they are not tiles, they are noise. So: a hard 30% split on
    # a second decorrelated per-tile hash, and a much stronger tint on the
    # tiles that take it.
    tile_id = np.floor(gy) * 31.0 + np.floor(gx) * 17.0
    var = ((tile_id * 0.6180339887) % 1.0).astype(np.float32)
    var2 = ((tile_id * 0.7548776662 + 0.31) % 1.0).astype(np.float32)
    old = (var < 0.30).astype(np.float32)
    m.tint(P.TERRACOTTA_AGED, old * (0.62 + 0.30 * var2))
    # Everything else takes a smaller kiln-position value swing, so the 70%
    # that are not "aged" are still not one colour.
    m.darken((1.0 - old) * var2 * 0.9, 0.14)
    m.lighten((1.0 - old) * smoothstep(0.55, 1.0, var2), 0.10)

    # Lichen and moss in the shaded laps, moisture-driven.
    moss = smoothstep(0.55, 0.85, normalize01(fbm(s, 6, seed + 31))) * (1.0 - lap * 0.6)
    m.tint(P.HERB_GREEN, moss * 0.5)
    m.roughness = np.ones(s, np.float32)
    m.rough(0.68, 0.14, 0.08, seed + 33)
    # Per-tile roughness. A tile that spent its firing near the kiln mouth
    # vitrifies and comes out slicker; one that has weathered thirty winters is
    # matt and porous. Without this every tile on the roof takes the sun's
    # specular at exactly the same width, which is the "printed sheet" read
    # that survives even after the colour variance is fixed — the highlight has
    # to break tile by tile.
    m.roughness = np.clip(m.roughness + (var2 - 0.5) * 0.26 + old * 0.10,
                          0.20, 1.0)
    m.roughness = np.clip(m.roughness + moss * 0.2, 0.03, 1.0)
    m.cavity_dirt((1.0 - lap) * 0.6, 0.3)
    return m


def cobblestone(name="cobble", size=1024, seed=0, wetness=0.0):
    """Street paving: rounded boulders pitched on edge and brought to course.

    ## Why this was rebuilt (D-050)

    This is the surface of **every street in the town**, and through four
    art-director passes it has been rejected every time under one word: *crazy
    paving*. `ad-town-04` §2 names four frames — `mere-walk-05`,
    `craft-walk-04`, `t-square`, `kirk-walk-06` — and attributes it to the 421
    literal `uv_scale=` sites.

    **It is not the scale.** `tools/uv_density.py`, area-weighted off the
    shipped glTF, puts `cobble` at 2.06 m per tile against 2.00 authored — a
    3 % error, on the largest ground surface in the build. The pattern is
    landing at exactly the size it was authored for. What was wrong is what the
    pattern IS:

        cells = worley(s, 12, ...)                                # f1 distance
        edges = 1 - smoothstep(0.0, 0.11, worley(s, 12, "f2f1"))  # the joint
        dome  = clip(1 - cells * 1.15, 0, 1) ** 0.5

    A Worley cell boundary is the **perpendicular bisector of two feature
    points**. It is dead straight, and three of them meet at 120°. So a field
    of Worley cells is, by construction, a field of straight-sided irregular
    polygons packed edge to edge — which is not a description of a cobbled
    street, it is the definition of crazy paving. This module already makes
    exactly that argument, in `rubble_weathered`: *"worley puts one feature
    point per cell of a uniform lattice, so it is isotropic by construction:
    what came out was random polygons with no bedding at all — crazy paving,
    stood on its end and called a wall."* `rubble` was rebuilt on `coursed` and
    the art director called the result "the best masonry in the build". The
    same argument was never applied to `cobble`, and `cobble` covers twenty
    times the area.

    Two more defects compounded it. `edges` thresholds `f2f1` at 0.11, which is
    a **hairline** — the stones met with no joint the eye could find, so they
    read as one plane scored with lines rather than as separate objects. And
    `dome` is driven by the f1 *distance*, which is a broad smooth basin
    covering the whole cell, not a shoulder that dies into the joint: every
    stone came out flat-topped. Flat polygons + hairline joints + one value is
    a patio.

    So: laid on `coursed`, like `sett`, `brick`, `rubble` and `cobble_wall`.
    What keeps it from reading as `sett` — which is dressed and is the *point*
    of having both — is that a cobble is a rounded boulder: high `wobble` and a
    low `bond` so the courses wander and no perpend runs through two, a strong
    dome instead of a flat riven top, and a fat grit-filled joint instead of
    `sett`'s 55 mm of sand.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(P.COBBLE)

    # 0.14 m cobbles on a 2 m tile: 14 x 14. A street cobble is 100-160 mm —
    # bigger than that and it is a sett, smaller and it is a pebble.
    #
    # `wobble` 0.70 is deliberately near the top of the usable range (the note
    # on `coursed` puts the dissolve at ~0.8). A cobbled street IS brought to
    # course — that is how it is laid and how it drains — but the courses
    # wander by most of a stone, which is the difference between this and the
    # dressed setts on the market place. `bond` 0.37 breaks the perpends so no
    # vertical joint runs through two courses.
    #
    # `joint` is a fraction of the shorter unit side: 0.085 on a 0.143 m stone
    # is **24 mm** of grit-filled joint. That is what a cobbled street has, and
    # its shadow is most of what makes the stones read as separate objects at
    # any distance past 4 m.
    joint, ident, ty, tx = coursed(size, 14, 14, bond=0.37, joint=0.085,
                                   wobble=0.70, seed=seed + 41)

    # A cobble is a boulder laid on its round: the face is a dome that dies
    # into the joint, not a flat plate with a bevel. The 0.45 exponent gives a
    # full rounded shoulder rather than a cone, and multiplying by `1 - joint`
    # makes the stone meet the grit at its own foot.
    dome = (np.sin(np.clip(ty, 0, 1) * np.pi) ** 0.45 *
            np.sin(np.clip(tx, 0, 1) * np.pi) ** 0.45) * (1.0 - joint)
    # Each stone sits at its own level — a cobbled street is never flush, and
    # the proud ones are what catch a low sun.
    m.add_height(dome * 0.95 + (ident - 0.5) * 0.26 * (1.0 - joint)
                 - joint * 0.95)
    # Water-rolled surface: no facets, just the pitting of a river stone.
    m.add_height(normalize01(fbm(s, 90, seed + 42, octaves=2)) * 0.07 * dome)

    # -- per-stone colour, from the bond's own identity ---------------------
    # Weak stone-to-stone variance is why a cobbled street reads as flat grey
    # mud past a few metres: the normal map mips away and the ALBEDO has to
    # carry the read on its own. `ident` is one stable value per stone, so this
    # fills each stone rather than blurring across them.
    stone = (ident - 0.5) * 2.0                          # -1 .. +1
    face = 1.0 - joint
    m.darken(np.clip(-stone, 0, 1) * face, 0.24)
    m.lighten(np.clip(stone, 0, 1) * face, 0.30)
    m.tint(P.FOUNDATION, smoothstep(0.34, 0.78, ident) * face * 0.50)
    m.tint("#6B6358", smoothstep(0.28, 0.0, ident) * face * 0.50)
    # The odd red sandstone cobble in among the granite. One stone in twenty.
    m.tint(P.mix(P.TERRACOTTA_AGED, P.COBBLE_WORN, 0.55),
           smoothstep(0.95, 1.0, ident) * face * 0.65)

    # Polish where boots go. This was a diagonal band drawn across the tile at
    # a fixed angle through its centre, which on a 10 m lane is FIVE parallel
    # diagonal stripes in register — a corduroy, not a desire path (FREQ_FLOOR).
    # A desire path is a route through a town and belongs to the road mesh, not
    # to a 2 m tile; what the tile can honestly carry is patchy wear.
    path = smoothstep(0.40, 0.88, mottle(size, seed + 44, freq=7, octaves=3))
    m.darken(path, 0.10)

    # Roughness. `- dome * 0.14` on top of the traffic polish took the crown of
    # every stone to ~0.28, and the rendered street came back with a wet sheen
    # across the whole carriageway — a washed patio, not dry granite at 09:30.
    # The polish belongs to where the boots go, not to every stone.
    m.rough(0.78, 0.12, 0.07, seed + 45)
    m.roughness = np.clip(m.roughness - path * 0.26, 0.06, 1.0)

    # What is IN the joint is sand and grit, and it is warm grey. `ad-town-03`
    # §14 lists green mortar as one of the town's five last-resort greens, and
    # this was the largest of them: `HERB_GREEN` at 0.55 along every joint of
    # every cobbled street. Moss survives, at a third the strength and only in
    # patches, because a cobbled street does grow moss — between the stones
    # nobody walks on, not along every joint in the town.
    grit = joint * smoothstep(0.35, 0.85, normalize01(fbm(s, 24, seed + 49)))
    m.tint(P.mix(P.PLASTER_SHADE, P.COBBLE_WORN, 0.5), grit * 0.45)
    m.lighten(grit, 0.10)
    m.add_height(grit * 0.16)
    moss = joint * (1.0 - path) * smoothstep(0.62, 0.88, mottle(size, seed + 46, freq=9))
    m.tint(P.mix(P.HERB_GREEN, P.PLASTER_SHADE, 0.45), moss * 0.42)

    if wetness > 0:
        pud = smoothstep(0.6, 0.85, normalize01(fbm(s, 5, seed + 47))) * wetness
        m.roughness = np.clip(m.roughness - pud * 0.55, 0.03, 1.0)
        m.darken(pud, 0.3)

    # The joint shadow, in the ALBEDO and in the AO — because at 8 m the normal
    # map is two mips down and gone, and the joint is the whole read.
    m.darken(joint, 0.20)
    m.cavity_dirt(joint * 0.9, 0.35)
    # Pull the finished mean back onto the locked COBBLE value. The
    # cumulative darken/cavity passes had drifted it a full dE 37 to
    # COBBLE_WORN, so the town's paving shipped as its own gutter tone.
    # Multiplicative, so every per-stone value above survives it.
    m.hold_to(P.COBBLE)
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

    # Woven structure, via the shared helper. The hand-rolled version here was a
    # pure product of sines at 130 cycles — under four pixels per cycle on the
    # 512 px map this material actually gets, so it aliased into moiré rather
    # than resolving as cloth, and being a perfect product of sines it was a
    # machine weave besides (§2: nothing hand-made repeats exactly). `weave()`
    # exists precisely to stop this builder and `sailcloth` diverging.
    m.add_height(weave(size, 150, seed + 61, slub=0.40) * 0.14 +
                 fbm(s, 30, seed + 61) * 0.06)

    if stripe:
        # Hand-dyed stripes, via `stripes()` for the same reason. Duty 0.42 so
        # the accent is the narrower band: an awning is ground colour with a
        # stripe on it, and at 50/50 the six stripes read as a beach ball —
        # which is exactly how the market rendered.
        m.tint(accent, stripes(size, 6, seed + 62, duty=0.42, wander=0.045))

    # Sun bleaching on the upper surface, dirt where rain collects.
    bleach = smoothstep(0.3, 1.0, gradient_v(s, invert=True)) * 0.5
    m.lighten(bleach * normalize01(fbm(s, 4, seed + 63)), 0.22)
    m.darken(smoothstep(0.6, 1.0, gradient_v(s)) * 0.6, 0.18)

    # Patches and a small tear — every awning in a real market is repaired.
    patch = smoothstep(0.72, 0.80, normalize01(fbm(s, 9, seed + 64)))
    m.darken(patch, 0.16)
    m.add_height(patch * 0.18)

    # Oiled canvas weathers in blotches: the dressing goes on unevenly, wears
    # off the folds first, and takes dirt where it stays tacky. Without it both
    # the ground and the stripe were single flat colours and the awning read
    # as a printed sheet rather than as woven cloth.
    m.albedo_break(0.25, 0.14, seed + 66, broad_freq=5, fine_freq=30, warm=0.22)

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


def foundation_stone(name="stone", size=1024, seed=0, courses=9, moss=0.30):
    """Squared-and-graded coursed masonry — the town's default `stone` key.

    ## Why this was rebuilt

    This is `LIBRARY["stone"]`: the church, the fountain, every plinth, the
    perron steps and the market paving. `ad-town-03` §1 measured it at roughly
    60 % of the pixels in the mandated arrival frame, and named it the single
    highest-value fix in the build. Pass 02 had blamed `rubble_weathered`, a
    whole wave rebuilt *that* function correctly, and nothing on screen moved —
    because the crazy paving the art director was looking at was this.

    The old body was four lines and three of them were wrong:

    1. `worley(s, 6)` plus `worley(..., "f2f1")` — **two interleaved Worley
       fields**. `worley` seeds one feature point per cell of a uniform
       lattice, so it is isotropic by construction: random polygons with no
       bedding. That is crazy paving, and it was stood on end and called a
       plinth. `coursed` lays a real bond, and it is the same generator brick,
       ashlar, sett, slate and `rubble_weathered` already use.
    2. Value variation came from `fbm(s, 12)` and `fbm(s, 9)` — **independent
       noise fields not keyed to the cell**. A blur that crosses stone
       boundaries is not per-stone variation; every stone came out the same
       value and the surface flattened to one grey past 4 m. Value is now
       driven by `coursed`'s own `ident`, so a stone is an object.
    3. `ground_splash` darkened the bottom of the sheet, which on a tiling
       material is a **dark horizontal band every 2 m up the wall**. See the
       tile-repeat rule above `mottle`. Ground damp is the venue's job.

    `rubble_weathered` is the *ungraded* walling — field stone, high wobble,
    galleting. This is its dressed cousin: squared, graded to course, tighter
    joints and a drafted margin round each face, which is what a plinth, a
    step, a pier and a paved market place are actually built of.

    ## The family rebuild (wave 06)

    Rebuilt onto `masonry_bond` / `masonry_colour` — one geology, one mortar,
    one weathering logic for the whole town, per `ad-town-05` §7. Three
    specific defects went with it:

    - `wobble=0.40` on a 9 x 5 lattice warped the perpends by half a unit, so
      the squarest wall in the town still had wandering joints. `wobble_u` is
      measured in units and this one is 0.09 — a chiselled stone, laid by eye.
    - `cam * 0.16` was a half-sine across the *whole stone*: a 0.40 m dome.
      The drafted margin was fighting it and losing. It is a flat face with a
      22 mm arris now, which is what a drafted margin actually looks like.
    - The +/-21 % per-stone value was authored and then overwritten by two
      `tint(..., 0.45)` calls. It is applied last, at +/-24 %.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    # Squared and graded by a jobbing mason, and on the town's plinths and
    # steps, so it is half-dressed and has been rained on for a century.
    BODY = masonry_body(dressing=0.36, weathered=0.22)
    m.set_base(BODY)

    # Squared and graded: a 0.22 m rise and a 0.40 m stone, which is a plinth
    # course, a step, a pier and a paved market place. Everything a mason
    # squared before he laid it.
    joint, ident, face, arris = masonry_bond(
        m, size, seed + 81, course_m=2.0 / max(courses, 2), stone_m=0.40,
        joint_mm=16.0, arris_mm=22.0, wobble_u=0.09, stagger=0.30, vary=0.13,
        camber=0.03)

    # Boaster tooling and punch work: two noise scales in the height per Art
    # Bible §8, and they live inside the arris so they stop at the chamfer.
    tool = normalize01(fibre(size, 34.0, seed + 82, along="u", warp_amp=0.35))
    m.add_height((tool - 0.5) * 0.08 * arris)
    m.add_height((normalize01(fbm(s, 40, seed + 83, octaves=3)) - 0.5)
                 * 0.11 * face)

    bio = masonry_colour(m, size, seed + 84, joint, ident, face,
                         spread=0.24, warm=0.30, cool=0.24, patina=0.12,
                         grain=0.10, lichen=0.26 * moss, mortar=0.58, tool=0.05)

    m.rough(0.79, 0.12, 0.07, seed + 87)
    m.roughness = np.clip(m.roughness + joint * 0.12 + bio * 0.30, 0.03, 1.0)
    m.cavity_dirt(joint * 0.85, 0.34)
    m.hold_to(BODY, 0.5)
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

    # Hand-ground pigment in an oil or milk binder is never one value: it is
    # laid on in strokes, it sinks into the grain unevenly, and it chalks in the
    # sun. Without this the paint read as a solid fill with mud spots on it —
    # `painted_crimson` measured L* sigma 0.93.
    m.albedo_break(0.28, 0.14, seed + 105, broad_freq=5, fine_freq=28, warm=0.22)

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
    """The family, dressed: squared blocks, fine joints, tooled faces.

    The same limestone as `rubble` and `stone`, cut by a mason who was paid
    properly. That is the whole difference and it is the difference that
    carries the story: the guild is the only building in Hearthmere built by
    outside money to outside standards, and regular ashlar against everyone
    else's rubble-and-plaster says so without a word of exposition. This key is
    also the town's DRESSINGS — quoins, jambs, sills, string courses,
    voussoirs — which is why it has to sit against `rubble` on the same wall
    without reading as a different rock.

    ## Wave 06

    Its joint was 0.008 of a 0.286 m unit — **4.6 mm, or 1.2 texels** at the
    shipped 256 px/m. Physically correct for fine ashlar and completely
    invisible: it filters to nothing in the first mip, which is why every
    ashlar surface in the build reads as a blank pale slab past 10 m and why
    `ad-town-05` §7 counts "giant-plate ashlar" as its own treatment. The
    mortar is floored at three texels now (see `masonry_bond`), and the base
    moved from `#B3A894` — a stone of its own, paler and warmer than anything
    else in the town — onto the family body.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    # Properly dressed, and old: these are the quoins and jambs that have taken
    # every cart wheel and every winter since the church was built.
    BODY = masonry_body(dressing=0.74, weathered=0.14)
    m.set_base(BODY)

    # 0.30 m courses, 0.60 m blocks, laid square: a real ashlar module. The
    # joint is 12 mm, which is three texels and the smallest line that
    # survives to the 40 m LOD.
    jm, blk, face, arris = masonry_bond(
        m, size, seed + 130, course_m=0.30, stone_m=0.60,
        joint_mm=12.0, arris_mm=14.0, wobble_u=0.035, stagger=0.16, vary=0.06,
        camber=0.02)

    # Tooled face: fine chisel marks, inside the arris.
    m.add_height(ridged(s, 64, seed + 131, octaves=2) * 0.09 * arris)

    bio = masonry_colour(m, size, seed + 132, jm, blk, face,
                         spread=0.19, warm=0.26, cool=0.22, patina=0.12,
                         grain=0.13, lichen=0.16, mortar=0.50, tool=0.06)

    m.rough(0.68, 0.11, 0.06, seed + 133)
    m.roughness = np.clip(m.roughness + bio * 0.22, 0.03, 1.0)
    m.cavity_dirt(jm * 0.8, 0.35)
    m.hold_to(BODY, 0.5)
    return m


def banner_cloth(name="banner", size=512, seed=0, colour=P.GUILD_CRIMSON):
    """Heavy dyed wool for banners. Uneven dye, sun-fade, frayed lower edge.

    Sun-fade is authored as a TINT toward `CANVAS_CREAM`, not as `lighten`.
    `lighten` walks a colour toward white, which is the one direction that
    destroys both chroma and hue at once; the first pass used it at 0.20 over
    the top half of the sheet, and the guild's banner shipped a dusty pink
    measured 6.3 (then 7.4 once the seed was made deterministic) against §4.
    Real sun-faded madder goes toward the undyed wool underneath it, which is a
    warm cream — same hue family, lower chroma, and §5 gets its wear anyway.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(colour)

    m.add_height(weave(size, 200, seed + 141, slub=0.30) * 0.16 +
                 fbm(s, 22, seed + 141) * 0.08)

    # Vat-dyed wool is never even; the blotching is what stops it reading as
    # a flat colour swatch. Kept symmetric about the base so the mean holds.
    blotch = normalize01(fbm(s, 5, seed + 142, octaves=3))
    m.darken(smoothstep(0.55, 0.0, blotch), 0.16)
    m.tint(P.shade(colour, 1.30), smoothstep(0.6, 1.0, blotch) * 0.45)

    # Sun-bleached toward the hanging edge (the top gets the weather), dirt and
    # damp at the bottom where it hangs against the wall.
    _v, _u = _uv(size)
    m.tint(P.shade(colour, 1.55), smoothstep(0.5, 0.0, _v) * 0.55)
    m.cavity_dirt(smoothstep(0.84, 1.0, _v) * 0.7, 0.30)

    # Fraying: the lower edge loses threads, which is the one asymmetry every
    # hanging textile in the town has.
    fray = smoothstep(0.93, 1.0, _v) * smoothstep(0.45, 0.8,
                                                  normalize01(fbm(s, 40, seed + 144)))
    m.add_height(-fray * 0.3)

    # Hand-dyed wool is the LEAST even colour in the town — a vat dyes unevenly,
    # the cloth takes it differently where it was folded, and the light strikes
    # a nap differently along its length. The blotch pass above is a single
    # 5-cycle field worth 0.16 of darkening, which measured out at L* sigma 1.1
    # across the whole `banner` + `cloth_*` family: six materials rendering as
    # flat vinyl, which is precisely the §5 "painted cardboard" failure.
    m.albedo_break(0.32, 0.16, seed + 145, broad_freq=5, fine_freq=34, warm=0.22)

    m.rough(0.90, 0.07, 0.05, seed + 143)
    m.hold_to(colour, 0.85)
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


# Skin and hair builders lived here. Removed with the townsfolk venue — see
# D-012. Characters are out of scope for v2, and a character material set is
# authored against a skinned mesh, not against this environment pipeline.


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
    # Poured wax is cloudy where it cooled fast against the seal and clear where
    # it stayed molten, and it picks up soot from the taper that melted it. This
    # was the flattest albedo in the entire library at L* sigma 0.37, which
    # reads as a solid moulded bead rather than as poured wax.
    m.albedo_break(0.30, 0.16, seed + 194, broad_freq=6, fine_freq=30, warm=0.25)
    m.rough(0.22, 0.10, 0.06, seed + 193)
    return m


# ---------------------------------------------------------------------------
# Ground cover
# ---------------------------------------------------------------------------
# The terrain is the largest surface in the build by two orders of magnitude,
# so its materials get the same treatment as a hero building rather than being
# treated as backdrop. Each of these is a distinct *substrate*, not a tint of
# the others: turf, wet silt, loose shingle, submerged bed, open water. Using
# one brown for all ground is what makes procedural terrain read as a
# heightmap with a texture on it.

def meadow_grass(name="grass", size=1024, seed=0):
    """Cropped meadow turf — the default cover outside the trodden town.

    Grass has to survive being looked at from 100 m and from 1 m. What carries
    that is not blade detail (which mips away by 15 m) but CLUMP structure: a
    Worley cell field at ~25 cm giving tussocks, under broad 2-4 m patches of
    drier and greener ground. Uniform green turf is the golf-course tell and
    reads as a shader default from any distance.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base("#5E7A3E")

    # Tussocks. f2f1 gives the parting between clumps, which is where the
    # thatch and the soil show through.
    clump = worley(s, 34, seed + 201, metric="f2f1")
    m.add_height(clump * 0.45 + ridged(s, 300, seed + 202, octaves=2) * 0.22)
    m.darken((1.0 - normalize01(clump)) * 0.8, 0.30)

    # Patchiness — drainage, wear, and where the sun bakes it off.
    #
    # Frequency 13, not 5. This tile covers 6 m of world and repeats ~30 times
    # across the town; anything in it at 1-2 m reads from the air as a regular
    # quilt, and it did. Low-frequency ground colour is world-space
    # information and belongs in COLOR_0 (venues/terrain.py), not in a texture
    # that tiles. What stays here is sub-metre.
    patch = normalize01(fbm(s, 13, seed + 203, octaves=4))
    m.tint("#7C8F46", smoothstep(0.5, 1.0, patch) * 0.75)     # sun-dried
    m.tint("#40602F", smoothstep(0.5, 0.0, patch) * 0.65)     # damp hollows
    m.lighten(smoothstep(0.72, 1.0, patch), 0.12)

    # Bare soil showing through where the turf is thin, plus seed heads.
    thin = smoothstep(0.80, 0.93, normalize01(fbm(s, 11, seed + 204, octaves=3)))
    m.tint("#6E5C46", thin * 0.7)
    heads = smoothstep(0.88, 0.97, normalize01(worley(s, 60, seed + 205, metric="f2f1")))
    m.lighten(heads, 0.22)
    m.tint("#B7A863", heads * 0.5)

    # Leaves are glossier than they look, and that sheen stops turf reading
    # as felt.
    m.rough(0.62, 0.16, 0.09, seed + 206)
    m.cavity_dirt((1.0 - normalize01(clump)) * 0.6, 0.22)
    return m


def town_earth(name="earth", size=1024, seed=0):
    """Trodden ground between the buildings: the town's default surface.

    Deliberately NOT `beaten_earth`. That one is authored for a 2 m tile in the
    blacksmith's yard, and on a 4 m terrain tile its broad fbm resolves into
    half-metre pale clouds with no detail between them — the ground read as
    brown paper with mould on it in the first terrain render, and the grit that
    was supposed to carry the close read sat at 4 cm and mipped away by 3 m.

    So this is authored the other way round: almost no low-frequency albedo at
    all (world-scale colour is COLOR_0's job on a surface this large), and all
    the energy between 2 cm and 30 cm where the player actually stands.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base("#6E5C46")

    # Structure: a packed gravel-and-clay surface.
    #
    # ## This was the fifth crazy paving, and nobody had named it (D-050)
    #
    # `bailey-walk-04`, bottom right, 2 m from the eye: the ground the player
    # is standing on is a field of **straight-sided polygons packed edge to
    # edge with hairline creases between them, every plate the same value** —
    # visually identical to the `cobble` defect and to `ad-town-04` §8's
    # "crocodile skin". It is the surface under the player in half the frames
    # in the review set and no pass has ever named it, because everyone was
    # looking at the paving.
    #
    # It is the same mechanism. `worley(..., "f2f1")` is ~0 at a cell boundary
    # and rises through the interior, so using it directly as height turns
    # EVERY cell into a raised plate: 100 % stone coverage, a complete
    # tessellation. Packed ground is not a tessellation of stone. It is earth
    # with the stones that have worked to the surface showing through it —
    # about a third of the area, and the rest is dirt.
    #
    # The per-stone value had the second half of the same defect: `per` was an
    # independent `fbm(s, 46)`, a field at roughly the stone frequency but not
    # REGISTERED to the stones, so its light and dark blur across cell
    # boundaries and every plate ends up the same value. `worley(metric="id")`
    # is one stable value per cell — the fix this module already documents on
    # `mathx.worley` and applies in `cobblestone` and `rubble_weathered`.
    sgap = normalize01(worley(s, 30, seed + 251, metric="f2f1"))    # ~13 cm
    sid = worley(s, 30, seed + 251, metric="id")
    fines = worley(s, 88, seed + 252, metric="f2f1")                # ~4.5 cm
    # Which stones are proud. ~35 % of cells; the rest of the surface is earth.
    proud = smoothstep(0.30, 0.72, sid)
    stones = smoothstep(0.12, 0.58, sgap) * proud
    m.add_height(stones * 0.32 + fines * 0.14 + fbm(s, 150, seed + 253) * 0.10)

    # Per-stone value, keyed to the CELL so a stone is one object. Low
    # contrast: this is dust-covered gravel, not shingle, and it only applies
    # where there is a stone at all.
    per = np.floor(sid * 5.0) / 5.0
    m.darken(per * 0.8 * stones, 0.20)
    m.lighten(smoothstep(0.55, 1.0, per) * stones, 0.15)
    m.tint(P.COBBLE_WORN, smoothstep(0.45, 1.0, per) * stones * 0.42)
    m.tint("#5A4632", smoothstep(0.35, 0.0, per) * stones * 0.45)
    # The earth between them, which is now most of the surface and has to be a
    # surface in its own right rather than a background colour.
    earth = 1.0 - stones
    m.darken(earth * normalize01(fbm(s, 22, seed + 260, octaves=3)) * 0.9, 0.16)
    m.albedo_break(0.16, 0.10, seed + 261, broad_freq=14, fine_freq=52, warm=0.20)

    # Cart ruts and boot scuffs. HEIGHT and roughness only — putting them in
    # albedo is what produced the cloud blotches, because a 4 m tile repeats
    # thirty times across the town and any albedo feature above a metre becomes
    # a visible quilt.
    ruts = fbm(s, 6, seed + 255, octaves=3)
    m.add_height(ruts * 0.26)

    # Residue at ground level: straw and chaff, and the dark specks of trodden
    # muck. Art Bible §7 — evidence of use, at the scale it is actually seen.
    #
    # Gated by a sparse mask, and only 5% of the surface. Ungated, a ridged
    # field thresholded at 0.90 covers a fifth of every square metre and the
    # ground renders as a carpet of yellow noodles — straw does not lie evenly,
    # it collects where a cart stopped.
    sparse = smoothstep(0.62, 0.86, normalize01(fbm(s, 5, seed + 259, octaves=2)))
    straw = smoothstep(0.93, 0.99, normalize01(ridged(s, 34, seed + 256, octaves=2))) * sparse
    m.tint("#A8975F", straw * 0.55)
    m.add_height(straw * 0.08)
    muck = smoothstep(0.86, 0.96, normalize01(worley(s, 26, seed + 257)))
    m.tint("#3A2E22", muck * 0.65)

    # Damp in the ruts, dusty on the high spots.
    m.rough(0.90, 0.07, 0.07, seed + 258)
    m.roughness = np.clip(m.roughness - smoothstep(0.3, 0.9, normalize01(-ruts)) * 0.16, 0.05, 1.0)
    m.cavity_dirt((1.0 - stones) * 0.45, 0.22)
    return m


def river_mud(name="mud", size=1024, seed=0):
    """The wet margin: silt at the waterline, always dark, always shining.

    This band is what makes water read as water. Without a distinct wet strip
    the shoreline is a hard line between grass and a blue plane, which is the
    most common giveaway of procedural terrain.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base("#4E4033")

    # Silt is smooth at scale and cracked where it dries between floods.
    m.add_height(fbm(s, 7, seed + 211, octaves=4) * 0.28 + fbm(s, 40, seed + 212) * 0.10)
    crack = 1.0 - smoothstep(0.0, 0.05, worley(s, 18, seed + 213, metric="f2f1"))
    m.add_height(-crack * 0.30)
    m.cavity_dirt(crack * 0.6, 0.30)

    # Hoof and boot prints holding standing water — the darkest, glossiest bits.
    prints = smoothstep(0.74, 0.88, normalize01(worley(s, 22, seed + 214)))
    m.darken(prints, 0.42)
    m.add_height(-prints * 0.22)

    # Embedded gravel and the weed wrack left by the last high water.
    grit = smoothstep(0.78, 0.92, normalize01(worley(s, 52, seed + 215, metric="f2f1")))
    m.lighten(grit, 0.30)
    m.add_height(grit * 0.16)
    weed = smoothstep(0.84, 0.95, normalize01(fbm(s, 14, seed + 216, octaves=3)))
    m.tint("#4A5C33", weed * 0.55)

    m.rough(0.44, 0.18, 0.08, seed + 217)
    m.roughness = np.clip(m.roughness - prints * 0.30, 0.04, 1.0)
    return m


def river_gravel(name="gravel", size=1024, seed=0):
    """Loose river shingle; also the scree on the terrace scarps.

    Deliberately distinct from `cobble` (laid paving) and `stone` (coursed
    rubble): shingle is unsorted, rounded, and has no bond pattern at all.
    Reusing cobble here would put a made street surface on a riverbank.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base("#8C8272")

    # ## The crocodile skin (D-050)
    #
    # `bailey-walk-04`, bottom right, 2 m from the eye. This is the surface at
    # the foot of the enceinte and it rendered as **straight-sided angular
    # plates packed edge to edge with hairline creases, every plate the same
    # value** — `ad-town-04` §8's "crocodile skin", and the same failure as
    # `cobble` and `town_earth`. Shingle is the one ground in the library that
    # is genuinely unsorted and genuinely has no bond, so `worley` is the right
    # generator here. What was wrong is that it was used as a **complete
    # tessellation**: `(1 - big)` is nonzero over every cell, so every cell got
    # a stone and the bank came out as one continuous crazed plane.
    #
    # A shingle bank is stones ON silt, and you can see the silt. The
    # difference between shingle and crazy paving is the same difference as
    # between a cobbled street and a patio: **coverage below 1.0, and value
    # keyed to the stone.**
    big_d = worley(s, 26, seed + 221)
    big_id = worley(s, 26, seed + 221, metric="id")
    small = worley(s, 64, seed + 222)
    # Which stones are there at all. ~55 % of the coarse cells carry a stone;
    # the rest is the silt and sand they are lying in.
    lie = smoothstep(0.18, 0.62, big_id)
    stone = np.clip(1.0 - big_d, 0, 1) * lie
    m.add_height(stone * 0.46 + (1.0 - small) * 0.16 * (0.35 + 0.65 * lie))
    edges = (1.0 - smoothstep(0.0, 0.18,
                              worley(s, 26, seed + 221, metric="f2f1"))) * lie
    m.add_height(-edges * 0.30)

    # Per-stone colour keyed to the CELL. `fbm(s, 40)` is a field at roughly
    # the stone frequency but NOT registered to the stones, so its light and
    # dark blur across boundaries and every stone comes out the same value —
    # the second half of why this read as one crazed plane. `worley(id)` is one
    # value per stone, which is what `mathx.worley` documents it for.
    per = np.floor(big_id * 6.0) / 6.0
    m.darken(per * 0.9 * stone, 0.26)
    m.lighten(smoothstep(0.5, 1.0, per) * stone, 0.32)
    m.tint(P.COBBLE_WORN, smoothstep(0.30, 0.0, per) * stone * 0.55)
    m.tint("#A08A6C", smoothstep(0.62, 1.0, per) * stone * 0.38)
    # The silt between them, darker and damper than the stone standing in it.
    m.darken((1.0 - stone) * (0.4 + 0.6 * normalize01(fbm(s, 30, seed + 225))),
             0.22)
    m.albedo_break(0.14, 0.09, seed + 226, broad_freq=16, fine_freq=58, warm=0.20)

    m.cavity_dirt(edges * 0.9 + (1.0 - stone) * 0.35, 0.35)
    m.rough(0.78, 0.13, 0.08, seed + 224)
    return m


def river_bed(name="riverbed", size=1024, seed=0):
    """Submerged bed: shingle under weed, seen through moving water.

    Darker, greener and much smoother than dry shingle, because it is always
    wet and because anything viewed through water loses contrast fast.
    """
    m = river_gravel(name, size, seed + 40)
    s = (size, size)
    m.darken(np.ones(s, np.float32), 0.34)
    m.tint("#2E4436", 0.42)                        # depth-tinted green

    # Weed streamers, aligned by the current rather than isotropic.
    weed = smoothstep(0.55, 0.85, normalize01(fbm(s, 6, seed + 231, octaves=4)))
    streamer = smoothstep(0.5, 0.9, normalize01(ridged(s, 30, seed + 232, octaves=2)))
    m.tint("#3C6B44", np.clip(weed * streamer, 0, 1) * 0.75)
    m.add_height(weed * streamer * 0.18)

    # Silt drifts in the slack water.
    silt = smoothstep(0.6, 0.9, normalize01(fbm(s, 4, seed + 233, octaves=3)))
    m.tint("#4E4033", silt * 0.5)

    m.rough(0.30, 0.10, 0.05, seed + 234)
    return m


def water_surface(name="water", size=1024, seed=0, flow=0.0):
    """The Mere and the Emberflow.

    Opaque, very smooth and dark green rather than glTF-transmissive: at the
    locked 09:30 rig the PMREM sky dome is the dominant term, so a roughness
    ~0.06 surface picks up sky and sun glint and reads unmistakably as water.
    Transmission would buy a little bed show-through at the cost of sort order
    across a 150 m lake; the shallow margin is instead carried by the mud band
    and by per-vertex depth tinting on the water mesh (see venues/terrain.py).

    Two ripple scales, because one gives a repeating quilt: long wind-driven
    swell plus fine capillary chop.

    Colour is derived from §4's VERDIGRIS rather than from a literal. §4 has no
    water row, and the first pass invented `#28453F` for it — which the palette
    checker read at 8.6, its worst offender in the whole library, because an
    invented colour has no family to be measured against. Deep still water IS
    the copper-green family at low value: same hue, lower lightness, and
    lightness is the one axis §5 requires to vary.

    Value raised from `shade(..., 0.30)` to `0.55`. At 0.30 the derivation was
    still 6.8 off §4 measured pixel-wise, because the metric only discounts
    lightness to a quarter and a shade that deep is 40 L away from the family
    it claims. It was also wrong on its own terms: the albedo of a lake at
    09:30 is nearly irrelevant next to the sky it reflects, so authoring it near
    black bought no darkness in the render and cost the palette read.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    # More IRON and a higher value than the 0.34/0.50 this shipped at, which
    # fixes a visual defect and a metric one with the same move.
    #
    # Visually: at 0.34 iron the Mere rendered as a saturated turquoise, which
    # belongs to a warm sea and not to a northern river town — the swatch sheet
    # reads it next to `algae` and `verdigris` and all three are the same
    # colour. A mere fed by an upland river is grey-green; its chroma comes
    # from the sky it reflects, not from its own albedo.
    #
    # Metrically: the remaining 5.4 was almost entirely the lightness term.
    # §4's checker discounts lightness to a quarter, but the old DEEP sat 22 L*
    # below VERDIGRIS, and a quarter of 22 is 5.5 on its own — the whole
    # warning. Chroma BELOW the palette costs nothing, so desaturating toward
    # iron is free under the metric and correct in the render; raising the
    # value is what actually pays the warning off. Both directions agree, which
    # is the sign that the palette rule and the eye want the same thing here.
    # Chroma comes DOWN again, from mix 0.52 to 0.74. `ad-town-05` §2 measured
    # the result of 0.52 in three frames and called it "tropical emerald-teal"
    # in `t-gate-north` at 8 m and "a solid opaque emerald sheet" in
    # `t-approach-ne`, and it is right: at 0.52 the linear albedo runs
    # R:G:B = 0.37 : 1.00 : 0.69, so the DIFFUSE term — which at 09:30 with a
    # 3.2-intensity sun is not small — is four times greener than it is red,
    # and no amount of specular work can pull a frame back from that. A mere
    # fed by an upland river is a grey-green whose colour is the sky it
    # reflects; the albedo's job is to be dark and nearly neutral so the sky
    # has somewhere to land. At 0.74 the ratio is 0.48 : 1.00 : 0.71, which is
    # about what a still northern lake measures off a colour chart.
    #
    # This is free under §4's metric, which discounts chroma BELOW the palette
    # entirely and only charges lightness — and the lightness is unchanged.
    DEEP = P.shade(P.mix(P.VERDIGRIS, P.IRON, 0.74), 0.80)
    SLACK = P.shade(P.mix(P.VERDIGRIS, P.IRON, 0.60), 0.92)
    m.set_base(DEEP)

    swell = fbm(s, 4, seed + 241, octaves=3)
    chop = ridged(s, 26, seed + 242, octaves=3)
    fine = fbm(s, 70, seed + 243, octaves=2)
    m.add_height(swell * 0.55 + chop * 0.30 + fine * 0.12)

    # Wind lanes, and the paler scatter where the chop catches the sky.
    lanes = normalize01(fbm(s, 3, seed + 244, octaves=3))
    m.tint(SLACK, smoothstep(0.45, 1.0, lanes) * 0.6)
    m.tint(P.shade(SLACK, 1.35), smoothstep(0.62, 0.95, normalize01(chop)) * 0.5)
    m.darken(smoothstep(0.5, 0.0, lanes) * 0.7, 0.12)

    if flow > 0:
        # A river is not a lake with the same texture on it. Current shears the
        # surface into lanes that run WITH the flow and lace it with the pale
        # standing ripples that form over a shallow bed — the two things that
        # make moving water legible in a still frame.
        lace = normalize01(ridged(s, 14, seed + 246, octaves=3))
        drag = fibre(size, 9.0, seed + 247, along="v", warp_amp=0.35)
        m.add_height(drag * 0.32 * flow + lace * 0.20 * flow)
        m.tint(P.shade(SLACK, 1.5), smoothstep(0.55, 0.95, lace) * 0.55 * flow)
        m.roughness = np.clip(m.roughness + drag * 0.10 * flow, 0.03, 1.0)
        # Foam collects on the slack side of every ripple crest.
        foam = smoothstep(0.86, 0.98, lace * (0.6 + 0.4 * drag)) * flow
        m.tint(P.mix(P.PLASTER, P.VERDIGRIS, 0.25), foam * 0.8)
        m.roughness = np.clip(m.roughness + foam * 0.55, 0.03, 1.0)

    # Very smooth but NOT uniform (Art Bible §5): ruffled patches are rougher,
    # and that variance is what makes the reflection break up instead of
    # sitting on the surface as one mirror.
    #
    # The floor is 0.13, not 0.05. At 0.05 the sun's specular lobe is narrow
    # enough that a single aerial frame catches it as one blown-white blob the
    # size of the quay — bloom then takes it to pure white and the lake reads
    # as a hole in the terrain. A ruffled lake never mirrors that hard.
    #
    # Raised from 0.12/0.06 when the Mere moved in to the town (D-024): the
    # water is now IN two of the three hero frames rather than 40 m behind
    # them, and at the grazing angle you get standing on the quay or the
    # bridge approach the glitter path along the far bank was still clipping
    # to white through the bloom pass.
    # The floor is 0.21, up from 0.13, and the variance is nearly as large as
    # the base. Both halves matter and the second is the important one.
    #
    # A GGX lobe's peak goes as roughness^-4, so 0.13 is asking for a mirror
    # and the sun answered with a blown plate. But roughness alone cannot fix
    # it: GGX conserves energy, so a rougher surface spreads the SAME light
    # over more area. Measured at floor 0.30 the blown region grew from 40% of
    # the Mere to 85% of it — a worse frame at a lower peak. The specular has
    # to be BROKEN UP, not spread, and that is what the wind-lane variance
    # here and the per-vertex swell in `venues/terrain._water` do between them.
    #
    # 0.21 is also the honest floor. A mere with a working quay on it is
    # ruffled by wind at every hour the game is set at; glass-calm water is a
    # dawn condition and the locked rig is 09:30.
    m.rough(0.26, 0.15, 0.06, seed + 245)
    m.roughness = np.clip(m.roughness + smoothstep(0.40, 1.0, lanes) * 0.20, 0.21, 1.0)
    if flow > 0:
        # Moving water is rougher still: the surface is being continuously
        # broken by the bed, so a river never mirrors the way a lake can.
        m.roughness = np.clip(m.roughness + 0.08 * flow, 0.21, 1.0)
    m.metalness[:] = 0.0
    m.ao[:] = 1.0
    return m


def water_foam(name="foam", size=512, seed=0):
    """The WRACK line at the waterline. Alpha sheet, symmetric across V.

    Every lake and every slow river has one, and it is the difference between
    a shoreline and a boundary between two polygons. Wind pushes scum, pollen,
    duckweed and dead reed against the lee shore, and the water thins to
    nothing there, so a band of broken material collects along the exact
    contour where the surface meets the ground.

    It is NOT white. `ad-town-05`'s `t-aerial-sw` shows this material as a hard
    white scalloped ring round the north-east of the Mere, and that is what a
    near-`PLASTER_SHADE` base at 0.90 roughness does under a 3.2-intensity sun
    once bloom has had it — the brightest thing in the frame drawn as a
    continuous outline round the lake, which is the single most artificial
    reading available. Standing-water wrack is olive-brown: rotted reed, dead
    weed, pollen scum and pond litter, all of it darker than the water it
    floats on and much darker than the sand behind it. Aerated white water is a
    different substance and now has its own material (`water_fall`); the mill
    wheel's tail race is the one place in Hearthmere that has any right to it.

    Symmetric across V rather than gradient, because the marching-squares
    contour that carries it has no consistent handedness — a one-sided
    gradient would face landward on half the lake and lakeward on the other.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    v, _u = _uv(size)
    # Derived from ONE family, not mixed halfway between two. A 50/50 of
    # OAK_WEATHERED and HERB_GREEN sits between both in hue and §4's checker
    # charges hue in full, so it measured 9.6 against a fail threshold of 9.0.
    # Duckweed and pond scum ARE the herb-green family at low lightness and low
    # chroma, and §4 charges lightness at a quarter and chroma-below-palette at
    # nothing — so the honest colour and the cheap one are the same colour.
    m.set_base(P.shade(P.mix(P.HERB_GREEN, P.IRON, 0.30), 0.78))

    # Across-the-ribbon profile: densest on the line, gone by the edges.
    core = np.clip(1.0 - np.abs(v * 2.0 - 1.0), 0, 1) ** 0.75
    # Broken into lumps and streaks, or it is a painted stripe. Two scales: the
    # long wind-drawn windrows and the individual bubble rafts inside them.
    rows = normalize01(fbm(s, 5, seed + 301, octaves=3))
    raft = normalize01(worley(s, 26, seed + 302, metric="f2f1"))
    lump = normalize01(fbm(s, 48, seed + 303, octaves=3))
    cover = np.clip(core * (0.35 + 0.95 * rows) * (0.45 + 0.75 * lump), 0, 1)
    # Thinner than it was: 0.30/0.62 kept about two-thirds of the ribbon, so
    # even a broken texture read as a solid band at 40 m. 0.44/0.78 keeps
    # roughly a third, and the ribbon reads as drift rather than as an outline.
    alpha = smoothstep(0.44, 0.78, cover)
    m.cut(alpha, feather=0.18)

    # Bubbles read by their shadow, not their colour: a foam raft is a lot of
    # tiny hemispheres and what you see is the dark between them.
    m.add_height(raft * 0.42 + lump * 0.20)
    m.cavity_dirt((1.0 - raft) * 0.55, 0.30)
    # Duckweed in the slack of the windrows; rotted reed and silt everywhere
    # else. A pale fleck of actual froth survives, but as a minority.
    m.tint(P.HERB_GREEN, smoothstep(0.62, 0.92, rows) * 0.55)
    m.tint(P.shade(P.OAK_WEATHERED, 0.82), smoothstep(0.55, 0.0, rows) * 0.30)
    m.tint(P.PLASTER_SHADE, smoothstep(0.90, 1.0, normalize01(raft)) * 0.30)
    m.albedo_break(0.22, 0.14, seed + 304, broad_freq=6, fine_freq=30, warm=0.18)
    m.rough(0.90, 0.08, 0.05, seed + 305)
    m.metalness[:] = 0.0
    return m


def water_fall(name="water_fall", size=512, seed=0):
    """Falling water: a fountain jet, a weir lip, the mill race's overshot.

    A separate material from `foam` for one measurable reason. `foam` is
    alpha-MASKED, and an alpha mask on a 0.09–0.30 m ribbon is a trap: at 6 m
    the ribbon is thirty pixels wide and samples mip 0, where the lace is
    dense; at 12 m it is three pixels wide and samples mip 4, where the same
    lace has averaged to about 0.3 — under the alpha-test threshold, so every
    fragment is discarded and THE WATER DISAPPEARS. That is the whole of
    `ad-town-05` §9: "`fountain-free` at 6 m has falling water; `t-square` at
    12 m has none". Nothing was culling it. It was mipping out of existence.

    So this is a BLEND material. Blending has no threshold, so a ribbon that
    covers a third of a pixel contributes a third of a pixel of white and the
    fall survives to any distance the geometry does. It also fixes the other
    half of the same finding — "hard-edged opaque pale ribbons stuck to the air
    with no transparency" — because falling water IS translucent, brightest
    where the sheet folds and nearly clear where it is stretched thin.

    Structure, across V (which `_fall` runs down the drop) and U (across the
    ribbon): the sheet leaves the rim coherent, necks, breaks into strands, and
    is spray by the time it lands. Across the ribbon it is dense in the middle
    and ragged at the edges. Both are what the eye actually reads on a jet.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    v, u = _uv(size)
    # Aerated water is nearly white but never pure white — it takes the colour
    # of what it is falling through and a little of the basin under it.
    m.set_base(P.mix(P.PLASTER, P.VERDIGRIS, 0.10))

    # Down the fall: coherent at the lip, stranded in the middle, spray at the
    # bottom. `v` is 0 at the rim.
    strands = normalize01(fibre(size, 26.0, seed + 411, along="v", warp_amp=0.55))
    breakup = normalize01(fbm(s, 9, seed + 412, octaves=4))
    coherent = 1.0 - smoothstep(0.02, 0.55, v)
    shred = smoothstep(0.30, 1.0, v)

    # Across the ribbon: full in the middle, torn at the edges.
    core = np.clip(1.0 - np.abs(u * 2.0 - 1.0), 0.0, 1.0) ** 0.55

    dens = np.clip(core * (coherent + (1.0 - coherent) *
                           (0.30 + 0.85 * strands) * (0.45 + 0.80 * breakup)), 0.0, 1.0)
    # Spray thins the tail rather than cutting it: droplets are small and many.
    dens = dens * (1.0 - 0.45 * shred * (1.0 - smoothstep(0.35, 0.85, strands)))
    # This lands in the albedo's alpha channel exactly as `cut` does, but the
    # LIBRARY entry flags it `blend`, so it is read as OPACITY and never
    # thresholded — which is the entire point of the material. Ceiling under 1
    # so even the coherent core is water and not paint.
    m.cut(np.clip(dens * 0.94, 0.0, 1.0))

    # The white of falling water is froth, and froth reads by its shadowing.
    m.add_height(strands * 0.55 + breakup * 0.25)
    m.cavity_dirt((1.0 - strands) * 0.35, 0.16)
    # A hint of the sky in the sheet where it is stretched and clear.
    m.tint(P.mix(P.VERDIGRIS, P.PLASTER, 0.55), coherent * core * 0.30)
    m.rough(0.22, 0.14, 0.05, seed + 413)
    m.metalness[:] = 0.0
    m.ao[:] = 1.0
    return m


# ---------------------------------------------------------------------------
# Roofing
# ---------------------------------------------------------------------------
# A town's roofscape is half its silhouette and, from the aerial and top-down
# views the Directive requires, most of its visible surface area. One roof
# material across ninety buildings is what makes a procedural town read as a
# single extruded object, so the roof family is deliberately the widest in the
# library: two clay grades, slate, lead, copper, and thatch.

def slate_roof(name="slate", size=1024, seed=0):
    """Riven slate in diminishing courses. Wealthier roofs; §4 SLATE.

    Slate is split, not moulded, so every slate is a different thickness and
    sits at a slightly different angle. That variance is the entire read — a
    slate roof with uniform courses is a corrugated sheet, and it is the most
    common way this material fails.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(P.SLATE)

    # 0.16 m exposure (Art Bible §3) on the registry's 4 m tile = 25 courses.
    # Slates are wider than they are exposed, so 12 across at 0.33 m.
    joint, unit, ty, tx = coursed(size, 25, 12, bond=0.5, joint=0.018,
                                  wobble=0.5, seed=seed + 301)
    # Each slate is a flat plate that laps the one below. The lap shadow at the
    # head of the course is what gives a slate roof its horizontal banding.
    lap = smoothstep(0.0, 0.10, ty)
    m.add_height((lap - 1.0) * 0.55)
    m.ao = np.clip(m.ao - (1.0 - lap) * 0.5, 0, 1)
    # Individual slates sit proud or sunk by a few millimetres, and a couple
    # have slipped — every old slate roof has at least one.
    m.add_height((unit - 0.5) * 0.16 - joint * 0.35)
    slipped = smoothstep(0.94, 0.99, unit)
    m.add_height(-slipped * 0.5)

    # Riven face: the cleavage plane is not smooth, it is stepped in fine
    # laminations that run with the bedding.
    m.add_height(fibre(size, 55.0, seed + 302, along="u", warp_amp=0.25) * 0.10)

    # Per-slate colour. Welsh-grade slate runs blue-grey to purple-grey to
    # green-grey out of the same quarry.
    m.darken(unit * 0.9, 0.20)
    m.tint(P.mix(P.SLATE, P.IRON, 0.45), smoothstep(0.55, 1.0, unit) * 0.6)
    m.tint(P.mix(P.SLATE, P.HERB_GREEN, 0.30), smoothstep(0.30, 0.0, unit) * 0.45)

    # Lichen. It grows on the exposed tail of each slate, not in the lap, and
    # it is the only warm colour on a cold roof — worth having.
    lichen = smoothstep(0.62, 0.90, normalize01(fbm(s, 9, seed + 303, octaves=3))) * lap
    m.tint(P.mix(P.HERB_GREEN, P.CANVAS_CREAM, 0.45), lichen * 0.5)

    m.rough(0.58, 0.16, 0.09, seed + 304)
    m.roughness = np.clip(m.roughness + lichen * 0.30, 0.03, 1.0)
    m.cavity_dirt((1.0 - lap) * 0.7 + joint * 0.4, 0.30)
    m.hold_to(P.SLATE, 0.7)
    return m


def lead_sheet(name="lead", size=512, seed=0):
    """Milled-by-hand lead for flashings, ridge rolls, valleys and gutters.

    Sand-cast lead is the softest thing on a roof: it takes the shape of what
    it is dressed over, it creeps and ripples with the seasons, and it goes to
    a pale carbonate bloom that is nearly white on the exposed faces and stays
    dark grey in the folds. That bloom is what stops it reading as grey paint.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(P.mix(P.SLATE, P.IRON, 0.40))
    r, _mt = P.METAL_SPEC["iron"]
    # Not fully metallic: the carbonate bloom is a dielectric crust, and pure
    # metal here renders the flashings as black slots between roof planes.
    m.metalness[:] = 0.45

    # Dressing marks — the bossing stick leaves broad soft dents, and the sheet
    # ripples where it has crept down the slope.
    m.add_height(fbm(s, 5, seed + 311, octaves=3) * 0.42 +
                 fbm(s, 17, seed + 312, octaves=2) * 0.16)
    creep = fibre(size, 7.0, seed + 313, along="v", warp_amp=0.30)
    m.add_height(creep * 0.18)

    # Bloom on the weather faces, dark in the folds.
    bloom = smoothstep(0.45, 0.88, normalize01(fbm(s, 8, seed + 314, octaves=4)))
    m.tint(P.mix(P.PLASTER_SHADE, P.SLATE, 0.45), bloom * 0.7)
    m.metalness = np.clip(m.metalness - bloom * 0.35, 0, 1)
    m.roughness = np.ones(s, np.float32)
    m.rough(0.42, 0.20, 0.10, seed + 315)
    m.roughness = np.clip(m.roughness + bloom * 0.35, 0.05, 1.0)

    # Wash streaks below the sheet: lead runoff stains everything under it, and
    # the stain starts on the lead itself.
    m.darken(runs(size, seed + 316, count=7, length=0.6, start=0.15) * 0.8, 0.22)
    m.cavity_dirt(1.0 - normalize01(creep), 0.20)
    return m


def copper_verdigris(name="copper", size=1024, seed=0, aged=0.75):
    """Sheet copper going to verdigris — spire, cupola, weathercock, finials.

    The whole point is the TRANSITION. Uniform green is a painted prop; uniform
    brown is a new roof nobody has. Real copper is brown where it is sheltered
    and rubbed, green where it is washed, and the green arrives in vertical
    RUNS because it is carried down the sheet by rain. `runs()` exists for this.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(P.mix(P.BRONZE, P.IRON, 0.25))
    m.metalness[:] = 1.0

    # Standing seams every 0.5 m, which is how sheet copper is actually laid.
    joint, unit, ty, tx = coursed(size, 3, 4, bond=0.0, joint=0.035,
                                  wobble=0.25, seed=seed + 321)
    seam = 1.0 - smoothstep(0.0, 0.06, np.minimum(tx, 1.0 - tx))
    m.add_height(seam * 0.45)
    # Oil-canning: the pillowing of a thin sheet between its fixings.
    m.add_height(fbm(s, 11, seed + 322, octaves=3) * 0.24)

    # Patina. Two overlapping fields: broad wash zones, plus the runs.
    wash = smoothstep(0.30, 0.75, normalize01(fbm(s, 6, seed + 323, octaves=4)))
    streak = runs(size, seed + 324, count=13, length=0.85, sharpness=2.0)
    patina = np.clip((wash * 0.75 + streak * 0.9) * aged, 0, 1)
    m.tint(P.VERDIGRIS, patina * 0.92)
    m.tint(P.mix(P.VERDIGRIS, P.SKY_FILL, 0.30), smoothstep(0.6, 1.0, patina) * 0.4)
    # Verdigris is a mineral crust: it is not metal and it is not smooth.
    m.metalness = np.clip(m.metalness - patina * 0.95, 0, 1)
    m.add_height(patina * 0.14 + fbm(s, 46, seed + 325) * patina * 0.10)

    # Bare copper survives where hands and weather rub: the seams and the
    # ridge, which is exactly where the eye looks first.
    bare = np.clip(seam * 0.8 - patina * 0.5, 0, 1)
    m.tint(P.BRONZE, bare * 0.7)
    m.metalness = np.clip(m.metalness + bare * 0.6, 0, 1)

    rv, _ = P.METAL_SPEC["verdigris"]
    rb, _ = P.METAL_SPEC["bronze"]
    m.roughness = np.ones(s, np.float32)
    m.rough(rb, 0.16, 0.08, seed + 326)
    m.roughness = np.clip(m.roughness + patina * (rv - rb) + patina * 0.12, 0.05, 1.0)
    m.cavity_dirt(seam * 0.5, 0.22)
    return m


def ridge_tile(name="ridge", size=512, seed=0):
    """Half-round clay ridge and hip tiles, bedded in lime mortar.

    A separate material from the pantile because it is a separate object with a
    separate story: it is the highest, most exposed clay on the building, so it
    is the most weathered, it is bedded in a mortar that cracks and gets
    repointed, and its curvature runs the other way.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(P.TERRACOTTA_AGED)

    # Ridge tiles are ~0.45 m long, so ~4 per 2 m run, laid end to end.
    joint, unit, ty, tx = coursed(size, 1, 4, bond=0.0, joint=0.045,
                                  wobble=0.30, seed=seed + 331)
    # Half-round section across V, plus a taper: hand-thrown tiles are never
    # true and they nest by being slightly conical.
    m.add_height(np.sin(np.clip(ty, 0, 1) * np.pi) * 0.75)
    m.add_height(-joint * 0.6)

    # Mortar bedding squeezed out at the joints, later repointed in a lighter
    # lime. This is the residue Art Bible §7 asks for at material scale.
    mortar = smoothstep(0.25, 0.7, joint) * (0.5 + 0.5 * normalize01(
        fbm(s, 20, seed + 332, octaves=2)))
    m.tint(P.PLASTER_SHADE, mortar * 0.8)
    m.add_height(mortar * 0.2)
    m.roughness = np.ones(s, np.float32)

    # Per-tile firing variance, stronger than the field tiles because these
    # came off the top of the kiln.
    m.tint(P.TERRACOTTA, smoothstep(0.55, 1.0, unit) * 0.6)
    m.darken(unit * 0.7, 0.14)
    m.tint(P.mix(P.TERRACOTTA_AGED, P.IRON, 0.35), smoothstep(0.22, 0.0, unit) * 0.5)

    # Moss on the north flank, and the pale efflorescence salts weep out of.
    moss = smoothstep(0.6, 0.9, normalize01(fbm(s, 7, seed + 333, octaves=3))) * \
        smoothstep(0.15, 0.6, ty)
    m.tint(P.HERB_GREEN, moss * 0.45)
    m.lighten(smoothstep(0.85, 0.98, normalize01(fbm(s, 13, seed + 334))), 0.16)

    m.add_height(fbm(s, 60, seed + 335) * 0.08)
    m.rough(0.70, 0.14, 0.08, seed + 336)
    m.roughness = np.clip(m.roughness + mortar * 0.18 + moss * 0.18, 0.03, 1.0)
    m.cavity_dirt(joint * 0.8, 0.32)
    return m


# ---------------------------------------------------------------------------
# Masonry
# ---------------------------------------------------------------------------
# Five stone materials rather than one, because in a real town the stone tells
# you who paid for the building. Fine ashlar is outside money. Rubble is the
# parish. River cobble walling is what a man builds himself out of the field.
# Limewash is what he does to it when it lets water in. Sandstone is whatever
# the nearest quarry happens to be. Using one grey "stone" everywhere throws
# all of that away and is the single biggest reason a procedural town reads as
# one building repeated.

def ashlar_civic(name="ashlar_civic", size=1024, seed=0):
    """The family, finely dressed: the moot hall, the guild tower, the nave.

    Distinct from `ashlar` by being *finer* in every respect — thinner joints,
    larger stones, a rubbed rather than tooled face. Fine ashlar's whole read
    is that the joints nearly disappear and the surface is carried by
    stone-to-stone colour alone, which means the per-block variance has to do
    all the work.

    ## Wave 06

    "Nearly disappear" was taken literally and the wall disappeared with them.
    At 0.008 of a 0.286 m unit the mortar was 4.6 mm; this key is `hero` class
    and ships at 512 px/m, so that is 2.4 texels — one mip from nothing. The
    review has this as "the church tower behind it is a blank pale slab at
    20 m" (§the two-second list, `fountain-free`) and `uv_density` separately
    warns it at 0.60x. 8 mm now, four texels, and it holds a course line to
    the far LOD. Base colour onto the family body.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    # The top of the dressing axis and the bottom of the weathering one: this
    # is the only stone in Hearthmere that outside money paid for and the only
    # one anyone has ever come back and scoured. It is the family's pale warm
    # end and it has to be, because it is the nave — 55 % of the spawn frame —
    # and the guild tower that closes the market square at 43 m.
    BODY = masonry_body(dressing=1.0, weathered=0.04)
    m.set_base(BODY)

    # 0.30 m courses, 0.75 m stones, 8 mm joint: the finest wall in the town,
    # and still a wall you can see the bond of.
    joint, unit, face, arris = masonry_bond(
        m, size, seed + 341, course_m=0.30, stone_m=0.75,
        joint_mm=8.0, arris_mm=10.0, wobble_u=0.02, stagger=0.10, vary=0.04,
        camber=0.015)
    # Rubbed face: very fine drag lines.
    m.add_height(fibre(size, 90.0, seed + 342, along="v", warp_amp=0.12)
                 * 0.05 * arris)

    # Bed-to-bed banding inside each stone. Freestone is sedimentary and even
    # the finest ashlar shows it; without it the wall reads as plasterboard,
    # which is what the first pass produced.
    _hard, _seam, _within = bedding(size, seed + 3461, beds=30, tilt=0.02)
    m.darken(_hard * 0.7 * face, 0.07)
    m.add_height((_hard - 0.5) * 0.07 * face)

    # Fine ashlar's whole read is stone-to-stone colour, because the joints
    # nearly disappear — so this key needs the WIDEST per-stone spread in the
    # family, not the narrowest, and it shipped with the narrowest (0.17
    # against `rubble`'s 0.28). Measured at 0.4 m it was the second flattest
    # masonry in the town, which is `ad-town-06` §5's "the church tower is a
    # blank pale slab at 20 m" and `mere-walk-03`'s "blank ashlar plane over
    # 40 % of the frame". A freestone wall is quarried a bed at a time and the
    # beds are not the same colour; you can count the stones on Bath Abbey.
    bio = masonry_colour(m, size, seed + 343, joint, unit, face,
                         spread=0.24, warm=0.30, cool=0.24, patina=0.14,
                         grain=0.16, lichen=0.12, mortar=0.45)
    # And a slow drift ACROSS the courses on top of the per-stone value: a
    # lift's worth of stone came off one barge and the next lift did not.
    # Kept deliberately weak and at freq 9, not 6: on the contact sheet at
    # freq 6 and 0.10 the low octave merged into ~0.9 m blooms and the 2 m tile
    # started to read in a 2x2 layup — the tile-repeat rule bites hardest on
    # the smoothest surface in the family, because there is nothing else on it
    # to hide behind.
    lift_v = mottle(size, seed + 3462, freq=9, octaves=2)
    m.darken(smoothstep(0.52, 0.14, lift_v) * face, 0.055)
    m.lighten(smoothstep(0.58, 0.94, lift_v) * face, 0.05)

    # Weathering that only a dressed wall gets: the joints wash clean and the
    # faces hold a fine soot-and-rain patina.
    grime = smoothstep(0.55, 1.0, mottle(size, seed + 344, freq=7, octaves=4))
    m.cavity_dirt(grime * 0.35, 0.20)

    m.rough(0.55, 0.10, 0.07, seed + 345)
    m.roughness = np.clip(m.roughness + bio * 0.20, 0.03, 1.0)
    # Hold to THIS key's body, not to the family's mean. Holding every key to
    # `MASON_BODY` was the second half of the wave-06 collapse: `hold_to` is a
    # per-channel gain onto a target colour, so three keys ending on the family
    # mean at strength 0.6 pulled 60 % of the difference between them straight
    # back out. The rule is one BODY per grade of work, and the hold has to
    # honour the grade or the grade does not ship.
    m.hold_to(BODY, 0.6)
    return m


def rubble_weathered(name="rubble", size=1024, seed=0, courses=6,
                     aspect=1.35, moss=1.0):
    """Random rubble BROUGHT TO COURSE — field stone laid to rough beds.

    ## Why this was rebuilt

    The old version was two interleaved Worley fields. `worley` puts one
    feature point per cell of a uniform lattice, so it is **isotropic by
    construction**: what came out was random polygons with no bedding at all —
    crazy paving, stood on its end and called a wall. The art-director pass
    rejected on it twice (`ad-town-02` §9 and §10), and it is not a minor
    surface: it covers roughly 60% of the pixels in the mandated arrival frame
    (the church piers, the arcade, the reveals) plus the whole town wall.

    Three separate defects, and all three were named in that review:

    1. **No bedding.** Real rubble — including "random" rubble — is *brought to
       course* every 0.18–0.28 m, because a wall carries load and a mason has
       to reach the next lift. `mathx.coursed` lays the beds; stones vary in
       width within a course and the break joints are offset course to course,
       so no vertical joint runs through two.
    2. **Every stone the same value.** There was jitter in the SHAPE and none
       in the albedo, so past ~4 m the whole surface flattened to one grey and
       Art Bible §8's "variation from at least two noise sources" was met by
       one. Stone value now spreads +/-18% per stone from `coursed`'s own
       per-stone identity, and a second low-frequency mask moves whole LIFTS
       so the courses read as separate days' work.
    3. **Green mortar.** The joint was tinted `HERB_GREEN` *globally*, which
       put a green cast over the church, the perron cheeks, the podium and the
       enceinte. Mortar is now a warm lime grey. Moss is a LOCAL mask, low on
       the wall where the ground damp actually is, and it is a parameter
       (`moss`) so a dry gable and a wet plinth are not the same texture.

    `foundation_stone` remains the squared-and-graded version for plinths; this
    is the ungraded walling, with galleting — chips wedged into the joints —
    which is the detail that says a person built it by hand.

    ## The wavy cyclopean block, and where it actually came from (wave 06)

    `ad-town-05` §1 makes this the single highest-value fix in the build: it is
    the church nave (55 % of the mandated arrival frame at 1-3 m), the
    watermill's 12 m elevation (70 % of `mereshore-free`), six other
    close-range walls, and it is the reason six of the eight frames that now
    survive two seconds against a shipped AAA MMO fail at ten.

    The review's diagnosis — "blocks 0.6-1.1 m with ~10 cm rounded arrises,
    wandering joints, adjacent blocks a few luminance levels apart" — is three
    separate faults in this function, and NONE of them was a Worley field. The
    Worley rebuild had already happened; the crazy paving was rebuilt out of
    `coursed` afterwards.

    1. **`wobble=0.62` on an 8-column lattice is 1.25 units of peak-to-peak
       warp.** `coursed`'s warp is scaled by `cols`, so it is measured in
       lattice widths: past half a unit the perpends of neighbouring stones
       cross and two units merge into one amorphous polygon. At 1.25 the bond
       is *gone*, and what a warped-past-destruction lattice produces is
       wandering polygons meeting at three-way junctions — a Worley
       tessellation, rebuilt out of a regular grid. See `coursed`'s note.
       Now `wobble_u=0.30`, which is measured in units and stays under the
       merge threshold, plus `stagger` and `vary` (per-course phase and width)
       which are what actually make a wall read as hand-laid.
    2. **The face was a half-sine across the whole stone.** `face = sin(bed *
       pi) ** 0.65` at 0.30 amplitude is a pillow, and on the coarse patch
       lattice below it was a **0.5-0.67 m pillow**. That is the inflated foam.
       Random rubble is not domed: it is a rough flat face with a broken arris.
       `masonry_bond` cuts a 30 mm chamfer and leaves the face flat.
    3. **The coarse patch lattice was selected by `fbm(s, 3)`** — one blob per
       tile, the exact thing `FREQ_FLOOR` forbids — and it put 0.5-0.67 m
       megaliths over about half the sheet. Against the 1.75 m figure those
       are the megaliths the review measured. Gone; the size variation is
       `sneck` now, which goes the other way (a lift of *small* squaring
       stones) and is selected by `mottle`.

    And the fourth, which `cobble_walling` diagnosed last wave and fixed only
    for itself: the +/-18 % per-stone value was applied FIRST and then two
    `tint(..., 0.45)` calls and a `tint(..., 0.20)` were painted over it, which
    is where "a few luminance levels" comes from. `masonry_colour` applies it
    last for every key in the family.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    # Undressed field stone that nobody has spent a penny on since it was laid.
    # The weathered end of the axis without being the wet end — that is
    # `cobble_wall`.
    BODY = masonry_body(dressing=0.0, weathered=0.44)
    m.set_base(BODY)

    # Random rubble brought to course: a 0.20 m lift, stones 0.34 m mean and
    # 0.25-0.45 m in practice once `vary` and `wobble_u` have had them. Nothing
    # a man cannot lift onto a scaffold, which is the scale test the megaliths
    # failed. 26 mm of mortar, and a 30 mm broken arris.
    joint, ident, face, arris = masonry_bond(
        m, size, seed + 351, course_m=1.20 / max(courses, 2),
        stone_m=0.36 * aspect / 1.35,
        joint_mm=26.0, arris_mm=30.0, wobble_u=0.30, stagger=0.62, vary=0.26,
        bond=0.34, camber=0.05, sneck=0.30)

    # The stone surface itself: a rough face, quarried not rubbed.
    m.add_height((normalize01(fbm(s, 26, seed + 352, octaves=3)) - 0.5)
                 * 0.24 * face)

    # Galleting: chips of stone driven into the mortar. The detail that says a
    # person built it by hand, and it is the one thing the old body got right.
    gallet = smoothstep(0.74, 0.92, normalize01(worley(s, 52, seed + 354,
                                                       metric="f2f1"))) * joint
    m.add_height(gallet * 0.45)
    m.lighten(gallet, 0.28)

    bio = masonry_colour(m, size, seed + 355, joint, ident, face,
                         spread=0.28, warm=0.36, cool=0.28, patina=0.15,
                         grain=0.12, lichen=0.30 * moss, damp=0.26 * moss,
                         mortar=0.55)

    m.rough(0.84, 0.13, 0.08, seed + 358)
    m.roughness = np.clip(m.roughness + bio * 0.32, 0.03, 1.0)
    m.cavity_dirt(joint, 0.45)
    m.hold_to(BODY, 0.5)
    return m



def cobble_walling(name="cobble_wall", size=1024, seed=0):
    """River cobble walling — the same stone, rounded by the Emberflow.

    The wall you build out of what the river gives you: whole water-worn
    stones bedded in a fat mortar, brought to rough course every 0.17 m
    because round stones will not stack otherwise. It is the poorest walling
    in Hearthmere and it is on the bailey and the back lanes.

    ## The fourth rebuild, and what the third one still had wrong

    `ad-town-03` §1/§10, `ad-town-04` §6 and `ad-town-05` §5 have all rejected
    this key. Pass 05's finding is that it *changed failure mode* rather than
    getting fixed: at 2 m it read as **cracked mud** — "irregular polygonal
    plates, straight edges, three-way junctions, plates 0.5-0.9 m across
    against a 1.75 m figure".

    That is a Worley tessellation, and the previous rebuild had already taken
    Worley out. It came back through `coursed`: **`wobble=0.52` on an
    11-column lattice is 1.44 units of peak-to-peak warp.** The lattice was
    warped past the point where it is a lattice, so neighbouring cells swapped
    order and merged, and a 0.18 m cobble field turned into 0.5-0.9 m
    polygons. The order-inversion fix and the deeper joint the last rebuild
    landed were both correct and both invisible underneath that.

    Now on `masonry_bond` with the rest of the family: `wobble_u=0.22`, in
    units, which bends a bed line without merging two stones. Cobbles 0.20 m
    on a 0.17 m course — river cobble is 80-250 mm and it now measures inside
    that band against the figure.

    The other half of pass 05 is `craft-walk-04` at 25 m: "a dense regular
    chevron/zigzag moiré that reads as corrugated cardboard", diagnosed as a
    high-frequency normal at a grazing angle. The normal is calmer here — the
    dome is the only strong feature and the 44-cycle within-stone cloud has
    come out of the height entirely — and the joint shadow is duplicated into
    the albedo and the AO, which is where it has to be to survive mipping.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    # The poorest walling in the town and the wettest: river cobble off the
    # Emberflow bed, never dressed at all, and on the bailey and the back lanes
    # where the ground damp is. The cold dark end of the family.
    BODY = masonry_body(dressing=0.0, weathered=0.78)
    m.set_base(BODY)

    # 0.20 m stones on a 0.17 m course with a 45 mm bed: a fat lime-and-river-
    # sand mortar taking up nearly a third of the face, which is what makes a
    # cobble wall read as a cobble wall from across a lane. `dome` is the one
    # legitimate rounded face in the family — a whole 0.2 m boulder, not a
    # dressed block (see `masonry_bond`).
    joint, ident, face, dome = masonry_bond(
        m, size, seed + 361, course_m=0.185, stone_m=0.19,
        joint_mm=45.0, arris_mm=20.0, wobble_u=0.20, stagger=0.42, vary=0.26,
        dome=1.0)

    # Coarse grit and sand standing out of the weathered bed.
    grit = smoothstep(0.60, 0.86, normalize01(worley(s, 70, seed + 364,
                                                     metric="f2f1")))
    m.lighten(grit * joint, 0.10)
    m.add_height(grit * joint * 0.14)

    # River cobbles are water-SORTED, so they are a narrower and greyer
    # population than field rubble and their value spread is wider — that is
    # the whole difference between this key and `rubble`, and it is a number,
    # not a different rock.
    bio = masonry_colour(m, size, seed + 365, joint, ident, face,
                         spread=0.20, warm=0.24, cool=0.34, patina=0.16,
                         grain=0.17, lichen=0.30, damp=0.30, mortar=0.60)

    m.rough(0.80, 0.14, 0.09, seed + 366)
    m.roughness = np.clip(m.roughness - dome * 0.22 + bio * 0.30, 0.05, 1.0)
    # The joint shadow, in the channels that survive mipping.
    m.darken(joint, 0.22)
    m.cavity_dirt((1.0 - dome) * 0.55 + joint * 0.5, 0.35)
    m.hold_to(BODY, 0.45)
    return m


def limewashed_stone(name="limewash", size=1024, seed=0):
    """The family's rubble under limewash: the commonest wall in a poor quarter.

    Limewash is a thin coat, so the wall beneath still reads through it — the
    joints show as shadow lines and the stones as a faint quilt. It is renewed
    by brush every few years, so it is thick where the ladder reached and thin
    where it did not, and it has worn back to bare stone at every corner and
    every splash line.

    This is not a different stone from `rubble`. It is `rubble` with money
    spent on it: the same geology, the same mortar, the same lichen, one coat
    of lime. That is what "one family, varying by wealth" means in practice
    and it is why this function is now eight lines of substrate and a wash.

    ## Wave 06

    `wobble=0.55` on a 7-column lattice was 0.97 units of warp — the same
    lattice-destroying number as `rubble` and `cobble_wall`, and the reason
    what showed through the wash was a quilt of wandering polygons rather than
    a bond. The `v`-ramped renewal band was removed two waves ago and stays
    removed; see the tile-repeat rule above `mottle`.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    # `rubble`'s substrate: undressed, old. What makes this key different is
    # the money spent on the WASH, not on the stone, so the body underneath is
    # nearly `rubble`'s and only the coat is brighter.
    BODY = masonry_body(dressing=0.10, weathered=0.46)
    m.set_base(BODY)

    # Poorer walling than `stone`: smaller stones, laid rougher, wider joints.
    joint, ident, face, arris = masonry_bond(
        m, size, seed + 371, course_m=0.19, stone_m=0.30,
        joint_mm=28.0, arris_mm=28.0, wobble_u=0.28, stagger=0.58, vary=0.24,
        bond=0.38, camber=0.05, sneck=0.25)
    m.add_height((normalize01(fbm(s, 34, seed + 377, octaves=3)) - 0.5)
                 * 0.16 * face)

    # The substrate is coloured FIRST and in full, because what has to read
    # through a thin coat is a wall and not a quilt of one grey.
    bio = masonry_colour(m, size, seed + 372, joint, ident, face,
                         spread=0.26, warm=0.30, cool=0.26, patina=0.13,
                         grain=0.11, lichen=0.24, damp=0.20, mortar=0.55)

    # The wash. Brush-applied, so it has directional coverage; it POOLS in the
    # joint and is thin on the proud faces, which is the whole reason a
    # limewashed wall still reads as coursed from across a market place.
    brush = normalize01(fibre(size, 34.0, seed + 373, along="u", warp_amp=0.22))
    cover = np.clip(0.58 + brush * 0.20 + joint * 0.30 - arris * 0.16
                    - (ident - 0.5) * 0.22, 0, 1)
    m.tint(P.PLASTER, cover * 0.82)
    m.add_height(cover * 0.06)

    # Where the wash has failed: flaking off the arrises, in sheets, back to
    # the stone underneath — and the stone underneath has its own value again.
    flake = smoothstep(0.80, 0.91, normalize01(fbm(s, 26, seed + 375, octaves=4)))
    m.tint(BODY, flake * 0.85)
    m.darken(flake * np.clip(1.0 - ident * 2.0, 0.0, 1.0), 0.14)
    m.add_height(-flake * 0.08)

    # Renewal: which brushload of the last coat, as a patch and not a band.
    #
    # `ad-town-06` §5 wants weathering that survives to 12 m, and this key had
    # the least of any in the family: an albedo standard deviation of 0.023 and
    # 10 % of its variance above 0.5 m, which is a flat wall with a fine grain
    # on it. A limewashed wall is the most obviously PATCHY surface in a town —
    # it is renewed a gable at a time by whoever owned the house that year, and
    # the coat that went on in a wet spring is a different white from the one
    # that went on in a dry one. Three renewals at different ages, patchy and
    # overlapping, is the whole read at 10 m and it costs one more mottle.
    coat = smoothstep(0.55, 0.85, mottle(size, seed + 376, freq=9, octaves=2))
    m.tint(P.PLASTER_SHADE, coat * 0.34)
    old = smoothstep(0.66, 0.20, mottle(size, seed + 379, freq=6, octaves=3))
    # DARKEN, not tint. Measured: the wall's own pre-exposure mean sits at the
    # value of `mix(PLASTER_SHADE, BODY, 0.42)`, so tinting toward it moved
    # this sheet's 0.15 m variance by 0.0001 — a term that costs a mottle and
    # buys nothing. The trap is general and worth stating: `tint` toward a
    # colour the surface is already the value of is a no-op in value, and value
    # is what survives to 12 m. Check the target against the sheet, not against
    # the palette entry it was mixed from.
    m.darken(old * cover, 0.20)
    m.tint(P.mix(P.PLASTER_SHADE, MASON_WORN, 0.55), old * cover * 0.30)
    fresh = smoothstep(0.58, 0.90, mottle(size, seed + 3791, freq=7, octaves=2))
    m.lighten(fresh * cover, 0.14)

    m.rough(0.88, 0.09, 0.06, seed + 378)
    # An old coat is chalky and a new one is not: the renewal patches have to
    # read in roughness as well as value or they are a stain rather than paint.
    m.roughness = np.clip(m.roughness - cover * 0.10 + flake * 0.10
                          + bio * 0.20 + old * 0.10 - fresh * 0.07, 0.05, 1.0)
    m.tint(MASON_MORTAR, joint * 0.45)
    m.cavity_dirt(joint * 0.55, 0.26)
    m.hold_to(P.mix(P.PLASTER, BODY, 0.30), 0.6)
    return m


def sandstone(name="sandstone", size=1024, seed=0):
    """The family's bedded stone: the same quarry, taken from a lower bed.

    Its identity is the bedding plane. Laid face-bedded (which is wrong, and
    every real town has walls where someone did it), the beds delaminate and
    the face spalls off in flakes. Laid naturally, they read as fine horizontal
    striping across every block. Both are here, which is what makes this wall
    interesting rather than beige.

    ## Wave 06

    It was `mix(FOUNDATION, PRODUCE_ACCENT, 0.16)` — a distinctly orange stone
    that appears in `t-gate-north` as "a fine speckled sandstone" beside four
    other masonries, and is one of the seven treatments `ad-town-05` §7
    counts. It is the family body colour now; what makes it a different stone
    from `rubble` is the bedding and the coarse quarry face, not the hue.

    Its 8 mm joint was **2 texels** at the shipped density and filtered away
    in the first mip, which is why the gate frontispiece reads as a smeared
    cloudy mottle with no courses. `masonry_bond` floors the mortar at three
    texels; a joint you cannot see is a missing joint, not a fine one.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    # Half-dressed and fully exposed: this is the gate frontispiece and the
    # curtain's dressings, which have stood in the weather with nobody's money
    # on them since they were set.
    BODY = masonry_body(dressing=0.46, weathered=0.36)
    m.set_base(BODY)

    # Quarry-faced blockwork: 0.28 m beds, 0.55 m blocks, 18 mm joint, laid
    # square because the beds saw square.
    joint, unit, face, arris = masonry_bond(
        m, size, seed + 381, course_m=0.28, stone_m=0.55,
        joint_mm=18.0, arris_mm=20.0, wobble_u=0.07, stagger=0.24, vary=0.10,
        camber=0.02)

    # ## Character (wave 07)
    #
    # The wave-06 report signed this key off as "fixed as cohesion, not yet
    # fixed as character — I would call it `stone` with a coarser face", and
    # `ad-town-06` §5 agrees. The reason is a scale error, not a missing idea:
    # its identity — the bedding plane — was authored at `beds=22` on a 2 m
    # tile, which is a 0.09 m band, and 0.09 m is 2 px at the 25 m LOD and gone
    # by the first mip. It read at 2 m and nowhere else, and the gates are seen
    # from 15-130 m.
    #
    # A real bedded stone has TWO scales and this only had one. A quarry works
    # a face in BEDS 0.25-0.4 m thick, and each bed has its own colour and its
    # own hardness because it was laid down in a different decade of a different
    # sea; inside each bed are the fine laminations. So: a coarse bed group
    # that a whole course of blocks is cut from and which survives to 25 m, and
    # the fine laminae inside it that carry the last four metres.
    grp, gseam, _g = bedding(size, seed + 3821, beds=6, tilt=0.025)
    hard, seam, within = bedding(size, seed + 382, beds=22, tilt=0.03)

    # Soft beds weather back; hard beds stand proud. That differential is the
    # whole silhouette of a weathered sandstone block, and it is what makes
    # this key a different STONE rather than a different rock.
    m.add_height(((hard - 0.5) * 0.32 - seam * 0.26) * face)
    m.add_height(((grp - 0.5) * 0.22 - gseam * 0.30) * face)
    m.darken(hard * 0.85, 0.19)
    m.tint(MASON_WARM, smoothstep(0.62, 1.0, hard) * face * 0.40)
    m.tint(P.mix(BODY, P.PLASTER, 0.35), smoothstep(0.35, 0.0, hard) * face * 0.34)
    # The bed GROUP, in the albedo, where mipping cannot take it: an iron-rich
    # bed and a pale calcareous one, 0.33 m apart, banding straight through
    # every block on the course. This is the one term that makes the gate read
    # as bedded stone at 40 m instead of as beige.
    m.tint(MASON_WARM, smoothstep(0.52, 0.96, grp) * face * 0.46)
    m.tint(P.mix(MASON_FRESH, P.PLASTER, 0.30),
           smoothstep(0.46, 0.04, grp) * face * 0.40)
    # The open bedding seam itself: a dark line with a wash of grit under it,
    # which is what you actually see across a weathered sandstone wall.
    m.darken(gseam * face, 0.26)

    # Spalling on the face-bedded blocks — one in six or so.
    spall = smoothstep(0.80, 0.95, unit) * smoothstep(0.35, 0.75,
                                                     normalize01(fbm(s, 12, seed + 383)))
    m.add_height(-spall * 0.55)
    m.lighten(spall, 0.18)               # fresh stone under the weathered face

    bio = masonry_colour(m, size, seed + 384, joint, unit, face,
                         spread=0.15, warm=0.26, cool=0.20, patina=0.14,
                         grain=0.10, lichen=0.22, mortar=0.52)

    # Sandstone is a sponge: the salts it carries out bloom pale on the drying
    # line. `runs` is a wear pass, not a family tint, so it sits below the
    # value pass on purpose.
    m.lighten(smoothstep(0.72, 0.92, normalize01(fbm(s, 10, seed + 385, octaves=3))), 0.14)

    m.add_height(fbm(s, 80, seed + 386) * 0.07)      # sand grain
    m.rough(0.78, 0.12, 0.09, seed + 387)
    # The soft beds are the ones that hold water and grow the grit: roughness
    # follows the bed group, which is the third channel the bedding reads in
    # and the one that survives the longest at a grazing angle.
    m.roughness = np.clip(m.roughness + bio * 0.28 + gseam * 0.12
                          + (0.5 - grp) * 0.10, 0.03, 1.0)
    m.cavity_dirt(joint * 0.9 + seam * 0.3, 0.32)
    m.hold_to(BODY, 0.6)
    return m


# ---------------------------------------------------------------------------
# Brick
# ---------------------------------------------------------------------------

def handmade_brick(name="brick", size=1024, seed=0, bond=0.5):
    """Sand-struck handmade brick in a lime mortar, Flemish-ish bond.

    Everything about a handmade brick is irregular: it was thrown into a
    sanded wooden mould, so the arrises are soft and the face is creased; it
    was fired in a clamp, so the ones nearest the fire are dark and glassy and
    the ones at the edge are pink and soft. A brick texture with uniform units
    is the most recognisable single failure in architectural texturing, because
    everyone has stood next to a real brick wall.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.TERRACOTTA, P.TERRACOTTA_AGED, 0.40)
    m.set_base(BASE)

    # Imperial-ish brick: 215 x 65 mm plus a 12 mm bed = 9 courses per 2 m
    # tile heightwise, ~8 stretchers across.
    joint, unit, ty, tx = coursed(size, 26, 9, bond=bond, joint=0.055,
                                  wobble=0.35, seed=seed + 391)
    m.add_height(-joint * 0.75)

    # Frog and crease: the face dishes slightly and the arrises are rounded.
    m.add_height(np.sin(np.clip(tx, 0, 1) * np.pi) ** 0.4 *
                 np.sin(np.clip(ty, 0, 1) * np.pi) ** 0.4 * 0.16)
    m.add_height(fbm(s, 70, seed + 392) * 0.10)     # sand-struck tooth

    # Clamp firing: a full spread from underburnt salmon to overburnt blue.
    m.darken(unit * 0.9, 0.22)
    m.tint(P.mix(P.TERRACOTTA, P.PRODUCE_ACCENT, 0.30),
           smoothstep(0.55, 0.05, unit) * 0.55)                       # underburnt
    m.tint(P.mix(P.TERRACOTTA_AGED, P.SLATE, 0.45),
           smoothstep(0.72, 1.0, unit) * 0.75)                        # overburnt header
    # The glassy skin an overburnt brick gets is a roughness event, not a
    # colour one — without it the dark bricks read as painted.
    vitrified = smoothstep(0.80, 1.0, unit)

    # Mortar: coarse lime with a visible aggregate, struck flush then weathered
    # back, and repointed in patches with something greyer and harder.
    mort = smoothstep(0.30, 0.75, joint)
    m.tint(P.PLASTER_SHADE, mort * 0.9)
    grit = smoothstep(0.55, 0.85, normalize01(worley(s, 90, seed + 393, metric="f2f1")))
    m.lighten(grit * mort, 0.25)
    repoint = smoothstep(0.62, 0.78, normalize01(fbm(s, 4, seed + 394, octaves=2)))
    m.tint(P.mix(P.PLASTER_SHADE, P.SLATE, 0.35), mort * repoint * 0.8)

    m.rough(0.82, 0.12, 0.08, seed + 395)
    m.roughness = np.clip(m.roughness - vitrified * 0.42 + mort * 0.10, 0.05, 1.0)
    m.cavity_dirt(joint * 0.8, 0.30)
    m.hold_to(BASE, 0.6)
    return m


def brick_nogging(name="nogging", size=1024, seed=0):
    """Brick infill inside a timber frame — herringbone, and always failing.

    Nogging is a repair material: it replaces wattle and daub panel by panel as
    the daub falls out, so no two panels in a building match and the brick is
    whatever was to hand. Laid on the diagonal because a herringbone panel
    wedges itself into the frame instead of sliding out, which is also why it
    is instantly readable as nogging and not as a brick wall.
    """
    m = handmade_brick(name, size, seed + 20, bond=0.0)
    s = (size, size)

    # Rotate the bond 45 degrees by re-laying a diagonal course set over it and
    # keeping the previous pass only as the underlying colour field.
    v, u = _uv(size)
    du, dv = (u + v) * 0.5, (u - v) * 0.5
    gy = dv * 26.0 + fbm(s, 3, seed + 401, octaves=2) * 0.7
    gx = du * 26.0 + fbm(s, 4, seed + 402, octaves=2) * 0.7
    ty, tx = gy % 1.0, gx % 1.0
    d = np.minimum(np.minimum(tx, 1 - tx), np.minimum(ty, 1 - ty) * 0.34)
    jm = 1.0 - smoothstep(0.0, 0.055, d)
    m.height = np.zeros(s, np.float32)
    m.add_height(-jm * 0.8 + np.sin(np.clip(tx, 0, 1) * np.pi) ** 0.4 * 0.14)
    m.add_height(fbm(s, 70, seed + 403) * 0.09)
    m.tint(P.PLASTER_SHADE, smoothstep(0.30, 0.75, jm) * 0.85)

    # A panel that has been got at: bricks pushed out of line, and a patch of
    # daub still surviving in one corner. Art Bible §6 wants one visibly wrong
    # element per building; a wall material can supply its own.
    loose = smoothstep(0.86, 0.97, normalize01(fbm(s, 14, seed + 404, octaves=3)))
    m.add_height(loose * 0.35)
    m.darken(loose, 0.14)
    daub = smoothstep(0.80, 0.93, normalize01(fbm(s, 3, seed + 405, octaves=2)))
    m.tint(P.mix(P.PLASTER_SHADE, P.OAK_WEATHERED, 0.35), daub * 0.75)
    m.add_height(daub * 0.10)

    m.rough(0.84, 0.12, 0.08, seed + 406)
    m.cavity_dirt(jm * 0.7, 0.30)
    return m


# ---------------------------------------------------------------------------
# The church
# ---------------------------------------------------------------------------
# The player spawns on the altar (Directive §3), so these two materials are the
# first surfaces anyone in this world ever sees. They get hero treatment.

def stained_glass(name="stained", size=1024, seed=0, lit=True):
    """Coloured leaded lights: the church clerestory and the east window.

    Built from §4's accent colours as the glass palette, in leaded quarries
    with a painted border — NO figures and no lettering (§2). Medieval glass is
    not flat colour: it is streaky, full of bubbles and striations from the
    blowing, and each quarry is a slightly different pot-metal batch. That
    unevenness is what makes light through it
    read as glass rather than as coloured plastic.

    Emissive rather than transmissive, for the same reason `leaded_glass` is:
    the window has to read as a light source from inside a dim nave, and a
    transmissive material in a sorted-by-distance renderer does not.
    """
    m = MaterialSet(name, size)
    s = (size, size)

    # Quarries: small diamond panes in lead cames, with a heavier saddle bar
    # every few courses. Diamonds, not squares — that is the medieval form.
    v, u = _uv(size)
    du, dv = (u + v) * 9.0, (u - v) * 9.0
    ty, tx = dv % 1.0, du % 1.0
    d = np.minimum(np.minimum(tx, 1 - tx), np.minimum(ty, 1 - ty))
    lead = 1.0 - smoothstep(0.020, 0.055, d)
    quarry = ((np.floor(dv) * 13.0 + np.floor(du) * 7.0) * 0.6180339887) % 1.0

    # The glass palette, drawn from §4's accents so the church stays tied to the
    # town's colour instead of floating into its own scheme.
    #
    # WEIGHTED, and clustered. The first version assigned six fully-saturated
    # pots to six equal bands of a per-quarry hash, which is a uniform random
    # scatter of six primaries across a diamond lattice — an argyle sweater. It
    # was the worst-looking material in the library on the contact sheet and it
    # is the first surface anyone in this world sees, standing on the altar
    # (Directive §3).
    #
    # Two things fix it, and both are what real glazing does. A medieval window
    # is mostly WHITE — plain or grisaille quarries — with pot-metal colour used
    # sparingly, because coloured glass was the expensive part; so the field
    # here is 55% white glass. And the colour that is there is grouped into
    # zones rather than sprinkled, because a glazier cuts from one sheet at a
    # time; `zone` is a low-frequency field that decides WHICH colour a region
    # draws from, so the window reads as composed panels rather than confetti.
    WHITE = P.mix(P.PLASTER, P.CANVAS_CREAM, 0.5)
    pots = [P.GUILD_CRIMSON,
            P.mix(P.SKY_FILL, P.IRON, 0.45),
            P.INN_GREEN,
            P.PUB_AMBER,
            P.mix(P.VERDIGRIS, P.SKY_FILL, 0.30)]
    m.set_base(WHITE)
    zone = normalize01(fbm(s, 3, seed + 4101, octaves=2))
    # Per-quarry draw, biased toward white and toward this region's own pot.
    pick = (quarry * 0.72 + zone * 0.28) % 1.0
    coloured = smoothstep(0.53, 0.60, quarry)          # 55% stays white glass
    for i, c in enumerate(pots):
        band = ((pick >= i / len(pots)) & (pick < (i + 1) / len(pots))
                ).astype(np.float32)
        m.tint(c, band * coloured)

    # Pot-metal streaking: colour varies WITHIN a quarry, in the direction the
    # sheet was drawn.
    streak = fibre(size, 22.0, seed + 411, along="u", warp_amp=0.55)
    m.darken(streak * 0.7, 0.22)
    m.lighten(smoothstep(0.55, 1.0, normalize01(fbm(s, 30, seed + 412))), 0.16)

    # Seeds and bubbles trapped in the blow, and the reamy ripple of the sheet.
    m.add_height(fbm(s, 14, seed + 413, octaves=3) * 0.40 +
                 fbm(s, 55, seed + 414) * 0.12)
    bubble = smoothstep(0.88, 0.97, normalize01(worley(s, 34, seed + 415, metric="f2f1")))
    m.add_height(bubble * 0.30)

    # Lead cames and the saddle bars that carry the panel's weight.
    # Saddle bars: the iron bars every leaded panel is tied to, five up the
    # window. The band mask is `1 - smoothstep(0, w, |offset|)` and nothing
    # else — the first version subtracted 0.46 from the offset first, which
    # made the mask 1 across the entire pane. Combined with `metal = lead +
    # bar` that set metalness to 1 over the whole window, so the church's
    # east light shipped as a sheet of black iron with coloured seams.
    bar = 1.0 - smoothstep(0.006, 0.016, np.abs((v * 5.0) % 1.0 - 0.5))
    metal = np.clip(lead + bar, 0, 1)
    m.tint(P.IRON, metal * 0.95)
    m.metalness = metal * 0.85
    m.add_height(lead * 0.55 + bar * 0.30)

    # Grisaille border: a painted band of foliate ornament, fired on. Pictorial
    # only — §2 forbids readable lettering anywhere in the world.
    border = smoothstep(0.03, 0.0, np.minimum(np.minimum(u, 1 - u),
                                              np.minimum(v, 1 - v)) - 0.03)
    m.darken(border * (1.0 - metal) * 0.8, 0.35)

    m.rough(0.09, 0.06, 0.03, seed + 416)
    m.roughness = np.clip(m.roughness + metal * 0.62 + bubble * 0.1, 0.03, 1.0)

    if lit:
        # Sun through the glass. Brightness follows the pot colour's own
        # luminance so the reds stay deep and the whites blaze, which is
        # exactly what a real window does and is the whole reason a nave is
        # worth standing in.
        lum = np.clip(m.albedo.mean(-1) * 1.6, 0, 1)
        strength = (1.0 - metal) * (0.55 + 0.45 * lum) * (0.7 + 0.3 * streak)
        m.emissive = np.clip(m.albedo, 0, 1) * strength[..., None] * 3.4
        m.glow(P.SUN, (1.0 - metal) * smoothstep(0.75, 1.0, lum), 1.4)
    else:
        m.emissive = np.clip(m.albedo, 0, 1) * ((1.0 - metal) * 0.22)[..., None]
    return m


def alabaster(name="alabaster", size=1024, seed=0, marble=False):
    """The summoning altar: alabaster, with the subsurface faked in albedo.

    Alabaster's whole quality is that light goes *into* it and comes back out
    a few millimetres away, so the stone glows from within and its veins read
    softly rather than as printed lines. With no subsurface term available, the
    honest fake is: lift the base value well above the palette's stone family,
    keep chroma warm, blur every vein into a wide soft halo, and drop roughness
    low enough that the specular does the rest. Sharp veins on a matte white
    surface is what makes fake marble look like Formica.

    `marble=True` gives the harder, cooler, sharper-veined version for the
    church floor and the font.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.PLASTER, P.CANVAS_CREAM, 0.30 if not marble else 0.10)
    if marble:
        BASE = P.mix(BASE, P.SLATE, 0.12)
    m.set_base(BASE)

    # Cloudy internal structure: broad, soft, low-contrast. This is the
    # "light is coming out of the stone" cue.
    cloud = normalize01(fbm(s, 4, seed + 421, octaves=5))
    m.darken(smoothstep(0.55, 0.0, cloud) * 0.8, 0.10 if not marble else 0.14)
    m.tint(P.mix(BASE, P.PRODUCE_ACCENT, 0.14), smoothstep(0.5, 1.0, cloud) * 0.5)

    # Veins. Ridged noise gives the branching network; the SOFTNESS is what
    # separates alabaster from a printed slab.
    raw = normalize01(ridged(s, 6, seed + 422, octaves=4))
    sharp = 0.955 if marble else 0.90
    vein = smoothstep(sharp, 1.0, raw)
    halo = smoothstep(sharp - (0.05 if marble else 0.16), 1.0, raw)
    m.tint(P.mix(BASE, P.OAK_WEATHERED, 0.45 if marble else 0.28), vein * 0.75)
    m.tint(P.mix(BASE, P.OAK_WEATHERED, 0.12), halo * 0.5)
    m.add_height(-vein * (0.10 if marble else 0.04))

    # Second, finer vein set at a different angle — one family of veins reads
    # as a decal, two read as geology.
    fine = smoothstep(0.94, 1.0, normalize01(ridged(s, 15, seed + 423, octaves=3)))
    m.tint(P.mix(BASE, P.SLATE, 0.30), fine * (0.55 if marble else 0.30))

    # Tool and wear story: the altar is polished where hands and knees go, and
    # the arrises are chipped where a thousand years of processions caught them.
    m.add_height(fbm(s, 100, seed + 424) * 0.05)
    chip = smoothstep(0.90, 0.98, normalize01(worley(s, 24, seed + 425, metric="f2f1")))
    m.add_height(-chip * 0.35)
    m.lighten(chip, 0.16)

    # Depth-of-field in the stone itself. The cloud pass above is a single
    # 4-cycle field worth 0.10 of darkening, which left the altar at L* sigma
    # 1.51 and mean 85, which reads as a blank white block — and it is the
    # first surface anyone in this world stands on (Directive §3). Alabaster's read is that
    # its value wanders continuously and softly, because that is what light
    # re-emerging a few millimetres from where it went in actually does.
    m.albedo_break(0.22 if marble else 0.30, 0.09, seed + 427,
                   broad_freq=3, fine_freq=18, warm=0.34 if not marble else 0.14)

    m.rough(0.22 if marble else 0.30, 0.14, 0.07, seed + 426)
    m.roughness = np.clip(m.roughness + chip * 0.45 + vein * 0.08, 0.04, 1.0)
    m.cavity_dirt(chip * 0.5, 0.18)
    m.hold_to(BASE, 0.5)
    return m


# ---------------------------------------------------------------------------
# Wet things
# ---------------------------------------------------------------------------

def algae(name="algae", size=512, seed=0):
    """The green band on everything that sits in water: piles, steps, hulls.

    A quay wall without this band has no waterline, and without a waterline the
    water has no level and the whole waterfront stops being believable. It is
    the cheapest possible fix for the single biggest tell.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.HERB_GREEN, P.VERDIGRIS, 0.35)
    # 0.72, not 0.55. Algae is dark but it is not black-green, and the deep
    # shade put the whole live band 15 L* under §4's nearest family (INN_GREEN)
    # for a measured 5.0 — a warning bought entirely with value, on a material
    # whose job is to be SEEN as a waterline band against the stone above it.
    m.set_base(P.shade(BASE, 0.72))

    # Filamentous growth hanging with gravity, plus the flat slime under it.
    hair = fibre(size, 26.0, seed + 431, along="v", warp_amp=0.7)
    m.add_height(hair * 0.30 + fbm(s, 40, seed + 432) * 0.12)
    m.darken(hair * 0.6, 0.20)
    m.tint(P.shade(BASE, 1.25), smoothstep(0.45, 1.0, hair) * 0.55)

    # Zonation: the band is not uniform. Bright green where it is wet twice a
    # day, black-green below, dry and grey-bleached above.
    _v, _u = _uv(size)
    zone = _v + fbm(s, 3, seed + 433, octaves=2) * 0.18
    m.tint(P.shade(P.mix(BASE, P.IRON, 0.35), 0.6), smoothstep(0.55, 1.0, zone) * 0.7)
    m.tint(P.mix(P.COBBLE_WORN, P.HERB_GREEN, 0.30), smoothstep(0.35, 0.0, zone) * 0.8)

    # Weed wrack and the odd shell caught in it.
    wrack = smoothstep(0.80, 0.94, normalize01(fbm(s, 10, seed + 434, octaves=3)))
    m.tint(P.mix(P.OAK_DARK, P.HERB_GREEN, 0.35), wrack * 0.6)

    # Always wet, so low roughness — but only in the live band. The dry zone
    # above is chalky. Two sources, per §5, and both physically motivated.
    m.rough(0.30, 0.16, 0.08, seed + 435)
    m.roughness = np.clip(m.roughness + smoothstep(0.55, 1.0, zone) * 0.45, 0.04, 1.0)
    m.cavity_dirt((1.0 - normalize01(hair)) * 0.5, 0.25)
    return m


def wet_mud(name="mud_wet", size=1024, seed=0):
    """Standing mud: the ford, the tannery yard, the cattle crossing.

    `river_mud` is the drying margin — cracked, gritty, mostly matte.
    This is mud that has not dried and will not: churned by hooves, holding
    water in every print, and glossy enough that it mirrors the sky. The gloss
    is the point. Matte mud is dirt.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.OAK_DARK, P.COBBLE_WORN, 0.42)
    m.set_base(BASE)

    # Churn: overlapping hoof and boot prints at two sizes, all holding water.
    hoof = worley(s, 15, seed + 441)
    boot = worley(s, 26, seed + 442)
    prints = np.clip((1.0 - hoof) * 0.7 + (1.0 - boot) * 0.45, 0, 1)
    m.add_height(-prints * 0.65 + fbm(s, 8, seed + 443, octaves=3) * 0.30)
    # Squeeze ridges around the rim of each print — the mud has to go somewhere.
    rim = smoothstep(0.05, 0.22, worley(s, 15, seed + 441, metric="f2f1"))
    m.add_height((1.0 - rim) * 0.28)

    water = smoothstep(0.45, 0.85, prints)
    m.darken(water, 0.34)
    m.tint(P.shade(P.mix(P.VERDIGRIS, P.IRON, 0.45), 0.55), water * 0.35)   # sky in it

    # What is trodden into it: straw, chaff, dung, and the pale silt that dries
    # on the high spots between showers.
    straw = smoothstep(0.90, 0.99, normalize01(ridged(s, 30, seed + 444, octaves=2))) * \
        smoothstep(0.5, 0.85, normalize01(fbm(s, 5, seed + 445)))
    m.tint(P.mix(P.CANVAS_CREAM, P.OAK_WEATHERED, 0.35), straw * 0.7)
    m.add_height(straw * 0.10)
    m.lighten(smoothstep(0.72, 0.95, 1.0 - prints), 0.14)

    m.rough(0.55, 0.18, 0.09, seed + 446)
    m.roughness = np.clip(m.roughness - water * 0.46, 0.04, 1.0)
    m.cavity_dirt(prints * 0.5, 0.25)
    m.hold_to(BASE, 0.55)
    return m


# ---------------------------------------------------------------------------
# Ground cover
# ---------------------------------------------------------------------------
# Everything below is a SUBSTRATE, not a tint of the one above it. The terrain
# is the largest surface in the build by two orders of magnitude and the player
# looks at it from 1.62 m for the whole session; using one brown for all of it
# is what makes procedural terrain read as a heightmap with a texture on it.

def grass_variant(name="grass", size=1024, seed=0, density=1.0, dry=0.0,
                  trodden=0.0):
    """Meadow turf at a chosen density, dryness and wear.

    Three parameters because a town needs at least three grasses and they are
    the same plant: lush in the water meadow, dry on the south bank the sun
    bakes, and worn to bare soil on the green where the market carts turn. One
    grass everywhere is the golf-course tell.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    # Desaturated 25 % toward the palette's own neutral. `ad-town-03` §2 read
    # `grass_lush` as "a saturated emerald - more saturated than anything else
    # in the town, including the crimson confectioner", and on a ground cover
    # that is a disaster: it is the largest area in the frame, so it sets the
    # chroma the eye calibrates everything else against. Real turf at 09:30 in
    # a north-European summer is a grey-green.
    LUSH = P.mix(P.mix(P.HERB_GREEN, P.OAK_DARK, 0.26), P.COBBLE_WORN, 0.22)
    m.set_base(LUSH)

    # Tussocks. f2f1 gives the parting between clumps, which is where the
    # thatch and the soil show through.
    freq = 34.0 / max(density, 0.35) ** 0.5
    clump = worley(s, int(freq), seed + 451, metric="f2f1")
    m.add_height(clump * (0.30 + 0.25 * density) +
                 ridged(s, 300, seed + 452, octaves=2) * 0.22)
    m.darken((1.0 - normalize01(clump)) * 0.8, 0.30)

    # Sub-metre patchiness only. Anything above a metre in a tile that repeats
    # thirty times across the town reads from the air as a regular quilt;
    # world-scale ground colour is COLOR_0's job (venues/terrain.py).
    patch = normalize01(fbm(s, 13, seed + 453, octaves=4))

    # `burn` is computed BEFORE the green passes and used to gate them, which is
    # the fix the previous two attempts at this material missed. Both the bright
    # sun-patch tint and the burn mask derive from the SAME `patch` field, so
    # the straw was being laid over precisely the greenest ground — and 8% of
    # that green surviving a 0.92 tint is what produced the khaki that measured
    # 8.8 against §4. Gating the green by `1 - burn` means the two populations
    # never overlap in the first place, instead of being separated afterwards
    # by a `hold_to` that cannot separate them because the pixels are genuinely
    # a blend of both.
    # `dry` moves the THRESHOLD, it does not scale the opacity. Multiplying the
    # mask by `dry` caps it — at the registry's `dry=0.85` even completely
    # burnt-off ground kept 15% of the green showing through the straw laid
    # over it, and 15% green under straw is the khaki that no §4 family owns.
    # It was the last 8.0 in the library and it was baked into the parameter's
    # own definition. Drought does not make grass semi-transparent; it makes
    # MORE OF THE FIELD dead, and the dead part is fully dead.
    if dry > 0:
        t = (1.0 - np.clip(dry, 0.0, 1.0)) * 0.86
        burn = smoothstep(t, t + 0.15, patch)
    else:
        burn = np.zeros(s, np.float32)
    green = 1.0 - burn

    m.tint(P.shade(P.HERB_GREEN, 1.22), smoothstep(0.5, 1.0, patch) * 0.75 * green)
    m.tint(P.shade(P.mix(P.HERB_GREEN, P.OAK_DARK, 0.45), 0.85),
           smoothstep(0.5, 0.0, patch) * 0.65 * green)

    if dry > 0:
        # Drought does not tint grass evenly: it kills the thin ground first
        # and leaves the hollows green, which is what makes a dry field read
        # as a field rather than as a colour change.
        # Straw, not gold-green. `mix(HERB_GREEN, BRASS, 0.3)` is the obvious
        # way to write "drying grass" and it measures 14.9 against §4 on its
        # own — it sits in the gap between the palette's green and its gold and
        # belongs to neither, exactly the trap the leaf atlases fell into. Dead
        # grass IS straw, and straw is the CANVAS_CREAM family at lower value.
        DRY = P.mix(P.CANVAS_CREAM, P.OAK_WEATHERED, 0.35)
        # NEAR-BINARY, not a ramp — the same correction the leaf atlases needed
        # and for the identical reason. `smoothstep(0.30, 0.85, patch)` spreads
        # the green-to-straw transition over more than half the tile, so most of
        # the surface was a half-and-half blend sitting between §4's HERB_GREEN
        # and its CANVAS_CREAM and belonging to neither: measured 8.8, the
        # library's worst unwaived material and a hair off an outright FAIL.
        # The per-population `hold_to` below cannot rescue it, because a pixel
        # that is genuinely half of each is not IN either population.
        #
        # It is also what drought looks like. Grass does not fade evenly; the
        # thin ground over gravel burns off completely while the hollow beside
        # it stays green, and the boundary between them is sharp.
        m.tint(DRY, burn)
        m.lighten(burn, 0.06)

    if trodden > 0:
        # Wear opens the sward and the soil comes through. It also FLATTENS,
        # so the height amplitude and the roughness both drop.
        bare = smoothstep(0.55, 0.9, normalize01(fbm(s, 9, seed + 454, octaves=3))) * trodden
        m.tint(P.mix(P.OAK_WEATHERED, P.HERB_GREEN, 0.22), bare * 0.75)
        m.height = m.height * (1.0 - bare * 0.7)
        scuff = smoothstep(0.6, 0.95, normalize01(worley(s, 40, seed + 455,
                                                         metric="f2f1"))) * trodden
        m.lighten(scuff, 0.16)

    # Bare soil where the turf is thin, plus seed heads.
    # Both gated by `green` too: bare soil showing through a SWARD is a green
    # story, and over burnt ground it just adds a third hue to the blend.
    thin = smoothstep(0.80, 0.93, normalize01(fbm(s, 11, seed + 456, octaves=3)))
    m.tint(P.mix(P.OAK_WEATHERED, P.HERB_GREEN, 0.20), thin * 0.6 * green)
    heads = smoothstep(0.88, 0.97, normalize01(worley(s, 60, seed + 457, metric="f2f1")))
    m.tint(P.mix(P.CANVAS_CREAM, P.OAK_WEATHERED, 0.30), heads * 0.5)

    m.rough(0.62 + dry * 0.14, 0.16, 0.09, seed + 458)
    m.cavity_dirt((1.0 - normalize01(clump)) * 0.6, 0.22)
    # Held PER POPULATION, like the leaf atlases and for the same reason: a
    # drying field is green sward and straw side by side, and holding the two
    # to one average colour produces the khaki in between, which is on no §4
    # family at all (measured 9.4 that way, 3.x held separately).
    LUSH_HOLD = P.mix(P.HERB_GREEN, P.OAK_DARK, 0.22)
    m.hold_to(LUSH_HOLD, 0.55, mask=1.0 - burn)
    if dry > 0:
        # 0.9, not 0.6. A 60% hold leaves the burnt population 40% of the way
        # back toward the green it was tinted over, and 40% of the way between
        # two §4 families is the olive that measured 8.8. The straw population
        # has its own family and there is no reason to hold it only halfway to
        # it — the variance §5 wants is already in `albedo_break` and in the
        # patch fields above, and `hold_to` is multiplicative so none of it is
        # flattened by pulling the mean the whole way home.
        m.hold_to(P.mix(P.CANVAS_CREAM, P.OAK_WEATHERED, 0.35), 0.9, mask=burn)
    return m


def moss_bed(name="moss", size=512, seed=0):
    """Deep moss: north walls, the well head, the graveyard, under the eaves.

    Moss is not "green noise". It grows in domed cushions with a visible
    boundary, it holds water so it is dark and its roughness drops after rain,
    and it is fringed with the pale sporophyte stalks that catch the light.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.shade(P.mix(P.HERB_GREEN, P.OAK_DARK, 0.30), 0.95)
    m.set_base(BASE)

    cushion = 1.0 - worley(s, 11, seed + 461)
    m.add_height(cushion * 0.6 + fbm(s, 90, seed + 462) * 0.22)
    m.darken((1.0 - cushion) * 0.9, 0.32)
    m.tint(P.mix(P.HERB_GREEN, P.CANVAS_CREAM, 0.30), smoothstep(0.55, 1.0, cushion) * 0.6)
    m.tint(P.shade(P.mix(P.HERB_GREEN, P.IRON, 0.35), 0.7),
           smoothstep(0.35, 0.0, cushion) * 0.7)

    # Sporophytes: thousands of fine stalks with a capsule on top, and the
    # only warm colour on the surface.
    stalk = smoothstep(0.90, 0.99, normalize01(worley(s, 80, seed + 463, metric="f2f1")))
    m.tint(P.mix(P.PRODUCE_ACCENT, P.OAK_WEATHERED, 0.45), stalk * 0.7)
    m.add_height(stalk * 0.18)

    # The substrate showing at the edges of the colony.
    edge = smoothstep(0.72, 0.95, normalize01(fbm(s, 5, seed + 464, octaves=3)))
    m.tint(P.COBBLE_WORN, edge * 0.55)

    m.rough(0.74, 0.16, 0.10, seed + 465)
    m.roughness = np.clip(m.roughness - smoothstep(0.5, 1.0, cushion) * 0.18, 0.05, 1.0)
    m.cavity_dirt((1.0 - cushion) * 0.7, 0.30)
    return m


def granite_sett(name="sett", size=1024, seed=0):
    """Squared granite setts: the market place, the bridge deck, the gate arch.

    Not cobbles. A sett is dressed to a cube and laid to a pattern, so it is
    the paving of a town that could afford paving — which is the story the
    market square should be telling against Ford Road's rounded cobbles.
    Laid in fan courses, because that is how a large square is actually set out
    and it is the one paving pattern that reads instantly from the air.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.COBBLE, P.SLATE, 0.22)
    m.set_base(BASE)

    # 0.16 m setts on a 2 m tile: 12 x 12, with a strong wobble because they
    # are hand-dressed and hand-laid on sand.
    joint, unit, ty, tx = coursed(size, 12, 12, bond=0.5, joint=0.055,
                                  wobble=0.55, seed=seed + 471)
    m.add_height(-joint * 0.9)
    # Each sett domes very slightly and sits at its own level.
    m.add_height(np.sin(np.clip(tx, 0, 1) * np.pi) * np.sin(np.clip(ty, 0, 1) * np.pi) * 0.22)
    m.add_height((unit - 0.5) * 0.20)
    # Split face: granite is riven, so every top face is a field of small
    # conchoidal facets. This is what sparkles under a low sun.
    m.add_height(worley(s, 90, seed + 472, metric="f2f1") * 0.16)

    # Per-sett colour. Granite runs pink to blue-grey through one quarry face.
    m.darken(unit * 0.9, 0.20)
    m.tint(P.mix(P.COBBLE, P.PLASTER_SHADE, 0.35), smoothstep(0.55, 1.0, unit) * 0.45)
    m.tint(P.mix(P.SLATE, P.OAK_DARK, 0.25), smoothstep(0.30, 0.0, unit) * 0.50)
    # Mica: bright specks, high spec, no colour. The signature of granite.
    mica = smoothstep(0.93, 0.99, normalize01(worley(s, 140, seed + 473, metric="f2f1")))
    m.lighten(mica, 0.35)

    # Traffic polish, sand and moss in the joints away from it.
    #
    # This was two wheel lines drawn at fixed `u`, times `fbm(s, 4)`. Both are
    # tile landmarks (see FREQ_FLOOR): the road is 8-14 m wide and the tile is
    # 2 m, so it drew SEVEN pairs of ruts across the carriageway, in register,
    # every 2 m along it — the "obvious light/dark chequerboard at 2-8 m" of
    # `ad-town-03` §15. A texture cannot know where the wheels went; the road
    # does. What survives here is the polish itself, as patches.
    lane = smoothstep(0.42, 0.90, mottle(size, seed + 474, freq=7, octaves=3))
    m.darken(lane, 0.10)
    sand = smoothstep(0.30, 0.8, joint)
    m.tint(P.mix(P.CANVAS_CREAM, P.COBBLE_WORN, 0.5), sand * (1.0 - lane) * 0.5)
    moss = sand * (1.0 - lane) * smoothstep(0.45, 0.85, normalize01(fbm(s, 8, seed + 475)))
    m.tint(P.HERB_GREEN, moss * 0.55)

    m.rough(0.70, 0.13, 0.08, seed + 476)
    m.roughness = np.clip(m.roughness - lane * 0.30 - mica * 0.5 + moss * 0.15, 0.04, 1.0)
    m.cavity_dirt(joint * 0.8, 0.30)
    m.hold_to(BASE, 0.7)
    return m


def flagstone(name="flag", size=1024, seed=0):
    """Worn flagstone: the church floor, thresholds, the well apron, arcades.

    The material that carries the Directive's "a stone floor worn into a path
    from altar to doors". A flag is a big thin slab, so the story is entirely
    in HOW IT HAS WORN — dished in the middle of every walking line, the joints
    opened and filled with grit, corners broken, and one slab replaced in
    something that does not match.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.FOUNDATION, P.COBBLE_WORN, 0.28)
    m.set_base(BASE)

    # ~0.65 m flags: 3 x 3 on a 2 m tile, laid to random widths. `joint` is a
    # fraction of the shorter unit side, so 0.014 on a 0.67 m flag is ~19 mm of
    # opened joint, which is what an old floor has.
    joint, unit, ty, tx = coursed(size, 3, 3, bond=0.35, joint=0.014,
                                  wobble=0.22, seed=seed + 481)
    m.add_height(-joint * 0.7)

    # Dishing: each flag is worn hollow, deepest where the traffic runs. The
    # traffic band used to be centred at a fixed `u`, which drew a worn stripe
    # down the middle of every 2 m tile — a corduroy across the nave rather
    # than one path from door to altar (FREQ_FLOOR). The path the Directive
    # asks for is authored in the church floor's geometry; the tile carries the
    # uneven wear that goes under it.
    path = smoothstep(0.38, 0.90, mottle(size, seed + 482, freq=7, octaves=3))
    dish = np.sin(np.clip(tx, 0, 1) * np.pi) * np.sin(np.clip(ty, 0, 1) * np.pi)
    m.add_height(-dish * (0.10 + path * 0.30))

    # Broken arrises and a spalled corner or two.
    chip = smoothstep(0.86, 0.97, normalize01(worley(s, 30, seed + 483, metric="f2f1")))
    m.add_height(-chip * 0.40)
    m.lighten(chip, 0.16)

    # Per-flag colour, plus the one replaced slab in a different stone.
    m.darken(unit * 0.8, 0.16)
    m.tint(P.FOUNDATION, smoothstep(0.5, 1.0, unit) * 0.40)
    odd = smoothstep(0.93, 0.97, unit)
    m.tint(P.mix(P.SLATE, P.COBBLE_WORN, 0.35), odd * 0.85)

    # Polish where feet go, grit and candle-grease dark in the joints.
    m.darken(path * (1.0 - joint), 0.12)

    # Stone-to-stone AND within-stone value. `unit` gives nine flags nine
    # values, which is not enough information to fill a church floor: at L*
    # sigma 1.55 the nave read as white ceramic tiling. A flag is a sedimentary
    # slab with its own cloud and its own damp, and this floor is the surface
    # the Directive asks to be "worn into a path from altar to doors".
    m.albedo_break(0.28, 0.14, seed + 486, broad_freq=5, fine_freq=26, warm=0.24)

    m.rough(0.62, 0.14, 0.08, seed + 484)
    m.roughness = np.clip(m.roughness - path * 0.34 + chip * 0.25, 0.04, 1.0)
    m.add_height(fbm(s, 70, seed + 485) * 0.06)
    m.cavity_dirt(joint * 0.9, 0.40)
    m.hold_to(BASE, 0.65)
    return m


def cinder_ground(name="cinder", size=1024, seed=0):
    """Forge cinder and clinker: the smithy floor, the ash path, the midden.

    The darkest ground in the town and the only one with no organic content at
    all. It matters because it is the material proof that the forge WORKS —
    twenty years of raked-out fire, trodden into a surface.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.shade(P.mix(P.IRON, P.OAK_DARK, 0.35), 1.35)
    m.set_base(BASE)

    # Clinker: fused, vesicular lumps at two grades, plus the fine ash between.
    big = worley(s, 30, seed + 491, metric="f2f1")
    fine = worley(s, 78, seed + 492, metric="f2f1")
    m.add_height(big * 0.34 + fine * 0.20 + fbm(s, 130, seed + 493) * 0.10)
    vesic = smoothstep(0.55, 0.9, normalize01(worley(s, 160, seed + 494)))
    m.add_height(-vesic * 0.14)

    per = per_unit(size, 40, seed + 495, steps=5)
    m.darken(per * 0.9, 0.28)
    # Fused clinker goes glassy blue-black; unburnt charcoal stays matte; scale
    # off the anvil is red-brown. Three populations, one surface.
    m.tint(P.shade(P.mix(P.SLATE, P.IRON, 0.55), 0.9), smoothstep(0.62, 1.0, per) * 0.7)
    m.tint(P.mix(P.TERRACOTTA_AGED, P.IRON, 0.55), smoothstep(0.25, 0.0, per) * 0.6)
    glassy = smoothstep(0.72, 1.0, per)

    # Ash: pale, and it collects in the hollows rather than on the lumps.
    ash = smoothstep(0.55, 0.9, normalize01(fbm(s, 16, seed + 496, octaves=3))) * \
        (1.0 - normalize01(big))
    m.tint(P.mix(P.COBBLE_WORN, P.PLASTER_SHADE, 0.35), ash * 0.55)

    m.rough(0.88, 0.10, 0.07, seed + 497)
    m.roughness = np.clip(m.roughness - glassy * 0.45, 0.05, 1.0)
    m.metalness = np.clip(glassy * 0.18, 0, 1)      # a little iron is still iron
    m.cavity_dirt((1.0 - normalize01(big)) * 0.5, 0.20)
    return m


def river_sand(name="sand", size=1024, seed=0):
    """River sand: the ford's beach, the mason's heap, the smith's floor.

    Sand's read is almost entirely in the normal map — ripples at two scales,
    footprints, and the darker damp line where the water reaches. Its albedo is
    nearly flat, which is exactly why it needs the roughness rule applying
    hardest: dry sand is matte and wet sand is not.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.CANVAS_CREAM, P.FOUNDATION, 0.42)
    m.set_base(BASE)

    # Wind and current ripples, crossed at an angle.
    rip = fibre(size, 30.0, seed + 501, along="v", warp_amp=0.35)
    rip2 = fibre(size, 12.0, seed + 502, along="u", warp_amp=0.55)
    m.add_height(rip * 0.26 + rip2 * 0.18 + fbm(s, 150, seed + 503) * 0.12)
    m.darken(rip * 0.5, 0.08)

    # Coarse fraction: shell, grit and small pebbles the water sorted out.
    grit = smoothstep(0.80, 0.95, normalize01(worley(s, 90, seed + 504, metric="f2f1")))
    m.add_height(grit * 0.20)
    m.lighten(grit, 0.24)
    m.tint(P.COBBLE_WORN, smoothstep(0.88, 0.98,
                                     normalize01(worley(s, 34, seed + 505))) * 0.6)

    # Damp patches. Two noise scales, and they do most of the work here.
    damp = smoothstep(0.45, 0.85, normalize01(fbm(s, 5, seed + 506, octaves=4)))
    m.darken(damp, 0.26)
    m.rough(0.90, 0.08, 0.06, seed + 507)
    m.roughness = np.clip(m.roughness - damp * 0.42, 0.06, 1.0)
    m.hold_to(BASE, 0.6)
    return m


def yard_litter(name="yard", size=1024, seed=0):
    """Dung-and-straw yard: the stables, the waggon yard, the beast market.

    The single most useful "this place is used by animals" surface in the
    build, and one nobody thinks to author. It is not mud: it is a trodden mat
    of straw bedding with dung worked through it, drying pale on top and black
    underneath, and it is the only ground in the town with real THICKNESS.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.OAK_WEATHERED, P.CANVAS_CREAM, 0.28)
    m.set_base(BASE)

    # The straw mat: strongly directional in patches, matted flat, at two
    # lengths because it has been trodden and re-strewn many times.
    long_ = fibre(size, 26.0, seed + 511, along="u", warp_amp=0.9)
    short = fibre(size, 60.0, seed + 512, along="v", warp_amp=0.7)
    mix = smoothstep(0.35, 0.65, normalize01(fbm(s, 4, seed + 513, octaves=2)))
    straw = long_ * mix + short * (1.0 - mix)
    m.add_height(straw * 0.42 + fbm(s, 20, seed + 514, octaves=3) * 0.20)
    m.lighten(smoothstep(0.55, 1.0, straw), 0.26)
    m.tint(P.mix(P.CANVAS_CREAM, P.PRODUCE_ACCENT, 0.22), smoothstep(0.6, 1.0, straw) * 0.5)

    # Dung: dark, wet, and it flattens the straw where it lands.
    dung = smoothstep(0.62, 0.86, normalize01(fbm(s, 9, seed + 515, octaves=4)))
    m.tint(P.shade(P.mix(P.OAK_DARK, P.HERB_GREEN, 0.22), 1.1), dung * 0.85)
    m.height = m.height * (1.0 - dung * 0.6)
    m.add_height(dung * 0.14)

    # Trodden-through patches where the bedding has worn to the yard beneath.
    worn = smoothstep(0.74, 0.92, normalize01(fbm(s, 6, seed + 516, octaves=3)))
    m.tint(P.mix(P.COBBLE_WORN, P.OAK_DARK, 0.35), worn * 0.7)
    m.height = m.height * (1.0 - worn * 0.5)

    m.rough(0.92, 0.08, 0.06, seed + 517)
    m.roughness = np.clip(m.roughness - dung * 0.34, 0.06, 1.0)
    m.cavity_dirt(dung * 0.4 + worn * 0.3, 0.28)
    return m


# ---------------------------------------------------------------------------
# Timber
# ---------------------------------------------------------------------------
# `oak_timber` covers the frame. These cover everything the frame is NOT: the
# cheap wood, the wet wood, the burnt wood, and the cut end — which is the one
# view of timber that shows what it actually is, and the one nobody authors.

def timber(name="timber", size=1024, seed=0, species="elm", weathered=0.4,
           tar=0.0, char=0.0):
    """Non-oak timber, by species, with tarring and charring as wear states.

    Species differ in three things and only three things matter at gameplay
    distance: base colour, grain COARSENESS, and how the grain contrasts.
    Elm is wild and interlocked; pine is straight with hard resinous latewood
    bands and big knots; the greyed board has lost its colour entirely and is
    all texture. Getting the coarseness right is what separates them at 3 m —
    tinting one oak three ways does not.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    SPEC = {
        # (base, grain freq, grain contrast, knot freq, ring tint)
        "elm":   (P.mix(P.OAK, P.OAK_WEATHERED, 0.35), 16.0, 0.62, 4, P.OAK_DARK),
        "pine":  (P.mix(P.CANVAS_CREAM, P.OAK, 0.55), 34.0, 0.85, 2, P.OAK_WEATHERED),
        "grey":  (P.mix(P.OAK_WEATHERED, P.COBBLE_WORN, 0.55), 24.0, 0.45, 3, P.SLATE),
        "ash":   (P.mix(P.CANVAS_CREAM, P.OAK, 0.35), 20.0, 0.55, 3, P.OAK_WEATHERED),
    }
    base, gf, gc, kf, ring = SPEC.get(species, SPEC["elm"])
    m.set_base(base)

    # Grain along V (mesh.plank lays boards that way). `fibre` is the sanctioned
    # implementation — a clean sine aliases against the plank UV scale and reads
    # as painted stripes, which was oak_timber's first-pass defect.
    grain = fibre(size, gf, seed + 521, along="u", warp_amp=0.55)
    m.add_height(grain * (0.12 + gc * 0.10) + fbm(s, 70, seed + 522) * 0.06)
    m.darken(grain * gc, 0.20)
    m.tint(ring, normalize01(np.abs(fbm(s, 3, seed + 523, octaves=2))) * 0.22)

    # Knots, with the grain sweeping round them. Pine has many and they are
    # black and resinous; elm has few and they are burrs.
    knot = 1.0 - smoothstep(0.0, 0.13, worley(s, kf, seed + 524))
    m.darken(knot, 0.55 if species != "pine" else 0.75)
    m.add_height(-knot * (0.4 if species != "pine" else 0.25))
    if species == "pine":
        # Resin bleeds out of the knots and goes sticky-glossy.
        bleed = smoothstep(0.35, 0.9, knot)
        m.tint(P.mix(P.PRODUCE_ACCENT, P.OAK_DARK, 0.35), bleed * 0.55)

    if weathered > 0:
        silver = normalize01(fbm(s, 7, seed + 525)) * weathered
        m.tint(P.mix(base, P.COBBLE_WORN, 0.55), silver * 0.5)
        # Weathering opens the grain: the soft earlywood erodes and the
        # latewood stands proud. That relief IS what "weathered board" looks
        # like — colour alone gives a grey plank, not an old one.
        m.add_height(grain * weathered * 0.30)
        splits = smoothstep(0.86, 0.98, grain) * smoothstep(0.4, 0.9,
                                                            normalize01(fbm(s, 2, seed + 526)))
        m.add_height(-splits * 0.5)
        m.cavity_dirt(splits * weathered, 0.5)

    # Same defect and same fix as `oak_timber`: the species differ in grain
    # COARSENESS, which is a height property, so with a flat albedo all four
    # of them converged on one smooth board by 15 m. Elm measured L* sigma 1.39
    # and the greyed board 0.87 — the two flattest woods in the town.
    m.albedo_break(0.28 + gc * 0.11, 0.14, seed + 533, broad_freq=4,
                   fine_freq=max(16.0, gf))

    m.rough(0.76, 0.13, 0.08, seed + 527)

    if tar > 0:
        # Pine tar on a boat, a shed or a quay pile. Thick, near-black, brushed
        # on, and it RUNS — the runs are the whole read.
        brush = normalize01(fibre(size, 9.0, seed + 528, along="u", warp_amp=0.4))
        cover = np.clip(0.65 + brush * 0.5, 0, 1) * tar
        drip = runs(size, seed + 529, count=11, length=0.8, sharpness=2.6) * tar
        coat = np.clip(cover + drip * 0.9, 0, 1)
        m.tint(P.shade(P.OAK_DARK, 0.45), coat * 0.92)
        m.add_height(coat * 0.10 + drip * 0.14)
        m.roughness = np.clip(m.roughness - coat * 0.42, 0.06, 1.0)
        # Sun-checked tar goes matte and crazes where it is thickest.
        craze = 1.0 - smoothstep(0.0, 0.06, worley(s, 34, seed + 530, metric="f2f1"))
        m.roughness = np.clip(m.roughness + craze * coat * 0.5, 0.06, 1.0)
        m.add_height(-craze * coat * 0.05)

    if char > 0:
        # Fire risk is a real thing in a timber town, and a charred wall or a
        # burnt beam re-used as a lintel is exactly the residue §7 wants. Char
        # is alligatored into deep cubic cracks with grey ash on the ridges and
        # bright carbon in the fissures.
        allig = 1.0 - smoothstep(0.0, 0.09, worley(s, 26, seed + 531, metric="f2f1"))
        depth = np.clip(char * (0.55 + 0.45 * normalize01(fbm(s, 5, seed + 532, octaves=3))),
                        0, 1)
        m.tint(P.shade(P.IRON, 0.30), depth * 0.95)
        m.tint(P.mix(P.COBBLE_WORN, P.PLASTER_SHADE, 0.4), (1.0 - allig) * depth * 0.35)
        m.add_height(-allig * depth * 0.55)
        m.roughness = np.clip(m.roughness + depth * 0.25 - allig * depth * 0.35, 0.06, 1.0)
        m.cavity_dirt(allig * depth, 0.45)
    return m


def end_grain(name="endgrain", size=512, seed=0):
    """The sawn end of a log: woodpile faces, block, chopping stump, joist ends.

    A woodpile textured with side grain is one of those mistakes that nobody
    can name but everybody sees. End grain is concentric — growth rings about a
    pith, radial checks opening from the centre outward, bark on the outside —
    and it is a completely different image from every other wood in the library.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.OAK, P.CANVAS_CREAM, 0.30)
    m.set_base(BASE)

    # Rings about a pith that is deliberately off centre — a tree grown in
    # wind is never concentric, and a centred pith reads as a dartboard.
    v, u = _uv(size)
    cx, cy = 0.5 + 0.10 * np.cos(seed * 0.7), 0.5 + 0.10 * np.sin(seed * 1.3)
    r = np.hypot(u - cx, (v - cy) * 1.12)
    r = r * (1.0 + fbm(s, 4, seed + 541, octaves=3) * 0.20)      # wobbly rings
    rings = np.sin(r * 92.0) * 0.5 + 0.5
    late = smoothstep(0.55, 0.95, rings)                        # dense latewood
    m.add_height(-late * 0.22 + fbm(s, 90, seed + 542) * 0.08)
    m.darken(late, 0.26)
    m.tint(P.OAK_WEATHERED, late * 0.35)

    # Radial checks: they open from the pith and widen outward, which is the
    # single most recognisable thing about a seasoned log end.
    ang = np.arctan2(v - cy, u - cx)
    spokes = normalize01(np.abs(np.sin(ang * 7.0 + fbm(s, 3, seed + 543) * 3.0)))
    check = smoothstep(0.93, 1.0, spokes) * smoothstep(0.04, 0.35, r)
    m.add_height(-check * 0.85)
    m.cavity_dirt(check, 0.55)

    # Saw marks across the face — a pit saw leaves parallel scores, not a
    # smooth surface.
    m.add_height(fibre(size, 46.0, seed + 544, along="v", warp_amp=0.12) * 0.07)

    # Bark and sapwood at the rim.
    rim = smoothstep(0.40, 0.50, r)
    m.tint(P.mix(P.PLASTER_SHADE, P.OAK, 0.45), smoothstep(0.36, 0.44, r) * 0.6)  # sapwood
    m.tint(P.OAK_DARK, rim * 0.9)
    m.add_height(rim * (fbm(s, 40, seed + 545) * 0.4 - 0.1))

    m.rough(0.86, 0.10, 0.07, seed + 546)
    m.roughness = np.clip(m.roughness - late * 0.10, 0.06, 1.0)
    return m


# ---------------------------------------------------------------------------
# Textiles
# ---------------------------------------------------------------------------
# Hearthmere has awnings, bedding, sacks, bolts, laundry, sails and nets. In v1
# they were all one striped canvas, which is why the quest board came out as
# laundry. Cloth divides by FIBRE, WEAVE and DYE, and those are three
# independent axes — a sailcloth and a sack are the same colour and could not
# look less alike.

def sailcloth(name="sailcloth", size=1024, seed=0):
    """Heavy flax canvas: sails, waggon tilts, rick covers, stall backs.

    Sailcloth is made in narrow cloths seamed together, and the seams — double
    rows of stitching with the cloth doubled under — are what identify it at
    any distance. It is also oiled or dressed, so it is stiffer and glossier
    than any other cloth in the town, and it holds hard creases where it was
    folded.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.CANVAS_CREAM, P.PLASTER_SHADE, 0.35)
    m.set_base(BASE)

    m.add_height(weave(size, 190, seed + 551, slub=0.45) * 0.16 +
                 fbm(s, 34, seed + 552) * 0.06)

    # Seams every ~0.5 m: doubled cloth, two rows of stitching.
    _v, _u = _uv(size)
    sm = ((_u + fbm(s, 3, seed + 553, octaves=2) * 0.02) * 4.0) % 1.0
    seam = 1.0 - smoothstep(0.0, 0.045, np.abs(sm - 0.5))
    m.add_height(seam * 0.35)
    stitch = seam * (np.sin(_v * 220.0 * np.pi) * 0.5 + 0.5) ** 3
    m.add_height(-stitch * 0.30)
    m.darken(stitch, 0.30)

    # Hard fold creases: sailcloth is stored folded and remembers it.
    crease = smoothstep(0.90, 1.0, normalize01(ridged(s, 5, seed + 554, octaves=2)))
    m.add_height(-crease * 0.28)
    m.darken(crease, 0.16)

    # Weathering: sun-bleached on the exposed face, mildew-spotted where it
    # was rolled up wet, and stained brown along the bottom edge.
    m.lighten(smoothstep(0.4, 1.0, normalize01(fbm(s, 6, seed + 555, octaves=3))), 0.16)
    mildew = smoothstep(0.84, 0.95, normalize01(worley(s, 18, seed + 556, metric="f2f1")))
    m.tint(P.mix(P.OAK_WEATHERED, P.HERB_GREEN, 0.30), mildew * 0.65)
    m.tint(P.mix(P.OAK_WEATHERED, P.CANVAS_STRIPE, 0.25),
           runs(size, seed + 557, count=6, length=0.5, start=0.55) * 0.7)

    # Patches: every working sail is a map of its own repairs.
    patch = smoothstep(0.80, 0.86, normalize01(fbm(s, 7, seed + 558, octaves=2)))
    m.add_height(patch * 0.22)
    m.darken(patch, 0.12)

    # Flax cloth is spun and woven cloth by cloth, and every one takes the
    # dressing differently; at L* sigma 2.2 and mean 80 this was a white sheet
    # with faint scratches on it.
    m.albedo_break(0.23, 0.14, seed + 5510, broad_freq=5, fine_freq=30, warm=0.24)

    m.rough(0.74, 0.12, 0.07, seed + 559)      # dressed: glossier than sacking
    m.roughness = np.clip(m.roughness + mildew * 0.18, 0.05, 1.0)
    m.hold_to(BASE, 0.6)
    return m


def sacking(name="sacking", size=1024, seed=0):
    """Coarse hessian: grain sacks, wool packs, the mill, the granary.

    The opposite of sailcloth in every way that matters: an open plain weave of
    thick uneven yarn, undyed and dusty, with the weave itself as the dominant
    visual feature at a metre. The gaps between the yarns are real gaps, so it
    catches an enormous amount of contact shadow.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.CANVAS_CREAM, P.OAK_WEATHERED, 0.42)
    m.set_base(BASE)

    # Coarse open weave — a third of the thread count of sailcloth, with much
    # heavier slub, and the interstices modelled as holes in the height.
    # ~4 mm yarn on a 2 m tile. At the first pass's 62 threads the yarn was
    # 6 cm thick and the sack rendered as a regular polka-dot grid — which is
    # also an Art Bible §2 problem, because nothing hand-made repeats that
    # exactly.
    w = weave(size, 260, seed + 561, slub=0.85)
    m.add_height(w * 0.42)
    open_ = smoothstep(0.30, 0.0, normalize01(w))
    m.ao = np.clip(m.ao - open_ * 0.55, 0, 1)
    m.darken(open_, 0.42)

    # Yarn colour varies along its length because it is unbleached jute.
    m.darken(normalize01(fbm(s, 11, seed + 562, octaves=3)) * 0.8, 0.16)
    m.tint(P.mix(P.OAK_WEATHERED, P.COBBLE_WORN, 0.30),
           smoothstep(0.5, 1.0, normalize01(fbm(s, 8, seed + 563))) * 0.35)

    # What sacks carry shows on them: flour bloom, chaff caught in the weave,
    # and the dark ring where a wet sack stood on a stone floor.
    dust = smoothstep(0.55, 0.9, normalize01(fbm(s, 5, seed + 564, octaves=3)))
    m.tint(P.PLASTER, dust * 0.40)
    chaff = smoothstep(0.90, 0.98, normalize01(worley(s, 46, seed + 565, metric="f2f1")))
    m.tint(P.mix(P.CANVAS_CREAM, P.PRODUCE_ACCENT, 0.30), chaff * 0.7)
    m.darken(smoothstep(0.88, 1.0, _uv(size)[0]), 0.30)

    # Loose threads and a burst seam. Every granary has one.
    m.add_height(fibre(size, 90.0, seed + 566, along="u", warp_amp=0.9) * 0.10)

    m.rough(0.94, 0.06, 0.05, seed + 567)
    m.cavity_dirt(open_ * 0.8, 0.30)
    m.hold_to(BASE, 0.65)
    return m


def wool_bolt(name="wool", size=1024, seed=0, colour=P.GUILD_CRIMSON):
    """Dyed broadcloth on the bolt: the tailor, the market, the dyer's poles.

    Fulled and teasel-raised, so it has a soft nap rather than a visible weave,
    and a directional sheen that flips light-to-dark with the nap — which is
    the thing that makes cloth read as *expensive* cloth. Selvedge down one
    edge, because that is where the bolt shows what it is.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(colour)

    # Nap, not weave. Fine directional fibres with a broad sheen banding.
    nap = fibre(size, 130.0, seed + 571, along="v", warp_amp=0.30)
    m.add_height(nap * 0.10 + fbm(s, 46, seed + 572) * 0.05)
    sheen = normalize01(fbm(s, 6, seed + 573, octaves=3))
    m.darken(smoothstep(0.55, 0.0, sheen), 0.16)
    m.tint(P.shade(colour, 1.28), smoothstep(0.5, 1.0, sheen) * 0.45)

    # Vat dyeing is uneven at the fold lines and richer at the selvedge where
    # the cloth hung in the liquor longest.
    fold = smoothstep(0.90, 1.0, normalize01(ridged(s, 4, seed + 574, octaves=2)))
    m.tint(P.shade(colour, 1.22), fold * 0.5)
    _v, _u = _uv(size)
    sel = smoothstep(0.06, 0.0, _u) + smoothstep(0.94, 1.0, _u)
    m.tint(P.mix(colour, P.OAK_DARK, 0.30), np.clip(sel, 0, 1) * 0.6)
    m.add_height(np.clip(sel, 0, 1) * 0.20)

    # Slubs and burrs the fulling did not take out — a hand product always has
    # a few, and they are what stop broadcloth reading as velour.
    burr = smoothstep(0.92, 0.99, normalize01(worley(s, 40, seed + 575, metric="f2f1")))
    m.add_height(burr * 0.18)
    m.darken(burr, 0.18)

    # The nap is authored at frequency 130 — about 1.5 cm — and it is the only
    # thing carrying this material. On the 512 px map a 1 m bolt gets, that is
    # under four pixels a cycle, so it aliases to nothing and all five wool
    # bolts shipped as solid-colour balls (L* sigma 1.1 to 2.2). Broadcloth's
    # real read at arm's length is the SHEEN banding of the nap, which is a
    # sub-decimetre feature, not a sub-centimetre one.
    m.albedo_break(0.28, 0.16, seed + 577, broad_freq=6, fine_freq=26, warm=0.20)

    m.rough(0.86, 0.10, 0.06, seed + 576)
    m.roughness = np.clip(m.roughness - smoothstep(0.6, 1.0, sheen) * 0.16, 0.05, 1.0)
    m.hold_to(colour, 0.8)
    return m


def linen_laundry(name="linen", size=1024, seed=0):
    """Washed linen on the line: shifts, sheets, bandages, tavern cloths.

    Laundry strung between jetties is the highest-value life detail available
    on a back lane (Art Bible §7), and it needs a cloth that is UNDYED — bright
    enough to catch the eye from the square, with the hard creases of being
    wrung out and the slight translucency of wet linen at the edges.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.PLASTER, P.CANVAS_CREAM, 0.25)
    m.set_base(BASE)

    m.add_height(weave(size, 150, seed + 581, slub=0.40) * 0.13 +
                 fbm(s, 40, seed + 582) * 0.05)

    # Wring creases: a strong directional crumple set into the cloth.
    crease = normalize01(ridged(s, 7, seed + 583, octaves=3))
    m.add_height((crease - 0.5) * 0.36)
    m.darken(smoothstep(0.45, 0.0, crease), 0.14)
    m.lighten(smoothstep(0.62, 1.0, crease), 0.12)

    # Not perfectly white: some pieces are bleaching, some are still grey, some
    # have a stain nobody got out. Every one of those is a story.
    grey = smoothstep(0.55, 0.9, normalize01(fbm(s, 4, seed + 584, octaves=3)))
    m.tint(P.mix(BASE, P.SLATE, 0.16), grey * 0.55)
    stain = smoothstep(0.88, 0.96, normalize01(worley(s, 9, seed + 585, metric="f2f1")))
    m.tint(P.mix(P.CANVAS_CREAM, P.OAK_WEATHERED, 0.45), stain * 0.55)
    # Blue from the laundry blueing — a real period detail and a colour lift.
    m.tint(P.mix(P.PLASTER, P.SKY_FILL, 0.20),
           smoothstep(0.72, 1.0, normalize01(fbm(s, 6, seed + 586))) * 0.35)

    # Hem and a patched elbow.
    _v, _u = _uv(size)
    hem = smoothstep(0.035, 0.0, np.minimum(_v, 1 - _v))
    m.add_height(hem * 0.28)
    m.darken(hem, 0.10)

    # Home-washed linen is not one white. It is bleached unevenly on the grass,
    # thin where it has been worn, and every piece on the line has had a
    # different number of washes. At L* sigma 1.18 and mean 86.5 this was a
    # sheet of printer paper, and laundry is meant to be the eye-catching life
    # detail on a back lane (§7) rather than a white rectangle.
    m.albedo_break(0.25, 0.14, seed + 588, broad_freq=5, fine_freq=30, warm=0.25)

    m.rough(0.88, 0.09, 0.06, seed + 587)
    m.hold_to(BASE, 0.6)
    return m


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------
# One material per trade, because a shop whose goods are made of "canvas" and
# "oak" is a shop with nothing in it. These are the surfaces that prove work
# happens: what the tanner hangs up, what the chandler dips, what the baker
# pulls out, what the fishwife stands behind.

def tanned_hide(name="hide", size=1024, seed=0, raw=0.0):
    """Vegetable-tanned leather: aprons, jerkins, harness, the tannery racks.

    Grain side out: the pore pattern is fine and directional, it creases into
    permanent fold lines wherever it has been bent, and it takes a deep
    burnished polish exactly where it is handled. `raw=1` gives the pale
    untanned hide stretched on the tannery frames.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.OAK, P.PRODUCE_ACCENT, 0.22)
    if raw > 0:
        BASE = P.mix(BASE, P.PLASTER_SHADE, 0.55 * raw)
    m.set_base(BASE)

    # Pore/grain structure — fine, and dense enough to survive to 3 m.
    pore = worley(s, 110, seed + 591, metric="f2f1")
    m.add_height(pore * 0.20 + fbm(s, 46, seed + 592) * 0.10)
    m.darken((1.0 - normalize01(pore)) * 0.7, 0.14)

    # Fold lines: the record of what shape this leather has been held in.
    fold = normalize01(ridged(s, 5, seed + 593, octaves=3))
    m.add_height(-smoothstep(0.86, 1.0, fold) * 0.42)
    m.darken(smoothstep(0.80, 1.0, fold), 0.26)
    m.lighten(smoothstep(0.55, 0.80, fold) * 0.6, 0.14)      # burnished ridges

    # Hide colour is never even: the back is darker than the belly, and the
    # tan pit leaves banding.
    m.darken(normalize01(fbm(s, 4, seed + 594, octaves=3)) * 0.9, 0.20)
    m.tint(P.mix(BASE, P.OAK_DARK, 0.40),
           smoothstep(0.60, 1.0, normalize01(fbm(s, 3, seed + 595))) * 0.5)

    # Flesh-side scars, brand marks and the holes where it was laced to a frame.
    scar = smoothstep(0.90, 0.98, normalize01(worley(s, 12, seed + 596, metric="f2f1")))
    m.lighten(scar, 0.22)
    m.add_height(scar * 0.15)

    m.rough(0.58 if raw == 0 else 0.82, 0.16, 0.08, seed + 597)
    m.roughness = np.clip(m.roughness - smoothstep(0.55, 0.85, fold) * 0.22, 0.05, 1.0)
    m.cavity_dirt(smoothstep(0.84, 1.0, fold) * 0.7, 0.30)
    return m


def raw_fleece(name="fleece", size=1024, seed=0):
    """Unwashed fleece: the wool market, the packs, the fuller's, the bed.

    Fleece comes off the sheep in LOCKS — twisted staples with a crimp, matted
    at the cut end and open at the tip — not as a fluffy mass. The lock
    structure and the yellow lanolin grease at the base are the two things that
    make it read as raw wool rather than as cotton wool.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.PLASTER, P.CANVAS_CREAM, 0.45)
    m.set_base(BASE)

    lock, lap = flakes(size, 20, seed + 601, elong=2.2, overlap=0.45)
    m.add_height(lock * 0.55)
    m.ao = np.clip(m.ao - lap * 0.45, 0, 1)
    # Crimp: the fine wave along every staple, which is what catches light.
    crimp = fibre(size, 120.0, seed + 602, along="v", warp_amp=0.25)
    m.add_height(crimp * 0.18)
    m.darken(lap * 0.9, 0.30)

    # Lanolin: yellow-brown grease, heaviest at the cut end and in the mat.
    grease = np.clip(lap * 0.7 + smoothstep(0.5, 0.9,
                                            normalize01(fbm(s, 7, seed + 603, octaves=3))), 0, 1)
    m.tint(P.mix(P.CANVAS_CREAM, P.PRODUCE_ACCENT, 0.30), grease * 0.60)

    # Field dirt: the tips are weathered grey and full of vegetable matter.
    tip = smoothstep(0.5, 1.0, normalize01(lock))
    m.tint(P.mix(P.COBBLE_WORN, P.CANVAS_CREAM, 0.4), tip * 0.35)
    vm = smoothstep(0.92, 0.99, normalize01(worley(s, 50, seed + 604, metric="f2f1")))
    m.tint(P.mix(P.OAK_WEATHERED, P.HERB_GREEN, 0.25), vm * 0.7)

    m.rough(0.90, 0.09, 0.06, seed + 605)
    m.roughness = np.clip(m.roughness - grease * 0.30, 0.06, 1.0)   # grease is glossy
    m.cavity_dirt(lap * 0.7, 0.28)
    m.hold_to(BASE, 0.55)
    return m


def wax_block(name="beeswax", size=512, seed=0, tallow=False):
    """Beeswax and tallow: the chandler, the church candles, sealed jars.

    They are the two ends of one trade and they must not look alike. Beeswax
    is golden, translucent and slightly glossy, and it holds the comb's
    hexagonal ghost in a pressed cake. Tallow is opaque, greasy, grey-white and
    granular, it goes rancid yellow at the surface, and it is what everyone in
    town actually burns.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    if tallow:
        BASE = P.mix(P.PLASTER_SHADE, P.CANVAS_CREAM, 0.30)
    else:
        BASE = P.mix(P.CANVAS_CREAM, P.BRASS, 0.35)
    m.set_base(BASE)

    if not tallow:
        # The comb ghost: a hexagonal field pressed into the cake, soft-edged
        # because the wax was warm when it was pressed.
        cell = worley(s, 34, seed + 611, metric="f2f1")
        m.add_height((1.0 - smoothstep(0.0, 0.20, cell)) * -0.18)
        m.darken((1.0 - smoothstep(0.0, 0.22, cell)) * 0.8, 0.10)
        # Translucency fake: the thin parts read lighter and warmer, which is
        # the only cue available without a subsurface term.
        thick = normalize01(fbm(s, 6, seed + 612, octaves=3))
        m.tint(P.mix(BASE, P.SUN, 0.30), smoothstep(0.45, 1.0, thick) * 0.75)
        m.tint(P.mix(BASE, P.PRODUCE_ACCENT, 0.35), smoothstep(0.45, 0.0, thick) * 0.55)
        m.rough(0.34, 0.14, 0.07, seed + 613)
    else:
        # Tallow: crystalline, granular, and it blooms rancid at the surface.
        gran = worley(s, 96, seed + 614, metric="f2f1")
        m.add_height(gran * 0.28 + fbm(s, 100, seed + 615) * 0.10)
        m.lighten(smoothstep(0.4, 1.0, normalize01(gran)), 0.14)
        rancid = smoothstep(0.40, 0.85, normalize01(fbm(s, 18, seed + 616, octaves=4)))
        m.tint(P.mix(P.CANVAS_CREAM, P.PRODUCE_ACCENT, 0.28), rancid * 0.7)
        # Wick soot and the trapped air a dipped candle always has. Without
        # them tallow renders as a blank white ball and proves nothing about
        # the chandler.
        soot = smoothstep(0.88, 0.98, normalize01(worley(s, 30, seed + 6161)))
        m.tint(P.mix(P.OAK_DARK, P.COBBLE_WORN, 0.4), soot * 0.55)
        void = smoothstep(0.86, 0.97, normalize01(worley(s, 22, seed + 6162, metric="f2f1")))
        m.add_height(-void * 0.35)
        m.cavity_dirt(void * 0.7, 0.30)
        m.rough(0.62, 0.18, 0.09, seed + 617)
        # Grease sweats out and shines in patches. Two sources, per §5.
        sweat = smoothstep(0.7, 0.95, normalize01(fbm(s, 14, seed + 618)))
        m.roughness = np.clip(m.roughness - sweat * 0.40, 0.05, 1.0)

    # Both are poured or dipped, so both have run lines down the side.
    m.add_height(runs(size, seed + 619, count=8, length=0.85) * 0.22)
    # Both are also cast in batches from a pot that was never the same twice,
    # and both were flat: beeswax at L* sigma 1.58 and tallow at 1.23, which on
    # the chandler's bench is two identical cream balls.
    m.albedo_break(0.28, 0.14, seed + 620, broad_freq=5, fine_freq=28,
                   warm=0.30 if not tallow else 0.18)
    return m


def flour_dust(name="flour", size=512, seed=0):
    """Flour-dusted board: the bakery, the mill floor, the granary steps.

    Not a colour — a COVERING. It sits on top of whatever it is on, it is
    thickest in the corners and where a sack was set down, it takes handprints
    and knife marks, and it kills roughness variation to a dead matte. It is
    the fastest way to prove a bakery bakes.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.OAK, P.OAK_WEATHERED, 0.40)
    m.set_base(BASE)

    # The board beneath, so the dust has something to sit on.
    grain = fibre(size, 22.0, seed + 621, along="u", warp_amp=0.5)
    m.add_height(grain * 0.12)
    m.darken(grain * 0.6, 0.18)
    # Knife scores across it.
    cuts = smoothstep(0.96, 1.0, normalize01(ridged(s, 22, seed + 622, octaves=2)))
    m.add_height(-cuts * 0.30)
    m.cavity_dirt(cuts, 0.35)

    # The dust. Patchy, with clear swept and unswept zones and a drift where
    # the sack was tipped.
    drift = smoothstep(0.30, 0.85, normalize01(fbm(s, 13, seed + 623, octaves=4)))
    speck = smoothstep(0.55, 0.9, normalize01(worley(s, 110, seed + 624, metric="f2f1")))
    dust = np.clip(drift * 0.85 + speck * 0.35, 0, 1)
    m.tint(P.PLASTER, dust * 0.88)
    m.add_height(dust * 0.06)

    # A handprint's worth of clean board showing through, and the smear where
    # someone wiped it. Residue, §7.
    wipe = smoothstep(0.55, 0.9, normalize01(fibre(size, 15.0, seed + 625,
                                                   along="u", warp_amp=0.8)))
    m.tint(BASE, np.clip(wipe * drift, 0, 1) * 0.55)

    m.rough(0.80, 0.12, 0.07, seed + 626)
    m.roughness = np.clip(m.roughness + dust * 0.18, 0.05, 1.0)
    return m


def fish_board(name="fish", size=1024, seed=0):
    """The fishmonger's slab: wet boards, scales, brine and ice-melt.

    The wettest surface in the town after the river, and the only place where
    scale iridescence appears. What sells it is the CONTRAST — a near-mirror
    wet zone against dry salt-bleached board — which is precisely the two-scale
    roughness rule doing real work rather than being satisfied on paper.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.OAK_WEATHERED, P.COBBLE_WORN, 0.45)
    m.set_base(BASE)

    # Boards, scrubbed pale, laid across the slab with gaps for the drip.
    joint, unit, ty, tx = coursed(size, 7, 1, bond=0.0, joint=0.030,
                                  wobble=0.06, seed=seed + 631)
    m.add_height(-joint * 0.7)
    m.add_height(fibre(size, 30.0, seed + 632, along="u", warp_amp=0.45) * 0.14)
    m.lighten(unit * 0.6, 0.14)                       # scrubbed, salt-bleached

    # Scales stuck to the wood — the residue that proves the trade.
    # Scales are 8 mm and they stick to the board in ONES, not in drifts. The
    # first pass used a 46-cell field ungated, which put white blooms the size
    # of a hand across the slab and read as mould rather than as fish.
    scale, lap = flakes(size, 90, seed + 633, elong=1.2, overlap=0.3)
    scale = smoothstep(0.55, 0.92, scale)
    stuck = smoothstep(0.74, 0.93, normalize01(fbm(s, 9, seed + 634, octaves=3)))
    sc = np.clip(scale * stuck, 0, 1)
    m.tint(P.mix(P.STEEL, P.PLASTER, 0.30), sc * 0.7)
    # Iridescence, faked as a hue split across the scale field. Restrained: two
    # tints, both palette-derived, or it goes to oil-slick rainbow.
    m.tint(P.mix(P.SKY_FILL, P.VERDIGRIS, 0.40), sc * lap * 0.45)
    m.tint(P.mix(P.PRODUCE_ACCENT, P.PLASTER, 0.55), sc * (1.0 - lap) * 0.30)
    m.add_height(sc * 0.14)

    # Brine: standing wet in the low board joints, dried to salt on the high
    # ones. This is the read.
    wet = np.clip(smoothstep(0.45, 0.85, normalize01(fbm(s, 4, seed + 635, octaves=4)))
                  + joint * 0.6, 0, 1)
    m.darken(wet, 0.34)
    salt = smoothstep(0.80, 0.96, normalize01(fbm(s, 34, seed + 636))) * (1.0 - wet)
    m.tint(P.PLASTER, salt * 0.38)

    m.rough(0.78, 0.14, 0.08, seed + 637)
    m.roughness = np.clip(m.roughness - wet * 0.66 - sc * 0.25 + salt * 0.15, 0.03, 1.0)
    m.cavity_dirt(joint * 0.8, 0.35)
    return m


def bread_crust(name="bread", size=512, seed=0, glaze=0.0):
    """Baked crust: loaves, rolls, pies. `glaze` gives the confectioner's work.

    Crust is a gradient, not a colour: pale where the loaves touched each other
    in the oven, dark where the crown caught the heat, blistered and matte on
    top, and split along the slash where it burst as it rose. The pale contact
    patches are the detail that makes bread read as baked rather than as a
    brown lump.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.PRODUCE_ACCENT, P.OAK, 0.35)
    m.set_base(BASE)

    # Bake gradient.
    heat = normalize01(fbm(s, 11, seed + 641, octaves=4))
    m.tint(P.mix(P.OAK_DARK, P.TERRACOTTA_AGED, 0.45), smoothstep(0.55, 1.0, heat) * 0.7)
    m.tint(P.mix(P.CANVAS_CREAM, P.PRODUCE_ACCENT, 0.35), smoothstep(0.45, 0.0, heat) * 0.8)

    # Blister and crumb: fine bubbles across the crust and a coarse open crumb
    # where it has split.
    blister = worley(s, 34, seed + 642)
    m.add_height((1.0 - blister) * 0.26 + fbm(s, 90, seed + 643) * 0.10)
    # One or two slashes, not a network. Ridged noise at freq 5 covers the
    # whole loaf in pale worms; gated by a sparse mask it reads as the cut the
    # baker actually made.
    sparse = smoothstep(0.72, 0.90, normalize01(fbm(s, 3, seed + 6441, octaves=2)))
    split = smoothstep(0.86, 1.0, normalize01(ridged(s, 9, seed + 644, octaves=2))) * sparse
    m.add_height(-split * 0.55)
    m.tint(P.mix(P.CANVAS_CREAM, P.PLASTER, 0.4), split * 0.7)    # crumb showing
    m.cavity_dirt(split * 0.4, 0.20)

    # Flour on the peel, and the dark speckle of scorched bran.
    m.tint(P.PLASTER, smoothstep(0.72, 0.95, normalize01(fbm(s, 9, seed + 645))) * 0.45)
    m.darken(smoothstep(0.93, 0.99, normalize01(worley(s, 60, seed + 646))), 0.5)

    m.rough(0.72, 0.16, 0.09, seed + 647)

    if glaze > 0:
        # Sugar glaze: poured, so it pools in the hollows and runs off the
        # crown, and it is the glossiest thing in the town after wet fish.
        pool = np.clip(smoothstep(0.35, 0.9, 1.0 - normalize01(blister)) +
                       runs(size, seed + 648, count=10, length=0.7) * 0.8, 0, 1) * glaze
        m.tint(P.mix(P.PLASTER, P.CANVAS_CREAM, 0.25), pool * 0.85)
        m.lighten(pool, 0.20)
        m.add_height(pool * 0.10)
        m.roughness = np.clip(m.roughness - pool * 0.62, 0.03, 1.0)
        # Crystallised edges where the glaze set hard and cracked.
        craze = 1.0 - smoothstep(0.0, 0.05, worley(s, 44, seed + 649, metric="f2f1"))
        m.roughness = np.clip(m.roughness + craze * pool * 0.35, 0.03, 1.0)
        m.add_height(-craze * pool * 0.06)
    return m


def glazed_pottery(name="pottery", size=512, seed=0, glaze_colour=None):
    """Lead-glazed earthenware: jugs, pancheons, crocks, the apothecary's jars.

    A thrown pot's identity is the THROWING RINGS — concentric ridges the
    fingers left — and the way the glaze pools thick and dark in them while
    running thin and translucent over the shoulders. Glaze also stops short of
    the foot, so there is always a band of raw fired clay at the bottom.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BODY = P.mix(P.TERRACOTTA_AGED, P.CANVAS_CREAM, 0.25)
    GLAZE = glaze_colour if glaze_colour is not None else \
        P.mix(P.BRONZE, P.HERB_GREEN, 0.35)
    m.set_base(BODY)

    # Throwing rings run around the pot, so along U in a cylindrical unwrap.
    _v, _u = _uv(size)
    # ~1.2 cm apart on a 1 m tile. At the first pass's 26 they were 7.7 cm and
    # the pot read as a striped beach towel rather than as thrown clay.
    # Throwing rings are a HEIGHT cue and almost nothing else. Given real
    # albedo weight they read as corduroy — a regular light-dark banding is the
    # one thing a hand-thrown pot never has, because the glaze pools across the
    # rings rather than following them.
    ring = np.sin((_v * 84.0 + fbm(s, 3, seed + 651, octaves=2) * 2.4) * np.pi) * 0.5 + 0.5
    ring = ring * (0.45 + 0.55 * normalize01(fbm(s, 7, seed + 6511, octaves=3)))
    m.add_height(ring * 0.09 + fbm(s, 60, seed + 652) * 0.06)

    # Glaze coverage: dipped, so it stops in a wavering line above the foot and
    # runs in tears down from it.
    stop = 0.90 + fbm(s, 4, seed + 653, octaves=2) * 0.06
    cover = smoothstep(0.03, -0.02, _v - stop)
    tear = runs(size, seed + 654, count=12, length=0.16, start=float(np.mean(stop)))
    cover = np.clip(cover + tear * 0.9, 0, 1)
    m.tint(GLAZE, cover * 0.9)
    # Pooling: thicker glaze in the ring hollows is darker and more saturated.
    pool = np.clip(cover * (1.0 - ring), 0, 1)
    m.tint(P.shade(GLAZE, 0.55), pool * 0.35)
    m.lighten(cover * smoothstep(0.75, 1.0, ring), 0.08)

    # Crazing: the fine crackle network in an old lead glaze, stained by use.
    craze = 1.0 - smoothstep(0.0, 0.035, worley(s, 34, seed + 655, metric="f2f1"))
    m.darken(craze * cover, 0.22)
    m.add_height(-craze * cover * 0.05)

    # Kiln accidents: a spot where the glaze crawled, and a grit stuck in it.
    crawl = smoothstep(0.92, 0.99, normalize01(worley(s, 16, seed + 656, metric="f2f1")))
    m.tint(BODY, crawl * cover * 0.8)

    m.rough(0.80, 0.12, 0.07, seed + 657)
    m.roughness = np.clip(m.roughness - cover * 0.58 + craze * cover * 0.10, 0.04, 1.0)
    m.cavity_dirt((1.0 - cover) * 0.4, 0.22)
    return m


# ---------------------------------------------------------------------------
# Metals
# ---------------------------------------------------------------------------
# `wrought_iron` is the structural default. These four are the ones with a
# specific job: iron that has been outside for fifty years, the bell, the good
# fittings on a rich door, and a blade.

def pitted_iron(name="iron_pitted", size=1024, seed=0):
    """Iron left in the weather: gate hinges, the ford chain, the wall cramps.

    Fifty years of rust-scale-rust cycling does not darken iron evenly, it
    EATS it — deep pits with sharp rims, laminated scale lifting in plates, and
    a colour that runs orange through liver-brown to near-black across a
    handspan. The pitting has to be in the height map or it is just a rust
    decal.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(P.mix("#575047", P.TERRACOTTA_AGED, 0.25))
    m.metalness[:] = 0.35        # heavily oxidised: mostly dielectric crust

    # Pitting at two scales, both with sharp rims.
    deep = worley(s, 18, seed + 661)
    fine = worley(s, 52, seed + 662)
    pit = np.clip(smoothstep(0.42, 0.0, deep) * 0.8 + smoothstep(0.30, 0.0, fine) * 0.5, 0, 1)
    m.add_height(-pit * 0.75 + fbm(s, 100, seed + 663) * 0.10)

    # Laminated scale lifting off in plates.
    plate, lap = flakes(size, 14, seed + 664, elong=1.4, overlap=0.35)
    m.add_height(plate * 0.30 - lap * 0.35)
    m.ao = np.clip(m.ao - lap * 0.5, 0, 1)

    # The rust colour run. Three populations across one surface.
    band = normalize01(fbm(s, 6, seed + 665, octaves=4))
    m.tint(P.mix(P.TERRACOTTA, P.PRODUCE_ACCENT, 0.30), smoothstep(0.55, 1.0, band) * 0.8)
    m.tint(P.mix(P.TERRACOTTA_AGED, P.OAK_DARK, 0.45), smoothstep(0.5, 0.15, band) * 0.7)
    m.tint(P.shade(P.IRON, 1.2), smoothstep(0.25, 0.0, band) * 0.8)

    # Bright metal survives only where something rubs — the hinge knuckle, the
    # bearing face of a hand-forged link. That single bright note is what stops
    # the whole object reading as terracotta.
    rub = smoothstep(0.88, 0.98, normalize01(fbm(s, 9, seed + 666, octaves=2))) * \
        (1.0 - pit)
    m.tint(P.STEEL, rub * 0.55)
    m.metalness = np.clip(m.metalness + rub * 0.6, 0, 1)

    # Rust weeps down and stains whatever is below. The stain starts here.
    m.tint(P.mix(P.TERRACOTTA_AGED, P.OAK_DARK, 0.30),
           runs(size, seed + 667, count=9, length=0.7, start=0.1) * 0.6)

    r, _ = P.METAL_SPEC["iron"]
    m.rough(r + 0.28, 0.18, 0.10, seed + 668)
    m.roughness = np.clip(m.roughness - rub * 0.45, 0.06, 1.0)
    m.cavity_dirt(pit * 0.8 + lap * 0.4, 0.35)
    return m


def bell_bronze(name="bronze", size=512, seed=0, bell=True):
    """Cast bell bronze: the church bell, the moot hall bell-cote, the mortar.

    A cast surface is nothing like a forged one: it carries the sand mould's
    texture, the seam where the mould halves met, blowholes, and — on a bell —
    a mirror-bright strike ring where the clapper has polished a band right
    through the patina. That band is the whole story of the object.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(P.BRONZE)
    r, _mt = P.METAL_SPEC["bronze"]
    m.metalness[:] = 0.9

    # Sand-cast skin: fine and slightly granular, not smooth.
    m.add_height(fbm(s, 40, seed + 671, octaves=3) * 0.16 +
                 fbm(s, 110, seed + 672) * 0.08)
    blow = smoothstep(0.88, 0.98, normalize01(worley(s, 22, seed + 673, metric="f2f1")))
    m.add_height(-blow * 0.45)
    m.cavity_dirt(blow, 0.45)

    # Mould seam: a raised line, dressed back but never quite gone.
    _v, _u = _uv(size)
    seam = 1.0 - smoothstep(0.0, 0.012, np.abs(_u - 0.5 +
                                               fbm(s, 3, seed + 674, octaves=2) * 0.02))
    m.add_height(seam * 0.30)

    # Patina: bronze outdoors goes brown then green, and it goes green FIRST
    # where water sits — under the lip, in the inscription bands, in the
    # blowholes.
    wash = smoothstep(0.40, 0.85, normalize01(fbm(s, 7, seed + 675, octaves=4)))
    patina = np.clip(wash * 0.8 + blow * 0.5 +
                     runs(size, seed + 676, count=10, length=0.7) * 0.7, 0, 1)
    m.tint(P.mix(P.VERDIGRIS, P.OAK_DARK, 0.30), patina * 0.75)
    m.metalness = np.clip(m.metalness - patina * 0.7, 0, 1)

    m.roughness = np.ones(s, np.float32)
    m.rough(r, 0.14, 0.07, seed + 677)
    m.roughness = np.clip(m.roughness + patina * 0.38, 0.05, 1.0)

    if bell:
        # The strike ring: a band the clapper has kept bright and burnished.
        ring = smoothstep(0.10, 0.03, np.abs(_v - 0.74))
        m.tint(P.mix(P.BRASS, P.BRONZE, 0.45), ring * 0.85)
        m.metalness = np.clip(m.metalness + ring * 0.9, 0, 1)
        m.roughness = np.clip(m.roughness - ring * 0.45, 0.04, 1.0)
        # Cast decoration bands above and below it — pictorial, never lettered.
        deco = (1.0 - smoothstep(0.0, 0.018, np.abs(_v - 0.55))) + \
               (1.0 - smoothstep(0.0, 0.018, np.abs(_v - 0.60)))
        m.add_height(np.clip(deco, 0, 1) * 0.35)
    return m


def brass_fitting(name="brass", size=512, seed=0):
    """Cast and turned brass: door furniture, lamp mounts, scales, buckles.

    The town's only bright warm metal. It is *handled*, so its story is the
    inverse of everything else in the library — dirt in the crevices and a
    high polish exactly where fingers land, rather than wear on the edges.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(P.BRASS)
    r, _mt = P.METAL_SPEC["brass"]
    m.metalness[:] = 1.0

    # Turning marks (fine concentric) plus casting texture underneath.
    m.add_height(fibre(size, 70.0, seed + 681, along="v", warp_amp=0.10) * 0.10 +
                 fbm(s, 60, seed + 682) * 0.07)
    # File marks from the fitter dressing the casting.
    m.add_height(fibre(size, 34.0, seed + 683, along="u", warp_amp=0.20) * 0.06)

    # Tarnish: brass goes brown-then-green in the parts nobody touches.
    # Fine, not blobby. A tarnish field at freq 8 on a 1 m tile puts 12 cm
    # patches on a door handle, and large soft patches of green on yellow read
    # as mould on cheese at any distance.
    tarnish = smoothstep(0.45, 0.90, normalize01(fbm(s, 26, seed + 684, octaves=4)))
    m.tint(P.mix(P.BRONZE, P.OAK_DARK, 0.35), tarnish * 0.45)
    m.tint(P.mix(P.VERDIGRIS, P.BRONZE, 0.55), smoothstep(0.80, 1.0, tarnish) * 0.35)
    m.metalness = np.clip(m.metalness - tarnish * 0.25, 0, 1)

    # Hand polish. Broad, soft-edged, and it removes the tarnish entirely.
    hand = smoothstep(0.40, 0.88, normalize01(fbm(s, 7, seed + 685, octaves=3)))
    m.tint(P.BRASS, hand * 0.8)
    m.metalness = np.clip(m.metalness + hand * 0.5, 0, 1)

    m.roughness = np.ones(s, np.float32)
    m.rough(r, 0.14, 0.06, seed + 686)
    m.roughness = np.clip(m.roughness + tarnish * 0.30 - hand * 0.16, 0.04, 1.0)
    m.cavity_dirt(smoothstep(0.5, 1.0, tarnish) * 0.5, 0.30)
    return m


def blued_steel(name="steel_blued", size=512, seed=0):
    """Blued and polished steel: blades on the smith's rack, tools, the anvil face.

    Fire-blued steel is an interference film, so its colour is a RUN — straw to
    brown to purple to blue to grey — following how hot each part of the piece
    got. That run is the single most recognisable thing about hand-finished
    steel and it costs almost nothing to author.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    m.set_base(P.shade(P.mix(P.STEEL, P.SLATE, 0.55), 0.50))
    r, _mt = P.METAL_SPEC["steel"]
    m.metalness[:] = 1.0

    # Grinding and polishing scratches, strongly directional along the blade.
    # Grinding scratches carry this material. Faint ones over a light base made
    # it read as glazed porcelain; the strongest single tell of worked metal is
    # a fine ANISOTROPIC scratch field, and it has to be visible.
    scratch = fibre(size, 190.0, seed + 691, along="v", warp_amp=0.05)
    m.add_height(scratch * 0.20 + fbm(s, 90, seed + 692) * 0.04)
    m.darken(scratch * 0.6, 0.10)
    # Hammer planishing behind the edge bevel.
    m.add_height(worley(s, 20, seed + 693, metric="f2f1") * 0.10)

    # The temper run, driven by a broad gradient so it reads as heat, not noise.
    _v, _u = _uv(size)
    heat = np.clip(_v + fbm(s, 3, seed + 694, octaves=3) * 0.22, 0, 1)
    # The run is kept SHALLOW on purpose. A full-strength straw-purple-blue
    # sequence is what a real temper looks like and it measured 8.9 against §4,
    # because the purple midpoint sits between GUILD_CRIMSON and SLATE and
    # belongs to neither. Pulled toward the grey end, it still reads as a
    # tempered blade at gameplay distance — which is a tool rack at 3 m, not a
    # blade held up to the light.
    m.tint(P.mix(P.BRASS, P.STEEL, 0.55), smoothstep(0.20, 0.42, heat) *
           (1.0 - smoothstep(0.42, 0.58, heat)) * 0.55)               # straw
    # Pulled further still, from 0.74 to 0.88. The previous value was already a
    # concession and it was not enough: the residual band measured a+5 b-3,
    # a warm grey-magenta with no §4 family at all, and it carried the material
    # to 6.5. SLATE is the only neutral §4 has in that value range and the
    # purple has to essentially become it. What is lost is invisible at the
    # distance this is seen from — a tool rack at 3 m — and what is gained is
    # that the smith's blades stop being the only lilac object in Hearthmere.
    m.tint(P.mix(P.GUILD_CRIMSON, P.SLATE, 0.88), smoothstep(0.42, 0.62, heat) *
           (1.0 - smoothstep(0.62, 0.76, heat)) * 0.32)               # purple
    # SLATE-family, not SKY_FILL-family. §4's only blues are SKY_FILL and RIM
    # and both are LIGHTING rows — light, and no business being an albedo. A
    # `mix(SKY_FILL, IRON, 0.55)` landed at L*54 with RIM as its nearest family
    # 19 L* above it, which is a 4.8 lightness charge and most of this
    # material's 6.5. SLATE is the one §4 row that is actually a dark blue-grey
    # object colour, and a blued blade IS slate-coloured.
    m.tint(P.mix(P.SLATE, P.STEEL, 0.22), smoothstep(0.62, 0.88, heat) * 0.7)  # blue

    # Edge: bright, unblued, and the highest-spec surface in the town.
    edge = smoothstep(0.10, 0.0, _u) + smoothstep(0.90, 1.0, _u)
    edge = np.clip(edge, 0, 1)
    m.tint(P.STEEL, edge * 0.9)

    # A blade is looked after, so almost no rust — but "almost" is what makes
    # it real. A few specks where a fingerprint sat overnight.
    spot = smoothstep(0.95, 0.995, normalize01(worley(s, 26, seed + 695, metric="f2f1")))
    m.tint(P.mix(P.TERRACOTTA_AGED, P.IRON, 0.35), spot * 0.7)
    m.metalness = np.clip(m.metalness - spot * 0.6, 0, 1)

    m.roughness = np.ones(s, np.float32)
    m.rough(r, 0.10, 0.05, seed + 696)
    m.roughness = np.clip(m.roughness - edge * 0.07 + spot * 0.4, 0.03, 1.0)
    return m


# ---------------------------------------------------------------------------
# Vegetation
# ---------------------------------------------------------------------------
# Cut-out foliage, which is a different discipline from every other material
# here: it is authored as an ATLAS of individual leaves with real alpha, and
# the generator maps a card's UVs onto one atlas rect. Doing it as an opaque
# green noise texture on a cone is what produced v1's candy-striped shrubs.

def leaf_atlas(name="leaf", size=1024, seed=0, species="oak"):
    """An alpha leaf atlas for one species. Sixteen SPRAYS on a 4x4 sheet.

    Four species were asked for because a town's planting is not one plant:
    oak in the churchyard, ash on the river bank, apple in the orchard, willow
    at the water. They differ in outline, in leaflet count, in blade proportion
    and in vein pattern, and all four are readable at 5 m — which is where the
    difference between a modelled town and a green blob is decided.

    **This sheet ships all green, in every season, deliberately.** It used to
    bake a quarter of its leaves bright autumn orange, and since a card that
    maps the whole 4x4 draws every one of the sixteen cells — and 72 % of cards
    do — every canopy in Hearthmere rendered as multicoloured confetti at 09:30
    in high summer with no parameter that could turn it off. The season was
    painted into the texture. It is now a per-card COLOR_0 tint applied at
    generation time by `vegetation.leaf_cards`, so a turning tree is a decision
    about a tree rather than a property of leaves.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    # Species differ by mixing HERB_GREEN with other section 4 rows, never by
    # saturating it. `shade(green, 1.3)` looks like the obvious way to make a
    # sunlit leaf and it is wrong: scaling linear RGB raises CHROMA in step
    # with lightness, and section 1 lists "candy-bright" under "Not this". Real
    # sunlit foliage is lighter AND less saturated — which is `mix` toward the
    # palette's own light neutrals, and costs nothing under the checker because
    # chroma below the family is free.
    SPEC = {
        # base tone, serration freq, elongation, vein freq,
        # leaflets per shoot, shoot divergence, reach
        "oak":    (P.mix(P.HERB_GREEN, P.OAK_DARK, 0.28), 7, 2.30, 9.0,
                   (5, 7), 0.62, 1.06),
        # Ash is pinnate: many narrow leaflets on a long rachis, which is the
        # species read at any distance where the shape survives at all.
        "ash":    (P.mix(P.HERB_GREEN, P.PLASTER, 0.08), 13, 3.10, 13.0,
                   (7, 9), 0.66, 1.20),
        "apple":  (P.mix(P.HERB_GREEN, P.SLATE, 0.20), 17, 2.00, 11.0,
                   (5, 7), 0.58, 1.08),
        # Willow: a long narrow blade, and a lot of them, hanging.
        "willow": (P.mix(P.HERB_GREEN, P.PLASTER_SHADE, 0.12), 5, 4.60, 7.0,
                   (8, 11), 0.72, 1.30),
    }
    tone, lobes, elong, vfreq, leaflets, spread, reach = SPEC.get(species,
                                                                 SPEC["oak"])
    m.set_base(tone)

    alpha, along, across, ident = leaf_cards(size, seed + 701, rows=4, cols=4,
                                             lobes=lobes, elong=elong,
                                             leaflets=leaflets, spread=spread,
                                             reach=reach)

    # Midrib and laterals. The midrib is a raised keel; the laterals branch off
    # it at an angle and are the finest thing that survives to 3 m.
    mid = smoothstep(0.10, 0.0, np.abs(across))
    lat = normalize01(np.abs(np.sin((across * 2.4 + along * vfreq) * np.pi)))
    lat = smoothstep(0.80, 1.0, lat) * (1.0 - mid)
    m.add_height(mid * 0.55 + lat * 0.20 + fbm(s, 90, seed + 702) * 0.06)
    m.darken(lat * 0.7, 0.16)
    m.lighten(mid, 0.14)

    # Leaf-to-leaf colour: sun leaves are yellower and thicker, shade leaves
    # bluer and thinner. `ident` is per LEAFLET now rather than per cell, so a
    # single spray carries five or six distinguishable leaves instead of one
    # flat tone across the whole card — which is most of what stops a canopy
    # reading as painted cardboard.
    # Species read from SHAPE — leaflet count, blade proportion, elongation —
    # not from hue. Section 4 has exactly one green, and a foliage set that
    # differentiates its species by walking away from it ends up with four
    # trees that each belong to a different town.
    m.tint(P.mix(tone, P.PLASTER, 0.13), smoothstep(0.55, 1.0, ident) * 0.65)
    m.tint(P.shade(P.mix(tone, P.SLATE, 0.16), 0.80),
           smoothstep(0.45, 0.0, ident) * 0.6)
    # Shade within the spray: the leaflets low on a shoot sit under the ones
    # above them and are darker for it. Cheap self-shadowing, and the reason a
    # spray reads as depth rather than as a flat cut-out.
    m.darken(smoothstep(0.55, 0.0, along) * 0.55, 0.16)

    # Damage. Every real leaf has some: insect holes, a browned margin, a tear.
    hole = smoothstep(0.90, 0.97, normalize01(worley(s, 60, seed + 703,
                                                     metric="f2f1")))
    m.tint(P.mix(P.OAK_WEATHERED, P.OAK_DARK, 0.4),
           smoothstep(0.80, 0.97, normalize01(worley(s, 60, seed + 703,
                                                     metric="f2f1"))) * 0.45)
    edge_brown = smoothstep(0.86, 1.0, np.abs(across))
    m.tint(P.OAK_WEATHERED, edge_brown * 0.28)

    # Waxy cuticle: leaves are glossier than they look and that sheen is what
    # separates foliage from felt.
    m.rough(0.44, 0.18, 0.10, seed + 704)
    m.roughness = np.clip(m.roughness + lat * 0.12, 0.05, 1.0)

    # One population, one hold. The sheet used to carry two — green leaves and
    # turned ones — and needed a masked hold each; with the season moved out to
    # COLOR_0 there is a single family here and it holds to it.
    m.hold_to(tone, 0.85)
    m.cut(np.clip(alpha - hole * 1.2, 0, 1))
    return m


def needle_atlas(name="leaf_yew", size=1024, seed=0):
    """A yew's flat needle spray. Sixteen sprays on a 4x4 sheet, alpha cut.

    The churchyard yew had no atlas at all: it was routed to `blob_canopy` as a
    MASS, on the argument that a yew reads as a mass at any distance. It does —
    at any distance except the one that matters. The two yews flank the church
    at a ~9 m crown, a player stands under them ten seconds after spawning, and
    a 28-facet lathe at that size has facets three to four metres across. They
    rendered as two flat dark-green angular slabs cropping both aisles off the
    west front, and that frame is the worst in the build.

    A yew is not a broadleaf, so it does not get `leaf_atlas`: the unit is a
    flat spray of linear needles set in two ranks along a shoot, which is what
    this draws — the same spray machinery with the blade run out to a needle's
    proportion and its serration removed.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    # The darkest green in the town, and deliberately still a green: section 1
    # lists crushed black under "Not this", and a yew photographed at 09:30 is
    # a very dark OLIVE with a bright edge, never a silhouette.
    TONE = P.mix(P.HERB_GREEN, P.OAK_DARK, 0.46)
    m.set_base(TONE)

    alpha, along, across, ident = leaf_cards(size, seed + 741, rows=4, cols=4,
                                             lobes=0, elong=6.2,
                                             leaflets=(11, 14), spread=0.46,
                                             reach=1.34, stem=0.10)

    # A needle has one midrib and no laterals, and it is keeled, not flat.
    mid = smoothstep(0.34, 0.0, np.abs(across))
    m.add_height(mid * 0.7 + fbm(s, 120, seed + 742) * 0.05)
    m.lighten(mid, 0.10)
    # The underside band. Yew needles are two-toned — dark above, pale grey-
    # green beneath — and since the cards are double-sided the sheet has to
    # carry both or the back faces of the canopy go flat.
    m.tint(P.mix(TONE, P.PLASTER, 0.34), smoothstep(0.62, 1.0, np.abs(across)) * 0.5)

    # Needle-to-needle variation. A yew shoot carries three years of growth at
    # once and the new season's needles are a full step lighter.
    m.tint(P.mix(P.HERB_GREEN, P.BRASS, 0.16), smoothstep(0.62, 1.0, ident) * 0.55)
    m.tint(P.shade(TONE, 0.78), smoothstep(0.40, 0.0, ident) * 0.55)
    # Older needles low on the shoot sit under the new growth and are darker.
    m.darken(smoothstep(0.5, 0.0, along) * 0.6, 0.18)

    m.rough(0.40, 0.16, 0.09, seed + 743)
    m.hold_to(TONE, 0.85)
    m.cut(alpha)
    return m


def tree_impostor(name="tree_far", size=512, seed=0):
    """Four whole-tree silhouettes on a 2x2 sheet: the distance wood's atlas.

    The wooded ring was 2,300 instances of a 90-triangle lathe. That is 207,000
    triangles spent on the thing the art director called a row of green crystals
    across the Mere, and it is most of why `landscape` was carrying 83 % of the
    town's geometry. A tree at 140 m is fifteen pixels wide: what survives is
    the SILHOUETTE and nothing else, and a silhouette is what a billboard is
    for. Three crossed quads and a cap read better than the lathe did and cost
    eight triangles instead of ninety.

    Four variants rather than one, because a single silhouette repeated two
    thousand times along a horizon is legible AS a repeat, and the horizon is
    the one place the eye is best at catching it.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    v, u = _uv(size)
    gy, gx = v * 2.0, u * 2.0
    iy, ix = np.floor(gy), np.floor(gx)
    ty, tx = gy % 1.0, gx % 1.0
    ident = (iy * 2.0 + ix) / 4.0

    # v runs 0 at the crown's top to 1 at the ground, so a card hung by its top
    # edge stands the tree the right way up.
    cx, cy = 0.5, 0.40
    dx, dy = (tx - cx), (ty - cy)
    th = np.arctan2(dy, dx)
    rad = np.sqrt(dx * dx + (dy * 1.18) ** 2)
    ph = ident * 6.283
    # A crown is lobed at two frequencies and is never an ellipse.
    edge = 0.40 * (1.0 + 0.17 * np.sin(th * 3.0 + ph) +
                   0.10 * np.sin(th * 7.0 - ph * 1.7) +
                   0.06 * np.sin(th * 13.0 + ph * 0.6))
    # Broken margin: real canopy edges are ragged at clump scale, and a clean
    # analytic edge is the tell that gives a billboard away even at 200 m.
    ragged = (normalize01(fbm(s, 26, seed + 761, octaves=3)) - 0.5) * 0.10
    canopy = smoothstep(0.010, -0.004, rad - edge - ragged)
    # Sky through the crown: a real tree is not a solid blob against the light.
    gap = smoothstep(0.62, 0.80, normalize01(worley(s, 13, seed + 762)))
    canopy = np.clip(canopy - gap * smoothstep(0.25, 0.95, rad / 0.40), 0, 1)

    # The bole, from under the crown to the ground. Without it every tree in
    # the ring floats — directive 6.1, and an impostor is not exempt from it.
    trunk_x = cx + 0.03 * np.sin(ph)
    bole = (smoothstep(0.030, 0.020, np.abs(tx - trunk_x)) *
            smoothstep(0.36, 0.46, ty) * smoothstep(1.00, 0.96, ty))
    alpha = np.clip(np.maximum(canopy, bole), 0, 1)

    BASE = P.mix(P.HERB_GREEN, P.OAK_DARK, 0.18)
    m.set_base(BASE)
    # Clump structure. At this range it is the only shading there is, and the
    # difference between a tree and a green pentagon is entirely in this.
    clump = worley(s, 15, seed + 763, metric="f2f1")
    fine = worley(s, 44, seed + 764, metric="f2f1")
    m.add_height(clump * 0.5 + fine * 0.22)
    shade_ = np.clip((1.0 - normalize01(clump)) * 0.8 +
                     (1.0 - normalize01(fine)) * 0.35, 0, 1)
    m.darken(shade_, 0.34)
    m.ao = np.clip(m.ao - shade_ * 0.5, 0, 1)
    # Sky light falls on the top of a crown and nowhere else. This vertical
    # ramp is what makes a flat card read as a sphere of leaves.
    m.lighten(smoothstep(0.55, 0.02, ty) * (1.0 - shade_ * 0.6), 0.13)
    m.darken(smoothstep(0.24, 0.78, ty), 0.30)
    m.tint(P.mix(P.HERB_GREEN, P.BRASS, 0.18), smoothstep(0.7, 1.0, ident) * 0.30)
    m.tint(P.mix(P.HERB_GREEN, P.SLATE, 0.22), smoothstep(0.3, 0.0, ident) * 0.30)
    m.tint(P.mix(P.OAK_DARK, P.COBBLE_WORN, 0.55), bole * 0.9)
    m.rough(0.62, 0.16, 0.08, seed + 765)
    m.hold_to(BASE, 0.75, mask=canopy)
    m.cut(alpha)
    return m


def hedge_mass(name="hedge", size=1024, seed=0):
    """A hedge's surface: many small leaves, deep shadow, twigs and dead wood.

    Deliberately NOT a leaf atlas. A hedge is read as a MASS — the individual
    leaf never resolves — so what carries it is the clump-scale shadow break-up
    and the pale twiggy interior showing through the gaps. Instancing leaf
    cards to make a hedge is the expensive way to get a worse result.

    **It is cut out at clump scale, though**, which is new. `ad-town-03` §19
    read the field boundaries as "solid dark-green extruded ribbons with a
    sinusoidal top edge", and that is what an opaque skin on an extruded ribbon
    always looks like: a rubber slab. A real hedge is see-through in perhaps a
    tenth of its area, and because `hedge_run` is double-sided the holes show
    the far face's interior — dark, out of focus, and reading as depth into the
    bush rather than as damage. One alpha channel, and the silhouette stops
    being a solid.

    It is also no longer built out of the same green Worley mottle as `ivy` and
    `foliage`; see the note in `ivy` about the three-way split.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.HERB_GREEN, P.OAK_DARK, 0.24)
    m.set_base(BASE)

    # The skin is LEAVES, at hawthorn scale — the same core scatter `ivy` and
    # `weeds` use, so the three read as one planting rather than three
    # unrelated greens, and none of them is a Worley mottle any more. 5 cm
    # leaves on a 2 m tile is 38 across, which is the size at which a clipped
    # hedge stops being felt and starts being a plant.
    leaf, radial, ang, lident, llap = shingle_leaves(
        size, seed + 719, cells=38, radius=0.021, lobes=3, sinus=0.22,
        elong=1.30)
    m.add_height((np.cos(np.clip(radial, 0, 1) * 1.3) * 0.34 - llap * 0.40) * leaf)
    m.darken(llap * 0.9, 0.30)
    m.darken((1.0 - lident) * leaf, 0.18)
    m.tint(P.mix(P.HERB_GREEN, P.BRASS, 0.22), smoothstep(0.76, 1.0, lident) * leaf * 0.45)

    # Clumps, over the leaves: a hedge is bundles of shoots, and it is the
    # clump-scale shadow that carries the mass at 10 m when no leaf resolves.
    big = worley(s, 18, seed + 711, metric="f2f1")
    small = worley(s, 70, seed + 712, metric="f2f1")
    m.add_height(big * 0.55 + small * 0.24 + fbm(s, 110, seed + 713) * 0.10)
    shade_ = np.clip((1.0 - normalize01(big)) * 0.85 +
                     (1.0 - normalize01(small)) * 0.45, 0, 1)
    m.darken(shade_, 0.46)
    m.ao = np.clip(m.ao - shade_ * 0.62, 0, 1)

    # Sunlit tips: bright, yellow-green, and only on the outermost clumps.
    tip = smoothstep(0.58, 1.0, normalize01(big)) * leaf
    m.lighten(tip, 0.18)
    m.tint(P.shade(P.HERB_GREEN, 1.25), tip * 0.7)

    # New growth, as PATCHES. This was a `v` ramp — "the top of the hedge is
    # yellower" — which on a tiling sheet is a yellow band every 2 m along a
    # 60 m field boundary. A tile has no top; see FREQ_FLOOR.
    new = smoothstep(0.50, 0.88, mottle(size, seed + 714, freq=8, octaves=3))
    m.tint(P.mix(P.HERB_GREEN, P.BRASS, 0.20), new * leaf * 0.45)

    # The dark twiggy interior and the odd dead branch, which is the detail
    # that makes a hedge read as grown rather than as extruded.
    gap = smoothstep(0.72, 0.95, normalize01(fbm(s, 8, seed + 715, octaves=4)))
    m.tint(P.shade(P.OAK_DARK, 0.7), gap * 0.9)
    dead = smoothstep(0.94, 1.0, normalize01(ridged(s, 18, seed + 716, octaves=2)))
    m.tint(P.mix(P.OAK_WEATHERED, P.COBBLE_WORN, 0.4), dead * 0.7)
    m.add_height(dead * 0.18)

    m.rough(0.56, 0.18, 0.10, seed + 717)
    m.cavity_dirt(shade_ * 0.5, 0.22)
    m.hold_to(BASE, 0.75)

    # The cut. A hole needs BOTH a gap between the leaves and a gap between the
    # clumps, so the sheet loses about a tenth of its area at clump scale with
    # a leaf-shaped margin, rather than going lacy everywhere.
    hole = np.clip((1.0 - leaf) * smoothstep(0.55, 0.90, gap + (1.0 - normalize01(big)) * 0.35), 0, 1)
    m.cut(1.0 - smoothstep(0.25, 0.55, hole))
    return m


def ivy(name="ivy", size=1024, seed=0):
    """Ivy on a wall: overlapping palmate leaves, ALPHA-CUT, with stems.

    ## Why this was rebuilt

    `ad-town-03` §14 read the shipped sheet and found "an opaque green Voronoi
    crazy paving with no alpha cutout and no leaf shapes whatever". That is
    exactly what it was: `flakes()` is a Worley cell field, so what this drew
    was polygons, and with no alpha the `ivy_panel` quads and the town wall's
    ivy boxes rendered as **solid green rectangles pasted on the wall**. That
    one texture is simultaneously §14's "green daub doing wall infill" and
    §18's "flat rectangular ivy" — one material, two findings.

    It also had no business being the same recipe as `hedge_mass` and
    `foliage`. Three surfaces that a player reads completely differently — a
    climber on a wall, the clipped skin of a hedge, and the weeds in a paving
    joint — were one green mottle, which is what "green is the material of last
    resort in five places" actually means. They are three materials now:

      `ivy`     a cut-out mat of palmate leaves, for walls
      `hedge`   a clipped MASS, holed at clump scale so it is not a rubber slab
      `weeds`   a cut-out mat of small ground leaves and blades, for the ground

    Ivy's identity: leaves overlap in shingled layers all facing outward, pale
    veins radiate palmately from the petiole, and the wiry brown stems with
    their root hairs show between the leaves. The margin has to be BROKEN —
    that is the whole difference between ivy and a green decal — which is what
    the alpha buys and what `ivy_panel`'s ragged quad grid could only fake.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.shade(P.mix(P.HERB_GREEN, P.SLATE, 0.25), 0.86)
    m.set_base(BASE)

    alpha, radial, angle, ident, lap = shingle_leaves(
        size, seed + 721, cells=21, radius=0.043, lobes=5, sinus=0.62,
        elong=1.26)

    # The leaf is domed and its margin turns down, which is what makes a mat of
    # them catch light as a hundred separate objects rather than one sheet.
    m.add_height((np.cos(np.clip(radial, 0, 1) * 1.4) * 0.55 - lap * 0.55) * alpha)
    m.ao = np.clip(m.ao - lap * 0.55, 0, 1)
    m.darken(lap * 0.9, 0.42)

    # Palmate venation: `lobes` main veins from the petiole to each lobe tip,
    # pale against the dark blade — the single identifying feature of ivy.
    vein = smoothstep(0.72, 1.0, np.abs(np.cos(angle * 2.5))) * \
        smoothstep(0.08, 0.30, radial) * (1.0 - smoothstep(0.86, 1.0, radial))
    mid = smoothstep(0.14, 0.0, np.abs(np.sin(angle))) * (1.0 - smoothstep(0.9, 1.0, radial))
    vein = np.clip(np.maximum(vein, mid), 0, 1) * alpha
    m.tint(P.mix(P.HERB_GREEN, P.CANVAS_CREAM, 0.45), vein * (1.0 - lap) * 0.55)
    m.add_height(vein * 0.16)

    # Leaf-to-leaf variance, and the paler juvenile growth at the leading edge.
    m.darken((1.0 - ident) * alpha, 0.22)
    m.tint(P.mix(P.HERB_GREEN, P.BRASS, 0.25), smoothstep(0.74, 1.0, ident) * alpha * 0.55)
    m.tint(P.shade(P.mix(P.HERB_GREEN, P.OAK_DARK, 0.40), 0.82),
           smoothstep(0.30, 0.0, ident) * alpha * 0.55)
    # The margin of an ivy leaf is a shade paler and often bronzed.
    m.tint(P.mix(P.HERB_GREEN, P.OAK_WEATHERED, 0.35),
           smoothstep(0.80, 1.0, radial) * alpha * 0.30)

    # Stems and aerial roots, running UP the wall between the leaves. They are
    # part of the cut-out: a stem crossing a gap is what stops the holes in the
    # mat reading as damage.
    stem = normalize01(fibre(size, 9.0, seed + 724, along="v", warp_amp=1.3))
    stemm = smoothstep(0.86, 0.96, stem) * (1.0 - smoothstep(0.2, 0.6, alpha))
    m.tint(P.mix(P.OAK_WEATHERED, P.OAK_DARK, 0.45), stemm * 0.9)
    m.add_height(stemm * 0.26)

    m.rough(0.38, 0.18, 0.10, seed + 725)      # ivy is the waxiest leaf here
    m.roughness = np.clip(m.roughness + lap * 0.25 + stemm * 0.35, 0.05, 1.0)
    m.cavity_dirt(lap * 0.6, 0.26)
    m.hold_to(BASE, 0.80, mask=(alpha > 0.5).astype(np.float32))
    m.cut(np.clip(alpha + stemm, 0, 1))
    return m


def ground_weeds(name="weeds", size=1024, seed=0):
    """Ground cover, alpha-cut: the weeds in a joint, the green in a gutter.

    The third of the split named in `ivy`. This is what lies flat ON the
    ground and on the bottom courses of a wall — plantain and dandelion
    rosettes, chickweed, a little grass — and the reason it cannot be `foliage`
    or `hedge` is that both of those are opaque, so `vegetation.joint_weeds`
    and `tussock` drew as **flat saturated-green triangles lying on the
    paving** (`ad-town-03` §14, `wharf-walk-07`). A weed has a silhouette or it
    is a sticker.

    Rosettes rather than a mat: fewer, rounder, blunter leaves than ivy, with
    real ground showing between them, and grass blades through the gaps.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.HERB_GREEN, P.OAK_WEATHERED, 0.16)
    m.set_base(BASE)

    # One lobe and a shallow sinus: an ovate, blunt-ended rosette blade, not a
    # palmate climber. Sparser, so the substrate reads between the clumps.
    alpha, radial, angle, ident, lap = shingle_leaves(
        size, seed + 731, cells=19, radius=0.036, lobes=1, sinus=0.16,
        elong=1.75, aspect=1.20)

    m.add_height((np.cos(np.clip(radial, 0, 1) * 1.25) * 0.40 - lap * 0.45) * alpha)
    m.ao = np.clip(m.ao - lap * 0.45, 0, 1)
    m.darken(lap * 0.85, 0.34)

    # Plantain's ribs: parallel, running the length of the blade, not palmate.
    rib = smoothstep(0.62, 1.0, np.abs(np.cos(angle * 3.5))) * \
        smoothstep(0.06, 0.26, radial)
    m.darken(rib * alpha * 0.7, 0.13)
    m.add_height(rib * alpha * 0.14)

    # Grass blades through the gaps: finer, lighter, and standing more upright.
    blade = normalize01(fibre(size, 26.0, seed + 732, along="v", warp_amp=1.5))
    blades = smoothstep(0.88, 0.97, blade) * (1.0 - smoothstep(0.25, 0.7, alpha))
    m.tint(P.mix(P.HERB_GREEN, P.BRASS, 0.30), blades * 0.85)
    m.add_height(blades * 0.30)

    # Leaf-to-leaf, plus the dry and the trodden ones. Ground cover in a town
    # is walked on, so a third of it is not green at all.
    m.darken((1.0 - ident) * alpha, 0.20)
    m.tint(P.mix(P.HERB_GREEN, P.PLASTER, 0.22), smoothstep(0.72, 1.0, ident) * alpha * 0.5)
    trod = smoothstep(0.58, 0.92, mottle(size, seed + 733, freq=9))
    m.tint(P.mix(P.OAK_WEATHERED, P.COBBLE_WORN, 0.35), trod * alpha * 0.45)

    m.rough(0.58, 0.16, 0.09, seed + 734)
    m.hold_to(BASE, 0.80, mask=(alpha > 0.5).astype(np.float32))
    m.cut(np.clip(alpha + blades, 0, 1))
    return m


def thatch_variant(name="thatch", size=1024, seed=0, age=0.5, material="reed"):
    """Thatch by age and material. The commonest roof in the town.

    Water reed is hard, grey-gold and lasts forty years; wheat straw is soft,
    warm and lasts fifteen. Both weather from the ridge down and from the
    surface in, so a thatch roof is a gradient — and the ONE thing that makes
    thatch read as thatch is the cut end at the eaves, a dense mat of stem
    ends, quite unlike the smooth swept surface above it.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    NEW = P.mix(P.CANVAS_CREAM, P.OAK, 0.30) if material == "straw" else \
        P.mix(P.CANVAS_CREAM, P.OAK_WEATHERED, 0.42)
    OLD = P.mix(P.OAK_WEATHERED, P.COBBLE_WORN, 0.45)
    m.set_base(P.mix(NEW, OLD, np.clip(age, 0, 1)))

    # -- stems ---------------------------------------------------------------
    # `crop/NEW-thatch.png` — `ad-town-04` §10 read the shipped sheet as "a flat
    # brown-olive blur with a low-contrast fingerprint whorl" containing "no
    # straw in it at all". The whorl is this line, and the cause is the warp:
    #
    # `fibre` phase-warps by `w * freq`, so `warp_amp=0.30` at `freq=170`
    # displaces the phase by up to **51 half-cycles**. That does not make stems
    # wander, it destroys them — every stem is shifted past its neighbours and
    # what is left is the contour map of the warp field, which is exactly the
    # fingerprint the review saw.
    #
    # The usable band is narrow and it is easy to overshoot in the other
    # direction: I rendered `0.016` and got perfectly parallel stripes, which
    # is the failure `fibre`'s own docstring names — "a clean sine aliases
    # against the UV scale and reads as painted stripes". `0.05 * 170` is ~8
    # half-cycles on the broad term at 3 cycles per tile, so a stem wanders by
    # about four stems across a 4 m tile: gently, and never past the point
    # where it stops being a stem.
    #
    # `along="u"` is correct and is deliberate. `core/roof.py` lays roof UVs as
    # `(t along the eaves, s up the slope)`, and `fibre` draws lines of
    # CONSTANT `g` — so `along="u"` gives lines of constant `t`, which run up
    # the slope. Water runs down the stems; this is the axis that has to be
    # right and it is easy to invert.
    #
    # Reed is 6-10 mm across and straw finer. On a 4 m tile that is more
    # frequency than 128 px/m can resolve, so this is the finest that survives:
    # about 2 cm, which reads as a stem field rather than as floorboards.
    freq = 220.0 if material == "straw" else 170.0
    stem = fibre(size, freq, seed + 731, along="u", warp_amp=0.05)
    m.add_height(stem * 0.30 + ridged(s, freq * 1.4, seed + 732, octaves=2) * 0.16)
    m.darken(stem * 0.8, 0.24)

    # Bundle courses: thatch is laid in bundles and the ridge of each course
    # shows as a SOFT SWELL along the eaves. This is the read at 20 m.
    #
    # `_v * 5.0` has period 0.4 of a tile — on the authored 4 m tile that is a
    # bundle every 1.6 m, four times what a thatcher lays. But 20.0 (0.40 m) at
    # the amplitudes below rendered as **corrugated iron** on `mere-walk-05`,
    # which is the exact failure `roof._thatch_slope` warns about: *"stacked
    # courses read as corrugated sheet, which is the opposite of thatch — whose
    # whole character is depth and the absence of any hard edge."*
    #
    # 14.0 is 0.57 m, a real course, at half the height and with the wander
    # doubled so no two bands run parallel for long. A thatch course is a swell
    # you can see from the square and cannot find with a finger.
    _v, _u = _uv(size)
    course = np.sin((_v * 14.0 + fbm(s, 8, seed + 733, octaves=2) * 1.1) * np.pi) * 0.5 + 0.5
    m.add_height(course * 0.16)
    m.darken(1.0 - course, 0.10)
    m.ao = np.clip(m.ao - (1.0 - course) * 0.18, 0, 1)

    # -- weathering, WITHOUT a gradient in v ---------------------------------
    # This carried three ramps in `v` — `smoothstep(0.35,1.0,_v)` for age,
    # `smoothstep(0.4,0.0,_v)` for the bleach, and `smoothstep(0.15,0.8,_v)`
    # on the moss — plus an eaves cut at `smoothstep(0.88,0.97,_v)`. On a 4 m
    # tile a 9 m cottage slope shows that band twice and a barn three times,
    # which is `ad-town-04` §10 exactly: *"a roof tiled three times in v gets
    # three eaves bands and three age gradients"*. See the tile-repeat rule
    # above `mottle`: a tile has no top and no bottom, and it cannot know where
    # the eaves is.
    #
    # The eaves cut is gone from the tile entirely, and it has not been lost:
    # `roof._thatch_slope` already builds the rolled eaves as GEOMETRY — three
    # facets curling under — which is what it is in reality and what the review
    # asked for. What survives here is the part a tile can honestly carry:
    # weathering in PATCHES, because a thatch roof does not age evenly, it ages
    # where the moss took and where the sun reaches.
    wear = mottle(size, seed + 737, freq=7, octaves=3)
    m.tint(OLD, smoothstep(0.42, 1.0, wear) * (0.35 + age * 0.45))
    m.lighten(smoothstep(0.45, 0.05, wear) * 0.7, 0.16)
    moss = smoothstep(0.62 - age * 0.20, 0.92,
                      normalize01(fbm(s, 14, seed + 734, octaves=3)))
    moss = moss * smoothstep(0.30, 0.75, wear)
    m.tint(P.mix(P.HERB_GREEN, P.OAK_DARK, 0.30), moss * (0.30 + age * 0.40))

    # Stem ENDS, where a bundle butt shows through the swept surface. In the
    # tile this is a scatter, not a band — the band is the mesh's eaves.
    ends = normalize01(worley(s, 120, seed + 735, metric="f2f1"))
    butt = smoothstep(0.55, 0.95, mottle(size, seed + 738, freq=11, octaves=2))
    m.add_height(butt * (ends * 0.30 - 0.08))
    m.lighten(butt * smoothstep(0.4, 1.0, ends), 0.20)
    m.darken(butt * (1.0 - ends) * 0.8, 0.22)

    # Spar coats and the netting an old roof gets to keep the birds out.
    if age > 0.6:
        # Same band mask as the window's saddle bars, and it had the same
        # `- 0.46` defect: the netting covered the whole roof instead of
        # being a grid of cords over it.
        net = np.clip((1.0 - smoothstep(0.004, 0.012, np.abs((_u * 24) % 1.0 - 0.5))) +
                      (1.0 - smoothstep(0.004, 0.012, np.abs((_v * 24) % 1.0 - 0.5))), 0, 1)
        m.darken(net * 0.7, 0.22)
        m.add_height(net * 0.10)

    m.rough(0.93 - age * 0.05, 0.08, 0.06, seed + 736)
    m.roughness = np.clip(m.roughness + moss * 0.10, 0.05, 1.0)
    m.cavity_dirt((1.0 - course) * 0.5, 0.28)
    return m


def straw_bundle(name="straw", size=512, seed=0, reed=False):
    """Loose straw and cut reed: bedding, packing, the thatcher's stack, ricks.

    Distinct from `thatch_variant` because loose straw has no course structure
    and no weathering gradient — it is a jackstraw pile of individual stems
    lying every which way, with the light passing between them.
    """
    m = MaterialSet(name, size)
    s = (size, size)
    BASE = P.mix(P.CANVAS_CREAM, P.HERB_GREEN, 0.20) if reed else \
        P.mix(P.CANVAS_CREAM, P.PRODUCE_ACCENT, 0.22)
    m.set_base(BASE)

    # Two crossed stem fields, so the pile has no single direction.
    a = fibre(size, 44.0, seed + 741, along="u", warp_amp=0.8)
    b = fibre(size, 38.0, seed + 742, along="v", warp_amp=0.9)
    mix = smoothstep(0.35, 0.65, normalize01(fbm(s, 5, seed + 743, octaves=2)))
    stem = a * mix + b * (1.0 - mix)
    m.add_height(stem * 0.55 + fbm(s, 120, seed + 744) * 0.10)
    m.darken((1.0 - normalize01(stem)) * 0.9, 0.42)
    m.ao = np.clip(m.ao - (1.0 - normalize01(stem)) * 0.5, 0, 1)

    # Per-stem colour: cut straw runs from bleached white to green-gold, and
    # the nodes are darker than the internodes.
    per = per_unit(size, 34, seed + 745, steps=6)
    m.lighten(smoothstep(0.55, 1.0, per), 0.24)
    m.tint(P.mix(BASE, P.OAK_WEATHERED, 0.40), smoothstep(0.35, 0.0, per) * 0.6)
    node = smoothstep(0.93, 0.99, normalize01(worley(s, 26, seed + 746, metric="f2f1")))
    m.darken(node, 0.30)

    # Chaff and grain heads still in it, and the dust that comes off it.
    head = smoothstep(0.88, 0.97, normalize01(worley(s, 18, seed + 747, metric="f2f1")))
    m.tint(P.mix(P.PRODUCE_ACCENT, P.CANVAS_CREAM, 0.45), head * 0.65)
    m.add_height(head * 0.16)

    m.rough(0.90, 0.09, 0.07, seed + 748)
    m.cavity_dirt((1.0 - normalize01(stem)) * 0.6, 0.28)
    m.hold_to(BASE, 0.6)
    return m


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------
# Every entry declares three things beyond its builder, and each of them was
# previously either implicit or held in a second file:
#
#   coverage  world metres spanned by one tile. Art Bible §5 says 2 m unless
#             noted, and this is where a material NOTES it. It is also the UV
#             scale a generator must use — see `uv_scale`.
#   klass     hero / standard / large, per §5's texel-density table. Together
#             with coverage it fixes the texture SIZE, which is why a build no
#             longer authors everything at 1024 regardless of whether the
#             player can get within 2 m of it.
#   flags     emissive / double / mask. `core/venue.py` used to hold these as
#             two hardcoded sets, which meant adding a lit material required
#             editing a file in a different directory and nothing failed if you
#             forgot — `glass_lit` shipped without its emissive wired for
#             exactly that reason.

# Art Bible §5 texel-density table.
# `impostor` is not a surface class, it is a whole-object class. A billboard
# sheet does not tile across a wall: one cell of it IS a nine-metre tree, seen
# only past 140 m where it is fifteen pixels wide. Declaring `tree_far` as
# `standard` with `coverage = 1.0` claimed its 512 px tile covered one metre of
# world — 512 px/m, twice the standard class, which is what validate failed on.
# The tile really covers a 2x2 grid of whole trees, about 16 m of world, and at
# the range it is drawn 32 px/m is already more resolution than the frame can
# show. The number is honest and the audit passes on the truth rather than on a
# coverage figure bent to hit a target.
DENSITY = {"hero": 512.0, "standard": 256.0, "large": 128.0, "impostor": 32.0}
# 512 is a hard floor, and it is not arbitrary. Every builder in this file
# carries a fine-detail octave between `fbm(s, 70)` and `fbm(s, 150)` — sand
# grain, plaster tooth, wood pore, mica. A tileable Perlin field needs about
# six pixels per cycle before it stops being detail and starts being static, so
# freq 90 needs 540 px. Shrinking below that does not make a cheaper material,
# it makes a noisy one, and the noise then survives every mip.
#
# The floor has a consequence worth stating plainly: it means a HERO material
# must cover >= 1 m, a STANDARD >= 2 m and a LARGE >= 4 m to land on its class
# density. Every entry below obeys that, and `density_audit` proves it.
SIZE_MIN, SIZE_MAX = 512, 2048


class Mat:
    """A library entry: a builder plus the metadata the pipeline needs.

    Callable, so `LIBRARY[key](name=..., seed=...)` still works exactly as it
    did for every existing caller. The size it passes is derived, not asked
    for, which is the whole point.
    """

    __slots__ = ("fn", "coverage", "klass", "flags", "_size")

    def __init__(self, fn, coverage=2.0, klass="standard", flags=(), size=None):
        self.fn = fn
        self.coverage = float(coverage)
        self.klass = klass
        self.flags = frozenset(flags)
        self._size = size

    @property
    def size(self):
        """Texture resolution: class density x world coverage, to a power of 2.

        An explicit `size=` overrides, and three materials use it. Each is a
        case where the builder's fine octaves sit above the class resolution —
        `earth` puts real structure at 2 cm on a 4 m tile — so honouring the
        class would replace detail with aliasing. Overriding is recorded at the
        entry rather than hidden in the builder.
        """
        if self._size:
            return int(self._size)
        want = DENSITY.get(self.klass, 256.0) * self.coverage
        p2 = int(2 ** round(np.log2(max(want, 1.0))))
        return int(np.clip(p2, SIZE_MIN, SIZE_MAX))

    @property
    def density(self):
        return self.size / self.coverage

    def __call__(self, **kw):
        kw.setdefault("size", self.size)
        m = self.fn(**kw)
        # The registry is the single source for these; a builder may not
        # disagree with the entry that names it.
        m.coverage, m.klass = self.coverage, self.klass
        return m


class UVScale(float):
    """A UV scale that has been *justified* — by the library or by a reason.

    A plain `float` reaching a mesh builder's `uv_scale=` is a build error
    (see `core/mesh.py:resolve_uv`). This type is the token that says the
    number came from `uv_scale()` or `uv_detail()` rather than from somebody
    typing a digit that looked right in one frame.

    ## Why a type and not a convention

    `ad-town-04` §2 counted **421 literal `uv_scale=` call sites against 3 uses
    of `MATS.uv_scale()`**, and every one of the four material rebuilds that
    wave — `coursed`, `foundation_stone`, `limewash`, `rubble` — landed
    correctly in the sheet and changed nothing on screen, because the number of
    metres each tile covered was decided at the mesh by a literal. A convention
    that has been ignored 421 times is not a convention. This makes the wrong
    thing raise.
    """

    __slots__ = ("key", "why")

    def __new__(cls, value, key=None, why=None):
        o = float.__new__(cls, value)
        o.key, o.why = key, why
        return o

    def __repr__(self):
        return (f"UVScale({float(self):.4f}, key={self.key!r}, "
                f"{1.0 / max(float(self), 1e-9):.2f} m/tile, why={self.why!r})")


def uv_scale(key):
    """UV units per world metre for a material. Pass to mesh builders.

    `core/mesh.py` lays UVs in METRES (`_planar_uv` with `uv_scale=1.0`), so a
    material with no scale applied covers one metre per tile whatever it was
    authored for. That is a texel-density error of exactly `coverage`x on every
    surface in the town, and it is why this function exists — see D-024.

    You should almost never need to call this: as of D-046 a mesh builder with
    no `uv_scale` asks the library itself, using the material key it was
    already given. It stays public for the code that lays UVs by hand
    (`streets._Paving`, `landscape`, `roof`), which has no builder to ask.
    """
    return UVScale(1.0 / LIBRARY[key].coverage, key, "library coverage")


def uv_detail(key, metres, why):
    """A LOCAL override of a material's authored coverage, with its reason.

    `metres` is world metres per tile — the same unit `Mat.coverage` is in, so
    a call reads as the thing it does: `uv_detail("slate", 0.40, "a 0.34 m
    sample slate on the shopfront: at the library's 4 m one tile shows a ninth
    of one tile-course and the sample reads as flat grey")`.

    Two cases are legitimate and no others are:

      **too small.** A member well under the tile — a 0.13 m heap of flour, a
      0.34 m slate, a 0.12 m wax seal — shows a fraction of one tile at the
      authored scale, and a fraction of a tile is not a texture, it is a
      colour. Tighten it.

      **too big to repeat.** A single giant unit — a lintel stone, a quay
      coping — where the authored tile would visibly repeat across one object.

    "It looked better" is not a reason and neither is silence, which is why
    `why` is required and is not defaulted.
    """
    if key not in LIBRARY:
        raise KeyError(f"uv_detail: unknown material {key!r}")
    m = float(metres)
    if not (m > 0.0):
        raise ValueError(f"uv_detail({key!r}): metres must be > 0, got {metres!r}")
    if not (isinstance(why, str) and len(why.strip()) >= 12):
        raise ValueError(
            f"uv_detail({key!r}, {metres}): `why` must be a real sentence. "
            f"An override with no reason is the literal this replaced.")
    return UVScale(1.0 / m, key, why)


def flagged(flag):
    return {k for k, m in LIBRARY.items() if flag in m.flags}


def density_audit():
    """[(key, size, coverage, px/m, class, target, verdict)] for every entry.

    Art Bible §8 lists texel density as a done-criterion, so it needs to be
    something a build can print rather than something a reviewer measures with
    a ruler. Tolerance is half a stop either way, because the sizes are powers
    of two and the coverages are not.
    """
    out = []
    for k in sorted(LIBRARY):
        m = LIBRARY[k]
        want = DENSITY.get(m.klass, 256.0)
        got = m.density
        ratio = got / want
        verdict = "ok" if 0.71 <= ratio <= 1.42 else ("over" if ratio > 1 else "under")
        out.append((k, m.size, m.coverage, got, m.klass, want, verdict))
    return out


# Coverage rationale, stated once here rather than repeated at 90 entries:
#   1.0 m  props and trim the player stands over — a barrel, a sign, a hide
#   2.0 m  the §5 default: walls, doors, cloth, most everything
#   4.0 m  ground and roofs, where a 2 m tile visibly repeats across a street
#   8.0 m  the lake, whose tile must not be countable from the wall walk
LIBRARY = {
    # -- architecture: walls -------------------------------------------------
    "plaster":      Mat(lambda **k: lime_plaster(**k), 2.0, "standard"),
    "plaster_shade": Mat(lambda **k: lime_plaster(shaded=True, **k), 2.0, "standard"),
    "limewash":     Mat(lambda **k: limewashed_stone(**k), 2.0, "standard"),
    "stone":        Mat(lambda **k: foundation_stone(**k), 2.0, "standard"),
    "rubble":       Mat(lambda **k: rubble_weathered(**k), 2.0, "standard"),
    "cobble_wall":  Mat(lambda **k: cobble_walling(**k), 2.0, "standard"),
    "ashlar":       Mat(lambda **k: ashlar(**k), 2.0, "standard"),
    "ashlar_civic": Mat(lambda **k: ashlar_civic(**k), 2.0, "hero"),
    "sandstone":    Mat(lambda **k: sandstone(**k), 2.0, "standard"),
    "brick":        Mat(lambda **k: handmade_brick(**k), 2.0, "standard"),
    "nogging":      Mat(lambda **k: brick_nogging(**k), 2.0, "standard"),
    "marble":       Mat(lambda **k: alabaster(marble=True, **k), 2.0, "hero"),
    # The altar the player spawns on. The only surface in the world that is
    # guaranteed to be looked at from under a metre, so it is hero class and it
    # gets a metre of coverage to spend it on.
    "alabaster":    Mat(lambda **k: alabaster(**k), 1.0, "hero"),

    # -- architecture: roofs -------------------------------------------------
    # Roofs are `large` per §5 and get 4 m tiles: a 2 m roof tile repeats
    # eleven times up a cottage gable and the repeat is countable from the
    # square.
    # `standard`, not `large`. §5 files roofs under Large (128 px/m) alongside
    # distant walls, and that was defensible while every roof sampled its 4 m
    # texture over 1.17 m of world and got 437 px/m by accident. With the UV
    # error fixed (D-041) the declared density is what ships, and 128 px/m puts
    # 20 px on a 0.16 m course — not enough to resolve the barrel curvature or
    # tell an aged tile from a fired one. A cottage eave is 2.4 m off the
    # ground and roofs are the largest surface in every aerial in the review
    # set, so they are not a Large-class surface in practice.
    "terracotta":   Mat(lambda **k: terracotta_tile(**k), 4.0, "standard"),
    "slate":        Mat(lambda **k: slate_roof(**k), 4.0, "standard"),
    "ridge":        Mat(lambda **k: ridge_tile(**k), 2.0, "standard"),
    "lead":         Mat(lambda **k: lead_sheet(**k), 2.0, "standard"),
    "copper":       Mat(lambda **k: copper_verdigris(**k), 2.0, "standard"),
    # Redirected from the first-pass `thatch()` builder, which had no course
    # structure, no stem direction and no eaves cut — a flat tan field on the
    # commonest roof in the town. The key is unchanged so the five venues using
    # it need no edit; `thatch()` itself is kept only as the reference the
    # variant was grown from.
    "thatch":       Mat(lambda **k: thatch_variant(age=0.45, material="reed", **k),
                        4.0, "standard"),
    "thatch_new":   Mat(lambda **k: thatch_variant(age=0.12, material="straw", **k), 4.0, "standard"),
    "thatch_old":   Mat(lambda **k: thatch_variant(age=0.85, material="reed", **k), 4.0, "standard"),

    # -- timber --------------------------------------------------------------
    "oak":          Mat(lambda **k: oak_timber(**k), 2.0, "standard"),
    "oak_dark":     Mat(lambda **k: oak_timber(tone=P.OAK_DARK, weathered=0.2, **k),
                        2.0, "standard"),
    "oak_weathered": Mat(lambda **k: oak_timber(tone=P.OAK_WEATHERED, weathered=0.8, **k),
                         2.0, "standard"),
    "elm":          Mat(lambda **k: timber(species="elm", **k), 2.0, "standard"),
    "pine_tarred":  Mat(lambda **k: timber(species="pine", tar=0.85, weathered=0.25, **k),
                        2.0, "standard"),
    "timber_grey":  Mat(lambda **k: timber(species="grey", weathered=0.95, **k),
                        2.0, "standard"),
    "timber_charred": Mat(lambda **k: timber(species="grey", char=0.9, weathered=0.3, **k),
                          2.0, "standard"),
    "endgrain":     Mat(lambda **k: end_grain(**k), 1.0, "hero"),
    "painted":      Mat(lambda **k: painted_wood(**k), 2.0, "standard"),
    "painted_crimson": Mat(lambda **k: painted_wood(colour=P.GUILD_CRIMSON, **k),
                           2.0, "standard"),
    # The guild's own colour. "painted" defaults to INN_GREEN, so the guild's
    # heraldic device shipped in the innkeeper's green — the one colour on the
    # building that must be unmistakably its own.
    "painted_amber": Mat(lambda **k: painted_wood(colour=P.PUB_AMBER, **k),
                         2.0, "standard"),

    # -- glass ---------------------------------------------------------------
    "glass":        Mat(lambda **k: leaded_glass(**k), 2.0, "standard",
                        flags=("emissive", "double", "blend")),
    # Lit glass. The inn's brief calls it "the most inviting thing in the
    # frame", and warm light behind glass is what actually delivers that —
    # daylight-neutral windows read as a building nobody is home in.
    "glass_lit":    Mat(lambda **k: leaded_glass(lit=True, **k), 2.0, "standard",
                        flags=("emissive", "double")),
    "stained":      Mat(lambda **k: stained_glass(lit=True, **k), 2.0, "hero",
                        flags=("emissive", "double")),
    "stained_dark": Mat(lambda **k: stained_glass(lit=False, **k), 2.0, "standard",
                        flags=("emissive", "double")),

    # -- metal ---------------------------------------------------------------
    "iron":         Mat(lambda **k: wrought_iron(**k), 1.0, "hero"),
    "iron_pitted":  Mat(lambda **k: pitted_iron(**k), 1.0, "hero"),
    "bronze":       Mat(lambda **k: bell_bronze(**k), 1.0, "hero"),
    "brass":        Mat(lambda **k: brass_fitting(**k), 1.0, "hero"),
    "steel_blued":  Mat(lambda **k: blued_steel(**k), 1.0, "hero"),
    "coal":         Mat(lambda **k: forge_coal(**k), 2.0, "standard",
                        flags=("emissive",)),

    # -- ground --------------------------------------------------------------
    # `earth` and `grass` carry structure down to 2 cm on a 4 m tile, which is
    # 200 px/m of real information; sizing them at the `large` class would
    # replace that with aliasing, so both override.
    "cobble":       Mat(lambda **k: cobblestone(**k), 2.0, "standard"),
    "sett":         Mat(lambda **k: granite_sett(**k), 2.0, "standard"),
    "flag":         Mat(lambda **k: flagstone(**k), 2.0, "standard"),
    "dirt":         Mat(lambda **k: beaten_earth(**k), 2.0, "standard"),
    "earth":        Mat(lambda **k: town_earth(**k), 4.0, "standard", size=1024),
    "cinder":       Mat(lambda **k: cinder_ground(**k), 2.0, "standard"),
    "sand":         Mat(lambda **k: river_sand(**k), 2.0, "standard"),
    "yard":         Mat(lambda **k: yard_litter(**k), 2.0, "standard"),
    "gravel":       Mat(lambda **k: river_gravel(**k), 2.0, "standard"),
    "grass":        Mat(lambda **k: meadow_grass(**k), 6.0, "large", size=1024),
    "grass_lush":   Mat(lambda **k: grass_variant(density=1.45, **k), 6.0, "large", size=1024),
    "grass_dry":    Mat(lambda **k: grass_variant(density=0.75, dry=0.85, **k), 6.0, "large", size=1024),
    "grass_worn":   Mat(lambda **k: grass_variant(density=0.55, trodden=0.9, **k), 6.0, "large", size=1024),
    "moss":         Mat(lambda **k: moss_bed(**k), 2.0, "standard"),

    # -- water ---------------------------------------------------------------
    # 2.5 m, which is what `core.kit.WATER_UV` has always laid and what the
    # ripple scale was tuned to; the 8.0/6.0 declared here were measured
    # rendering at 2.51 and are why the density audit could not see the error.
    "water":        Mat(lambda **k: water_surface(**k), 2.5, "standard",
                        flags=("blend",)),
    "water_flow":   Mat(lambda **k: water_surface(flow=1.0, **k), 2.5, "standard",
                        flags=("blend",)),
    "foam":         Mat(lambda **k: water_foam(**k), 2.0, "standard",
                        flags=("mask", "double")),
    # Falling water. BLEND and DOUBLE, and both matter: `mask` is what made the
    # fountain's ten falls vanish between 6 m and 12 m (the lace mips below the
    # alpha-test threshold — see `water_fall`), and a fall seen from behind is
    # still a fall. 1 m per tile, not 2: a jet is 0.09–0.30 m across, so at the
    # library's 2 m tile the whole ribbon samples 15 % of one tile and reads as
    # flat colour. Named so `client/src/water.js` harvests it with everything
    # else and it flows.
    "water_fall":   Mat(lambda **k: water_fall(**k), 1.0, "standard", size=256,
                        flags=("blend", "double")),
    "riverbed":     Mat(lambda **k: river_bed(**k), 2.0, "standard"),
    "mud":          Mat(lambda **k: river_mud(**k), 2.0, "standard"),
    "mud_wet":      Mat(lambda **k: wet_mud(**k), 2.0, "standard"),
    "algae":        Mat(lambda **k: algae(**k), 2.0, "standard"),

    # -- textiles ------------------------------------------------------------
    # Awnings in five colourways, not two. §4's accent table has five usable
    # dyes and a market where every stall flies the same two is a market that
    # reads as issued kit — which is what v1 shipped.
    "canvas":       Mat(lambda **k: canvas_awning(**k), 2.0, "standard",
                        flags=("double",)),
    "canvas_green": Mat(lambda **k: canvas_awning(accent=P.INN_GREEN, **k), 2.0,
                        "standard", flags=("double",)),
    "canvas_amber": Mat(lambda **k: canvas_awning(accent=P.PUB_AMBER, **k), 2.0,
                        "standard", flags=("double",)),
    "canvas_crimson": Mat(lambda **k: canvas_awning(accent=P.GUILD_CRIMSON, **k),
                          2.0, "standard", flags=("double",)),
    "canvas_slate": Mat(lambda **k: canvas_awning(accent=P.mix(P.SLATE, P.RIM, 0.08),
                                                  **k), 2.0, "standard",
                        flags=("double",)),
    "canvas_plain": Mat(lambda **k: canvas_awning(stripe=False, **k), 2.0,
                        "standard", flags=("double",)),
    "sailcloth":    Mat(lambda **k: sailcloth(**k), 2.0, "standard",
                        flags=("double",)),
    "sacking":      Mat(lambda **k: sacking(**k), 2.0, "standard"),
    "linen":        Mat(lambda **k: linen_laundry(**k), 2.0, "standard",
                        flags=("double",)),
    "banner":       Mat(lambda **k: banner_cloth(**k), 2.0, "standard",
                        flags=("double",)),
    # Dyed cloth. A hung, draped or folded textile needs several distinct dyes
    # or every awning, bedroll and laundry line reads as issued kit. Every one
    # is now derived from a §4 constant — `cloth_blue` was a hex literal and
    # measured 7.9 against the checker, the library's second-worst.
    "cloth_blue":   Mat(lambda **k: banner_cloth(colour=P.mix(P.SLATE, P.RIM, 0.08),
                                                 **k), 2.0, "standard", flags=("double",)),
    "cloth_green":  Mat(lambda **k: banner_cloth(colour=P.INN_GREEN, **k), 2.0, "standard", flags=("double",)),
    "cloth_rust":   Mat(lambda **k: banner_cloth(
        colour=P.mix(P.TERRACOTTA, P.OAK_WEATHERED, 0.35), **k), 2.0, "standard",
        flags=("double",)),
    "cloth_cream":  Mat(lambda **k: banner_cloth(colour=P.CANVAS_CREAM, **k), 2.0, "standard", flags=("double",)),
    "cloth_brown":  Mat(lambda **k: banner_cloth(colour=P.OAK_WEATHERED, **k), 2.0, "standard", flags=("double",)),
    "wool_crimson": Mat(lambda **k: wool_bolt(colour=P.GUILD_CRIMSON, **k), 1.0, "hero"),
    "wool_green":   Mat(lambda **k: wool_bolt(colour=P.INN_GREEN, **k), 1.0, "hero"),
    "wool_amber":   Mat(lambda **k: wool_bolt(colour=P.PUB_AMBER, **k), 1.0, "hero"),
    "wool_blue":    Mat(lambda **k: wool_bolt(colour=P.mix(P.SLATE, P.RIM, 0.08), **k),
                        1.0, "hero"),
    "wool_undyed":  Mat(lambda **k: wool_bolt(colour=P.mix(P.CANVAS_CREAM,
                                                           P.PLASTER_SHADE, 0.4), **k),
                        1.0, "hero"),

    # -- trades --------------------------------------------------------------
    "leather":      Mat(lambda **k: tanned_hide(**k), 1.0, "hero"),
    "hide_raw":     Mat(lambda **k: tanned_hide(raw=1.0, **k), 2.0, "standard"),
    "fleece":       Mat(lambda **k: raw_fleece(**k), 2.0, "standard"),
    "beeswax":      Mat(lambda **k: wax_block(**k), 1.0, "hero"),
    "tallow":       Mat(lambda **k: wax_block(tallow=True, **k), 1.0, "hero"),
    "flour":        Mat(lambda **k: flour_dust(**k), 1.0, "hero"),
    "fish":         Mat(lambda **k: fish_board(**k), 1.0, "hero"),
    "bread":        Mat(lambda **k: bread_crust(**k), 1.0, "hero"),
    "sugar":        Mat(lambda **k: bread_crust(glaze=1.0, **k), 1.0, "hero"),
    "pottery":      Mat(lambda **k: glazed_pottery(**k), 1.0, "hero"),
    "pottery_slip": Mat(lambda **k: glazed_pottery(
        glaze_colour=P.mix(P.PRODUCE_ACCENT, P.OAK_DARK, 0.35), **k), 1.0, "hero"),
    "parchment":    Mat(lambda **k: parchment(**k), 1.0, "hero"),
    "wax":          Mat(lambda **k: sealing_wax(**k), 1.0, "hero"),

    # -- vegetation ----------------------------------------------------------
    # The four leaf atlases are cut-out sheets: alpha MASK, double sided, and
    # a full 2 m of coverage because one tile holds sixteen leaves and each of
    # them has to survive being looked at from 2 m in a window box.
    "leaf_oak":     Mat(lambda **k: leaf_atlas(species="oak", **k), 2.0, "hero",
                        flags=("double", "mask")),
    "leaf_ash":     Mat(lambda **k: leaf_atlas(species="ash", **k), 2.0, "hero",
                        flags=("double", "mask")),
    "leaf_apple":   Mat(lambda **k: leaf_atlas(species="apple", **k), 2.0, "hero",
                        flags=("double", "mask")),
    "leaf_willow":  Mat(lambda **k: leaf_atlas(species="willow", **k), 2.0, "hero",
                        flags=("double", "mask")),
    # The yew is a conifer and gets a needle sheet, not a broadleaf one. It is
    # what took the churchyard yews off `blob_canopy` — see `needle_atlas`.
    "leaf_yew":     Mat(lambda **k: needle_atlas(**k), 2.0, "hero",
                        flags=("double", "mask")),
    # A hedge is a mass, but a mass with holes in it — see `hedge_mass`. MASK
    # rather than BLEND so it sorts against itself and against the town behind.
    "hedge":        Mat(lambda **k: hedge_mass(**k), 2.0, "standard",
                        flags=("double", "mask")),
    # The distance wood's billboard sheet. Four whole trees on a 2x2 grid, so
    # one tile is ~16 m of world, not 1 m — see DENSITY's `impostor` note.
    # `uv_scale()` is never used for it: `vegetation.distance_tree` addresses
    # its quadrant of the sheet explicitly.
    "tree_far":     Mat(lambda **k: tree_impostor(**k), 16.0, "impostor",
                        flags=("double", "mask")),
    # The three-way split of the old green mottle: a climber, a mass, and the
    # ground cover. Each is now cut out — an opaque green rectangle stuck to a
    # wall or lying on paving is `ad-town-03` §14 and §18 in one object.
    "ivy":          Mat(lambda **k: ivy(**k), 2.0, "standard",
                        flags=("double", "mask")),
    "weeds":        Mat(lambda **k: ground_weeds(**k), 2.0, "standard",
                        flags=("double", "mask")),
    "foliage":      Mat(lambda **k: foliage(**k), 2.0, "standard",
                        flags=("double",)),
    "foliage_flower": Mat(lambda **k: foliage(flowers=True, **k), 2.0, "standard",
                          flags=("double",)),
    "reed":         Mat(lambda **k: straw_bundle(reed=True, **k), 2.0, "standard"),
    "straw":        Mat(lambda **k: straw_bundle(**k), 2.0, "standard"),
}

# Back-compatible views of the flag data. `core/venue.py` held these as literal
# sets; they are derived now so that adding a material cannot forget them.
EMISSIVE = flagged("emissive")
DOUBLE_SIDED = flagged("double")
MASKED = flagged("mask")
BLEND = flagged("blend")
