import psycopg2
import os

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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    image_data TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT NOT NULL,
                    ai_category TEXT NOT NULL,
                    ai_subcategory TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL
                )
            """)
        self.conn.commit()

    def save_image(self, filename, image_data, category, subcategory):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO images (filename, image_data, category, subcategory, ai_category, ai_subcategory)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (filename, image_data, category, subcategory, category, subcategory))
        self.conn.commit()

    def get_all_images(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, filename, image_data, category, subcategory FROM images")
            return [
                {
                    'id': row[0],
                    'filename': row[1],
                    'image_data': row[2],
                    'category': row[3],
                    'subcategory': row[4]
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

        return {
            'total_images': total_images,
            'accuracy': accuracy,
            'category_distribution': category_distribution
        }

    def create_user(self, username, password, role):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (username, password, role)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (username, password, role))
            user_id = cur.fetchone()[0]
        self.conn.commit()
        return user_id

    def get_user(self, user_id):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, username, password, role FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if user:
                return {
                    'id': user[0],
                    'username': user[1],
                    'password': user[2],
                    'role': user[3]
                }
        return None

    def get_user_by_username(self, username):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, username, password, role FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            if user:
                return {
                    'id': user[0],
                    'username': user[1],
                    'password': user[2],
                    'role': user[3]
                }
        return None
