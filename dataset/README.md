# Dataset Setup

## Option 1 — Synthetic Demo Dataset (Fastest)

Generates 300 synthetic ocean images with random waste objects.
No internet required.

```bash
python prepare_dataset.py --source demo --n 300 --output dataset/
```

## Option 2 — Kaggle Marine Debris Dataset

1. Get Kaggle API credentials: https://www.kaggle.com/account
2. Place `kaggle.json` in `~/.kaggle/`
3. Run:

```bash
pip install kaggle
python prepare_dataset.py --source kaggle \
    --dataset arnavsmayan/marine-debris-dataset \
    --output dataset/
```

## Option 3 — Manual Dataset

1. Download images from any source (TACO, TrashNet, NOAA, etc.)
2. Place images in:
   - `dataset/images/train/`
   - `dataset/images/val/`
   - `dataset/images/test/`
3. Annotate using [LabelImg](https://github.com/HumanSignal/labelImg):
   - Set format to YOLO
   - Save `.txt` labels in corresponding `dataset/labels/` folders

4. Create `dataset/data.yaml`:

```yaml
path: /absolute/path/to/dataset
train: images/train
val:   images/val
test:  images/test
nc: 8
names:
  - Plastic Bottle
  - Plastic Bag
  - Fishing Net
  - Metal Debris
  - Organic Waste
  - Foam/Styrofoam
  - Rope/Twine
  - Unidentified Debris
```

## Label Format (YOLO)

Each `.txt` file contains one line per object:
```
<class_id> <cx_norm> <cy_norm> <w_norm> <h_norm>
```
All values are normalised 0–1 relative to image dimensions.

Example:
```
0 0.512 0.340 0.085 0.120
1 0.230 0.670 0.145 0.095
```
