from dataclasses import dataclass

from init_db import get_db_connection
from call_record import LLMCallRecord

@dataclass
class Stats:
    total: int
    avg_response_time: float
    total_cost: float
    avg_tokens: float

def row_to_record(row):
    return LLMCallRecord(
        model=row[4],
        prompt=row[6],
        instructions=row[5],
        answer=row[2],
        prompt_tokens=row[7],
        completion_tokens=row[8],
        total_tokens=row[9],
        response_time=row[10],
        cost=row[11],
        timestamp=row[12],
        id=row[0],
        question=row[1],
        course=row[3],
        purpose=row[13],
        session_id=row[14],
        user_answer=row[15],
    )

def get_conversations(limit=10):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, question, answer, course, model,
                instructions, prompt, 
                prompt_tokens, completion_tokens, total_tokens,
                response_time, cost, timestamp,
                purpose, session_id, user_answer
                FROM conversations
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [row_to_record(row) for row in rows]

def get_chat_list(limit=100):
    """以每段聊天最早保存的一条用户提问作标题，最近活动的聊天在前。"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH chats AS (
                    SELECT chat_id, MIN(id) AS first_id,
                           MAX(timestamp) AS updated_at, COUNT(*) AS turns
                    FROM chat_history
                    WHERE chat_id IS NOT NULL AND purpose = 'qa_answer'
                    GROUP BY chat_id
                )
                SELECT c.chat_id, h.question, c.updated_at, c.turns
                FROM chats c JOIN chat_history h ON h.id = c.first_id
                ORDER BY c.updated_at DESC, c.first_id DESC
                LIMIT %s
                """, (limit,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(zip(['chat_id', 'title', 'updated_at', 'turns'], row)) for row in rows]


def get_history(limit=10, chat_id=None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT id, question, answer, course, purpose, chat_id, session_id,
                       user_answer, timestamp, conversation_id, usage_json
                FROM chat_history
            """
            params = []
            if chat_id is not None:
                sql += " WHERE chat_id = %s AND purpose = 'qa_answer' ORDER BY id ASC"
                params.append(chat_id)
            else:
                sql += " ORDER BY timestamp DESC, id DESC"
            if limit is not None:
                sql += " LIMIT %s"
                params.append(limit)
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "id": row[0],
            "question": row[1],
            "answer": row[2],
            "course": row[3],
            "purpose": row[4],
            "chat_id": row[5],
            "session_id": row[6],
            "user_answer": row[7],
            "timestamp": row[8],
            "record_id": row[9],
            "usage": row[10],
        }
        for row in rows
    ]

def get_stats():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*),
                    COALESCE(AVG(response_time), 0),
                    COALESCE(SUM(cost), 0),
                    COALESCE(AVG(total_tokens), 0)
                FROM conversations
                """)
            row = cur.fetchone()
    finally:
        conn.close()

    return Stats(
        total=row[0],
        avg_response_time=row[1],
        total_cost=row[2],
        avg_tokens=row[3],
    )

if __name__ == "__main__":
    records = get_conversations()
    for record in records:
        print(record)
