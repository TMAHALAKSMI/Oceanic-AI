"""
train_model.py — Fine-tune YOLOv8 on ocean waste dataset.

Usage:
    python train_model.py --data dataset/data.yaml --epochs 50 --batch 16
    python train_model.py --data dataset/data.yaml --epochs 100 --pretrained yolov8s.pt

After training, copy best weights:
    cp runs/detect/train/weights/best.pt backend/models/ocean_waste_yolov8.pt
"""

import argparse
import shutil
import yaml
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Train YOLOv8 on Ocean Waste Dataset")
    p.add_argument("--data",      default="dataset/data.yaml",  help="Path to data.yaml")
    p.add_argument("--pretrained",default="yolov8n.pt",         help="Pretrained weights (yolov8n/s/m/l.pt)")
    p.add_argument("--epochs",    type=int, default=50,          help="Training epochs")
    p.add_argument("--batch",     type=int, default=16,          help="Batch size")
    p.add_argument("--imgsz",     type=int, default=640,         help="Image size")
    p.add_argument("--project",   default="runs/detect",         help="Save directory")
    p.add_argument("--name",      default="ocean_waste",         help="Run name")
    p.add_argument("--resume",    action="store_true",           help="Resume training")
    p.add_argument("--device",    default="",                    help="cuda device or cpu")
    return p.parse_args()


def verify_dataset(data_yaml: str):
    """Check that the dataset YAML and directories exist."""
    path = Path(data_yaml)
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset config not found: {data_yaml}\n"
            "Download a dataset first (see dataset/README.md)"
        )
    with open(path) as f:
        cfg = yaml.safe_load(f)
    print(f"Dataset: {cfg.get('path', '.')}")
    print(f"Classes ({cfg.get('nc', '?')}): {cfg.get('names', [])}")
    return cfg


def train(args):
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError(
            "ultralytics not installed. Run: pip install ultralytics"
        )

    cfg = verify_dataset(args.data)
    print(f"\nStarting training: {args.pretrained} → {args.epochs} epochs")

    model = YOLO(args.pretrained)

    results = model.train(
        data=args.data,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        project=args.project,
        name=args.name,
        resume=args.resume,
        device=args.device or None,
        patience=20,
        save=True,
        plots=True,
        verbose=True,
        # Augmentation
        mosaic=1.0,
        flipud=0.3,
        fliplr=0.5,
        degrees=15.0,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
    )

    best = Path(args.project) / args.name / "weights" / "best.pt"
    dest = Path("backend/models/ocean_waste_yolov8.pt")
    dest.parent.mkdir(parents=True, exist_ok=True)

    if best.exists():
        shutil.copy(best, dest)
        print(f"\n✓ Best weights copied to: {dest}")
    else:
        print(f"\nBest weights not found at {best}. Check training output.")

    print("\nTraining complete! Metrics summary:")
    print(results)


def evaluate(weights: str, data: str, imgsz: int = 640):
    """Run validation on the trained model."""
    from ultralytics import YOLO
    model  = YOLO(weights)
    metrics = model.val(data=data, imgsz=imgsz, verbose=True)
    print(f"mAP50:    {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")
    return metrics


if __name__ == "__main__":
    args = parse_args()
    train(args)
