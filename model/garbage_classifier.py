"""
Garbage Classifier using CNN (MobileNetV2 - Transfer Learning)
==============================================================
How it works:
  - MobileNetV2 is pre-trained on ImageNet (1.2 million images, 1000 classes),
    so it already knows how to "see" edges, textures and shapes.
  - We put our own small classification head on top (7 garbage classes).
  - `train.py` trains that head (and fine-tunes the last MobileNetV2 layers)
    on real garbage photos and saves the result to `model/garbage_model.keras`.
  - The web app loads that trained file at startup.

Garbage classes it can detect:
  0 - Cardboard
  1 - Glass
  2 - Metal
  3 - Organic Waste
  4 - Paper
  5 - Plastic
  6 - Not Garbage (clean area)
"""

import io
import json
import os

import numpy as np
from PIL import Image, ImageOps

# ── Try to import TensorFlow ──────────────────────────────────────────────────
try:
    import tensorflow as tf
    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
    from tensorflow.keras.layers import Dense, Dropout, GlobalAveragePooling2D
    from tensorflow.keras.models import Model
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False


MODEL_DIR  = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(MODEL_DIR, 'garbage_model.keras')  # created by train.py
INFO_PATH  = os.path.join(MODEL_DIR, 'model_info.json')      # accuracy etc., created by train.py

IMG_SIZE = 224  # MobileNetV2 expects 224x224 images

# Below this confidence (%) we tell the team the AI is not sure
UNCERTAIN_THRESHOLD = 50.0

# ── Class labels ─────────────────────────────────────────────────────────────
# The order matters: it must match the order used in train.py
GARBAGE_CLASSES = [
    "Cardboard",
    "Glass",
    "Metal",
    "Organic Waste",
    "Paper",
    "Plastic",
    "Not Garbage"
]

# Folder name of each class inside the training dataset (same order as above)
CLASS_FOLDERS = ["cardboard", "glass", "metal", "organic", "paper", "plastic", "not_garbage"]

# Danger level for each class (for team priority)
DANGER_LEVEL = {
    "Cardboard":     "Low",
    "Glass":         "High",      # dangerous — sharp
    "Metal":         "High",      # dangerous — sharp/rusty
    "Organic Waste": "Medium",    # smell, disease
    "Paper":         "Low",
    "Plastic":       "High",      # environmental damage
    "Not Garbage":   "None"
}

# Recommended action for each class
RECOMMENDED_ACTION = {
    "Cardboard":     "Collect and send to recycling center",
    "Glass":         "Handle carefully — use gloves. Send to glass recycling",
    "Metal":         "Use protective gear. Send to scrap/metal recycling",
    "Organic Waste": "Compost or send to organic waste facility",
    "Paper":         "Collect and send to paper recycling",
    "Plastic":       "Collect and send to plastic recycling",
    "Not Garbage":   "No action needed"
}


# ── Build the CNN Model ───────────────────────────────────────────────────────
def build_model():
    """
    Build CNN using Transfer Learning with MobileNetV2.
    Returns (model, base_model) so train.py can un-freeze the base later.
    """
    base_model = MobileNetV2(
        weights='imagenet',                    # Pre-trained ImageNet weights
        include_top=False,                     # Remove original 1000-class top layer
        input_shape=(IMG_SIZE, IMG_SIZE, 3)
    )
    base_model.trainable = False               # Freeze base — only train our head first

    # Our custom classification head
    x = base_model.output
    x = GlobalAveragePooling2D()(x)            # Feature maps → 1280 numbers
    x = Dense(128, activation='relu')(x)       # Hidden layer
    x = Dropout(0.3)(x)                        # Prevent overfitting
    predictions = Dense(len(GARBAGE_CLASSES), activation='softmax')(x)  # 7 outputs

    model = Model(inputs=base_model.input, outputs=predictions)
    return model, base_model


def load_model():
    """
    Load the trained model saved by train.py.
    Returns (model, trained):
      - (trained model, True)  if model/garbage_model.keras exists
      - (None, False)          if TensorFlow is missing or the model is not trained yet
    """
    if not TF_AVAILABLE or not os.path.exists(MODEL_PATH):
        return None, False
    model = tf.keras.models.load_model(MODEL_PATH)
    return model, True


def load_model_info():
    """Training results (accuracy, dataset size, date) saved by train.py."""
    if os.path.exists(INFO_PATH):
        with open(INFO_PATH) as f:
            return json.load(f)
    return None


# ── Preprocess Image ──────────────────────────────────────────────────────────
def preprocess_image(image_bytes):
    """Convert uploaded image bytes to a tensor ready for the CNN."""
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)            # Fix rotation of phone photos
    img = img.convert('RGB')                      # Make sure it's RGB (not RGBA/grayscale)
    img = img.resize((IMG_SIZE, IMG_SIZE))        # MobileNetV2 expects 224x224
    img_array = np.array(img, dtype=np.float32)   # Convert to numpy array
    img_array = np.expand_dims(img_array, axis=0) # Add batch dimension: (1, 224, 224, 3)
    img_array = preprocess_input(img_array)       # MobileNetV2 preprocessing (-1 to 1)
    return img_array


# ── Main Prediction Function ──────────────────────────────────────────────────
def predict_garbage(image_bytes, model):
    """
    Run CNN prediction on an image.
    Returns a dictionary with:
      - is_garbage: True/False
      - garbage_type: e.g. "Plastic"
      - confidence: e.g. 87.5 (percentage)
      - uncertain: True if confidence is below UNCERTAIN_THRESHOLD
      - danger_level: Low / Medium / High / None
      - recommended_action: what the team should do
      - all_predictions: scores for all classes
    """
    if model is None:
        return fallback_prediction()

    img_array = preprocess_image(image_bytes)

    # ── CNN Forward Pass ──────────────────────────────────────────────────────
    scores = model.predict(img_array, verbose=0)[0]   # Shape: (7,)

    # Get the class with highest score
    predicted_index = int(np.argmax(scores))
    predicted_class = GARBAGE_CLASSES[predicted_index]
    confidence      = round(float(scores[predicted_index]) * 100, 2)

    all_preds = {
        GARBAGE_CLASSES[i]: round(float(scores[i]) * 100, 2)
        for i in range(len(GARBAGE_CLASSES))
    }

    return {
        "is_garbage":          predicted_class != "Not Garbage",
        "garbage_type":        predicted_class,
        "confidence":          confidence,
        "uncertain":           confidence < UNCERTAIN_THRESHOLD,
        "danger_level":        DANGER_LEVEL[predicted_class],
        "recommended_action":  RECOMMENDED_ACTION[predicted_class],
        "all_predictions":     all_preds
    }


def fallback_prediction():
    """
    Used when there is no trained model (TensorFlow missing or train.py not run yet).
    We do NOT guess — we just tell the team to check the photo manually.
    """
    return {
        "is_garbage":         True,
        "garbage_type":       "Unknown",
        "confidence":         0.0,
        "uncertain":          True,
        "danger_level":       "Medium",
        "recommended_action": "AI model not available — inspect the photo manually",
        "all_predictions":    {},
        "note":               "No trained model loaded — run train.py"
    }
