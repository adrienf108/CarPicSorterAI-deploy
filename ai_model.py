import torch
import torchvision.transforms as transforms
from torchvision.models import resnet50, ResNet50_Weights
from PIL import Image
import io

class CarClassifier:
    def __init__(self):
        # Load pre-trained ResNet50 model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = resnet50(weights=ResNet50_Weights.DEFAULT)
        self.model.eval()
        self.model = self.model.to(self.device)

        # Load ImageNet class labels
        self.labels = []
        with open("imagenet_classes.txt", "r") as f:
            self.labels = [line.strip() for line in f.readlines()]

        # Define image transformations
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                              std=[0.229, 0.224, 0.225])
        ])

    def classify_image(self, image):
        """
        Classify an image using the pre-trained model.
        
        Args:
            image: PIL Image object
        
        Returns:
            dict: Classification results with probabilities
        """
        # Transform image
        img_tensor = self.transform(image).unsqueeze(0)
        img_tensor = img_tensor.to(self.device)

        # Get predictions
        with torch.no_grad():
            outputs = self.model(img_tensor)
            probabilities = torch.nn.functional.softmax(outputs[0], dim=0)

        # Get top 5 predictions
        top5_prob, top5_catid = torch.topk(probabilities, 5)
        
        results = []
        for i in range(5):
            results.append({
                'category': self.labels[top5_catid[i]],
                'probability': float(top5_prob[i]) * 100
            })

        return results

    @staticmethod
    def is_vehicle(category):
        """Check if the predicted category is related to vehicles"""
        vehicle_keywords = ['car', 'truck', 'van', 'bus', 'pickup', 'racer', 
                          'convertible', 'jeep', 'limousine', 'ambulance']
        return any(keyword in category.lower() for keyword in vehicle_keywords)
