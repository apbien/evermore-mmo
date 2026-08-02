#!/usr/bin/env python3
"""Sample the Python terrain evaluator at a list of points.

The other half of `tools/render/terrain_parity.mjs`. Reads a JSON array of
[x, z] pairs and writes {height, normal, water} to stdout. Kept as its own
entry point rather than living inside the parity script so the Python side can
also be driven by hand when a single sample is in dispute:

    echo "[[0,0],[0,-105]]" > /tmp/p.json
    python tools/assetgen/terrain_sample.py /tmp/p.json
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import terrain as TR   # noqa: E402


def main():
    pts = json.load(open(sys.argv[1]))
    a = np.asarray(pts, np.float64)
    x, z = a[:, 0], a[:, 1]
    T = TR.get()
    h = T.height(x, z)
    n = T.normal(x, z)
    json.dump({
        "height": [float(v) for v in h],
        "normal": [[float(c) for c in row] for row in n],
        "water": [bool(v) for v in (h < T.water_level())],
    }, sys.stdout)


if __name__ == "__main__":
    main()
