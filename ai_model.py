from custom_model import CustomModel
from PIL import Image
import numpy as np

class AIModel:
    def __init__(self):
        self.model = CustomModel()

    def predict(self, image):
        # Preprocess the image
        preprocessed_image = self.preprocess_image(image)
        
        # Get predictions
        main_category, subcategory = self.model.predict(preprocessed_image)
        
        return main_category, subcategory

    def preprocess_image(self, image):
        # Convert PIL Image to numpy array
        img_array = np.array(image)
        # Use the CustomModel's preprocess_image method
        return self.model.preprocess_image(img_array)
