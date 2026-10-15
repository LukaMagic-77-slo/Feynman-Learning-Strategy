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
