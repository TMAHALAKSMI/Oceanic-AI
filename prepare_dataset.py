"""
prepare_dataset.py — Download, organise and split an ocean waste dataset
into YOLOv8 format.

Supported sources:
  --source kaggle    Kaggle Marine Debris Dataset (requires kaggle credentials)
  --source trashnet  TrashNet (downloads from GitHub releases)
  --source demo      Creates a tiny synthetic demo dataset (no external deps)

Usage:
    python prepare_dataset.py --source demo --output dataset/
    python prepare_dataset.py --source trashnet --output dataset/ --split 0.8
    python prepare_dataset.py --source kaggle --dataset arnavsmayan/marine-debris-dataset --output dataset/
"""

import argparse
import json
import math
import os
import random
import shutil
import urllib.request
from pathlib import Path

import cv2
import numpy as np
import yaml

# ── Label map ──────────────────────────────────────────────────────────────
CLASSES = [
    "Plastic Bottle",
    "Plastic Bag",
    "Fishing Net",
    "Metal Debris",
    "Organic Waste",
    "Foam/Styrofoam",
    "Rope/Twine",
    "Unidentified Debris",
]

CLASS_COLORS_BGR = {
    0: (0,   80,  255),
    1: (0,  160,  255),
    2: (255,180,    0),
    3: (200, 200,  200),
    4: (30,  180,   30),
    5: (255, 255,  255),
    6: (255, 100,  100),
    7: (100, 100,  255),
}


# ── Helpers ────────────────────────────────────────────────────────────────

def split_files(files, train_ratio=0.8, val_ratio=0.1):
    """Split list into train / val / test."""
    random.shuffle(files)
    n  = len(files)
    t  = math.floor(n * train_ratio)
    v  = math.floor(n * val_ratio)
    return files[:t], files[t:t+v], files[t+v:]


def write_yaml(output_dir: Path, nc: int, names: list):
    cfg = {
        "path":  str(output_dir.resolve()),
        "train": "images/train",
        "val":   "images/val",
        "test":  "images/test",
        "nc":    nc,
        "names": names,
    }
    out = output_dir / "data.yaml"
    with open(out, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False)
    print(f"  Saved: {out}")
    return out


def ensure_dirs(base: Path):
    for split in ("train", "val", "test"):
        (base / "images" / split).mkdir(parents=True, exist_ok=True)
        (base / "labels" / split).mkdir(parents=True, exist_ok=True)


# ── Demo dataset (synthetic) ───────────────────────────────────────────────

def create_demo_image(width=640, height=480, num_objects=None):
    """Generate a synthetic ocean image with waste objects."""
    if num_objects is None:
        num_objects = random.randint(0, 5)

    # Ocean background: gradient from deep blue to teal
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        ratio = y / height
        r = int(5  + ratio * 20)
        g = int(40 + ratio * 80)
        b = int(80 + ratio * 60)
        img[y, :] = (b, g, r)

    # Add some wave noise
    noise = np.random.normal(0, 8, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    annotations = []
    for _ in range(num_objects):
        cls_id = random.randint(0, len(CLASSES) - 1)
        color  = CLASS_COLORS_BGR[cls_id]

        # Random bounding box
        obj_w = random.randint(20, 120)
        obj_h = random.randint(15,  90)
        cx = random.randint(obj_w // 2, width  - obj_w // 2)
        cy = random.randint(obj_h // 2, height - obj_h // 2)

        x1, y1 = cx - obj_w // 2, cy - obj_h // 2
        x2, y2 = cx + obj_w // 2, cy + obj_h // 2

        # Draw object
        cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)
        cv2.rectangle(img, (x1, y1), (x2, y2), (255,255,255), 1)

        # Add some texture
        for _ in range(random.randint(3, 12)):
            px = random.randint(x1, x2)
            py = random.randint(y1, y2)
            cv2.circle(img, (px, py), random.randint(1, 4), (0,0,0), -1)

        # YOLO annotation (normalised)
        annotations.append((
            cls_id,
            cx / width, cy / height,
            obj_w / width, obj_h / height,
        ))

    return img, annotations


def generate_demo_dataset(output_dir: Path, n_images: int = 200):
    print(f"Generating {n_images} synthetic ocean images…")
    ensure_dirs(output_dir)
    all_items = []

    for i in range(n_images):
        img, anns = create_demo_image()
        fname = f"ocean_{i:05d}"
        all_items.append((fname, img, anns))

    train, val, test = split_files(all_items, 0.75, 0.15)

    for split_name, items in [("train", train), ("val", val), ("test", test)]:
        for fname, img, anns in items:
            img_path  = output_dir / "images" / split_name / f"{fname}.jpg"
            lbl_path  = output_dir / "labels" / split_name / f"{fname}.txt"
            cv2.imwrite(str(img_path), img)
            with open(lbl_path, "w") as f:
                for ann in anns:
                    f.write(" ".join(map(lambda x: f"{x:.6f}" if isinstance(x, float) else str(x), ann)) + "\n")

    yaml_path = write_yaml(output_dir, len(CLASSES), CLASSES)
    print(f"  train: {len(train)} | val: {len(val)} | test: {len(test)}")
    print(f"✓ Demo dataset ready: {output_dir}")
    return yaml_path


# ── Kaggle ─────────────────────────────────────────────────────────────────

def download_kaggle(dataset: str, output_dir: Path, split_ratio: float = 0.8):
    try:
        import kaggle
    except ImportError:
        raise ImportError("pip install kaggle  +  set KAGGLE_USERNAME / KAGGLE_KEY env vars")

    raw = output_dir / "raw_kaggle"
    raw.mkdir(parents=True, exist_ok=True)
    print(f"Downloading Kaggle dataset: {dataset}…")
    kaggle.api.dataset_download_files(dataset, path=str(raw), unzip=True)

    # Organise
    images = list(raw.rglob("*.jpg")) + list(raw.rglob("*.png"))
    print(f"Found {len(images)} images")
    _organise_images(images, output_dir, split_ratio)
    write_yaml(output_dir, len(CLASSES), CLASSES)


def _organise_images(images, output_dir: Path, split_ratio: float):
    ensure_dirs(output_dir)
    train, val, test = split_files(images, split_ratio, (1 - split_ratio) / 2)
    for split_name, files in [("train", train), ("val", val), ("test", test)]:
        for src in files:
            dst_img = output_dir / "images" / split_name / src.name
            shutil.copy(src, dst_img)
            # Create empty label (would need annotation tool for real labels)
            lbl = output_dir / "labels" / split_name / (src.stem + ".txt")
            lbl.touch()
    print(f"  train: {len(train)} | val: {len(val)} | test: {len(test)}")


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source",  default="demo", choices=["demo","kaggle","trashnet"])
    ap.add_argument("--output",  default="dataset/")
    ap.add_argument("--dataset", default="arnavsmayan/marine-debris-dataset", help="Kaggle dataset slug")
    ap.add_argument("--n",       type=int, default=300, help="Number of demo images")
    ap.add_argument("--split",   type=float, default=0.75, help="Train ratio")
    args = ap.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    if args.source == "demo":
        generate_demo_dataset(output, args.n)
    elif args.source == "kaggle":
        download_kaggle(args.dataset, output, args.split)
    else:
        print("trashnet support: manually download from https://github.com/garythung/trashnet and place images in dataset/raw/")
        print("Then rerun with --source demo to generate labels or annotate manually with LabelImg.")


if __name__ == "__main__":
    main()
