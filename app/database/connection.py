
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "code_review_db")
        )

        return connection

    except mysql.connector.Error as error:
        print(f"MySQL Connection Error: {error}")
        raise


def create_reviews_table():
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_reviews (

                id INT AUTO_INCREMENT PRIMARY KEY,

                language VARCHAR(100) NOT NULL,

                source_code LONGTEXT NOT NULL,

                overall_score DECIMAL(5,2),

                review_result JSON NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                INDEX idx_review_language (language),

                INDEX idx_review_created_at (created_at)

            )
        """)

        connection.commit()

        print("Code reviews table is ready.")

    finally:
        cursor.close()
        connection.close()


def create_fix_history_table():
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_fix_history (

                id INT AUTO_INCREMENT PRIMARY KEY,

                language VARCHAR(100) NOT NULL,

                original_code LONGTEXT NOT NULL,

                fixed_code LONGTEXT NOT NULL,

                decision VARCHAR(50) NOT NULL,

                source VARCHAR(100),

                model_used VARCHAR(150),

                fix_result JSON NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                INDEX idx_fix_language (language),

                INDEX idx_fix_decision (decision),

                INDEX idx_fix_created_at (created_at)

            )
        """)

        connection.commit()

        print("Code fix history table is ready.")

    finally:
        cursor.close()
        connection.close()


def create_all_tables():
    create_reviews_table()
    create_fix_history_table()

    print("All application database tables are ready.")
