import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input, decode_predictions
import numpy as np
from PIL import Image

class AIModel:
    def __init__(self):
        self.model = MobileNetV2(weights='imagenet')

    def predict(self, image):
        # Get original image size
        width, height = image.size
        
        # Define the sliding window size and stride
        window_size = 224
        stride = 112  # 50% overlap
        
        predictions = []
        
        for y in range(0, height - window_size + 1, stride):
            for x in range(0, width - window_size + 1, stride):
                # Extract patch
                patch = image.crop((x, y, x + window_size, y + window_size))
                
                # Preprocess the patch
                img_array = tf.keras.preprocessing.image.img_to_array(patch)
                img_array = tf.expand_dims(img_array, 0)
                img_array = preprocess_input(img_array)
                
                # Make prediction on patch
                patch_predictions = self.model.predict(img_array)
                predictions.append(patch_predictions[0])
        
        # Aggregate predictions
        avg_prediction = np.mean(predictions, axis=0)
        decoded_predictions = decode_predictions(np.expand_dims(avg_prediction, 0), top=1)[0]
        
        # Extract category and subcategory
        _, category, _ = decoded_predictions[0]
        
        return category, category

    def preprocess_image(self, image):
        # Convert PIL Image to numpy array
        img_array = tf.keras.preprocessing.image.img_to_array(image)
        # Expand dimensions to create batch axis
        img_array = np.expand_dims(img_array, axis=0)
        # Preprocess the image (this function handles scaling)
        return preprocess_input(img_array)
