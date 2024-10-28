from PIL import Image
import io
import base64
import logging
import hashlib
import psycopg2
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def calculate_storage_usage():
    """Calculate current storage usage in the database"""
    try:
        conn = psycopg2.connect(
            host=os.environ['PGHOST'],
            database=os.environ['PGDATABASE'],
            user=os.environ['PGUSER'],
            password=os.environ['PGPASSWORD'],
            port=os.environ['PGPORT']
        )
        with conn.cursor() as cur:
            cur.execute("SELECT SUM(LENGTH(image_data)) FROM images")
            total_bytes = cur.fetchone()[0] or 0
            return total_bytes / (1024 * 1024)  # Convert to MB
    except Exception as e:
        logger.error(f"Error calculating storage usage: {str(e)}")
        return 0

def cleanup_old_images(days_threshold=30):
    """Remove images older than the specified threshold"""
    try:
        conn = psycopg2.connect(
            host=os.environ['PGHOST'],
            database=os.environ['PGDATABASE'],
            user=os.environ['PGUSER'],
            password=os.environ['PGPASSWORD'],
            port=os.environ['PGPORT']
        )
        with conn.cursor() as cur:
            threshold_date = datetime.now() - timedelta(days=days_threshold)
            cur.execute(
                "DELETE FROM images WHERE created_at < %s RETURNING id",
                (threshold_date,)
            )
            deleted_count = cur.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted_count} old images")
            return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up old images: {str(e)}")
        return 0

def optimize_image(image, max_dimension=1200, quality=75, convert_to_webp=True):
    """
    Aggressively optimize image by:
    1. Resizing to smaller max dimension
    2. Converting to WebP format
    3. Using higher compression
    4. Applying additional optimization techniques
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
            # WebP format typically provides better compression
            image.save(buffered, format="WebP", quality=quality, method=6, lossless=False)
        else:
            # JPEG with aggressive optimization
            image.save(buffered, format="JPEG", quality=quality, optimize=True,
                      progressive=True, subsampling='4:2:0')
        
        size_kb = len(buffered.getvalue()) / 1024
        logger.info(f"Optimized image size: {size_kb:.2f}KB")
        
        return buffered.getvalue()
    except Exception as e:
        logger.error(f"Error optimizing image: {str(e)}")
        return None

def calculate_image_hash(image_data):
    """Calculate SHA-256 hash of image data for deduplication"""
    return hashlib.sha256(image_data).hexdigest()

def is_duplicate_image(image_data):
    """Check if image is a duplicate based on its hash"""
    try:
        conn = psycopg2.connect(
            host=os.environ['PGHOST'],
            database=os.environ['PGDATABASE'],
            user=os.environ['PGUSER'],
            password=os.environ['PGPASSWORD'],
            port=os.environ['PGPORT']
        )
        image_hash = calculate_image_hash(image_data)
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM images WHERE MD5(image_data) = %s", (image_hash,))
            return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking for duplicate image: {str(e)}")
        return False

def image_to_base64(image, optimize=True):
    """Convert a PIL Image to a base64 encoded string with optimization"""
    try:
        # Check current storage usage
        current_usage_mb = calculate_storage_usage()
        logger.info(f"Current storage usage: {current_usage_mb:.2f}MB")
        
        # If storage is high, trigger cleanup of old images
        if current_usage_mb > 900:  # 90% of 1GB
            cleanup_old_images()
        
        if optimize:
            optimized_bytes = optimize_image(image)
            if optimized_bytes:
                # Check for duplicates before proceeding
                if is_duplicate_image(optimized_bytes):
                    logger.info("Duplicate image detected, skipping")
                    return None
                return base64.b64encode(optimized_bytes).decode()
        
        # Fallback to original method if optimization fails
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=75, optimize=True)
        return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        logger.error(f"Error converting image to base64: {str(e)}")
        return None

def vacuum_database():
    """Perform database vacuum to reclaim storage"""
    try:
        conn = psycopg2.connect(
            host=os.environ['PGHOST'],
            database=os.environ['PGDATABASE'],
            user=os.environ['PGUSER'],
            password=os.environ['PGPASSWORD'],
            port=os.environ['PGPORT']
        )
        # Disable autocommit for VACUUM
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("VACUUM FULL ANALYZE images")
        logger.info("Database vacuum completed successfully")
    except Exception as e:
        logger.error(f"Error performing database vacuum: {str(e)}")

# Initialize database table for storing image hashes if it doesn't exist
try:
    conn = psycopg2.connect(
        host=os.environ['PGHOST'],
        database=os.environ['PGDATABASE'],
        user=os.environ['PGUSER'],
        password=os.environ['PGPASSWORD'],
        port=os.environ['PGPORT']
    )
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS image_hashes (
                id SERIAL PRIMARY KEY,
                image_hash TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
except Exception as e:
    logger.error(f"Error initializing image_hashes table: {str(e)}")
