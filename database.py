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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add token_usage and image_size columns if they don't exist
            cur.execute('ALTER TABLE images ADD COLUMN IF NOT EXISTS token_usage INTEGER')
            cur.execute('ALTER TABLE images ADD COLUMN IF NOT EXISTS image_size INTEGER')
            
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

    def get_token_usage_stats(self):
        with self.conn.cursor() as cur:
            # Get total token usage
            cur.execute("SELECT COALESCE(SUM(total_tokens), 0) FROM token_usage")
            result = cur.fetchone()
            total_tokens = result[0] if result else 0

            # Get token usage over time
            cur.execute("""
                SELECT date, total_tokens, total_images, total_size
                FROM token_usage
                ORDER BY date
            """)
            results = cur.fetchall()
            usage_over_time = [
                {
                    'date': row[0],
                    'tokens': row[1],
                    'images': row[2],
                    'size': row[3]
                }
                for row in results
            ] if results else []

            # Get average tokens per image
            cur.execute("""
                SELECT 
                    COALESCE(SUM(total_tokens)::float / NULLIF(SUM(total_images), 0), 0)
                FROM token_usage
            """)
            result = cur.fetchone()
            avg_tokens_per_image = result[0] if result else 0

            return {
                'total_tokens': total_tokens,
                'usage_over_time': usage_over_time,
                'avg_tokens_per_image': avg_tokens_per_image
            }

    def get_statistics(self):
        try:
            with self.conn.cursor() as cur:
                # Get total images count
                cur.execute("SELECT COUNT(*) FROM images")
                result = cur.fetchone()
                total_images = result[0] if result else 0
                logger.info(f"Total images count: {total_images}")

                # Get correct predictions count
                cur.execute("""
                    SELECT COUNT(*) FROM images
                    WHERE category = ai_category AND subcategory = ai_subcategory
                """)
                result = cur.fetchone()
                correct_predictions = result[0] if result else 0
                accuracy = (correct_predictions / total_images * 100) if total_images > 0 else 0
                logger.info(f"Accuracy: {accuracy:.2f}%")

                # Get category distribution
                cur.execute("""
                    SELECT category, COUNT(*) as count
                    FROM images
                    GROUP BY category
                    ORDER BY count DESC
                """)
                category_distribution = [{'category': row[0], 'count': row[1]} for row in cur.fetchall()]
                logger.info(f"Retrieved category distribution for {len(category_distribution)} categories")

                # Get accuracy over time
                cur.execute("""
                    SELECT DATE(created_at) as date,
                           AVG(CASE WHEN category = ai_category AND subcategory = ai_subcategory THEN 1 ELSE 0 END) * 100 as accuracy
                    FROM images
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """)
                accuracy_over_time = [{'date': row[0], 'accuracy': row[1]} for row in cur.fetchall()]
                logger.info(f"Retrieved accuracy data for {len(accuracy_over_time)} days")

                # Get confusion matrix data
                cur.execute("""
                    SELECT ai_category, category, COUNT(*)
                    FROM images
                    GROUP BY ai_category, category
                """)
                confusion_data = cur.fetchall()
                categories = sorted(set(row[0] for row in confusion_data) | set(row[1] for row in confusion_data))
                confusion_matrix = np.zeros((len(categories), len(categories)), dtype=int)
                category_to_index = {cat: i for i, cat in enumerate(categories)}
                
                for ai_cat, true_cat, count in confusion_data:
                    i = category_to_index[true_cat]
                    j = category_to_index[ai_cat]
                    confusion_matrix[i, j] = count
                logger.info(f"Created confusion matrix with {len(categories)} categories")

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
                    for row in cur.fetchall()
                ]
                logger.info(f"Retrieved {len(top_misclassifications)} top misclassifications")

                # Get confidence distribution
                cur.execute("SELECT ai_confidence FROM images")
                confidence_distribution = [{'confidence': row[0]} for row in cur.fetchall()]
                logger.info(f"Retrieved confidence scores for {len(confidence_distribution)} images")

                # Get token usage statistics
                token_stats = self.get_token_usage_stats()
                logger.info("Retrieved token usage statistics")

                return {
                    'total_images': total_images,
                    'accuracy': accuracy,
                    'category_distribution': category_distribution,
                    'accuracy_over_time': accuracy_over_time,
                    'confusion_matrix': confusion_matrix.tolist() if isinstance(confusion_matrix, np.ndarray) else [],
                    'confusion_categories': categories,
                    'top_misclassifications': top_misclassifications,
                    'confidence_distribution': confidence_distribution,
                    'token_usage': token_stats
                }
        except Exception as e:
            logger.error(f"Error in get_statistics: {str(e)}")
            return {
                'total_images': 0,
                'accuracy': 0,
                'category_distribution': [],
                'accuracy_over_time': [],
                'confusion_matrix': [],
                'confusion_categories': [],
                'top_misclassifications': [],
                'confidence_distribution': [],
                'token_usage': {
                    'total_tokens': 0,
                    'avg_tokens_per_image': 0,
                    'usage_over_time': []
                }
            }
