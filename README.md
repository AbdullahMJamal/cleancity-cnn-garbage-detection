# CleanCity – CNN Garbage Detection System

A web app for **Sir Syed University of Engineering & Technology**: anyone can photograph garbage on campus,
a **CNN (MobileNetV2, transfer learning)** identifies what kind of waste it is, and the cleaning team
manages every report from a password-protected dashboard.

![Operations dashboard](docs/screenshots/operations-dashboard.png)

## Screenshots

| Report page | Mobile — report details |
|---|---|
| ![Report page](docs/screenshots/report-page.png) | ![Mobile report details](docs/screenshots/mobile-report-details.png) |

| Mobile — report form | Team login |
|---|---|
| ![Mobile report form](docs/screenshots/mobile-report-form.png) | ![Team login](docs/screenshots/team-login.png) |

## Features

**Report page** (`/`)
- Upload or drag & drop a photo (PNG / JPG / GIF / WEBP, max 16MB)
- Classified record panel: report number, photo, garbage type, confidence, danger level, recommended action, score for every class
- Warns when the AI is unsure (confidence below 50%)

**Operations dashboard** (`/team`, password protected)
- Stats: total reports (+ last 24h), pending triage (+ critical count), in progress, cleaned (+ resolution rate)
- Search, filter by waste type / danger / status, pagination
- Detail drawer: photo, GPS link, classification, class scores and a full **audit trail** of everything that happened to the report
- Actions: Dispatch team → Mark cleaned, Reject, Reopen, **Re-classify** (re-runs the CNN, e.g. after retraining), Delete

**Design**
- UI follows the "Municipal Utility Interface" design system in `docs/design/` (Google Stitch export):
  Inter + JetBrains Mono, flat 1px borders, status-colour chips, dense data table

**Under the hood**
- Trained CNN loaded once at startup (`model/garbage_model.keras`)
- SQLite database (unique IDs, safe with many users at once)
- Uploaded photos are checked, resized and re-saved as JPEG (removes hidden GPS metadata)
- CSRF protection on all team forms, secure session cookies
- 21 automated tests (`python -m pytest`)

## Project Structure

```
cleancity_cnn/
├── app.py                     ← Flask web app (run this!)
├── database.py                ← SQLite storage: reports + audit trail
├── train.py                   ← Trains the CNN and saves it
├── requirements.txt
├── model/
│   ├── garbage_classifier.py  ← CNN architecture, loading, prediction
│   ├── garbage_model.keras    ← The trained model (created by train.py)
│   └── model_info.json        ← Accuracy & training details
├── scripts/
│   └── prepare_dataset.py     ← Builds the training dataset from public datasets
├── templates/                 ← base / user / team / login pages
├── static/
│   ├── img/leaf.svg           ← Logo
│   └── uploads/               ← Photos submitted by users (not in git)
├── samples/                   ← Example photos to try the app (one per class)
├── tests/test_app.py          ← Automated tests
├── docs/
│   ├── design/                ← Original UI design (Stitch screens, HTML mockups, DESIGN.md)
│   └── screenshots/           ← Screenshots of the finished app
└── instance/                  ← Database + secret key (created automatically, not in git)
```

## How the CNN Works

```
User uploads photo
       ↓
Resize to 224×224, scale pixels to [-1, 1]
       ↓
MobileNetV2 (pre-trained on ImageNet) extracts 1280 visual features
       ↓
Our head: GlobalAveragePooling → Dense(128, ReLU) → Dropout(0.3) → Dense(7, Softmax)
       ↓
Cardboard / Glass / Metal / Organic Waste / Paper / Plastic / Not Garbage
       ↓
Confidence % + Danger Level + Recommended Action → shown to user and team
```

### Training (transfer learning in two phases)
1. **Head training** – MobileNetV2 frozen, only our new layers learn (Adam, lr = 1e-3)
2. **Fine-tuning** – last 40 MobileNetV2 layers un-frozen, tiny learning rate (1e-5)

Data augmentation (flip, rotation, zoom, contrast) and early stopping reduce overfitting.
80% of photos are used for training, 20% are held back to measure accuracy honestly.
Results (overall + per-class accuracy, confusion matrix) are saved in `model/model_info.json`.

### Dataset
| Our class     | Source                                                            |
|---------------|-------------------------------------------------------------------|
| Cardboard, Glass, Metal, Paper, Plastic, Organic Waste | Garbage Classification (12 classes, Kaggle / Hugging Face `UdaraChamidu/Garbage-Classification-with-12-classes`) — glass = brown + green + white glass, organic = biological |
| Not Garbage   | Intel Image Classification scenes: buildings, street, forest, sea, mountain (Hugging Face `sfarrukhm/intel-image-classification`) |

Up to 900 photos per class, so classes are balanced.

## Setup

### 1. Install packages
```
pip install -r requirements.txt
```
(TensorFlow is large — this may take 5–10 minutes.)

### 2. Run the app
In PyCharm: right-click `app.py` → Run 'app'. Or in a terminal:
```
python app.py
```
- Report page: http://127.0.0.1:5000/
- Team dashboard: http://127.0.0.1:5000/team — default password **`cleancity`**

To use your own password (recommended), set an environment variable before starting:
```
set TEAM_PASSWORD=your-password        (Windows cmd)
$env:TEAM_PASSWORD="your-password"     (PowerShell)
export TEAM_PASSWORD=your-password     (Linux / macOS)
```

### 3. (Optional) Retrain the model
The trained model is already included. To train it again:
```
python scripts/prepare_dataset.py --garbage-dir <12-class folder> --clean-dir <clean images folder> --out dataset
python train.py --data-dir dataset
```

### 4. Run the tests
```
python -m pytest
```

## Try It with Sample Images

The `samples/` folder has one example photo per class. Upload any of them on the report page:

| File | Expected result | Danger |
|---|---|---|
| `samples/plastic.jpg` | Plastic | High |
| `samples/glass.jpg` | Glass | High |
| `samples/metal.jpg` | Metal | High |
| `samples/organic.jpg` | Organic Waste | Medium |
| `samples/cardboard.jpg` | Cardboard | Low |
| `samples/paper.jpg` | Paper | Low |
| `samples/not_garbage.jpg` | Not Garbage | None |

All seven are classified correctly with over 99% confidence. `glass`, `organic`, `paper` and `not_garbage`
were never seen during training; `cardboard`, `metal` and `plastic` come from the training set (every photo
of those classes was used). Images are from the public datasets listed below.

## What the CNN Detects

| Garbage Type  | Danger Level | Action                          |
|---------------|--------------|---------------------------------|
| Plastic       | High         | Send to plastic recycling       |
| Glass         | High         | Handle with gloves              |
| Metal         | High         | Send to scrap recycling         |
| Organic Waste | Medium       | Compost or organic facility     |
| Cardboard     | Low          | Send to recycling center        |
| Paper         | Low          | Send to paper recycling         |
| Not Garbage   | None         | No action needed                |

## Technical Details

- CNN Architecture: MobileNetV2 (transfer learning) + custom classification head
- Pre-trained on: ImageNet (1.2M images, 1000 classes), fine-tuned on ~6,000 waste/scene photos
- Image preprocessing: EXIF rotation fix, resize to 224×224, normalize to [-1, 1]
- Framework: TensorFlow / Keras
- Backend: Python Flask + SQLite
- Frontend: HTML + CSS + JavaScript (no frameworks)
