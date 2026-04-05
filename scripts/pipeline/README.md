# PlanO Data Pipelines

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                  │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │   OSM    │  │ User     │  │ Malta PA │  │ Academic Datasets │  │
│  │ Overpass │  │ Uploads  │  │ Permits  │  │ CubiCasa/R2V/etc │  │
│  │  API     │  │ (opt-in) │  │  (PDF)   │  │                   │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬──────────┘  │
│       │              │              │                  │              │
├───────┼──────────────┼──────────────┼──────────────────┼──────────────┤
│       │         PROCESSING LAYER                       │              │
│       │              │              │                  │              │
│       ▼              ▼              ▼                  │              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │              │
│  │ osm_sync │  │ anonymize│  │ PDF      │            │              │
│  │ .py      │  │ + strip  │  │ extract  │            │              │
│  │ (weekly) │  │ PII      │  │ plans    │            │              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘            │              │
│       │              │              │                  │              │
│       ▼              ▼              ▼                  ▼              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    TRAINING DATA LAKE                         │   │
│  │                                                               │   │
│  │  data/osm/         Building footprints (validation GT)       │   │
│  │  data/rasta_training/                                        │   │
│  │    ├── user_optin/      Opted-in user plans (anonymized)     │   │
│  │    ├── pa_permits/      Malta PA extracted floor plans        │   │
│  │    ├── derived/         Statistical features (anonymous)     │   │
│  │    └── augmented/       Augmented per-country training sets   │   │
│  │  data/training_datasets/ Academic datasets (CubiCasa, R2V)   │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                              │                                       │
├──────────────────────────────┼───────────────────────────────────────┤
│                         TRAINING                                     │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  GPU Server (RTX 6000 Ada 48GB)                              │   │
│  │                                                               │   │
│  │  Base model: CubiCasa5k (cubicasa_model.pth)                │   │
│  │  Fine-tuned: plano_mt.pth (Malta), plano_it.pth (Italy)...  │   │
│  │                                                               │   │
│  │  Training trigger: monthly OR +500 new plans                 │   │
│  │  Validation: hold-out set + OSM footprint comparison         │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                              │                                       │
├──────────────────────────────┼───────────────────────────────────────┤
│                         DEPLOYMENT                                   │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Rasta API (FastAPI + Celery)                                │   │
│  │                                                               │   │
│  │  /api/upload → Celery worker → model inference → scene JSON  │   │
│  │                                                               │   │
│  │  Model selection: per-country (MT/IT/DE/FR) or default       │   │
│  │  A/B testing: new model vs baseline on 10% traffic           │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                              │                                       │
├──────────────────────────────┼───────────────────────────────────────┤
│                         MONITORING                                   │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Metrics: wall_iou, room_iou, door_mAP, overall_accuracy    │   │
│  │  Per-country tracking in data/rasta_metrics/                 │   │
│  │  Alert: retrain if accuracy drops below threshold            │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Pipelines

### 1. OSM Building Sync (`osm_sync.py`)
- **Schedule:** Weekly (Sunday 03:00 UTC)
- **What:** Downloads building footprints from OpenStreetMap for all target markets
- **Output:** `data/osm/{country}/buildings.json` + diff tracking
- **Used for:** Map overlays, building metadata, validation ground truth

```bash
python3 scripts/pipeline/osm_sync.py sync --country MT    # single country
python3 scripts/pipeline/osm_sync.py sync ALL              # all countries
python3 scripts/pipeline/osm_sync.py stats                 # show status
python3 scripts/pipeline/osm_sync.py diff                  # show changes
```

### 2. Rasta Training Pipeline (`rasta_training_pipeline.py`)
- **Schedule:** Continuous collection, monthly training
- **What:** Manages training data lifecycle — collect, anonymize, augment, train, deploy
- **Legal:** TOS Section 5.2 (derived data), Section 5.4 (opt-in content)

```bash
python3 scripts/pipeline/rasta_training_pipeline.py status
python3 scripts/pipeline/rasta_training_pipeline.py anonymize
python3 scripts/pipeline/rasta_training_pipeline.py augment --country MT
python3 scripts/pipeline/rasta_training_pipeline.py train --country MT
python3 scripts/pipeline/rasta_training_pipeline.py deploy
python3 scripts/pipeline/rasta_training_pipeline.py metrics
```

### 3. Derived Data Extraction (real-time)
- **Trigger:** Every floor plan upload (automatic)
- **What:** Extracts anonymized features (wall count, room ratios, thickness stats)
- **Legal:** TOS Section 5.2 — legitimate interest, no consent needed
- **Output:** `data/rasta_training/derived/*.json`

## Data Retention (per TOS)

| Data Type | Retention | Legal Basis |
|-----------|-----------|-------------|
| User floor plans | Until deletion + 90 days | Contract |
| Opted-in training data | Until opt-out | Consent |
| Derived features (anonymous) | Indefinite | Legitimate interest |
| OSM building data | Refreshed weekly | ODbL license |
| Trained models | Indefinite | Company asset |
| Accuracy metrics | Indefinite | Company asset |

## Cron Setup

```bash
# Add to crontab (local machine)
# Weekly OSM sync (Sunday 3am)
0 3 * * 0 cd ~/plano_master && python3 scripts/pipeline/osm_sync.py sync MT >> logs/osm_sync.log 2>&1

# Daily derived data stats
0 6 * * * cd ~/plano_master && python3 scripts/pipeline/rasta_training_pipeline.py status >> logs/rasta_pipeline.log 2>&1
```
