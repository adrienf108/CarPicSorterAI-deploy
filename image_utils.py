from PIL import Image
import io
import base64
import os
import shutil
from datetime import datetime, timedelta
import gc

def resize_image(image, size=(224, 224)):
    """Memory efficient image resizing"""
    try:
        resized = image.resize(size, Image.Resampling.LANCZOS)
        return resized
    finally:
        # Force garbage collection
        gc.collect()

def optimize_image(image, max_size=(800, 800), quality=80):
    """Optimize image size and quality for storage with memory management"""
    try:
        # Calculate aspect ratio
        aspect = image.width / image.height
        
        # Determine new size while maintaining aspect ratio
        if image.width > max_size[0] or image.height > max_size[1]:
            if aspect > 1:
                new_size = (max_size[0], int(max_size[0] / aspect))
            else:
                new_size = (int(max_size[1] * aspect), max_size[1])
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert RGBA to RGB if needed
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Optimize by reducing colors
        image = image.quantize(colors=256, method=2).convert('RGB')
        
        return image
    finally:
        # Force garbage collection
        gc.collect()

def image_to_base64(image):
    """Convert a PIL Image to a base64 encoded string with optimization"""
    try:
        # Optimize image before converting to base64
        optimized_image = optimize_image(image)
        buffered = io.BytesIO()
        optimized_image.save(buffered, format="JPEG", quality=80, optimize=True)
        # Get base64 string
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    finally:
        # Clear memory
        if 'optimized_image' in locals():
            del optimized_image
        if 'buffered' in locals():
            buffered.close()
        gc.collect()

def cleanup_temp_files(temp_dir="/tmp", max_age_minutes=15):
    """Aggressive cleanup of temporary files"""
    try:
        current_time = datetime.now()
        
        # Cleanup patterns
        temp_patterns = ('.partial', '.tmp', '.temp', '.pyc', '.pyo', '.pyd', '.log')
        cache_dirs = ('__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 
                     '.cache', '.streamlit')
        
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                if any(filename.endswith(pattern) for pattern in temp_patterns):
                    filepath = os.path.join(temp_dir, filename)
                    try:
                        if current_time - datetime.fromtimestamp(os.path.getmtime(filepath)) > timedelta(minutes=max_age_minutes):
                            os.remove(filepath)
                    except OSError:
                        continue

        # Clean up project directory
        for root, dirs, files in os.walk('.', topdown=True):
            # Skip .git and other system directories
            if '.git' in root or '.pythonlibs' in root:
                continue
                
            # Skip system directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in cache_dirs]
            
            # Remove cache directories
            for cache_dir in cache_dirs:
                if cache_dir in dirs:
                    try:
                        cache_path = os.path.join(root, cache_dir)
                        if os.path.exists(cache_path):
                            shutil.rmtree(cache_path)
                        dirs.remove(cache_dir)
                    except OSError:
                        continue
            
            # Remove temporary files
            for file in files:
                if any(file.endswith(pattern) for pattern in temp_patterns):
                    try:
                        file_path = os.path.join(root, file)
                        if current_time - datetime.fromtimestamp(os.path.getmtime(file_path)) > timedelta(minutes=max_age_minutes):
                            os.remove(file_path)
                    except OSError:
                        continue
        
        # Force garbage collection
        gc.collect()

    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
