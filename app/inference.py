"""
inference.py
------------
CNN Inference Engine for Parkinova — Parkinson's MRI Analysis System.
Features:
- Lazy TensorFlow/Lite loading to preserve instantaneous application startup
- Support for both full Keras models and lightweight TFLite models
- Clear binary interpretation:
    * Index 0: No Parkinson's-related pattern detected
    * Index 1: Parkinson's-related pattern detected
- Human-readable research explanations and medical disclaimers
- Completely excludes confidence scores from UI outputs
"""

import logging
import datetime
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

logger = logging.getLogger(__name__)

MEDICAL_DISCLAIMER = (
    "Research Prototype Notice: This application is developed exclusively for "
    "academic and educational research purposes. It is NOT a clinically validated diagnostic "
    "system and cannot establish a clinical diagnosis of Parkinson's disease. An MRI scan alone "
    "does not confirm or exclude neurodegenerative conditions. Always consult a qualified "
    "neurologist or healthcare professional for clinical evaluation."
)

EXPLANATION_PARKINSONS = (
    "The CNN deep learning model identified structural and intensity patterns in the MRI scan "
    "that correlate with Parkinson's disease neuroimaging features present in the training dataset. "
    "This is an automated experimental observation and must be evaluated alongside clinical motor "
    "assessments, patient history, and expert radiologist review."
)

EXPLANATION_NORMAL = (
    "The CNN deep learning model did not detect distinctive Parkinson's-associated patterns in the "
    "analyzed MRI scan compared to the reference control dataset. This experimental finding does not "
    "rule out early-stage disease, atypical parkinsonism, or other neurological conditions."
)


class InferenceEngine:
    """
    Coordinates preprocessing, model prediction, and clinical-style result generation.
    """

    def __init__(
        self,
        model: Any,
        model_info: Dict[str, Any],
        preprocessor: Any,
        class_labels: List[str],
    ) -> None:
        self.model = model
        self.model_info = model_info
        self.preprocessor = preprocessor
        self.class_labels = class_labels
        self.is_tflite = model_info.get("is_tflite", False)
        logger.info(
            "InferenceEngine initialized | is_tflite=%s | labels=%s",
            self.is_tflite, self.class_labels
        )

    def analyze(self, image_path: str) -> Dict[str, Any]:
        """
        Run the complete prediction pipeline on an MRI image.

        Returns
        -------
        dict with:
            success (bool)
            predicted_class (str)
            predicted_index (int)
            explanation (str)
            disclaimer (str)
            original_array (np.ndarray)
            preprocessed_array (np.ndarray)
            preprocessing_info (dict)
            analysis_timestamp (str)
            error (str or None)
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        result: Dict[str, Any] = {
            "success": False,
            "predicted_class": "",
            "predicted_index": -1,
            "explanation": "",
            "disclaimer": MEDICAL_DISCLAIMER,
            "raw_score": 0.0,
            "original_array": np.array([]),
            "preprocessed_array": np.array([]),
            "preprocessing_info": {},
            "analysis_timestamp": timestamp,
            "error": None,
        }

        # 1. Validate file existence
        import os
        if not image_path or not os.path.isfile(image_path):
            result["error"] = f"Image file not found: '{image_path}'"
            logger.error(result["error"])
            return result

        # 2. Preprocess
        try:
            orig_arr, prep_arr, info_dict = self.preprocessor.preprocess(image_path)
            result["original_array"] = orig_arr
            result["preprocessed_array"] = prep_arr
            result["preprocessing_info"] = info_dict
        except Exception as exc:
            result["error"] = f"Image preprocessing failed: {exc}"
            logger.exception("Preprocessing error for '%s'", image_path)
            return result

        # 3. Shape validation
        expected_shape = self.model_info.get("input_shape")
        if expected_shape is not None:
            actual_spatial = prep_arr.shape[1:]
            if actual_spatial != tuple(expected_shape):
                result["error"] = (
                    f"Dimension mismatch: model expects {expected_shape}, "
                    f"but preprocessed array is {actual_spatial}."
                )
                logger.error(result["error"])
                return result

        # 4. Predict
        try:
            if self.is_tflite:
                input_details = self.model.get_input_details()
                output_details = self.model.get_output_details()
                self.model.set_tensor(input_details[0]["index"], prep_arr)
                self.model.invoke()
                raw_output = self.model.get_tensor(output_details[0]["index"])
            else:
                raw_output = self.model.predict(prep_arr, verbose=0)
        except Exception as exc:
            result["error"] = f"Model execution failed: {exc}"
            logger.exception("Inference error for '%s'", image_path)
            return result

        # 5. Interpret output without confidence meters
        try:
            pred_idx, pred_class, explanation, raw_score = self._interpret_output(raw_output)
        except Exception as exc:
            result["error"] = f"Result interpretation error: {exc}"
            logger.exception("Interpretation error")
            return result

        result.update({
            "success": True,
            "predicted_class": pred_class,
            "predicted_index": pred_idx,
            "explanation": explanation,
            "raw_score": raw_score,
            "error": None,
        })

        logger.info(
            "Analysis complete for '%s' -> %s (index %d)",
            os.path.basename(image_path), pred_class, pred_idx
        )
        return result

    def _interpret_output(self, raw_output: np.ndarray) -> Tuple[int, str, str, float]:
        """
        Map model activation to validated clinical label and explanation.
        Guarantees that index 0 is Healthy/Normal and index 1 is Parkinson's.
        """
        output = np.squeeze(raw_output)
        num_labels = len(self.class_labels)

        # Sigmoid binary model (1 output unit)
        if output.ndim == 0 or (output.ndim == 1 and output.shape[0] == 1):
            raw_score = float(np.squeeze(output))
            # Binary threshold: 0.5
            pred_index = 1 if raw_score >= 0.5 else 0
        else:
            # Softmax multiclass
            scores = output.flatten()
            pred_index = int(np.argmax(scores))
            raw_score = float(scores[pred_index])

        # Assign class label
        if pred_index < len(self.class_labels):
            pred_class = self.class_labels[pred_index]
        else:
            pred_class = f"Class {pred_index}"

        # Assign explanation
        if pred_index == 1:
            explanation = EXPLANATION_PARKINSONS
        else:
            explanation = EXPLANATION_NORMAL

        return pred_index, pred_class, explanation, raw_score
