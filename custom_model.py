import base64
import json
import anthropic
from PIL import Image
import io
import os

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
        
        # Initialize Anthropic client with API key from environment
        self.client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

    def _format_prompt(self):
        """Create a structured prompt for image classification."""
        categories_str = json.dumps(self.main_categories, indent=2)
        subcategories_str = json.dumps(self.subcategories, indent=2)
        
        return f"""Please analyze this car image and classify it according to these categories and subcategories:

Main Categories:
{categories_str}

Subcategories for each main category:
{subcategories_str}

Please respond with ONLY a JSON object in this exact format:
{{
    "main_category": "category_name",
    "subcategory": "subcategory_name",
    "confidence": confidence_score
}}

Where confidence_score is a number between 0 and 1. If you're not confident about the classification (confidence < 0.7), use:
{{
    "main_category": "Uncategorized",
    "subcategory": "Uncategorized",
    "confidence": confidence_score
}}"""

    def _image_to_base64(self, image):
        """Convert PIL Image to base64 string."""
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def predict(self, image):
        """Predict the category and subcategory of an image using Anthropic's Claude."""
        try:
            # Convert image to base64
            image_base64 = self._image_to_base64(image)
            
            # Create the message with the image
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": self._format_prompt()
                        }
                    ]
                }]
            )
            
            # Get token usage and image size
            token_usage = message.usage.output_tokens
            image_size = len(image_base64)

            # Get the text content from the response
            response_text = message.content[0].text
            
            # Parse the response
            try:
                result = json.loads(response_text)
                if isinstance(result, dict) and all(k in result for k in ['main_category', 'subcategory', 'confidence']):
                    # Validate the main category and subcategory
                    main_category = result['main_category']
                    subcategory = result['subcategory']
                    confidence = float(result['confidence'])
                    
                    # Check if the categories are valid
                    if main_category not in self.main_categories + ['Uncategorized']:
                        return 'Uncategorized', 'Uncategorized', 0.0, token_usage, image_size
                    
                    if main_category != 'Uncategorized' and subcategory not in self.subcategories[main_category]:
                        return 'Uncategorized', 'Uncategorized', 0.0, token_usage, image_size
                    
                    return main_category, subcategory, confidence, token_usage, image_size
                
                return 'Uncategorized', 'Uncategorized', 0.0, token_usage, image_size
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Error parsing response: {str(e)}")
                return 'Uncategorized', 'Uncategorized', 0.0, token_usage, image_size

        except Exception as e:
            print(f"Error in prediction: {str(e)}")
            return 'Uncategorized', 'Uncategorized', 0.0, 0, 0

    def preprocess_image(self, image):
        """Convert numpy array to PIL Image."""
        return Image.fromarray(image)

    def learn_from_manual_categorization(self, image, main_category, subcategory):
        """Placeholder for future implementation of learning from manual categorizations."""
        pass
