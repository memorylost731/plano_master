# PlanO Rasta Engine

Floor plan recognition and analysis engine — replaces the external RasterScan API with a fully self-hosted, GPU-accelerated ML pipeline.

## Architecture

```
Upload floor plan image (PNG/JPG/PDF)
           │
           ▼
    ┌──────────────────────────┐
    │   Rasta Engine API       │
    │   POST /upload-plan      │
    │   POST /analyze          │
    └──────────┬───────────────┘
               │
    ┌──────────▼───────────────┐
    │   Detection Backend      │
    │                          │
    │   1. CubiCasa5k ML (GPU) │  ← trained model, 44 classes
    │   2. ONNX Runtime        │  ← optional, fastest inference
    │   3. OpenCV fallback     │  ← CPU, no model needed
    └──────────┬───────────────┘
               │
    ┌──────────▼───────────────┐
    │   React Planner JSON     │
    │                          │
    │   vertices, walls,       │
    │   rooms, doors, windows  │
    └──────────────────────────┘
```

## Deployments

| Location | URL | Backend | GPU |
|----------|-----|---------|-----|
| **GPU Server** (prod) | `:8020` | CubiCasa5k ML | RTX 6000 Ada 48GB |
| **ROG Laptop** (dev) | `:8011` | OpenCV fallback | CPU |

## Trained Model

The floor plan segmentation model was trained on **spark2** (NVIDIA GB10, 130GB unified RAM):

| Metric | Value |
|--------|-------|
| **Architecture** | `hg_furukawa_original` (Hourglass network) |
| **Dataset** | CubiCasa5k — 4,200 train + 400 val floor plans |
| **Classes** | 44 (21 rooms + 12 icons + 11 heatmaps) |
| **Best epoch** | 14/20 |
| **Best val loss** | 1.165 |
| **Checkpoint** | `model_best_val_loss_var.pkl` (200MB) |
| **Input** | 512×512 RGB image |
| **Output** | 44-channel segmentation mask |

### Room Classes (21)
Background, Wall, Room, Kitchen, Bathroom, Bedroom, Living Room, Dining Room,
Hallway, Closet, Balcony, Garage, Storage, Laundry, Toilet, Stairs, Elevator,
Office, Library, Studio, Other Room

### Icon Classes (12)
Background, Door (single/double/sliding), Window (single/double/bay),
Toilet, Bathtub, Shower, Sink, Kitchen Counter, Stairs Icon

### Heatmap Classes (11)
Door heatmaps (open/close points), Window heatmaps, Icon anchor points

## API Endpoints

### Floor Plan Detection

```
POST /upload-plan
  Body: multipart/form-data, file=<image>
  Returns: React Planner scene JSON
```

```
POST /analyze
  Body: multipart/form-data, file=<image>
  Returns: Detailed analysis (walls, rooms, doors, measurements)
```

```
GET /health
  Returns: {"status": "ok", "engine": "cubicasa5k|opencv-local", ...}
```

### Rasta Texture Pipeline

```
POST /api/identify-material
  Body: multipart/form-data, file=<photo>
  Returns: Material classification

POST /api/extract-texture
  Body: multipart/form-data, file=<photo>, material=<string>
  Returns: PBR texture maps

POST /api/material-to-scene
  Body: JSON {material, textures}
  Returns: React Planner scene properties

POST /api/texture-pipeline
  Body: multipart/form-data, file=<photo>
  Returns: Full pipeline output (material + textures + scene)

GET /api/materials
  Returns: List of all known materials
```

### AdS-CFT Geographic Engine

Physics-based signal propagation and building analysis on Anti-de Sitter spacetime.

```
GET  /ads/health          — Engine status (Λ < 0 always)
POST /ads/metric          — AdS metric tensor at geographic point
POST /ads/field-map       — Field intensity heatmap from emitters
POST /ads/resonance       — Building resonance modes (Fibonacci harmonics)
POST /ads/holographic     — 3D to 2D holographic projection
POST /ads/propagate       — Signal propagation via AdS geodesic
```

### Map Overlay Layers

```
GET /layers               — List all available layers
GET /layers/scada         — Malta SCADA infrastructure (366 assets)
GET /layers/tscm          — TSCM emitters (BLE/WiFi)
GET /layers/intel         — Intelligence overlay (persons of interest)
GET /layers/property      — Real estate data
GET /layers/timeline      — Geolocated forensic events
```

