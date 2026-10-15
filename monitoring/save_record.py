from datetime import datetime
from init_db import get_db_connection, DB_TIMEZONE

def save_conversation(record, question, course):
    timestamp = record.timestamp

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations (
                    question, answer, course, model, instructions, prompt, 
                    prompt_tokens, completion_tokens, total_tokens, 
                    response_time, cost, timestamp,
                    purpose, session_id, user_answer
                ) VALUES(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                RETURNING id
                """,
                (
                    question,
                    record.answer,
                    course,
                    record.model,
                    record.instructions,
                    record.prompt,
                    record.prompt_tokens,
                    record.completion_tokens,
                    record.total_tokens,
                    record.response_time,
                    record.cost,
                    timestamp,
                    record.purpose,
                    record.session_id,
                    record.user_answer,
                ),
            )
            conversation_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    return conversation_id
