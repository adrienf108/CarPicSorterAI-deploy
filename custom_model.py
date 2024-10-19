import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.models import Model

class CustomModel:
    def __init__(self):
        # Define the main categories and subcategories
        self.main_categories = ['Exterior', 'Interior', 'Engine', 'Undercarriage', 'Documents']
        self.subcategories = {
            'Exterior': ['3/4 front view', 'Side profile', '3/4 rear view', 'Rear view', 'Wheels', 'Details', 'Defects'],
            'Interior': ['Full interior view', 'Dashboard', 'Front seats', "Driver's seat", 'Rear seats', 'Steering wheel', 'Gear shift', 'Pedals and floor mats', 'Gauges/Instrument cluster', 'Details', 'Trunk/Boot'],
            'Engine': ['Full view', 'Detail'],
            'Undercarriage': ['Undercarriage'],
            'Documents': ['Invoices/Receipts', 'Service book', 'Technical inspections/MOT certificates']
        }
        
        # Set confidence threshold
        self.confidence_threshold = 0.7
        
        # Create the model
        self.model = self._create_model()
    
    def _create_model(self):
        # Use MobileNetV2 as the base model
        base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
        
        # Add custom layers
        x = GlobalAveragePooling2D()(base_model.output)
        main_output = Dense(len(self.main_categories), activation='softmax', name='main_category')(x)
        subcategory_output = Dense(max(len(subcats) for subcats in self.subcategories.values()), activation='softmax', name='subcategory')(x)
        
        model = Model(inputs=base_model.input, outputs=[main_output, subcategory_output])
        
        # Compile the model
        model.compile(optimizer='adam',
                      loss={'main_category': 'categorical_crossentropy', 'subcategory': 'categorical_crossentropy'},
                      loss_weights={'main_category': 1.0, 'subcategory': 1.0},
                      metrics=['accuracy'])
        
        return model
    
    def predict(self, preprocessed_image):
        # Make predictions
        main_pred, subcategory_pred = self.model.predict(preprocessed_image)
        
        # Get the main category and its confidence
        main_category_index = tf.argmax(main_pred[0]).numpy()
        main_category_confidence = tf.reduce_max(main_pred[0]).numpy()
        
        if main_category_confidence < self.confidence_threshold:
            return 'Uncategorized', 'Uncategorized', main_category_confidence
        
        main_category = self.main_categories[main_category_index]
        
        # Get the subcategory
        subcategory_index = tf.argmax(subcategory_pred[0]).numpy()
        subcategory = self.subcategories[main_category][subcategory_index % len(self.subcategories[main_category])]
        
        return main_category, subcategory, main_category_confidence

    def preprocess_image(self, image):
        # Resize the image to 224x224
        image = tf.image.resize(image, (224, 224))
        # Normalize the image
        image = image / 255.0
        # Add batch dimension
        image = tf.expand_dims(image, 0)
        return image

    def learn_from_manual_categorization(self, image, main_category, subcategory):
        # This is a placeholder for future implementation of learning from manual categorizations
        # In a real-world scenario, you would update the model based on this new information
        pass
