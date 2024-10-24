from custom_model import CustomModel
from PIL import Image
import numpy as np

class AIModel:
    def __init__(self):
        self.model = CustomModel()

    def predict(self, image):
        # image is now a PIL Image object
        preprocessed_image = self.preprocess_image(image)
        
        # Get all predictions from custom model
        main_category, subcategory, confidence, token_usage, image_size = self.model.predict(preprocessed_image)
        
        # Store token usage and image size in database if needed
        # For now, just return the original three values
        return main_category, subcategory, float(confidence)

    def preprocess_image(self, image):
        # image is now a PIL Image object
        img_array = np.array(image)
        # Use the CustomModel's preprocess_image method
        return self.model.preprocess_image(img_array)

    def learn_from_manual_categorization(self, image, main_category, subcategory):
        # Pass the learning task to the CustomModel
        self.model.learn_from_manual_categorization(image, main_category, subcategory)