## Training

### Prerequisites
- NVIDIA GPU with CUDA (GB10/RTX 6000 Ada tested)
- PyTorch 2.10+ with CUDA
- CubiCasa5k dataset (5.1GB from [Zenodo](https://zenodo.org/records/2613548))

### Reproduce Training

```bash
# On spark2 (or any machine with GPU + PyTorch)
cd ~/datasets/floorplans/cubicasa5k

# Download dataset
wget 'https://zenodo.org/records/2613548/files/cubicasa5k.zip?download=1' -O cubicasa5k_data.zip
unzip cubicasa5k_data.zip -d data/

# Train (20 epochs, fine-tune from pretrained weights)
python3 train.py \
    --data-path data/cubicasa5k/ \
    --n-epoch 20 \
    --batch-size 8 \
    --l-rate 0.0001 \
    --weights model_best_val_loss_var.pkl \
    --new-hyperparams \
    --scale

# Best model saved to: runs_cubi/<timestamp>/model_best_val_loss_var.pkl
```

### Deploy Model

```bash
# Copy trained model to GPU raster engine
scp model_best_val_loss_var.pkl gpu:~/plano-raster-engine/models/plano_trained.pkl

# Copy floortrans module (model architecture code)
scp -r floortrans/ gpu:~/plano-raster-engine/

# Restart raster engine
ssh gpu "cd ~/plano-raster-engine && .venv/bin/uvicorn server.app:app --host 0.0.0.0 --port 8020"
```

### Training Data Sources

| Dataset | Images | Source | Status |
|---------|--------|--------|--------|
| **CubiCasa5k** | 5,000 | [Zenodo](https://zenodo.org/records/2613548) | Trained |
| **MLSTRUCT-FP** | 954 | [GitHub](https://github.com/MLSTRUCT/MLSTRUCT-FP) | Available |
| **ROBIN** | ~500 | [GitHub](https://github.com/gesstalt/ROBIN) | Available |
| **ResPlan** | 17,000 | [GitHub](https://github.com/m-agour/ResPlan) | Available |
| **ArchCAD-400K** | 40,000+ | [HuggingFace](https://huggingface.co/datasets/jackluoluo/ArchCAD) | Available |
| **FloorPlanCAD** | 15,000 | [HuggingFace](https://huggingface.co/datasets/Voxel51/FloorPlanCAD) | Available |
| **Malta PA** | TBD | [PA eApps](https://eapps.pa.org.mt) | Requires Malta eID |
| **OSM Malta** | 37,495 footprints | [HDX](https://data.humdata.org/dataset/hotosm_mlt_buildings) | Downloaded |

## Self-Hosted Map Tiles

Vector tiles served by **Martin** (Rust) on the GPU server:

| Region | Size | Zoom | URL |
|--------|------|------|-----|
| Malta | 7.8 MB | 0-15 | `http://gpu:3030/malta/{z}/{x}/{y}` |
| Monaco-Riviera | 38 MB | 0-15 | `http://gpu:3030/monaco-riviera/{z}/{x}/{y}` |

Add more regions:
```bash
ssh gpu "~/tiles/pmtiles extract 'https://build.protomaps.com/20260322.pmtiles' \
  /mnt/disk2/media/tiles/europe.pmtiles --bbox='-25,35,45,72'"
docker restart martin
```

## File Structure

```
01_raster/
├── server/
│   ├── app_local.py          # FastAPI app (dev, OpenCV)
│   ├── ads_geo_engine.py     # AdS-CFT geographic engine
│   └── map_layers.py         # GeoJSON overlay layers
├── rasta/
│   ├── api.py                # Texture pipeline routes
│   ├── texture_identify.py   # Material classification
│   ├── texture_extract.py    # PBR texture extraction
│   └── texture_to_planner.py # Material → scene properties
├── models/                   # Trained weights (gitignored)
│   └── plano_trained.pkl     # CubiCasa5k fine-tuned (200MB)
├── train_rasta.py            # Training pipeline CLI
└── README.md                 # This file
```

## Co-Authors

- **Hadrien Majoie** — Architecture, integration, training pipeline
- **Cael** (cael@hacking.eu) — Autonomous agent contributions
- **CubiCasa5k** — Base model and dataset ([arXiv:1904.01920](https://arxiv.org/abs/1904.01920))
