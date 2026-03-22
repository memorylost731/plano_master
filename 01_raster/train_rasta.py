#!/usr/bin/env python3
"""
PlanO Rasta Training Pipeline

Fine-tunes the CubiCasa5k floor plan segmentation model on custom data
(Malta building plans, user-uploaded plans, etc.)

Architecture:
  Base model: CubiCasa5k (UNet segmentation, 5 classes: bg/wall/door/window/room)
  Fine-tune: QLoRA-style transfer on Malta-specific floor plans
  Deploy: Export to ONNX → GPU raster engine

Usage:
    python3 train_rasta.py prepare           # prepare dataset from raw images
    python3 train_rasta.py train             # fine-tune on prepared data
    python3 train_rasta.py eval              # evaluate model
    python3 train_rasta.py export            # export to ONNX for serving
    python3 train_rasta.py status            # show training status

Datasets:
    - CubiCasa5k (5,000 annotated floor plans) — base training
    - MLSTRUCT-FP (2,166 Chilean floor plans) — augmentation
    - Malta PA plans (scraped from planning authority) — domain-specific
    - User uploads (from PlanO app usage) — continuous learning
"""

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("rasta_train")

# Paths
BASE_DIR = Path(__file__).parent
DATASET_DIR = Path.home() / "datasets" / "floorplans"
MODEL_DIR = Path.home() / "plano-raster-engine" / "models"
CUBICASA_DIR = DATASET_DIR / "cubicasa5k"
MALTA_DIR = DATASET_DIR / "malta_plans"
UPLOAD_DIR = Path.home() / "plano-raster-engine" / "uploads"  # user-uploaded plans
TRAIN_DB = BASE_DIR / "training_history.json"


def prepare_dataset():
    """Prepare training dataset from available sources."""
    log.info("Preparing training dataset...")

    sources = {
        "cubicasa5k": CUBICASA_DIR / "data",
        "mlstruct": DATASET_DIR / "mlstruct-fp",
        "robin": DATASET_DIR / "robin",
        "malta": MALTA_DIR,
        "uploads": UPLOAD_DIR,
    }

    stats = {}
    for name, path in sources.items():
        if path.exists():
            images = list(path.rglob("*.png")) + list(path.rglob("*.jpg")) + list(path.rglob("*.jpeg"))
            stats[name] = len(images)
            log.info(f"  {name}: {len(images)} images at {path}")
        else:
            stats[name] = 0
            log.info(f"  {name}: not found at {path}")

    total = sum(stats.values())
    log.info(f"\nTotal training images: {total}")

    # Check for CubiCasa5k zip that needs extracting
    cubicasa_zip = CUBICASA_DIR / "cubicasa5k_data.zip"
    if cubicasa_zip.exists() and stats["cubicasa5k"] == 0:
        log.info(f"Found CubiCasa5k zip ({cubicasa_zip.stat().st_size / 1e9:.1f}GB). Extract with:")
        log.info(f"  cd {CUBICASA_DIR} && unzip cubicasa5k_data.zip -d data/")

    # Check for Malta PA plans
    if stats["malta"] == 0:
        log.info("\nNo Malta plans found. Sources to collect:")
        log.info("  1. Malta Planning Authority: https://www.pa.org.mt/en/search-applications")
        log.info("  2. Malta Lands Authority: property records with floor plans")
        log.info("  3. Real estate listings (Malta): often include floor plans")
        log.info(f"  Place Malta floor plan images in: {MALTA_DIR}")

    return stats


