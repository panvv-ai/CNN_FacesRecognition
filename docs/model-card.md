# Model Card

## Model

Face Workbench trains a small grayscale CNN classifier:

```text
Input 128 × 128 × 1
Conv2D(32, 5×5, ReLU) → MaxPool
Conv2D(64, 5×5, ReLU) → MaxPool
Flatten → Dense(512, ReLU)
Dense(number_of_people, Softmax)
```

## Intended use

- Local demonstrations of face collection, training, and recognition.
- Teaching classification, preprocessing, metadata, and job orchestration.
- Small consented datasets where the user understands the classifier's limitations.

## Not intended for

- Production identity verification, access control, surveillance, or high-risk decisions.
- Liveness detection, anti-spoofing, age estimation, emotion inference, or demographic inference.
- Large-gallery matching or substantial age/pose variation.
- Use without informed consent or another lawful basis.

## Data and evaluation

The repository includes a small demonstration set and does not claim benchmark
accuracy. Training requires at least two people and two readable samples per
person. Stored validation accuracy and macro F1 do not establish real-world
performance on a small dataset.

## Failure modes

Haar detection can miss occluded, small, rotated, or poorly lit faces.
Background, lighting, camera hardware, and label errors can dominate a small
classifier. Known-label softmax confidence is not an identity guarantee.
