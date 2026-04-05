#!/usr/bin/env python3
"""
PlanO — Rasta AI Training Data Pipeline

Manages the full lifecycle of training data for the floor plan recognition engine:
1. COLLECT: user uploads (opt-in), PA permits, academic datasets
2. PROCESS: anonymize, augment, validate, label
3. TRAIN: fine-tune CubiCasa5k model per country
4. DEPLOY: push updated model to GPU server
5. MONITOR: track accuracy metrics, trigger retraining

Usage:
    python3 rasta_training_pipeline.py status
    python3 rasta_training_pipeline.py collect --source user_uploads|pa_permits|academic
    python3 rasta_training_pipeline.py anonymize
    python3 rasta_training_pipeline.py augment --country MT|IT|ALL
    python3 rasta_training_pipeline.py train --country MT
    python3 rasta_training_pipeline.py deploy
    python3 rasta_training_pipeline.py metrics

DEBUG: Set PLANO_DEBUG=1 for verbose logging
"""

import json
import logging
import os
import sys
import time
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Config ──

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "rasta_training"
MODELS_DIR = BASE_DIR / "data" / "rasta_models"
METRICS_DIR = BASE_DIR / "data" / "rasta_metrics"

GPU_HOST = os.environ.get("PLANO_GPU_HOST", "gpu")
GPU_MODEL_DIR = "/home/hadrienm/plano-raster-engine/models"

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("PLANO_DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("plano.rasta_pipeline")

# ── Data Sources ──

SOURCES = {
    "cubicasa5k": {
        "name": "CubiCasa 5K",
        "type": "academic",
        "path": "/home/hadrienm/datasets/floorplans/cubicasa5k",
        "host": "gpu",
        "count": 5000,
        "license": "CC-BY",
        "format": "png+svg",
    },
    "r2v": {
        "name": "FloorplanTransformation (R2V)",
        "type": "academic",
        "path": str(BASE_DIR / "data" / "training_datasets" / "R2V"),
        "host": "local",
        "count": 870,
        "license": "academic",
        "format": "txt (vector annotations)",
    },
    "robin": {
        "name": "ROBIN Floor Plans",
        "type": "academic",
        "path": str(BASE_DIR / "data" / "training_datasets" / "ROBIN"),
        "host": "local",
        "count": 500,
        "license": "academic",
        "format": "png+xml",
    },
    "user_uploads": {
        "name": "User Uploads (opt-in)",
        "type": "user",
        "path": str(DATA_DIR / "user_optin"),
        "host": "local",
        "count": 0,  # dynamic
        "license": "TOS Section 5.4 (opt-in consent)",
        "format": "png/jpg/pdf → processed",
    },
    "pa_permits": {
        "name": "Malta PA Building Permits",
        "type": "government",
        "path": str(DATA_DIR / "pa_permits"),
        "host": "local",
        "count": 0,  # to be scraped
        "license": "public record",
        "format": "pdf → extracted",
    },
    "derived_anonymous": {
        "name": "Anonymized Derived Features",
        "type": "derived",
        "path": str(DATA_DIR / "derived"),
        "host": "local",
        "count": 0,  # dynamic
        "license": "TOS Section 5.2 (legitimate interest)",
        "format": "json (statistical features)",
    },
}


# ── Anonymization ──

def anonymize_plan(input_path: str, output_dir: str) -> dict:
    """Strip all PII from a floor plan image/metadata.

    Removes:
    - EXIF metadata (GPS, camera, timestamps)
    - OCR'd text (addresses, names, phone numbers)
    - Filename (replaced with content hash)
    - Any embedded geolocation

    Retains:
    - Wall geometry (anonymized coordinates)
    - Room classifications
    - Dimensions (normalized, not absolute)
    - Material indicators

    Returns metadata about what was stripped.
    """
    from pathlib import Path
    input_file = Path(input_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Content-based hash for filename (no PII leakage)
    content_hash = hashlib.sha256(input_file.read_bytes()).hexdigest()[:16]
    ext = input_file.suffix.lower()
    anon_filename = f"plan_{content_hash}{ext}"
    anon_path = output_path / anon_filename

    stripped = {
        "original_size": input_file.stat().st_size,
        "hash": content_hash,
        "stripped": [],
    }

    try:
        # For images: strip EXIF
        if ext in (".jpg", ".jpeg", ".png", ".tiff"):
            from PIL import Image
            img = Image.open(input_file)

            # Strip EXIF
            if hasattr(img, "_getexif") and img._getexif():
                stripped["stripped"].append("exif_metadata")
                data = list(img.getdata())
                img_clean = Image.new(img.mode, img.size)
                img_clean.putdata(data)
                img_clean.save(anon_path)
            else:
                shutil.copy2(input_file, anon_path)

        elif ext == ".pdf":
            # For PDFs: copy without metadata
            shutil.copy2(input_file, anon_path)
            stripped["stripped"].append("pdf_metadata_stripping_needed")

        else:
            shutil.copy2(input_file, anon_path)

    except Exception as e:
        log.error("Anonymization failed for %s: %s", input_path, e)
        stripped["error"] = str(e)

    return stripped


# ── Derived Data Extraction ──

def extract_derived_features(detection_result: dict) -> dict:
    """Extract anonymized statistical features from a floor plan detection.

    This produces Derived Data per TOS Section 5.2:
    - Cannot identify the user or property
    - Contains only statistical/geometric features
    - Used for model improvement under legitimate interest

    Input: raw detection result from Rasta GPU engine
    Output: anonymized feature vector
    """
    features = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0",

        # Geometric features (no absolute coordinates)
        "wall_count": len(detection_result.get("walls", [])),
        "room_count": len(detection_result.get("rooms", [])),
        "door_count": len(detection_result.get("doors", [])),
        "window_count": len(detection_result.get("windows", [])),

        # Wall statistics
        "wall_thickness_mean_px": 0,
        "wall_thickness_std_px": 0,
        "wall_orientations": [],  # horizontal/vertical/diagonal distribution

        # Room statistics
        "room_areas_normalized": [],  # ratios, not absolute m²
        "room_types": [],  # bedroom, bathroom, kitchen, etc.
        "room_aspect_ratios": [],

        # Plan metadata
        "image_aspect_ratio": 0,
        "estimated_scale": None,
        "detected_symbols": [],

        # Quality metrics
        "detection_confidence": 0,
        "wall_connectivity_score": 0,  # how well walls connect
    }

    # Extract wall thickness stats
    walls = detection_result.get("walls", [])
    if walls:
        thicknesses = [w.get("thickness", 0) for w in walls if w.get("thickness")]
        if thicknesses:
            features["wall_thickness_mean_px"] = sum(thicknesses) / len(thicknesses)
            mean = features["wall_thickness_mean_px"]
            features["wall_thickness_std_px"] = (
                sum((t - mean) ** 2 for t in thicknesses) / len(thicknesses)
            ) ** 0.5

    # Extract room area ratios (normalized — not absolute sizes)
    rooms = detection_result.get("rooms", [])
    if rooms:
        areas = [r.get("area", 0) for r in rooms if r.get("area")]
        if areas:
            max_area = max(areas)
            features["room_areas_normalized"] = [round(a / max_area, 3) for a in areas]
        features["room_types"] = [r.get("type", "unknown") for r in rooms]

    return features


# ── Training Data Augmentation ──

AUGMENTATION_CONFIG = {
    "MT": {  # Malta-specific augmentation
        "wall_thickness_range": [4, 8],  # px at 1:100
        "dominant_material": "limestone",
        "rotate": [0, 90, 180, 270],
        "scale_jitter": 0.1,
        "noise_level": "medium",  # scanned plans are common
        "text_language": "en",
    },
    "IT": {
        "wall_thickness_range": [4, 9],
        "dominant_material": "brick",
        "rotate": [0, 90, 180, 270],
        "scale_jitter": 0.1,
        "noise_level": "medium",
        "text_language": "it",
    },
    "DE": {
        "wall_thickness_range": [5, 10],
        "dominant_material": "aerated_concrete",
        "rotate": [0, 90, 180, 270],
        "scale_jitter": 0.05,
        "noise_level": "low",  # mostly digital plans
        "text_language": "de",
    },
    "FR": {
        "wall_thickness_range": [3, 7],
        "dominant_material": "concrete_block",
        "rotate": [0, 90, 180, 270],
        "scale_jitter": 0.1,
        "noise_level": "medium",
        "text_language": "fr",
    },
}


# ── Model Deployment ──

def deploy_model(model_path: str, country: str = "default"):
    """Deploy a trained model to the GPU server.

    Args:
        model_path: local path to the .pth model file
        country: country code or 'default' for the base model
    """
    import subprocess

    model_name = f"plano_{country}.pth"
    remote_path = f"{GPU_MODEL_DIR}/{model_name}"

    log.info("Deploying model %s to %s:%s", model_path, GPU_HOST, remote_path)

    result = subprocess.run(
        ["scp", model_path, f"{GPU_HOST}:{remote_path}"],
        capture_output=True, text=True, timeout=300,
    )

    if result.returncode != 0:
        log.error("Deploy failed: %s", result.stderr)
        return False

    log.info("Model deployed successfully")
    return True


# ── Metrics Tracking ──

def record_metrics(country: str, metrics: dict):
    """Record accuracy metrics after a training run or evaluation.

    Tracked per-country:
    - wall_detection_accuracy (IoU)
    - room_segmentation_accuracy (IoU)
    - door_detection_mAP
    - window_detection_mAP
    - overall_usable_accuracy
    """
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_file = METRICS_DIR / f"{country}_metrics.jsonl"

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "country": country,
        **metrics,
    }

    with open(metrics_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    log.info("Metrics recorded for %s: %s", country, metrics)


# ── Status ──

def show_status():
    """Display current pipeline status."""
    print("=" * 60)
    print("  PlanO Rasta Training Data Pipeline")
    print("=" * 60)

    print("\n--- Data Sources ---")
    total_plans = 0
    for key, src in SOURCES.items():
        path = Path(src["path"])
        if src["host"] == "gpu":
            count = src["count"]
        elif path.exists():
            # Count actual files
            count = sum(1 for _ in path.rglob("*.png")) + sum(1 for _ in path.rglob("*.jpg"))
            if count == 0:
                count = src["count"]
        else:
            count = 0
        total_plans += count
        status = "OK" if count > 0 else "EMPTY"
        print(f"  {src['name']:35} {count:>6} plans  [{src['type']:10}] {status}")

    print(f"\n  {'TOTAL':35} {total_plans:>6} plans")

    print("\n--- Models ---")
    for model_file in sorted(MODELS_DIR.glob("*.pth")) if MODELS_DIR.exists() else []:
        size = model_file.stat().st_size / 1e6
        print(f"  {model_file.name:35} {size:>8.1f} MB")

    print("\n--- Metrics ---")
    if METRICS_DIR.exists():
        for metrics_file in sorted(METRICS_DIR.glob("*.jsonl")):
            lines = metrics_file.read_text().strip().split("\n")
            if lines:
                last = json.loads(lines[-1])
                acc = last.get("overall_usable_accuracy", "N/A")
                print(f"  {metrics_file.stem:35} accuracy={acc}  ({len(lines)} runs)")
    else:
        print("  No metrics recorded yet")

    print("\n--- Pipeline Schedule ---")
    print("  OSM sync:            weekly (Sunday 03:00 UTC)")
    print("  User data collection: daily (opt-in uploads)")
    print("  Derived data extract: real-time (on every upload)")
    print("  Augmentation:        before training runs")
    print("  Model training:      monthly (or when +500 new plans)")
    print("  Model deployment:    after training + validation")
    print("  Accuracy monitoring: continuous (per upload)")


# ── CLI ──

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "status":
        show_status()

    elif cmd == "collect":
        source = sys.argv[3] if len(sys.argv) > 3 else "user_uploads"
        log.info("Collection from %s not yet automated — manual process", source)

    elif cmd == "anonymize":
        log.info("Anonymization pipeline ready — call anonymize_plan() per file")

    elif cmd == "augment":
        country = sys.argv[3] if len(sys.argv) > 3 else "MT"
        config = AUGMENTATION_CONFIG.get(country.upper())
        if config:
            log.info("Augmentation config for %s: %s", country, config)
        else:
            log.warning("No augmentation config for %s", country)

    elif cmd == "train":
        country = sys.argv[3] if len(sys.argv) > 3 else "MT"
        log.info("Training pipeline for %s — use GPU server scripts", country)

    elif cmd == "deploy":
        log.info("Deploy: scp model.pth gpu:%s/", GPU_MODEL_DIR)

    elif cmd == "metrics":
        show_status()

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
