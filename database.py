import psycopg2
import os
import bcrypt
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

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
        self.conn.commit()

    def reset_all_tables(self):
        with self.conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS images")
            cur.execute("DROP TABLE IF EXISTS users")
        self.conn.commit()
        self.create_tables()

    def save_image(self, filename, image_data, category, subcategory, user_id, ai_confidence: float):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO images (filename, image_data, category, subcategory, ai_category, ai_subcategory, ai_confidence, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (filename, image_data, category, subcategory, category, subcategory, ai_confidence, user_id))
        self.conn.commit()

    def get_all_images(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, filename, image_data, category, subcategory, ai_category, ai_subcategory, ai_confidence, user_id 
                FROM images
            """)
            return [
                {
                    'id': row[0],
                    'filename': row[1],
                    'image_data': row[2],
                    'category': row[3],
                    'subcategory': row[4],
                    'ai_category': row[5],
                    'ai_subcategory': row[6],
                    'ai_confidence': row[7],
                    'user_id': row[8]
                }
                for row in cur.fetchall()
            ]

    def update_categorization(self, image_id, new_category, new_subcategory):
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE images
                SET category = %s, subcategory = %s
                WHERE id = %s
            """, (new_category, new_subcategory, image_id))
        self.conn.commit()

    def get_statistics(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM images")
            total_images = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*) FROM images
                WHERE category = ai_category AND subcategory = ai_subcategory
            """)
            correct_predictions = cur.fetchone()[0]
            accuracy = (correct_predictions / total_images) * 100 if total_images > 0 else 0

            cur.execute("""
                SELECT category, COUNT(*) as count
                FROM images
                GROUP BY category
                ORDER BY count DESC
            """)
            category_distribution = [{'category': row[0], 'count': row[1]} for row in cur.fetchall()]

            cur.execute("""
                SELECT DATE(created_at) as date,
                       AVG(CASE WHEN category = ai_category AND subcategory = ai_subcategory THEN 1 ELSE 0 END) * 100 as accuracy
                FROM images
                GROUP BY DATE(created_at)
                ORDER BY date
            """)
            accuracy_over_time = [{'date': row[0], 'accuracy': row[1]} for row in cur.fetchall()]

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

            cur.execute("""
                SELECT ai_confidence
                FROM images
            """)
            confidence_distribution = [{'confidence': row[0]} for row in cur.fetchall()]

        return {
            'total_images': total_images,
            'accuracy': accuracy,
            'category_distribution': category_distribution,
            'accuracy_over_time': accuracy_over_time,
            'confusion_matrix': confusion_matrix.tolist(),
            'confusion_categories': categories,
            'top_misclassifications': top_misclassifications,
            'confidence_distribution': confidence_distribution
        }

    def create_user(self, username, password, role='user'):
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
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

    def get_user_by_username(self, username):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
        return user if user else None

    def update_user_role(self, user_id, new_role):
        with self.conn.cursor() as cur:
            cur.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        self.conn.commit()

    def get_all_users(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, username, role FROM users")
            return [{'id': row[0], 'username': row[1], 'role': row[2]} for row in cur.fetchall()]

if __name__ == "__main__":
    db = Database()
    db.reset_all_tables()
