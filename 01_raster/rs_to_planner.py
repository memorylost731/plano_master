#!/usr/bin/env python3
"""
RasterScan → React-Planner canonical SceneJson converter

INPUT  : RasterScan JSON
OUTPUT : React-Planner SceneJson (RAW, before cleaning)
"""

import json
import sys
import uuid

def uid():
    return uuid.uuid4().hex[:10]

def convert(rs):
    """
    rs = RasterScan JSON (already parsed)
    returns SceneJson dict
    """

    scene = {
        "unit": "cm",
        "layers": {
            "layer-1": {
                "id": "layer-1",
                "altitude": 0,
                "order": 0,
                "opacity": 1,
                "name": "default",
                "visible": True,
                "vertices": {},
                "lines": {},
                "holes": {},
                "areas": {},
                "items": {},
                "selected": {
                    "lines": [],
                    "holes": [],
                    "items": [],
                    "areas": [],
                    "vertices": []
                }
            }
        },
        "grids": {},
        "selectedLayer": "layer-1",
        "groups": {},
        "width": 3000,
        "height": 2000,
        "meta": {
            "source": "rasterscan"
        },
        "guides": {
            "horizontal": {},
            "vertical": {},
            "circular": {}
        }
    }

    # 🚧 NEXT STEPS (NOT IMPLEMENTED YET)
    # 1. rs["walls"] → vertices + lines
    # 2. close loops → areas
    # 3. rs["doors/windows"] → holes
    # 4. rs["symbols"] → items

    return scene


def main(inp, out):
    with open(inp, "r", encoding="utf-8") as f:
        rs = json.load(f)

    scene = convert(rs)

    with open(out, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=2)

    print(f"[OK] Planner JSON written to {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: rs_to_planner.py rasterscan.json output.scene.json")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
