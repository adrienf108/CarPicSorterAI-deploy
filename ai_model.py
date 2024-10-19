import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input, decode_predictions
import numpy as np

class AIModel:
    def __init__(self):
        self.model = MobileNetV2(weights='imagenet')

    def predict(self, image):
        # Preprocess the image
        img_array = tf.keras.preprocessing.image.img_to_array(image)
        img_array = tf.expand_dims(img_array, 0)
        img_array = preprocess_input(img_array)

        # Make prediction
        predictions = self.model.predict(img_array)
        decoded_predictions = decode_predictions(predictions, top=1)[0]

        # Extract category and subcategory
        _, category, _ = decoded_predictions[0]

        # For simplicity, we're using the same category as subcategory
        # In a real-world scenario, you'd have a more sophisticated categorization system
        return category, category

