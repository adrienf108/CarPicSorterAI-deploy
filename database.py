import psycopg2
import os
import bcrypt
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.environ['PGHOST'],
            database=os.environ['PGDATABASE'],
            user=os.environ['PGUSER'],
            password=os.environ['PGPASSWORD'],
            port=os.environ['PGPORT']
        )
        self.create_tables()

    def create_tables(self):
        with self.conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    image_data TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT NOT NULL,
                    ai_category TEXT NOT NULL,
                    ai_subcategory TEXT NOT NULL,
                    ai_confidence FLOAT NOT NULL,
                    user_id INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add token_usage and image_size columns if they don't exist
            cur.execute('ALTER TABLE images ADD COLUMN IF NOT EXISTS token_usage INTEGER')
            cur.execute('ALTER TABLE images ADD COLUMN IF NOT EXISTS image_size INTEGER')
            cur.execute('ALTER TABLE images ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS token_usage (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL UNIQUE,
                    total_tokens INTEGER NOT NULL,
                    total_images INTEGER NOT NULL,
                    total_size BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        self.conn.commit()

    def clear_old_uploads(self, days_threshold=30, size_threshold_mb=1000):
        """Clear uploads older than the specified threshold or when total size exceeds the limit"""
        try:
            with self.conn.cursor() as cur:
                # Delete old images
                cur.execute("""
                    DELETE FROM images 
                    WHERE created_at < NOW() - INTERVAL '%s days'
                    RETURNING id, filename
                """, (days_threshold,))
                old_deleted = cur.fetchall()
                
                # Calculate total size
                cur.execute("SELECT SUM(image_size) FROM images")
                total_size = cur.fetchone()[0] or 0
                total_size_mb = total_size / (1024 * 1024)  # Convert to MB
                
                # If still over threshold, delete least recently accessed images
                if total_size_mb > size_threshold_mb:
                    cur.execute("""
                        DELETE FROM images 
                        WHERE id IN (
                            SELECT id FROM images 
                            ORDER BY last_accessed ASC
                            LIMIT (
                                SELECT COUNT(*) / 2 
                                FROM images
                            )
                        )
                        RETURNING id, filename
                    """)
                    size_deleted = cur.fetchall()
                else:
                    size_deleted = []
                
                self.conn.commit()
                
                logger.info(f"Deleted {len(old_deleted)} old images and {len(size_deleted)} images due to size limit")
                return len(old_deleted) + len(size_deleted)
                
        except Exception as e:
            logger.error(f"Error clearing old uploads: {str(e)}")
            self.conn.rollback()
            return 0

    def update_last_accessed(self, image_id):
        """Update the last_accessed timestamp for an image"""
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE images 
                SET last_accessed = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (image_id,))
        self.conn.commit()

    # ... [rest of the Database class methods remain unchanged] ...
