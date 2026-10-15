import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[1]


def get_connection():
    load_dotenv(PROJECT_DIR / '.env')
    return psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=10)


def get_sections(course):
    """返回课程下的章节列表。"""
    with get_connection() as conn:
        rows = conn.execute(
            '''SELECT DISTINCT section FROM feynman_knowledge
               WHERE course = %s ORDER BY section''',
            (course,),
        ).fetchall()
    return [row[0] for row in rows]


def get_topics(course, section):
    """返回指定章节下的主题列表。"""
    with get_connection() as conn:
        rows = conn.execute(
            '''SELECT DISTINCT topic FROM feynman_knowledge
               WHERE course = %s AND section = %s ORDER BY topic''',
            (course, section),
        ).fetchall()
    return [row[0] for row in rows]


def get_knowledge(course, section, topic):
    """按课程、章节、主题精确查询，返回知识记录列表。"""
    with get_connection() as conn:
        rows = conn.execute(
            '''SELECT knowledge_id, course, section, topic, content, keywords
               FROM feynman_knowledge
               WHERE course = %s AND section = %s AND topic = %s
               ORDER BY knowledge_id''',
            (course, section, topic),
        ).fetchall()
    fields = ['知识点id', '课程', '章节', '主题', '知识点内容', '关键词']
    return [dict(zip(fields, row)) for row in rows]
