from datetime import datetime
from init_db import get_db_connection, DB_TIMEZONE
from psycopg.types.json import Jsonb


def save_history(record, question, course, conversation_id=None, usage=None):
    timestamp = record.timestamp

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_history (
                    question, answer, course, purpose, chat_id, session_id, user_answer, timestamp,
                    conversation_id, usage_json
                ) VALUES(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    question,
                    record.answer,
                    course,
                    record.purpose,
                    record.chat_id,
                    record.session_id,
                    record.user_answer,
                    timestamp,
                    conversation_id,
                    Jsonb(usage) if usage is not None else None,
                ),
            )
            history_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    return history_id
