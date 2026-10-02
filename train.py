"""
Train the CleanCity CNN
=======================
Fine-tunes MobileNetV2 (pre-trained on ImageNet) on garbage photos.

Dataset layout (one folder per class — see scripts/prepare_dataset.py):
    dataset/cardboard, dataset/glass, dataset/metal, dataset/organic,
    dataset/paper, dataset/plastic, dataset/not_garbage

Training happens in two phases:
  1. Base frozen   → only our new classification head learns (fast)
  2. Fine-tuning   → the last MobileNetV2 layers also learn, with a tiny learning rate

Output:
  model/garbage_model.keras  ← loaded by app.py
  model/model_info.json      ← accuracy & training details (shown on team dashboard)

Usage:
    python train.py --data-dir dataset
"""

import argparse
import json
import os
from datetime import datetime

import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

from model.garbage_classifier import (CLASS_FOLDERS, GARBAGE_CLASSES, IMG_SIZE,
                                      INFO_PATH, MODEL_PATH, build_model)

SEED = 42
FINE_TUNE_LAYERS = 40   # how many of the last MobileNetV2 layers to un-freeze in phase 2


def load_datasets(data_dir, batch_size):
    """
    80% train / 20% validation split, labels in the same order as GARBAGE_CLASSES.
    Both calls MUST use shuffle=True with the same seed: Keras shuffles the file list
    before splitting, so different settings would give overlapping, unbalanced splits.
    """
    common = dict(
        directory=data_dir,
        class_names=CLASS_FOLDERS,
        image_size=(IMG_SIZE, IMG_SIZE),
        batch_size=batch_size,
        validation_split=0.2,
        seed=SEED,
        shuffle=True,
        label_mode="int",
    )
    train_ds = tf.keras.utils.image_dataset_from_directory(subset="training", **common)
    val_ds   = tf.keras.utils.image_dataset_from_directory(subset="validation", **common)

    # Safety check: the two splits must not share any photo
    overlap = set(train_ds.file_paths) & set(val_ds.file_paths)
    assert not overlap, f"{len(overlap)} photos are in both training and validation sets"
    return train_ds, val_ds


def make_pipeline(train_ds, val_ds):
    """Data augmentation (only for training) + MobileNetV2 preprocessing."""
    augment = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.1),
        tf.keras.layers.RandomZoom(0.15),
        tf.keras.layers.RandomContrast(0.15),
    ])
    autotune = tf.data.AUTOTUNE
    train_ds = (train_ds
                .map(lambda x, y: (preprocess_input(augment(x, training=True)), y), num_parallel_calls=autotune)
                .prefetch(autotune))
    val_ds = val_ds.map(lambda x, y: (preprocess_input(x), y), num_parallel_calls=autotune).cache().prefetch(autotune)
    return train_ds, val_ds


def evaluate(model, val_ds):
    """Overall + per-class accuracy and a confusion matrix on the validation set."""
    y_true, y_pred = [], []
    for x, y in val_ds:
        y_true.extend(y.numpy())
        y_pred.extend(np.argmax(model.predict(x, verbose=0), axis=1))
    y_true, y_pred = np.array(y_true), np.array(y_pred)

    n = len(GARBAGE_CLASSES)
    confusion = np.zeros((n, n), dtype=int)
    for t, p in zip(y_true, y_pred):
        confusion[t, p] += 1

    per_class = {
        GARBAGE_CLASSES[i]: round(float(confusion[i, i] / max(confusion[i].sum(), 1)) * 100, 1)
        for i in range(n)
    }
    accuracy = round(float((y_true == y_pred).mean()) * 100, 1)
    return accuracy, per_class, confusion.tolist(), len(y_true)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="dataset")
    ap.add_argument("--epochs", type=int, default=6, help="phase 1 epochs (frozen base)")
    ap.add_argument("--fine-tune-epochs", type=int, default=6, help="phase 2 epochs (fine-tuning)")
    ap.add_argument("--batch-size", type=int, default=32)
    args = ap.parse_args()

    tf.keras.utils.set_random_seed(SEED)
    raw_train, raw_val = load_datasets(args.data_dir, args.batch_size)
    train_ds, val_ds = make_pipeline(raw_train, raw_val)

    model, base_model = build_model()
    callbacks = [tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3,
                                                  restore_best_weights=True)]

    # ── Phase 1: train only our classification head ──────────────────────────
    print("\n=== Phase 1: training classification head ===")
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
                  loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(train_ds, validation_data=val_ds, epochs=args.epochs, callbacks=callbacks)

    # ── Phase 2: fine-tune the last layers of MobileNetV2 ─────────────────────
    if args.fine_tune_epochs > 0:
        print(f"\n=== Phase 2: fine-tuning last {FINE_TUNE_LAYERS} MobileNetV2 layers ===")
        base_model.trainable = True
        for layer in base_model.layers[:-FINE_TUNE_LAYERS]:
            layer.trainable = False
        for layer in base_model.layers:                       # keep BatchNorm statistics frozen
            if isinstance(layer, tf.keras.layers.BatchNormalization):
                layer.trainable = False
        model.compile(optimizer=tf.keras.optimizers.Adam(1e-5),
                      loss="sparse_categorical_crossentropy", metrics=["accuracy"])
        model.fit(train_ds, validation_data=val_ds, epochs=args.fine_tune_epochs, callbacks=callbacks)

    # ── Evaluate & save ───────────────────────────────────────────────────────
    accuracy, per_class, confusion, n_val = evaluate(model, val_ds)
    print(f"\nValidation accuracy: {accuracy}%")
    for cls, acc in per_class.items():
        print(f"  {cls:14s} {acc}%")

    model.save(MODEL_PATH)
    info = {
        "trained_at":         datetime.now().strftime("%Y-%m-%d %H:%M"),
        "architecture":       "MobileNetV2 (ImageNet) + Dense(128) + Dropout(0.3) + Dense(7)",
        "classes":            GARBAGE_CLASSES,
        "train_images":       int(sum(len(y) for _, y in raw_train.unbatch().batch(1024))),
        "validation_images":  n_val,
        "val_accuracy":       accuracy,
        "per_class_accuracy": per_class,
        "confusion_matrix":   confusion,
    }
    with open(INFO_PATH, "w") as f:
        json.dump(info, f, indent=2)
    print(f"\nSaved model to {MODEL_PATH}")
    print(f"Saved training report to {INFO_PATH}")


if __name__ == "__main__":
    main()
