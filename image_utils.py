from PIL import Image
import io
import base64

def resize_image(image, size=(224, 224)):
    return image.resize(size, Image.LANCZOS)

def compress_image(image, max_size_mb=1):
    '''Compress image while maintaining quality'''
    # Convert to RGB if necessary
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Start with quality=85
    quality = 85
    buffered = io.BytesIO()
    
    # Save with compression
    image.save(buffered, format='JPEG', quality=quality, optimize=True)
    
    # Reduce quality until file size is under max_size_mb
    while buffered.tell() > max_size_mb * 1024 * 1024 and quality > 20:
        quality -= 5
        buffered = io.BytesIO()
        image.save(buffered, format='JPEG', quality=quality, optimize=True)
    
    return Image.open(buffered)

def image_to_base64(image):
    """Convert a PIL Image to a base64 encoded string"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()
