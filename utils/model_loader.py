"""
utils/model_loader.py
---------------------
Handles loading of Keras (.keras / .h5) and TFLite (.tflite) models
for the Parkinova inference pipeline.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class ModelLoader:
    """
    Loads a CNN model from disk and returns it alongside a metadata dict
    that the InferenceEngine and ImagePreprocessor consume.

    Supported formats:
        - Keras  : .keras / .h5
        - TFLite : .tflite
    """

    # Class-labels indexed by number of output units
    _LABEL_MAP: Dict[int, List[str]] = {
        1: ["Healthy", "Parkinson's"],   # sigmoid binary
        2: ["Healthy", "Parkinson's"],   # softmax 2-class
    }

    def load_model(self, model_path: str) -> Tuple[Any, Dict[str, Any]]:
        """
        Load model from *model_path* and return (model, info_dict).

        info_dict keys
        --------------
        model_name      : str   – stem of the file
        model_path      : str   – absolute path
        is_tflite       : bool
        input_shape     : tuple – (H, W, C) spatial dims, without batch
        num_classes     : int   – number of output units
        normalize_input : bool  – True if caller must scale pixels to [0,1]
        """
        path = Path(model_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        suffix = path.suffix.lower()
        logger.info("Loading model from: %s (format: %s)", path, suffix)

        if suffix == ".tflite":
            return self._load_tflite(path)
        elif suffix in (".keras", ".h5"):
            return self._load_keras(path)
        else:
            raise ValueError(
                f"Unsupported model format '{suffix}'. "
                "Expected .keras, .h5, or .tflite."
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_keras(self, path: Path) -> Tuple[Any, Dict[str, Any]]:
        import tensorflow as tf  # noqa: F401 – ensures TF is initialised
        import keras

        model = keras.models.load_model(str(path))
        input_shape = tuple(model.input_shape[1:])   # drop batch dim
        output_units = model.output_shape[-1]

        # Detect whether the model already rescales internally
        # (e.g. a keras.layers.Rescaling layer as first layer)
        has_rescaling = any(
            "rescaling" in type(layer).__name__.lower()
            for layer in model.layers
        )
        normalize_input = not has_rescaling  # caller must normalise only if model doesn't

        info: Dict[str, Any] = {
            "model_name": path.stem,
            "model_path": str(path),
            "is_tflite": False,
            "input_shape": input_shape,
            "num_classes": max(output_units, 2),   # treat sigmoid(1) as 2-class
            "normalize_input": normalize_input,
        }

        logger.info(
            "Keras model loaded | input=%s | outputs=%d | normalize=%s",
            input_shape, output_units, normalize_input,
        )
        return model, info

    def _load_tflite(self, path: Path) -> Tuple[Any, Dict[str, Any]]:
        import tensorflow as tf

        interpreter = tf.lite.Interpreter(model_path=str(path))
        interpreter.allocate_tensors()

        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()

        raw_shape = input_details[0]["shape"]          # [1, H, W, C]
        input_shape = tuple(int(d) for d in raw_shape[1:])
        output_units = int(output_details[0]["shape"][-1])

        info: Dict[str, Any] = {
            "model_name": path.stem,
            "model_path": str(path),
            "is_tflite": True,
            "input_shape": input_shape,
            "num_classes": max(output_units, 2),
            "normalize_input": True,   # TFLite models typically expect [0,1]
        }

        logger.info(
            "TFLite model loaded | input=%s | outputs=%d",
            input_shape, output_units,
        )
        return interpreter, info

    def get_class_labels(self, num_classes: int) -> List[str]:
        """Return ordered class labels for a given number of classes."""
        return self._LABEL_MAP.get(num_classes, [f"Class {i}" for i in range(num_classes)])

