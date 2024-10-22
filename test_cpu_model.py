from ai_model import AIModel
from PIL import Image

def main():
    print("Initializing AIModel...")
    model = AIModel()
    
    print("Creating dummy image...")
    dummy_image = Image.new('RGB', (224, 224), color='red')
    
    print("Making prediction...")
    main_category, subcategory, confidence = model.predict(dummy_image)
    
    print(f"Prediction results:")
    print(f"Main category: {main_category}")
    print(f"Subcategory: {subcategory}")
    print(f"Confidence: {confidence}")

if __name__ == "__main__":
    main()
