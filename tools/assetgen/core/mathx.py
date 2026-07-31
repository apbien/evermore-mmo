"""Deterministic math: seeded RNG and the noise fields every generator shares.

Determinism is a hard requirement (see docs/ARCHITECTURE.md §7). Every random
value in this project traces back to an asset ID through `rng_for`, so the same
commit produces byte-identical assets anywhere. Never use `random` or an
unseeded `np.random.default_rng` in a generator.
"""

from __future__ import annotations

import hashlib
import numpy as np


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------

def seed_from(*parts: object) -> int:
    """Stable 64-bit seed from any set of identifying parts.

    Uses blake2b rather than hash() because Python salts str hashing per
    process, which would silently break determinism across runs.
    """
    key = "|".join(str(p) for p in parts).encode("utf-8")
    return int.from_bytes(hashlib.blake2b(key, digest_size=8).digest(), "big")


def rng_for(*parts: object) -> np.random.Generator:
    """The only sanctioned way to obtain randomness in a generator."""
    return np.random.default_rng(seed_from(*parts))


def jitter(rng, base, frac):
    """Multiplicative variance. Art Bible §6 mandates this on repeated elements."""
    return base * (1.0 + rng.uniform(-frac, frac))


# ---------------------------------------------------------------------------
# Noise
# ---------------------------------------------------------------------------
# Value-gradient noise, tileable by construction. We use our own rather than a
# dependency so that output is pinned to this implementation forever — a noise
# library version bump would silently rewrite every texture in the repo.

def _fade(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def perlin2(shape, freq, seed, tileable=True):
    """Tileable 2D Perlin noise in [-1, 1].

    `freq` is cycles across the full image, so a 1024px texture covering 2m at
    freq=8 gives 25cm features.
    """
    h, w = shape
    fx = max(1, int(freq))
    fy = max(1, int(freq))
    rng = np.random.default_rng(seed)

    # Gradient grid, wrapped so the field tiles.
    ang = rng.uniform(0.0, 2.0 * np.pi, size=(fy + 1, fx + 1))
    if tileable:
        ang[-1, :] = ang[0, :]
        ang[:, -1] = ang[:, 0]
    gx, gy = np.cos(ang), np.sin(ang)

    ys = np.linspace(0.0, fy, h, endpoint=False)
    xs = np.linspace(0.0, fx, w, endpoint=False)
    xg, yg = np.meshgrid(xs, ys)

    x0, y0 = np.floor(xg).astype(int), np.floor(yg).astype(int)
    x1, y1 = x0 + 1, y0 + 1
    tx, ty = xg - x0, yg - y0

    def dot(ix, iy, dx, dy):
        return gx[iy, ix] * dx + gy[iy, ix] * dy

    n00 = dot(x0, y0, tx, ty)
    n10 = dot(x1, y0, tx - 1, ty)
    n01 = dot(x0, y1, tx, ty - 1)
    n11 = dot(x1, y1, tx - 1, ty - 1)

    u, v = _fade(tx), _fade(ty)
    return (n00 * (1 - u) + n10 * u) * (1 - v) + (n01 * (1 - u) + n11 * u) * v


def fbm(shape, freq, seed, octaves=5, gain=0.5, lacunarity=2.0):
    """Fractal noise. The workhorse for broad-scale material variation."""
    total = np.zeros(shape, dtype=np.float32)
    amp, f, norm = 1.0, float(freq), 0.0
    for o in range(octaves):
        total += amp * perlin2(shape, f, seed + o * 7919)
        norm += amp
        amp *= gain
        f *= lacunarity
    return total / max(norm, 1e-6)


def worley(shape, cells, seed, metric="f1"):
    """Tileable Worley/cellular noise in [0,1].

    Drives anything with discrete cells: cobbles, plaster crackle, wood pores,
    hammered-metal facets.

    Only the 3x3 neighbourhood of each pixel's own cell is searched. The naive
    all-points version is O(cells^2 * pixels) and takes minutes per 1k texture,
    which would stall every asset build; this is 9 vectorised passes regardless
    of cell count. Wrapping is handled by offsetting the cell index before the
    modulo, so the field still tiles seamlessly.
    """
    h, w = shape
    c = max(1, int(cells))
    rng = np.random.default_rng(seed)
    off = rng.random((c, c, 2)).astype(np.float32)     # feature point per cell

    ys = np.linspace(0.0, c, h, endpoint=False, dtype=np.float32)[:, None]
    xs = np.linspace(0.0, c, w, endpoint=False, dtype=np.float32)[None, :]
    cy = np.floor(ys).astype(np.int32)
    cx = np.floor(xs).astype(np.int32)

    best = np.full(shape, 1e9, dtype=np.float32)
    second = np.full(shape, 1e9, dtype=np.float32)

    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ny, nx = cy + dy, cx + dx
            wy, wx = np.mod(ny, c), np.mod(nx, c)
            fy = ny + off[wy, wx, 0]      # unwrapped, so distance stays continuous
            fx = nx + off[wy, wx, 1]
            d = np.hypot(ys - fy, xs - fx).astype(np.float32)
            np.minimum(second, np.maximum(best, d), out=second)
            np.minimum(best, d, out=best)

    if metric == "f2f1":
        return np.clip(second - best, 0.0, 1.0)
    return np.clip(best, 0.0, 1.0)


def ridged(shape, freq, seed, octaves=4):
    """Ridged fractal noise — sharp crests. Wood grain, cracks, streaking."""
    return 1.0 - np.abs(fbm(shape, freq, seed, octaves=octaves))


def normalize01(a):
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / (hi - lo) if hi - lo > 1e-9 else np.zeros_like(a)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / max(e1 - e0, 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def gradient_v(shape, invert=False):
    """Vertical 0..1 ramp. Drives ground-splash and water-streak masks."""
    h, w = shape
    g = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None].repeat(w, axis=1)
    return 1.0 - g if invert else g
