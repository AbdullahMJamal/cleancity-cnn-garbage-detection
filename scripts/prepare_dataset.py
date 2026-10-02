"""
Build the CleanCity training dataset from two public datasets.
=============================================================
1. Garbage photos (12 classes, Kaggle "Garbage Classification" by Mostafa Mohamed,
   mirrored on Hugging Face: UdaraChamidu/Garbage-Classification-with-12-classes)
2. Clean scenes for "Not Garbage" (Intel Image Classification:
   buildings / street / forest / sea / mountain, HF: sfarrukhm/intel-image-classification)

This script copies them into the folder layout train.py expects:

    dataset/
      cardboard/  glass/  metal/  organic/  paper/  plastic/  not_garbage/

Usage:
    python scripts/prepare_dataset.py --garbage-dir <12-class folder> --clean-dir <clean images> --out dataset
"""

import argparse
import os
import random
import shutil

# Our class folder  ←  folders from the 12-class dataset
MAPPING = {
    "cardboard": ["cardboard"],
    "glass":     ["brown-glass", "green-glass", "white-glass"],
    "metal":     ["metal"],
    "organic":   ["biological"],
    "paper":     ["paper"],
    "plastic":   ["plastic"],
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def list_images(folder):
    return sorted(os.path.join(folder, f) for f in os.listdir(folder)
                  if os.path.splitext(f)[1].lower() in IMAGE_EXTS)


def copy_sample(files, dest, limit, rng):
    os.makedirs(dest, exist_ok=True)
    rng.shuffle(files)
    for i, src in enumerate(files[:limit]):
        ext = os.path.splitext(src)[1].lower()
        shutil.copy(src, os.path.join(dest, f"{i:05d}{ext}"))
    return min(limit, len(files))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--garbage-dir", required=True)
    ap.add_argument("--clean-dir", required=True)
    ap.add_argument("--out", default="dataset")
    ap.add_argument("--per-class", type=int, default=900, help="max images per class (keeps classes balanced)")
    args = ap.parse_args()

    rng = random.Random(42)
    if os.path.exists(args.out):
        shutil.rmtree(args.out)

    for ours, theirs in MAPPING.items():
        files = [f for t in theirs for f in list_images(os.path.join(args.garbage_dir, t))]
        n = copy_sample(files, os.path.join(args.out, ours), args.per_class, rng)
        print(f"{ours:12s} {n} images")

    n = copy_sample(list_images(args.clean_dir), os.path.join(args.out, "not_garbage"), args.per_class, rng)
    print(f"{'not_garbage':12s} {n} images")


if __name__ == "__main__":
    main()
