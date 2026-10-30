import csv
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
from tqdm.auto import tqdm
from openai import OpenAI
from data_ingest import load_knowledge_data
from rag import RAG
from vector import create_vector_store
from agent.langchain_framework import LangChainRAG

FIELDS = ['id', 'question', 'answer_orig', 'answer_llm']
ERROR_FIELDS = ['id', 'question', 'error_type', 'error']


def record_key(row):
    return (row['id'], row['question'])


def read_csv(path, fields):
    if not path.exists():
        return []
    with path.open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != fields:
            raise ValueError(f'{path}字段应为{fields}，未覆盖原文件')
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f'{path}存在不完整记录，请先检查')
    return rows


def save_csv(path, rows, fields):
    """仅主线程写入，完整临时文件替换旧文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        file.flush()
        os.fsync(file.fileno())
    temporary.replace(path)


def generate_answer(row, assistant, idtodoc):
    answer = assistant.rag(row['question'])
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError('模型返回空答案')
    return {
        'id': row['id'], 'question': row['question'],
        'answer_orig': idtodoc[row['id']]['知识点内容'],
        'answer_llm': answer,
    }


def run_generation(answers, assistant, idtodoc, output, error_output, max_workers=6):
    existing = read_csv(output, FIELDS)
    if any(not row['answer_llm'].strip() for row in existing):
        raise ValueError('已有答案CSV包含空答案，请先检查')
    completed = {record_key(row): row for row in existing}
    if len(completed) != len(existing):
        raise ValueError('已有答案CSV含重复(id, question)，请先检查')
    errors = {record_key(row): row for row in read_csv(error_output, ERROR_FIELDS)}
    pending = [row for row in answers if record_key(row) not in completed]
    print(f'共{len(answers)}题，跳过已完成{len(answers)-len(pending)}题，待处理{len(pending)}题', flush=True)
    if not pending:
        return

    pool = ThreadPoolExecutor(max_workers=max_workers)
    futures = {}
    interrupted = False
    try:
        futures = {pool.submit(generate_answer, row, assistant, idtodoc): row for row in pending}
        with tqdm(total=len(pending), desc='生成答案', unit='题') as progress:
            for future in as_completed(futures):
                row = futures[future]
                key = record_key(row)
                try:
                    result = future.result()
                except Exception as exc:
                    errors[key] = {
                        'id': row['id'], 'question': row['question'],
                        'error_type': type(exc).__name__, 'error': str(exc),
                    }
                    save_csv(error_output, list(errors.values()), ERROR_FIELDS)
                    tqdm.write(f"失败：{row['id']} / {type(exc).__name__}")
                else:
                    completed[key] = result
                    # 仍按原测试集排序，不按线程完成顺序输出。
                    save_csv(output, [completed[record_key(r)] for r in answers
                                     if record_key(r) in completed], FIELDS)
                    errors.pop(key, None)
                    if error_output.exists():
                        save_csv(error_output, list(errors.values()), ERROR_FIELDS)
                progress.update(1)
                progress.set_postfix(saved=len(completed), failed=len(errors))
    except KeyboardInterrupt:
        interrupted = True
        for future in futures:
            future.cancel()
        print('\n已停止收集，已保存答案保留。正在执行的请求不能强制取消，可能仍需等待超时。', flush=True)
        raise
    finally:
        pool.shutdown(wait=True, cancel_futures=interrupted)
    print(f'结束：已保存{len(completed)}条；本次结束后错误文件含{len(errors)}条。', flush=True)
    print(f'答案：{output}\n失败：{error_output}', flush=True)
    if any(record_key(row) not in completed for row in answers):
        raise SystemExit('存在失败问题；排查后重跑同一命令，仅处理未完成问题。')


def main():
    load_dotenv(PROJECT_DIR / '.env')
    documents = load_knowledge_data()
    idtodoc = {doc['知识点id']: doc for doc in documents}
    answers = read_csv(PROJECT_DIR / 'data' / 'ground_truth.csv', ['question', 'id'])
    if not answers or any(not r['question'].strip() or r['id'] not in idtodoc for r in answers):
        raise ValueError('测试集为空，或存在空问题/未知知识点ID')
    if len({record_key(r) for r in answers}) != len(answers):
        raise ValueError('测试集含重复(id, question)')

    assistant = LangChainRAG()
    run_generation(
        answers,
        assistant,
        idtodoc,
        PROJECT_DIR / "data" / "aqa_answers_langchain.csv",
        PROJECT_DIR / "data" / "aqa_answers_langchain_errors.csv",
        max_workers=6,
    )


if __name__ == '__main__':
    main()
