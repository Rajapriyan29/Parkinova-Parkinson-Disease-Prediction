import os
import tensorflow as tf

keras_path = os.path.join("models", "parkinson_cnn.keras")
tflite_path = os.path.join("models", "parkinson_model.tflite")

print(f"Loading Keras model from {keras_path}...")
model = tf.keras.models.load_model(keras_path)
print(f"Model loaded successfully! Input shape: {model.input_shape}, Output shape: {model.output_shape}")

print("Converting to TensorFlow Lite...")
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

with open(tflite_path, "wb") as f:
    f.write(tflite_model)

size_mb = len(tflite_model) / (1024 * 1024)
print(f"Saved TFLite model to {tflite_path} ({size_mb:.2f} MB)")
