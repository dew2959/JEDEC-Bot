import os 
import json
import pandas as pd 
from datasets import Dataset
from dotenv import load_dotenv

from ragas import evaluate
from ragas.metrics import (answer_relevance, faithfulness, context_recall, context_precision)

from app.chain.rag_engine import JEDECBot

def main():
    print("Ragas 기반 JEDEC 챗봇 성능 평가 시작")

    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY 없음. env 파일 확인요망")
    
    db_path = "./chroma_dbs/DRAM_JESD79-5_DDR5_db"
    bot = JEDECBot(db_path)

    with open("test_dataset.json", "r", encoding='utf-8') as f:
        test_data = json.load(f)

    questions = []
    answers = []
    contexts = []
    ground_truths = []

    print(f"총 {len(test_data)}개의 질문에 대한 답변 생성 중")

    for item in test_data:
        q = item["question"]
        gt = item['ground_truth']

        response = bot.ask(q)

        ans = response.get("answer", "")

        ctxs = [doc.page_content for doc in response.get("source_documents", [])]

        questions.append(q)
        answers.append(ans)
        contexts.append(ctxs)
        ground_truths.append(gt)

        print(f"\n 질문 처리 완료: {q[:20]}")

    data_dict = {
        "question" : questions,
        "answer" : answers,
        "contexts" : contexts,
        "ground_truth" : ground_truths,
    }
    dataset = Dataset.from_dict(data_dict)

    print("\n Ragas 채점 시작")

    result = evaluate(
        dataset = dataset,
        metrics=[
            answer_relevance,
            faithfulness,
            context_recall,
            context_precision
        ]
    )

    print("\n ====최종 평가 결과 요약=====")
    print(result)

    df = result.to_pandas()
    df.to_csv("rag_evaluation_results.csv", index = False, encoding="utf-8-sig")
    print("\n 상세 결과 csv 파일로 저장 완료")

if __name__ == "__main__":
    main()