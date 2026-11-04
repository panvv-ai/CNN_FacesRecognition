import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf

from dataSet import DataSet
from train_model import Model


class ModelSmokeTest(unittest.TestCase):
    def test_train_save_load_and_predict(self):
        rng = np.random.default_rng(42)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            dataset_dir = root / "dataset"
            model_path = root / "model.keras"

            for label in ("alice", "bob"):
                label_dir = dataset_dir / label
                label_dir.mkdir(parents=True)
                for index in range(4):
                    image = rng.integers(0, 256, (128, 128, 3), dtype=np.uint8)
                    cv2.imwrite(str(label_dir / f"{index}.jpg"), image)

            dataset = DataSet(str(dataset_dir))
            self.assertEqual(dataset.num_classes, 2)
            self.assertEqual(dataset.X_train.shape[1:], (128, 128, 1))

            model = Model()
            model.read_trainData(dataset)
            model.build_model()
            model.model.compile(
                optimizer="adam",
                loss="categorical_crossentropy",
                metrics=["accuracy"],
            )
            model.model.fit(
                dataset.X_train,
                dataset.Y_train,
                epochs=1,
                batch_size=4,
                verbose=0,
            )
            model.save(str(model_path))

            restored = Model()
            restored.load(str(model_path))
            label, probability = restored.predict(dataset.X_test[0])

            self.assertIn(label, (0, 1))
            self.assertGreaterEqual(float(probability), 0.0)
            self.assertLessEqual(float(probability), 1.0)


if __name__ == "__main__":
    tf.get_logger().setLevel("ERROR")
    unittest.main()
