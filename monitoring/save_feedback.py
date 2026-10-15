from datetime import datetime
from init_db import get_db_connection, DB_TIMEZONE

def save_feedback(conversation_id, source, relevance=None,
                  explanation=None, score=None, user_id="anonymous"):
    if conversation_id is None:
        raise ValueError("没有成功保存的记录ID，不能提交反馈")
    if source == "user" and score not in (-1, 1):
        raise ValueError("用户反馈score只能是1或-1")
    if not user_id:
        raise ValueError("user_id不能为空；前端可传入浏览器会话ID")
    timestamp = datetime.now(DB_TIMEZONE)

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO feedback (
                    conversation_id, source, relevance, 
                    explanation, score, timestamp, user_id
                ) VALUES(
                    %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (conversation_id, source, user_id)
                DO UPDATE SET relevance=EXCLUDED.relevance,
                    explanation=EXCLUDED.explanation, score=EXCLUDED.score,
                    timestamp=EXCLUDED.timestamp
                RETURNING id
                """,
                (conversation_id, source, relevance, 
                 explanation, score, timestamp, user_id),
            )
            feedback_id = cur.fetchone()[0]
            conn.commit()
    finally:
        conn.close()
    return feedback_id
