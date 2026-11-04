# CNN_FacesRecognition

**CNN-based face dataset collection, model training, and inference from images, videos, and webcams.**

<p align="center">
  <a href="https://github.com/panvv-ai/CNN_FacesRecognition/actions/workflows/ci.yml">
    <img alt="CI" src="https://github.com/panvv-ai/CNN_FacesRecognition/actions/workflows/ci.yml/badge.svg">
  </a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="TensorFlow 2.21" src="https://img.shields.io/badge/TensorFlow-2.21-FF6F00?logo=tensorflow&logoColor=white">
  <img alt="OpenCV 5.0" src="https://img.shields.io/badge/OpenCV-5.0-5C3EE8?logo=opencv&logoColor=white">
</p>

<p align="center">
  <a href="README.md">简体中文</a> | <a href="README.en.md">English</a>
</p>

A Python project that uses a convolutional neural network (CNN) for face dataset collection, model training, and inference from images, videos, and webcams. It is intended for learning computer vision workflows and for small proof-of-concept applications.

## Contents

- [Overview](#overview)
- [Features](#features)
- [Technology stack](#technology-stack)
- [Workflow](#workflow)
- [Repository layout](#repository-layout)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Dataset conventions](#dataset-conventions)
- [Configuration](#configuration)
- [Testing and continuous integration](#testing-and-continuous-integration)
- [Privacy and security](#privacy-and-security)
- [Known limitations](#known-limitations)
- [Contributing](#contributing)
- [License](#license)

## Overview

The project provides an end-to-end pipeline:

1. Detect and crop faces from photos, videos, or a webcam.
2. Organize training images by person and generate class labels automatically.
3. Build and train a CNN classifier with TensorFlow/Keras.
4. Recognize faces in images, videos, and live webcam frames.

The model receives a `128 × 128` grayscale face image and returns a class index and confidence score. Video and webcam inference label results below `0.70` confidence as `unknown`.

## Features

| Module | Script | Description |
| --- | --- | --- |
| Photo collection | `faces_from_Photo.py` | Detect and crop faces from a directory of photos with OpenCV's Haar cascade |
| Video collection | `faces_from_Video.py` | Collect faces from a video file with Dlib's HOG detector |
| Webcam collection | `faces_from_Camera.py` | Capture faces in real time with random brightness and contrast augmentation |
| Data processing | `load_dataset.py`, `dataSet.py` | Load images and labels, grayscale and resize them, normalize values, and split the dataset |
| Model training | `train_model.py` | Build, train, evaluate, save, load, and use the CNN model |
| Photo inference | `Recognize_From_Photo.py` | Run recognition on a single image or a directory of images |
| Video inference | `Recognize_From_Vedio.py` | Detect and label faces in video frames |
| Webcam inference | `Recognize_From_Camera.py` | Display live face detection and recognition results |
| Automated verification | `tests/`, GitHub Actions | Exercise the train, save, reload, and predict workflow |

### Model architecture

```text
Input(128 × 128 × 1)
  -> Conv2D(32, 5 × 5, ReLU) -> MaxPooling2D
  -> Conv2D(64, 5 × 5, ReLU) -> MaxPooling2D
  -> Flatten
  -> Dense(512, ReLU)
  -> Dense(num_classes, Softmax)
```

## Technology stack

- Python 3.11+
- TensorFlow / Keras
- OpenCV
- scikit-learn
- NumPy
- Dlib for video and webcam dataset collection only

Runtime dependencies are pinned in [`requirements.txt`](requirements.txt). Dlib is isolated in [`requirements-face-detection.txt`](requirements-face-detection.txt).

## Workflow

```mermaid
flowchart LR
    A[Photo / video / webcam] --> B[Face detection and crop]
    B --> C[dataset/person/image]
    C --> D[Grayscale and 128×128 resize]
    D --> E[Train/test split]
    E --> F[Train CNN]
    F --> G[MyModel/model.keras]
    A --> H[Photo / video / webcam inference]
    G --> H
    H --> I[Name and confidence]
```

## Repository layout

```text
.
├── .github/
│   ├── dependabot.yml
│   └── workflows/ci.yml
├── dataset/                    # dataset/<person>/*.jpg
├── model_test/                 # images or videos used for inference
├── tests/                      # smoke tests
├── dataSet.py                  # data formatting and label encoding
├── load_dataset.py             # dataset reader
├── read_img.py                 # image directory utilities
├── train_model.py              # CNN definition, training, persistence, and prediction
├── faces_from_Photo.py         # face collection from photos
├── faces_from_Video.py         # face collection from a video
├── faces_from_Camera.py        # face collection from a webcam
├── Recognize_From_Photo.py     # photo inference
├── Recognize_From_Vedio.py     # video inference
├── Recognize_From_Camera.py    # live webcam inference
├── requirements.txt            # core dependencies
└── requirements-face-detection.txt
```

## Requirements

- Python 3.11 or later
- macOS, Linux, or Windows
- A webcam and Dlib when using video or webcam collection
- A TensorFlow-compatible CPU or GPU is recommended for training and live inference

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/panvv-ai/CNN_FacesRecognition.git
cd CNN_FacesRecognition

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install Dlib only when collecting faces from video or a webcam:

```bash
pip install -r requirements-face-detection.txt
```

On platforms without a Dlib binary package, installation compiles from source and normally requires CMake and a C++ toolchain.

### 2. Prepare a dataset

Store each person's images in a directory named after that person:

```text
dataset/
├── alice/
│   ├── 0001.jpg
│   └── 0002.jpg
└── bob/
    ├── 0001.jpg
    └── 0002.jpg
```

You can also collect images with the provided scripts:

```bash
# Collect from photos; create ./MySource_faces and the output directory first
python faces_from_Photo.py

# Collect from video; update the video path in the script
python faces_from_Video.py

# Collect from webcam; change cv2.VideoCapture(700) to the usual device index 0
python faces_from_Camera.py
```

Edit source paths, output paths, video filenames, and camera indices for your machine.

### 3. Train the model

```bash
python train_model.py
```

The model is saved to `MyModel/model.keras` by default. The script uses an `80:20` train/test split and prints test loss and accuracy.

### 4. Run inference

```bash
# Recognize photos under model_test/
python Recognize_From_Photo.py

# Recognize a video; set the video path in the script
python Recognize_From_Vedio.py

# Live webcam recognition; adjust the camera index when needed
python Recognize_From_Camera.py
```

Recognition scripts recover display names from the subdirectory names under `dataset/`. Keep the same directory structure during training and inference.

## Dataset conventions

- Each subdirectory represents one person; its name is used as the display label.
- The current loader reads `.jpg` files only.
- Images should contain clear, detectable faces and cover varied lighting, angles, and expressions.
- Training converts images to grayscale and resizes them to `128 × 128`.
- Do not commit private face photos, model weights, or local caches.

## Configuration

| Setting | Location | Default |
| --- | --- | --- |
| Input size | `train_model.py` | `128 × 128` |
| Epochs | `train_model.py` | `8` |
| Batch size | `train_model.py` | `20` |
| Model path | `train_model.py` | `./MyModel/model.keras` |
| Unknown-face threshold | `Recognize_From_Camera.py`, `Recognize_From_Vedio.py` | `0.70` |
| Collection target | `faces_from_Video.py`, `faces_from_Camera.py` | `200` |
| Camera device index | `faces_from_Camera.py`, `Recognize_From_Camera.py` | `700` |

## Testing and continuous integration

Run locally:

```bash
python -m unittest discover -s tests -v
```

The test creates a temporary dataset and runs one training pass, then saves, reloads, and invokes the model for prediction.

GitHub Actions runs the same check for pull requests and pushes to `master`. See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Privacy and security

Face images are sensitive personal information. Before using or publishing data, models, or recognition results from this project:

- Obtain explicit consent from the people involved or establish another lawful basis.
- Follow applicable privacy, biometric, and face-recognition regulations.
- Do not use the project for undisclosed surveillance, identity verification, or high-impact decisions without appropriate safeguards.
- Never publish real people's photos, model weights, secrets, or runtime logs without authorization.

The sample photos in this repository are included only to demonstrate the workflow. Maintainers should periodically verify that permission to publish them still applies.

## Known limitations

- The model is a basic CNN classifier and has no liveness detection, anti-spoofing, or cross-age recognition.
- Haar/HOG detection is less reliable with occlusion, small faces, and extreme lighting.
- A small dataset can overfit quickly; test accuracy does not represent production performance.
- Camera indices, file paths, and several training parameters are currently hard-coded.
- No pretrained model, packaged installation, or graphical interface is currently included.

## Contributing

Issues and pull requests are welcome:

1. Create a feature branch from `master`.
2. Keep each change focused and add or update tests.
3. Run `python -m unittest discover -s tests -v`.
4. Open a pull request and wait for CI and code review.

The `master` branch should remain buildable, testable, and reversible. Direct pushes, force pushes, and branch deletion are not allowed.

## License

No open-source license has been declared. Until a license is added, copyright remains with the repository owner by default. Obtain explicit permission before copying, modifying, distributing, or using the project commercially.

---

Maintainer blog: <https://www.cnblogs.com/panweiwei/>
