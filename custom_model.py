import numpy as np
from PIL import Image

class CustomModel:
    def __init__(self):
        self.main_categories = ['Exterior', 'Interior', 'Engine', 'Undercarriage', 'Documents']
        self.subcategories = {
            'Exterior': ['3/4 front view', 'Side profile', '3/4 rear view', 'Rear view', 'Wheels', 'Details', 'Defects'],
            'Interior': ['Full interior view', 'Dashboard', 'Front seats', "Driver's seat", 'Rear seats', 'Steering wheel', 'Gear shift', 'Pedals and floor mats', 'Gauges/Instrument cluster', 'Details', 'Trunk/Boot'],
            'Engine': ['Full view', 'Detail'],
            'Undercarriage': ['Undercarriage'],
            'Documents': ['Invoices/Receipts', 'Service book', 'Technical inspections/MOT certificates']
        }
        self.confidence_threshold = 0.7

    def predict(self, preprocessed_image):
        # Simulate a prediction by returning a random category and subcategory
        main_category = np.random.choice(self.main_categories)
        subcategory = np.random.choice(self.subcategories[main_category])
        confidence = np.random.uniform(0.5, 1.0)
        
        if confidence < self.confidence_threshold:
            return 'Uncategorized', 'Uncategorized', confidence
        
        return main_category, subcategory, confidence

    def preprocess_image(self, image):
        # Resize the image to 224x224
        image = image.resize((224, 224))
        # Convert to numpy array and normalize
        image_array = np.array(image) / 255.0
        return image_array

    def learn_from_manual_categorization(self, image, main_category, subcategory):
        # Placeholder for future implementation
        pass
