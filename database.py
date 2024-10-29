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
        """Create necessary database tables if they don't exist"""
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
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    token_usage INTEGER,
                    image_size INTEGER
                )
            ''')
            
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

    def clear_previous_uploads(self, user_id):
        """Clear all previous uploads for a user when starting a new session"""
        try:
            with self.conn.cursor() as cur:
                # Begin transaction
                cur.execute("BEGIN")
                
                # Get IDs of images to be deleted
                cur.execute("""
                    SELECT id, filename
                    FROM images 
                    WHERE user_id = %s
                """, (user_id,))
                images_to_delete = cur.fetchall()
                
                # Delete from images table
                cur.execute("""
                    DELETE FROM images 
                    WHERE user_id = %s
                """, (user_id,))
                
                # Clean up orphaned token_usage entries
                cur.execute("""
                    DELETE FROM token_usage
                    WHERE date < CURRENT_DATE
                    AND NOT EXISTS (
                        SELECT 1
                        FROM images
                        WHERE DATE(images.created_at) = token_usage.date
                    )
                """)
                
                # Commit transaction
                self.conn.commit()
                
                deleted_count = len(images_to_delete)
                logger.info(f"Cleared {deleted_count} previous uploads for user {user_id}")
                
                # Log detailed information about deleted images
                for img_id, filename in images_to_delete:
                    logger.info(f"Deleted image ID {img_id}: {filename}")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error clearing previous uploads: {str(e)}")
            self.conn.rollback()
            return 0
        finally:
            # Ensure connection is still valid
            if self.conn.closed:
                self.conn = psycopg2.connect(
                    host=os.environ['PGHOST'],
                    database=os.environ['PGDATABASE'],
                    user=os.environ['PGUSER'],
                    password=os.environ['PGPASSWORD'],
                    port=os.environ['PGPORT']
                )

    def __del__(self):
        """Ensure proper cleanup of database connection"""
        try:
            if hasattr(self, 'conn') and self.conn and not self.conn.closed:
                self.conn.close()
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")

    def get_user_by_username(self, username):
        try:
            with self.conn.cursor() as cur:
                cur.execute('''
                    SELECT id, username, password_hash, role 
                    FROM users 
                    WHERE username = %s
                ''', (username,))
                result = cur.fetchone()
                return result if result else None
        except Exception as e:
            logger.error(f"Error getting user by username: {str(e)}")
            return None

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
                old_deleted = cur.fetchall() or []
                
                # Calculate total size
                cur.execute("SELECT COALESCE(SUM(image_size), 0) FROM images")
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
                    size_deleted = cur.fetchall() or []
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

    def save_image(self, filename, image_data, category, subcategory, user_id, ai_confidence: float, token_usage: int = 0, image_size: int = 0):
        with self.conn.cursor() as cur:
            logger.info(f"Saving image {filename} with category: {category} - {subcategory}")
            cur.execute('''
                INSERT INTO images (
                    filename, image_data, category, subcategory, 
                    ai_category, ai_subcategory, ai_confidence, 
                    user_id, token_usage, image_size
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (filename, image_data, category, subcategory, 
                  category, subcategory, ai_confidence, user_id, 
                  token_usage, image_size))
            
            # Update token usage statistics
            today = datetime.now().date()
            cur.execute("""
                INSERT INTO token_usage (date, total_tokens, total_images, total_size)
                VALUES (%s, %s, 1, %s)
                ON CONFLICT (date)
                DO UPDATE SET 
                    total_tokens = token_usage.total_tokens + %s,
                    total_images = token_usage.total_images + 1,
                    total_size = token_usage.total_size + %s
            """, (today, token_usage, image_size, token_usage, image_size))
        self.conn.commit()

    def get_all_images(self):
        with self.conn.cursor() as cur:
            cur.execute('''
                SELECT id, filename, image_data, category, subcategory, user_id
                FROM images
                ORDER BY created_at DESC
            ''')
            results = cur.fetchall() or []
            logger.info(f"Retrieved {len(results)} images from database")
            return [{
                'id': row[0],
                'filename': row[1],
                'image_data': row[2],
                'category': row[3],
                'subcategory': row[4],
                'user_id': row[5]
            } for row in results]

    def update_categorization(self, image_id, new_category, new_subcategory):
        with self.conn.cursor() as cur:
            logger.info(f"Updating image {image_id} with new categories: {new_category} - {new_subcategory}")
            cur.execute("""
                UPDATE images
                SET category = %s, subcategory = %s
                WHERE id = %s
            """, (new_category, new_subcategory, image_id))
        self.conn.commit()

    def get_statistics(self):
        with self.conn.cursor() as cur:
            # Get total images count
            cur.execute("SELECT COALESCE(COUNT(*), 0) FROM images")
            total_images = cur.fetchone()[0]

            # Get correct predictions count
            cur.execute("""
                SELECT COALESCE(COUNT(*), 0) FROM images
                WHERE category = ai_category AND subcategory = ai_subcategory
            """)
            correct_predictions = cur.fetchone()[0]
            accuracy = (correct_predictions / total_images * 100) if total_images > 0 else 0

            # Get category distribution
            cur.execute("""
                SELECT category, COUNT(*) as count
                FROM images
                GROUP BY category
                ORDER BY count DESC
            """)
            category_distribution = [{'category': row[0], 'count': row[1]} for row in cur.fetchall() or []]

            # Get accuracy over time
            cur.execute("""
                SELECT DATE(created_at) as date,
                       AVG(CASE WHEN category = ai_category AND subcategory = ai_subcategory THEN 1 ELSE 0 END) * 100 as accuracy
                FROM images
                GROUP BY DATE(created_at)
                ORDER BY date
            """)
            accuracy_over_time = [{'date': row[0], 'accuracy': row[1]} for row in cur.fetchall() or []]

            # Get confusion matrix data
            cur.execute("""
                SELECT ai_category, category, COUNT(*)
                FROM images
                GROUP BY ai_category, category
            """)
            confusion_data = cur.fetchall() or []
            categories = sorted(set(row[0] for row in confusion_data) | set(row[1] for row in confusion_data))
            confusion_matrix = np.zeros((len(categories), len(categories)), dtype=int)
            category_to_index = {cat: i for i, cat in enumerate(categories)}
            
            for ai_cat, true_cat, count in confusion_data:
                i = category_to_index[true_cat]
                j = category_to_index[ai_cat]
                confusion_matrix[i, j] = count

            # Get top misclassifications
            cur.execute("""
                SELECT ai_category, category, COUNT(*) as count
                FROM images
                WHERE ai_category != category
                GROUP BY ai_category, category
                ORDER BY count DESC
                LIMIT 10
            """)
            top_misclassifications = [
                {'Predicted': row[0], 'Actual': row[1], 'Count': row[2]}
                for row in cur.fetchall() or []
            ]

            # Get confidence distribution
            cur.execute("""
                SELECT ai_confidence
                FROM images
            """)
            confidence_distribution = [{'confidence': row[0]} for row in cur.fetchall() or []]

            # Get token usage statistics
            token_stats = self.get_token_usage_stats()

            return {
                'total_images': total_images,
                'accuracy': accuracy,
                'category_distribution': category_distribution,
                'accuracy_over_time': accuracy_over_time,
                'confusion_matrix': confusion_matrix.tolist(),
                'confusion_categories': categories,
                'top_misclassifications': top_misclassifications,
                'confidence_distribution': confidence_distribution,
                'token_usage': token_stats
            }

    def get_token_usage_stats(self):
        with self.conn.cursor() as cur:
            # Get total token usage
            cur.execute("SELECT COALESCE(SUM(total_tokens), 0) FROM token_usage")
            total_tokens = cur.fetchone()[0]

            # Get token usage over time
            cur.execute("""
                SELECT date, total_tokens, total_images, total_size
                FROM token_usage
                ORDER BY date
            """)
            usage_over_time = [
                {
                    'date': row[0],
                    'tokens': row[1],
                    'images': row[2],
                    'size': row[3]
                }
                for row in cur.fetchall() or []
            ]

            # Get average tokens per image
            cur.execute("""
                SELECT COALESCE(SUM(total_tokens)::float / NULLIF(SUM(total_images), 0), 0)
                FROM token_usage
            """)
            avg_tokens_per_image = cur.fetchone()[0]

            return {
                'total_tokens': total_tokens,
                'usage_over_time': usage_over_time,
                'avg_tokens_per_image': avg_tokens_per_image
            }

    def create_user(self, username, password, role='user'):
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (username, password_hash, role)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (username, hashed_password.decode('utf-8'), role))
                result = cur.fetchone()
                user_id = result[0] if result else None
                self.conn.commit()
                return user_id
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            self.conn.rollback()
            return None

    def update_user_role(self, user_id, new_role):
        with self.conn.cursor() as cur:
            cur.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        self.conn.commit()

    def get_all_users(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, username, role FROM users")
            results = cur.fetchall() or []
            return [{'id': row[0], 'username': row[1], 'role': row[2]} for row in results]
