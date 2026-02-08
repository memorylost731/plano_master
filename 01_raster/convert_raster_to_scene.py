#!/usr/bin/env python3
import json
import sys
import uuid

TEMPLATE = sys.argv[1]
RASTER = sys.argv[2]
OUT = sys.argv[3]


def uid():
    return uuid.uuid4().hex[:10]


with open(TEMPLATE, encoding="utf-8") as f:
    scene = json.load(f)

with open(RASTER, encoding="utf-8") as f:
    raster = json.load(f)["data"]

layer = scene["layers"]["layer-1"]

# Full reset so there are no stale refs from the template
layer["vertices"] = {}
layer["lines"] = {}
layer["holes"] = {}
layer["areas"] = {}
layer["items"] = {}
layer["selected"] = {"lines": [], "holes": [], "items": [], "areas": [], "vertices": []}

vertex_map = {}


def shared_defaults():
    # These are the interactive defaults React-Planner expects (safe even if unused)
    return {
        "visible": True,
        "selected": False,
        "name": "",
        "type": "",
        "misc": {},
        "properties": {},
        # Critical for editability in many planners:
        "locked": False,
    }


def get_vertex(x, y):
    key = f"{x}_{y}"
    if key not in vertex_map:
        vid = uid()
        vertex_map[key] = vid
        v = shared_defaults()
        v.update(
            {
                "id": vid,
                "prototype": "vertices",
                "x": x,
                "y": y,
                "lines": [],
                "areas": [],
                "name": "Vertex",
            }
        )
        layer["vertices"][vid] = v
    return vertex_map[key]


# ----------------------------
# Walls (lines)
# ----------------------------
for wall in raster.get("walls", []) or []:
    pos = wall.get("position")
    if not pos or len(pos) < 2:
        continue

    (x1, y1), (x2, y2) = pos[0], pos[1]
    v1 = get_vertex(x1, y1)
    v2 = get_vertex(x2, y2)

    lid = uid()
    l = shared_defaults()
    l.update(
        {
            "id": lid,
            "prototype": "lines",
            "type": "wall",
            "name": "Wall",
            "vertices": [v1, v2],
            "holes": [],
            "properties": {
                "height": {"length": 300},
                "thickness": {"length": 20},
                "opacity": 1,
                "textureA": "bricks",
                "textureB": "bricks",
            },
        }
    )
    layer["lines"][lid] = l
    layer["vertices"][v1]["lines"].append(lid)
    layer["vertices"][v2]["lines"].append(lid)


# ----------------------------
# Areas (rooms) - de-duped
# ----------------------------
for room in raster.get("rooms", []) or []:
    raw_verts = []
    for p in room:
        if not isinstance(p, dict):
            continue
        if "x" not in p or "y" not in p:
            continue
        raw_verts.append(get_vertex(p["x"], p["y"]))

    # remove consecutive duplicates
    verts = []
    for vid in raw_verts:
        if not verts or verts[-1] != vid:
            verts.append(vid)

    # if explicitly closed
    if len(verts) >= 2 and verts[0] == verts[-1]:
        verts.pop()

    if len(set(verts)) < 3:
        continue

    aid = uid()
    a = shared_defaults()
    a.update(
        {
            "id": aid,
            "prototype": "areas",
            "type": "area",
            "name": "Area",
            "vertices": verts,
            "holes": [],
            "properties": {
                "patternColor": "#F5F4F4",
                "thickness": {"length": 0},
                "texture": "none",
            },
        }
    )
    layer["areas"][aid] = a

    # backrefs (once per vertex)
    for v in set(verts):
        layer["vertices"][v]["areas"].append(aid)

scene["selectedLayer"] = "layer-1"

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(scene, f, indent=2)

print("OK:", OUT)
