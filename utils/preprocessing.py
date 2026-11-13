"""
utils/preprocessing.py
-----------------------
Image preprocessing pipeline for Parkinova CNN inference.

Responsibilities:
  - Load image from disk using PIL
  - Resize to the model's required spatial dimensions
  - Convert to RGB (handles grayscale / RGBA / palette modes)
  - Optionally normalise pixel values to [0, 1]
  - Return (original_array, preprocessed_batch, info_dict) for the InferenceEngine
"""

import logging
from typing import Dict, Tuple, Any

import numpy as np

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Stateless image preprocessor for CNN inference.

    Parameters
    ----------
    input_shape : tuple
        Expected model input (H, W, C).  Defaults to (244, 244, 3).
    normalize : bool
        Whether to scale pixel values from [0, 255] → [0, 1].
        Set to False when the Keras model already includes a Rescaling layer.
    """

    def __init__(
        self,
        input_shape: Tuple[int, ...] = (244, 244, 3),
        normalize: bool = False,
    ) -> None:
        self.input_shape = input_shape
        self.normalize = normalize
        self.target_size = (input_shape[0], input_shape[1])  # (H, W)
        logger.info(
            "ImagePreprocessor ready | target=%s | normalize=%s",
            self.target_size, self.normalize,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def preprocess(
        self, image_path: str
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Load and preprocess an image for CNN inference.

        Returns
        -------
        original_array : np.ndarray
            uint8 RGB image at the original resolution (H, W, 3).
        preprocessed_batch : np.ndarray
            float32 array shaped (1, H_model, W_model, 3) ready for model.predict().
        info : dict
            Metadata about the preprocessing steps applied.
        """
        from PIL import Image

        # --- Load -----------------------------------------------------------
        pil_img = Image.open(image_path)
        original_size = pil_img.size          # (W, H) in PIL convention
        original_mode = pil_img.mode

        # --- Convert to RGB -------------------------------------------------
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        # --- Keep a copy of the original as uint8 array ---------------------
        original_array = np.array(pil_img, dtype=np.uint8)

        # --- Resize ---------------------------------------------------------
        # PIL resize takes (W, H); self.target_size is (H, W)
        target_wh = (self.target_size[1], self.target_size[0])
        resized = pil_img.resize(target_wh, Image.LANCZOS)
        pixel_array = np.array(resized, dtype=np.float32)

        # --- Normalise if required ------------------------------------------
        if self.normalize:
            pixel_array = pixel_array / 255.0

        # --- Add batch dimension --------------------------------------------
        batch = np.expand_dims(pixel_array, axis=0)   # (1, H, W, 3)

        info: Dict[str, Any] = {
            "original_size": original_size,
            "original_mode": original_mode,
            "target_size": self.target_size,
            "normalized": self.normalize,
            "dtype": str(batch.dtype),
            "batch_shape": batch.shape,
        }

        logger.debug(
            "Preprocessed '%s' | orig=%s → batch=%s | normalize=%s",
            image_path, original_size, batch.shape, self.normalize,
        )
        return original_array, batch, info

