import os
from pathlib import Path
import psycopg
from datetime import datetime
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_DIR / ".env")

DB_TIMEZONE = datetime.now().astimezone().tzinfo
print(f"Using timezone: {DB_TIMEZONE}")

def get_db_connection():
    return psycopg.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=10,
    )

def init_db(drop=False):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if drop:
                cur.execute("DROP TABLE IF EXISTS conversations")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    course TEXT NOT NULL,
                    model TEXT NOT NULL,
                    instructions TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    response_time FLOAT NOT NULL,
                    cost FLOAT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
            # 对已存在的表补列，不删除或重建旧数据。
            cur.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS purpose TEXT NOT NULL DEFAULT 'qa_answer'")
            cur.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS session_id TEXT")
            cur.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS user_answer TEXT")
        conn.commit()

    finally:
        conn.close()


def init_feedback():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    conversation_id INTEGER REFERENCES conversations(id),
                    source TEXT NOT NULL,
                    relevance TEXT,
                    explanation TEXT,
                    score INTEGER,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
            # 旧反馈user_id保留NULL，避免合并或删除历史记录。
            cur.execute("ALTER TABLE feedback ADD COLUMN IF NOT EXISTS user_id TEXT")
            cur.execute("""CREATE UNIQUE INDEX IF NOT EXISTS feedback_user_vote
                           ON feedback (conversation_id, source, user_id)""")
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    init_feedback()
    print("Database initialized")
