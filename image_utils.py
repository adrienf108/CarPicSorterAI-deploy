from PIL import Image
import io
import base64
import logging

logger = logging.getLogger(__name__)

def optimize_image(image, max_dimension=1920, quality=85, convert_to_webp=False):
    """
    Optimize image by:
    1. Resizing if larger than max dimension while maintaining aspect ratio
    2. Converting to RGB mode
    3. Applying JPEG/WebP compression with quality setting
    """
    try:
        # Convert to RGB mode if necessary
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')

        # Calculate new dimensions maintaining aspect ratio
        width, height = image.size
        if width > max_dimension or height > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height}")

        # Save optimized image to buffer
        buffered = io.BytesIO()
        if convert_to_webp:
            image.save(buffered, format="WebP", quality=quality, method=4)
        else:
            image.save(buffered, format="JPEG", quality=quality, optimize=True)
        
        size_kb = len(buffered.getvalue()) / 1024
        logger.info(f"Optimized image size: {size_kb:.2f}KB")
        
        return buffered.getvalue()
    except Exception as e:
        logger.error(f"Error optimizing image: {str(e)}")
        return None

def resize_image(image, size=(224, 224)):
    """Resize image while maintaining aspect ratio"""
    return image.resize(size, Image.Resampling.LANCZOS)

def image_to_base64(image, optimize=True):
    """Convert a PIL Image to a base64 encoded string with optimization"""
    try:
        if optimize:
            optimized_bytes = optimize_image(image)
            if optimized_bytes:
                return base64.b64encode(optimized_bytes).decode()
        
        # Fallback to original method if optimization fails
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        logger.error(f"Error converting image to base64: {str(e)}")
        return None
