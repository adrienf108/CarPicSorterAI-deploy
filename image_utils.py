from PIL import Image
import io
import base64

def resize_image(image, size=(224, 224)):
    return image.resize(size, Image.LANCZOS)

def resize_and_compress_image(image, max_size=(800, 800), quality=85):
    # Resize if image is larger than max_size
    if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
        image.thumbnail(max_size, Image.LANCZOS)
    
    # Convert to RGB if necessary
    if image.mode in ('RGBA', 'P'):
        image = image.convert('RGB')
    
    # Save with compression
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=quality, optimize=True)
    return buffered.getvalue()

def image_to_base64(image):
    """Convert a PIL Image to a base64 encoded string"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()
