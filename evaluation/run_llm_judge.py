import csv
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from pprint import pprint

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / '.env')

from openai import OpenAI
from tqdm.auto import tqdm
from llm_judge import judge_record, LLM_JUDGE_INSTRUCTIONS, AnswerEvaluation, aqa_judge_prompt
from run_answers_gen import save_csv

FIELDS = ['question', 'id', 'score', 'reasoning', 'input_hash', 'usage_json']
ERROR_FIELDS = ['id', 'question', 'error_type', 'error', 'cause']


def read_rows(path, required):
    if not path.exists():
        return []
    with path.open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        if not set(required).issubset(reader.fieldnames or []):
            raise ValueError(f'{path}缺少必需字段{required}')
        rows = list(reader)
    if any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError(f'{path}存在不完整记录')
    return rows


def key(row):
    return row['id'], row['question']


def input_hash(row):
    data = [row['id'], row['question'], row['answer_orig'], row['answer_llm'],
            os.environ.get('DASHSCOPE_MODEL'), os.environ.get('DASHSCOPE_BASE_URL'),
            LLM_JUDGE_INSTRUCTIONS, aqa_judge_prompt, AnswerEvaluation.model_json_schema()]
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def run_judging(answers, client, output, error_output, workers=6):
    old = read_rows(output, ['question', 'id', 'score', 'reasoning'])
    completed = {key(r): {f: r.get(f, '') for f in FIELDS} for r in old}
    if len(completed) != len(old):
        raise ValueError('已有结果含重复(id, question)，请先检查')
    errors = {key(r): r for r in read_rows(error_output, ERROR_FIELDS)}
    pending = [r for r in answers if key(r) not in completed
               or completed[key(r)].get('input_hash') != input_hash(r)]
    print(f'输入{len(answers)}条，待评估{len(pending)}条，跳过{len(answers)-len(pending)}条', flush=True)
    if old and any(not r.get('input_hash') for r in old):
        print('旧评分没有输入指纹，对应记录将重新评估；原文件保留到新结果成功写入。', flush=True)
    pool = ThreadPoolExecutor(max_workers=workers)
    futures = {}
    interrupted = False
    try:
        futures = {pool.submit(judge_record, r, client): r for r in pending}
        with tqdm(total=len(pending), desc='裁判评估', unit='题') as progress:
            for future in as_completed(futures):
                row = futures[future]
                try:
                    result, usage = future.result()
                    if result['score'] not in ('good', 'bad') or not result['reasoning'].strip():
                        raise ValueError('裁判返回无效评分或空理由')
                    usage_json = json.dumps(usage.model_dump(mode='json'), ensure_ascii=False)
                except Exception as exc:
                    errors[key(row)] = {
                        'id': row['id'], 'question': row['question'],
                        'error_type': type(exc).__name__, 'error': str(exc),
                        'cause': repr(exc.__cause__),
                    }
                    save_csv(error_output, list(errors.values()), ERROR_FIELDS)
                    tqdm.write(f"失败：{row['id']} / {type(exc).__name__}")
                else:
                    completed[key(row)] = {**result, 'input_hash': input_hash(row), 'usage_json': usage_json}
                    save_csv(output, list(completed.values()), FIELDS)
                    errors.pop(key(row), None)
                    if error_output.exists():
                        save_csv(error_output, list(errors.values()), ERROR_FIELDS)
                progress.update(1)
                progress.set_postfix(saved=len(completed), failed=len(errors))
    except KeyboardInterrupt:
        interrupted = True
        for future in futures:
            future.cancel()
        print('\n已保存结果保留；运行中的请求无法强制取消，仍可能等待超时。', flush=True)
        raise
    finally:
        pool.shutdown(wait=True, cancel_futures=interrupted)

    results = [completed[key(r)] for r in answers if key(r) in completed
               and completed[key(r)].get('input_hash') == input_hash(r)]
    usages = [json.loads(r['usage_json']) for r in results if r.get('usage_json')]
    print('results 前10条：')
    pprint([{k: r[k] for k in ['question','id','score','reasoning']} for r in results[:10]], sort_dicts=False)
    print('usages 前10条：')
    pprint(usages[:10], sort_dicts=False)
    print(f'当前输入有效评分：{len(results)}/{len(answers)}；文件：{output}', flush=True)
    if len(results) != len(answers):
        raise SystemExit(f'存在未完成评估，错误见{error_output}；重跑同一命令可补评。')


def main():
    answers = read_rows(PROJECT_DIR / 'data' / 'aqa_answers.csv',
                        ['id', 'question', 'answer_orig', 'answer_llm'])
    if not answers or any(not r[f].strip() for r in answers
                          for f in ['id','question','answer_orig','answer_llm']):
        raise ValueError('答案文件为空或必需字段包含空值')
    if len({key(r) for r in answers}) != len(answers):
        raise ValueError('答案文件存在重复(id, question)')
    for name in ['DASHSCOPE_API_KEY', 'DASHSCOPE_BASE_URL', 'DASHSCOPE_MODEL']:
        if not os.getenv(name):
            raise ValueError(f'缺少配置：{name}')
    # 外层llm_structured_retry最多3次；不再叠加SDK自动重试。
    with OpenAI(api_key=os.environ['DASHSCOPE_API_KEY'],
                base_url=os.environ['DASHSCOPE_BASE_URL'],
                timeout=60.0, max_retries=0) as client:
        run_judging(answers, client,
                    PROJECT_DIR / 'data' / 'aqa_judge_results.csv',
                    PROJECT_DIR / 'data' / 'aqa_judge_errors.csv')


if __name__ == '__main__':
    main()