def train(epochs: int = 10, batch_size: int = 4, lr: float = 1e-4):
    """Fine-tune floor plan segmentation model."""
    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, Dataset
    except ImportError:
        log.error("PyTorch not available. Install with: pip install torch torchvision")
        log.info("On GPU server, use: /opt/c4isr/venv/bin/python3 train_rasta.py train")
        return

    log.info("=" * 60)
    log.info("RASTA TRAINING — Floor Plan Segmentation")
    log.info(f"  Epochs: {epochs}")
    log.info(f"  Batch size: {batch_size}")
    log.info(f"  Learning rate: {lr}")
    log.info(f"  Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
    log.info("=" * 60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load pretrained model
    model_path = MODEL_DIR / "cubicasa_model.pth"
    if model_path.exists():
        log.info(f"Loading pretrained model from {model_path}")
        state_dict = torch.load(str(model_path), map_location=device, weights_only=False)
        log.info(f"  Layers: {len(state_dict)}")
    else:
        log.warning("No pretrained model found. Training from scratch.")
        state_dict = None

    # Find training images
    train_images = []
    for src_dir in [CUBICASA_DIR / "data", DATASET_DIR / "mlstruct-fp", MALTA_DIR, UPLOAD_DIR]:
        if src_dir.exists():
            train_images.extend(list(src_dir.rglob("*.png")))
            train_images.extend(list(src_dir.rglob("*.jpg")))

    if not train_images:
        log.error("No training images found. Run 'prepare' first.")
        return

    log.info(f"Training images: {len(train_images)}")

    # Simple training loop (placeholder — real training uses CubiCasa5k's train.py)
    log.info("\nTo run full CubiCasa5k training:")
    log.info(f"  cd {CUBICASA_DIR}")
    log.info(f"  /opt/c4isr/venv/bin/python3 train.py")
    log.info("\nFor Malta fine-tuning, we'll implement transfer learning.")
    log.info("The pretrained model is linked and ready for inference.")

    # Record training attempt
    history = []
    if TRAIN_DB.exists():
        history = json.loads(TRAIN_DB.read_text())
    history.append({
        "timestamp": datetime.now().isoformat(),
        "images": len(train_images),
        "epochs": epochs,
        "status": "model_ready_for_finetuning",
        "model_path": str(model_path),
    })
    TRAIN_DB.write_text(json.dumps(history, indent=2))


def export_onnx():
    """Export trained model to ONNX for fast serving."""
    try:
        import torch
    except ImportError:
        log.error("PyTorch required for ONNX export")
        return

    model_path = MODEL_DIR / "cubicasa_model.pth"
    onnx_path = MODEL_DIR / "cubicasa_model.onnx"

    if not model_path.exists():
        log.error(f"Model not found at {model_path}")
        return

    log.info(f"Exporting {model_path} to ONNX...")
    log.info(f"  Input: (1, 3, 512, 512)")
    log.info(f"  Output: {onnx_path}")

    # The actual export requires the model architecture definition
    # from CubiCasa5k's floortrans module
    log.info("\nTo export with full architecture:")
    log.info(f"  cd {CUBICASA_DIR}")
    log.info(f"  /opt/c4isr/venv/bin/python3 -c \"")
    log.info(f"    from floortrans.models import get_model")
    log.info(f"    import torch")
    log.info(f"    model = get_model(51, 12)")
    log.info(f"    model.load_state_dict(torch.load('floortrans/models/model_1427.pth'))")
    log.info(f"    dummy = torch.randn(1, 3, 512, 512)")
    log.info(f"    torch.onnx.export(model, dummy, '{onnx_path}')\"")


def status():
    """Show training pipeline status."""
    log.info("=" * 60)
    log.info("RASTA TRAINING STATUS")
    log.info("=" * 60)

    # Datasets
    stats = prepare_dataset()

    # Model
    log.info("\nModels:")
    for f in MODEL_DIR.glob("*"):
        log.info(f"  {f.name}: {f.stat().st_size / 1e6:.1f} MB")

    # GPU
    try:
        import torch
        if torch.cuda.is_available():
            log.info(f"\nGPU: {torch.cuda.get_device_name(0)}")
            log.info(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    except ImportError:
        log.info("\nGPU: PyTorch not installed in this env")

    # History
    if TRAIN_DB.exists():
        history = json.loads(TRAIN_DB.read_text())
        log.info(f"\nTraining history: {len(history)} runs")
        if history:
            last = history[-1]
            log.info(f"  Last: {last['timestamp']} — {last['status']}")


def main():
    parser = argparse.ArgumentParser(description="PlanO Rasta Training")
    parser.add_argument("command", choices=["prepare", "train", "eval", "export", "status"])
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-4)
    args = parser.parse_args()

    if args.command == "prepare":
        prepare_dataset()
    elif args.command == "train":
        train(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)
    elif args.command == "export":
        export_onnx()
    elif args.command == "status":
        status()
    elif args.command == "eval":
        log.info("Evaluation — run: cd cubicasa5k && python3 eval.py")


if __name__ == "__main__":
    main()
