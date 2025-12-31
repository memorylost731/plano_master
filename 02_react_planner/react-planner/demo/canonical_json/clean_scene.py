import json, sys

INP = sys.argv[1]
OUT = sys.argv[2]

scene = json.load(open(INP, "r", encoding="utf-8"))

layer_id = scene.get("selectedLayer") or "layer-1"
layers = scene.get("layers", {})
if layer_id not in layers:
  raise SystemExit(f"selectedLayer '{layer_id}' not in layers")

layer = layers[layer_id]

vertices = layer.get("vertices", {})
lines = layer.get("lines", {})
areas = layer.get("areas", {})

line_ids = set(lines.keys())
area_ids = set(areas.keys())
vertex_ids = set(vertices.keys())

# 1) Clean vertex backrefs: remove non-existent line/area ids
for vid, v in vertices.items():
  v["lines"] = [lid for lid in v.get("lines", []) if lid in line_ids]
  v["areas"] = [aid for aid in v.get("areas", []) if aid in area_ids]

# 2) Ensure line essentials exist (wall contract)
for lid, l in lines.items():
  if "prototype" not in l: l["prototype"] = "lines"
  if "type" not in l or not l["type"]: l["type"] = "wall"
  if "properties" not in l or l["properties"] is None: l["properties"] = {}

  props = l["properties"]
  props.setdefault("opacity", 1)
  props.setdefault("textureA", "bricks")
  props.setdefault("textureB", "bricks")

  # critical nested lengths
  props.setdefault("height", {"length": 300})
  if not isinstance(props["height"], dict) or "length" not in props["height"]:
    props["height"] = {"length": 300}

  props.setdefault("thickness", {"length": 20})
  if not isinstance(props["thickness"], dict) or "length" not in props["thickness"]:
    props["thickness"] = {"length": 20}

  # validate referenced vertices
  vpair = l.get("vertices", [])
  if len(vpair) != 2 or any(v not in vertex_ids for v in vpair):
    raise SystemExit(f"Line {lid} has invalid vertices: {vpair}")

# 3) Ensure area essentials exist
for aid, a in areas.items():
  if "prototype" not in a: a["prototype"] = "areas"
  if "type" not in a or not a["type"]: a["type"] = "area"
  if "properties" not in a or a["properties"] is None: a["properties"] = {}
  props = a["properties"]
  props.setdefault("patternColor", "#F5F4F4")
  props.setdefault("texture", "none")
  props.setdefault("thickness", {"length": 0})
  if not isinstance(props["thickness"], dict) or "length" not in props["thickness"]:
    props["thickness"] = {"length": 0}

  # validate vertex loop
  av = a.get("vertices", [])
  if len(av) < 3 or any(v not in vertex_ids for v in av):
    raise SystemExit(f"Area {aid} has invalid vertices: {av}")

# Write cleaned JSON (pretty for debugging)
json.dump(scene, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("OK:", OUT)
