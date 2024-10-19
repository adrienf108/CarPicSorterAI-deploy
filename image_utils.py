from PIL import Image
import io
import base64

def resize_image(image, max_size=(300, 300)):
    """Resize an image while maintaining aspect ratio"""
    image.thumbnail(max_size)
    return image

def image_to_base64(image):
    """Convert a PIL Image to a base64 encoded string"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

