import json, uuid, sys

INP = sys.argv[1]
OUT = sys.argv[2]
DX = float(sys.argv[3])
DY = float(sys.argv[4])

def nid():
  return uuid.uuid4().hex[:10]

scene = json.load(open(INP, "r", encoding="utf-8"))
layer_id = scene.get("selectedLayer") or "layer-1"
layer = scene["layers"][layer_id]

# Clone only the first area (room) in the file
areas = list(layer["areas"].values())
if not areas:
  raise SystemExit("No areas found to clone.")
src_area = areas[0]
src_vids = src_area["vertices"]

# Collect lines that belong to that area by scanning vertices -> lines
src_line_ids = set()
for vid in src_vids:
  src_line_ids.update(layer["vertices"][vid]["lines"])
src_line_ids = [lid for lid in src_line_ids if lid in layer["lines"]]

# New IDs
vmap = {vid: nid() for vid in src_vids}
lmap = {lid: nid() for lid in src_line_ids}
new_area_id = nid()

# Clone vertices
for old_vid in src_vids:
  v = layer["vertices"][old_vid].copy()
  v["id"] = vmap[old_vid]
  v["x"] = v["x"] + DX
  v["y"] = v["y"] + DY
  v["lines"] = [lmap[lid] for lid in v.get("lines", []) if lid in lmap]
  v["areas"] = [new_area_id]
  layer["vertices"][v["id"]] = v

# Clone lines
for old_lid in src_line_ids:
  l = layer["lines"][old_lid].copy()
  l["id"] = lmap[old_lid]
  l["vertices"] = [vmap[v] for v in l["vertices"]]
  l["holes"] = []  # keep simple
  layer["lines"][l["id"]] = l

# Clone area
a = src_area.copy()
a["id"] = new_area_id
a["vertices"] = [vmap[v] for v in src_vids]
a["holes"] = []
layer["areas"][a["id"]] = a

# Expand scene bounds if needed
allx = [v["x"] for v in layer["vertices"].values()]
ally = [v["y"] for v in layer["vertices"].values()]
scene["width"] = int(max(scene.get("width", 0), max(allx) + 200))
scene["height"] = int(max(scene.get("height", 0), max(ally) + 200))

json.dump(scene, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print("Wrote:", OUT)
