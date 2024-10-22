from custom_model import CustomModel
from PIL import Image

class AIModel:
    def __init__(self):
        self.model = CustomModel()

    def predict(self, image):
        # image is a PIL Image object
        preprocessed_image = self.preprocess_image(image)
        
        # Get predictions
        main_category, subcategory, confidence = self.model.predict(preprocessed_image)
        
        return main_category, subcategory, float(confidence)

    def preprocess_image(self, image):
        # Use the CustomModel's preprocess_image method
        return self.model.preprocess_image(image)

    def learn_from_manual_categorization(self, image, main_category, subcategory):
        # Pass the learning task to the CustomModel
        self.model.learn_from_manual_categorization(image, main_category, subcategory)
