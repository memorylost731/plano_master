#!/usr/bin/env python3
import json
import sys
import uuid
import copy

TEMPLATE = sys.argv[1]
RASTER = sys.argv[2]
OUT = sys.argv[3]

def uid():
    return uuid.uuid4().hex[:10]

with open(TEMPLATE) as f:
    scene = json.load(f)

with open(RASTER) as f:
    raster = json.load(f)["data"]

layer = scene["layers"]["layer-1"]
layer["vertices"].clear()
layer["lines"].clear()
layer["areas"].clear()

vertex_map = {}

def get_vertex(x, y):
    key = f"{x}_{y}"
    if key not in vertex_map:
        vid = uid()
        vertex_map[key] = vid
        layer["vertices"][vid] = {
            "id": vid,
            "prototype": "vertices",
            "x": x,
            "y": y,
            "lines": [],
            "areas": [],
            "visible": True,
            "selected": False,
            "name": "Vertex",
            "type": "",
            "misc": {},
            "properties": {}
        }
    return vertex_map[key]

# Walls
for wall in raster.get("walls", []):
    (x1, y1), (x2, y2) = wall["position"]
    v1 = get_vertex(x1, y1)
    v2 = get_vertex(x2, y2)

    lid = uid()
    layer["lines"][lid] = {
        "id": lid,
        "type": "wall",
        "prototype": "lines",
        "name": "Wall",
        "vertices": [v1, v2],
        "holes": [],
        "visible": True,
        "selected": False,
        "misc": {},
        "properties": {
            "height": {"length": 300},
            "thickness": {"length": 20},
            "opacity": 1,
            "textureA": "bricks",
            "textureB": "bricks"
        }
    }
    layer["vertices"][v1]["lines"].append(lid)
    layer["vertices"][v2]["lines"].append(lid)

# Areas (rooms)
for room in raster.get("rooms", []):
    aid = uid()
    verts = []
    for p in room:
        verts.append(get_vertex(p["x"], p["y"]))

    layer["areas"][aid] = {
        "id": aid,
        "type": "area",
        "prototype": "areas",
        "name": "Area",
        "vertices": verts,
        "holes": [],
        "visible": True,
        "selected": False,
        "misc": {},
        "properties": {
            "patternColor": "#F5F4F4",
            "thickness": {"length": 0},
            "texture": "none"
        }
    }

    for v in verts:
        layer["vertices"][v]["areas"].append(aid)

scene["selectedLayer"] = "layer-1"

with open(OUT, "w") as f:
    json.dump(scene, f, indent=2)

print("OK:", OUT)
