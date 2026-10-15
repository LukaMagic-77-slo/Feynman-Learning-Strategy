# evaluation/run_gen_data.py
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv

load_dotenv(PROJECT_DIR / ".env")

from gen_data import documents, generate_all


if __name__ == "__main__":
    df = generate_all(documents)
    print(f"生成完成，共 {len(df)} 个问题")