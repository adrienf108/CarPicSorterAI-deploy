import psycopg2
import os
import bcrypt
from datetime import datetime, timedelta

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

    def save_image(self, filename, image_data, category, subcategory, user_id):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO images (filename, image_data, category, subcategory, ai_category, ai_subcategory, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (filename, image_data, category, subcategory, category, subcategory, user_id))
        self.conn.commit()

    def get_all_images(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, filename, image_data, category, subcategory, user_id FROM images")
            return [
                {
                    'id': row[0],
                    'filename': row[1],
                    'image_data': row[2],
                    'category': row[3],
                    'subcategory': row[4],
                    'user_id': row[5]
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
            result = cur.fetchone()
            total_images = result[0] if result else 0

            cur.execute("""
                SELECT COUNT(*) FROM images
                WHERE category = ai_category AND subcategory = ai_subcategory
            """)
            result = cur.fetchone()
            correct_predictions = result[0] if result else 0

            accuracy = (correct_predictions / total_images) * 100 if total_images > 0 else 0

            cur.execute("""
                SELECT category, COUNT(*) as count
                FROM images
                GROUP BY category
                ORDER BY count DESC
            """)
            category_distribution = [{'category': row[0], 'count': row[1]} for row in cur.fetchall()]

        return {
            'total_images': total_images,
            'accuracy': accuracy,
            'category_distribution': category_distribution
        }

    def get_accuracy_over_time(self, days=30):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT DATE(created_at) as date,
                       COUNT(*) FILTER (WHERE category = ai_category AND subcategory = ai_subcategory) as correct,
                       COUNT(*) as total
                FROM images
                WHERE created_at >= %s
                GROUP BY DATE(created_at)
                ORDER BY DATE(created_at)
            """, (datetime.now() - timedelta(days=days),))
            return [{'date': row[0], 'accuracy': (row[1] / row[2]) * 100 if row[2] > 0 else 0} for row in cur.fetchall()]

    def get_confusion_matrix(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT ai_category, category, COUNT(*)
                FROM images
                GROUP BY ai_category, category
            """)
            return [{'ai_category': row[0], 'true_category': row[1], 'count': row[2]} for row in cur.fetchall()]

    def get_top_misclassifications(self, limit=10):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT ai_category, category, COUNT(*) as count
                FROM images
                WHERE ai_category != category
                GROUP BY ai_category, category
                ORDER BY count DESC
                LIMIT %s
            """, (limit,))
            return [{'ai_category': row[0], 'true_category': row[1], 'count': row[2]} for row in cur.fetchall()]

    def get_performance_by_category(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT category,
                       COUNT(*) FILTER (WHERE category = ai_category) as correct,
                       COUNT(*) as total
                FROM images
                GROUP BY category
            """)
            return [{'category': row[0], 'accuracy': (row[1] / row[2]) * 100 if row[2] > 0 else 0, 'total': row[2]} for row in cur.fetchall()]

    def get_user_activity(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT u.username, COUNT(i.id) as image_count
                FROM users u
                LEFT JOIN images i ON u.id = i.user_id
                GROUP BY u.id, u.username
                ORDER BY image_count DESC
            """)
            return [{'username': row[0], 'image_count': row[1]} for row in cur.fetchall()]

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
