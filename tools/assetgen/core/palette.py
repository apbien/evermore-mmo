"""The locked palette from docs/ART_BIBLE.md §4.

Single source of truth for colour. Generators import from here and never write
a literal hex value — that is how palette drift starts, and palette drift is
what makes a town look like it was built by seven different studios.

Colours are authored as sRGB hex and converted to linear for shading.
"""

from __future__ import annotations

import numpy as np

# --- Architecture ----------------------------------------------------------
PLASTER          = "#E8DCC4"
PLASTER_SHADE    = "#D4C4A8"
OAK              = "#8B6F47"
OAK_WEATHERED    = "#6B5638"
OAK_DARK         = "#4A3728"
TERRACOTTA       = "#B5603E"
TERRACOTTA_AGED  = "#8F4E36"
SLATE            = "#5A6270"
COBBLE           = "#8A8578"
COBBLE_WORN      = "#6E6A60"
FOUNDATION       = "#9A9083"

# --- Metals ----------------------------------------------------------------
IRON             = "#3A3632"
IRON_HOT         = "#FF7A2E"
BRONZE           = "#A87438"
VERDIGRIS        = "#5FA88C"
STEEL            = "#C8CCD4"
BRASS            = "#C9A227"

# --- Accent & life ---------------------------------------------------------
GUILD_CRIMSON    = "#A32C34"
INN_GREEN        = "#4A7C59"
PUB_AMBER        = "#C87F2A"
CANVAS_CREAM     = "#DCC9A0"
CANVAS_STRIPE    = "#9C4A3C"
HERB_GREEN       = "#6B8E4E"
PRODUCE_ACCENT   = "#D4832F"

# --- Lighting --------------------------------------------------------------
SUN              = "#FFF2D8"
SKY_FILL         = "#93BEE8"
GROUND_BOUNCE    = "#7A6A52"
RIM              = "#8FB8E8"
FORGE_FIRE       = "#FF8C42"
CANDLE           = "#FFB35C"
WINDOW_SPILL     = "#FFD9A0"

# Warm AO tint — Art Bible §1: contact shadows are never neutral grey.
AO_TINT          = "#4A3828"

# Locked review lighting, Art Bible §4.
SUN_ELEVATION_DEG = 38.0
SUN_AZIMUTH_DEG   = 125.0


def hex_to_rgb(h):
    """sRGB hex -> float triple in [0,1]."""
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def srgb_to_linear(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def linear_to_srgb(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055).astype(np.float32)


def rgb(h):
    """Palette hex -> linear float triple, for shading maths."""
    return srgb_to_linear(hex_to_rgb(h))


def mix(a, b, t):
    """Blend two palette hexes in linear space, returning a linear triple."""
    return rgb(a) * (1.0 - t) + rgb(b) * t


# Roughness / metalness pairs for the metals table in Art Bible §4.
METAL_SPEC = {
    "iron":      (0.55, 1.0),
    "iron_hot":  (0.40, 1.0),
    "bronze":    (0.35, 1.0),
    "verdigris": (0.70, 0.0),
    "steel":     (0.15, 1.0),
    "brass":     (0.28, 1.0),
}
