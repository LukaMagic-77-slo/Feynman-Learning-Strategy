"""本地知识入库和pgvector检索；导入不会连接数据库或删表。"""
import argparse
import json
import math
import os
from pathlib import Path
from dotenv import load_dotenv
from data_ingest import DEFAULT_DATA_PATH, load_knowledge_data

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_EMBEDDING_MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'

def document_text(doc):
    return '\n'.join([doc['课程'], doc['章节'], doc['主题'],
                      doc['知识点内容'], '、'.join(doc['关键词'])])

def vec_to_str(vector):
    values = [float(x) for x in vector]
    if not values or not all(math.isfinite(x) for x in values):
        raise ValueError('向量必须是非空有限数值序列')
    return '[' + ','.join(str(x) for x in values) + ']'

class PgVectorStore:
    def __init__(self, embedder, dsn, embedding_model):
        self.embedder = embedder
        self.dsn = dsn
        self.embedding_model = embedding_model
        self.dimension = int(embedder.get_sentence_embedding_dimension())
        if self.dimension <= 0:
            raise ValueError('向量维度必须大于0')

    def _connect(self):
        import psycopg
        return psycopg.connect(self.dsn, connect_timeout=10)

    def _check_config(self, conn):
        config = conn.execute('SELECT model, dimension FROM feynman_vector_config WHERE singleton=TRUE').fetchone()
        if config != (self.embedding_model, self.dimension):
            raise ValueError('数据库模型/维度与当前配置不一致；请使用原模型，或另建数据库重新入库。')

    def initialize(self):
        with self._connect() as conn:
            conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
            conn.execute('''CREATE TABLE IF NOT EXISTS feynman_vector_config (
                singleton BOOLEAN PRIMARY KEY CHECK(singleton),
                model TEXT NOT NULL, dimension INTEGER NOT NULL)''')
            conn.execute('INSERT INTO feynman_vector_config VALUES (TRUE,%s,%s) ON CONFLICT(singleton) DO NOTHING',
                         (self.embedding_model, self.dimension))
            self._check_config(conn)
            conn.execute(f'''CREATE TABLE IF NOT EXISTS feynman_knowledge (
                knowledge_id TEXT PRIMARY KEY, course TEXT NOT NULL,
                section TEXT NOT NULL, topic TEXT NOT NULL, content TEXT NOT NULL,
                keywords JSONB NOT NULL, embedding vector({self.dimension}) NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())''')

    def upsert(self, documents):
        if not documents:
            raise ValueError('知识库为空')
        vectors = self.embedder.encode([document_text(d) for d in documents],
            batch_size=16, normalize_embeddings=True, show_progress_bar=True)
        if len(vectors) != len(documents):
            raise ValueError('文档和向量数量不一致')
        from psycopg.types.json import Jsonb
        with self._connect() as conn:
            self._check_config(conn)
            for doc, vec in zip(documents, vectors):
                if len(vec) != self.dimension:
                    raise ValueError('向量维度不一致')
                conn.execute('''INSERT INTO feynman_knowledge
                    (knowledge_id,course,section,topic,content,keywords,embedding)
                    VALUES (%s,%s,%s,%s,%s,%s,%s::vector)
                    ON CONFLICT(knowledge_id) DO UPDATE SET
                    course=EXCLUDED.course, section=EXCLUDED.section,
                    topic=EXCLUDED.topic, content=EXCLUDED.content,
                    keywords=EXCLUDED.keywords, embedding=EXCLUDED.embedding,
                    updated_at=NOW()''', (doc['知识点id'], doc['课程'], doc['章节'],
                    doc['主题'], doc['知识点内容'], Jsonb(doc['关键词']), vec_to_str(vec)))
        return len(documents)

    def search(self, query, course='概率论', num_results=5):
        if not isinstance(query, str) or not query.strip():
            raise ValueError('问题不能为空')
        if num_results < 1:
            raise ValueError('结果数必须大于0')
        vec = self.embedder.encode(query, normalize_embeddings=True)
        with self._connect() as conn:
            self._check_config(conn)
            rows = conn.execute('''SELECT knowledge_id,course,section,topic,content,keywords,
                1-(embedding <=> %s::vector) AS similarity
                FROM feynman_knowledge WHERE course=%s
                ORDER BY embedding <=> %s::vector, knowledge_id LIMIT %s''',
                (vec_to_str(vec), course, vec_to_str(vec), num_results)).fetchall()
        return [dict(zip(['知识点id','课程','章节','主题','知识点内容','关键词','相似度'], r)) for r in rows]

def create_vector_store():
    load_dotenv(PROJECT_DIR / '.env')
    dsn = os.getenv('DATABASE_URL')
    if not dsn:
        raise ValueError('请在项目.env中设置DATABASE_URL，见.env.example')
    from sentence_transformers import SentenceTransformer
    name = os.getenv('EMBEDDING_MODEL', DEFAULT_EMBEDDING_MODEL)
    return PgVectorStore(SentenceTransformer(name), dsn, name)

def main():
    parser = argparse.ArgumentParser(description='概率论持久化向量知识库')
    parser.add_argument('command', choices=['validate','ingest','search'])
    parser.add_argument('query', nargs='?')
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA_PATH)
    args = parser.parse_args()
    if args.command == 'validate':
        docs = load_knowledge_data(args.data)
        for doc in docs:
            document_text(doc)
        print(f'验证通过：{len(docs)}条；未调用模型或数据库')
        return
    if args.command == 'search' and not args.query:
        parser.error('search需要提供问题')
    store = create_vector_store()
    if args.command == 'ingest':
        store.initialize()
        print(f'已新增或更新 {store.upsert(load_knowledge_data(args.data))} 条知识')
    else:
        print(json.dumps(store.search(args.query), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
