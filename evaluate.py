import os
import json
import asyncio
import pandas as pd
from typing import Dict, Any
from dotenv import load_dotenv
from openai import AsyncOpenAI

from ragas.metrics import DiscreteMetric   
from ragas import experiment
from ragas.llms import llm_factory

from app.chain.rag_engine import JEDECBot

## 현재 ragas 버전 0.4.3, 공식 문서 docs.ragas.io 코드 예시 참고, 26-02-23 기준
## 커스텀 지표(Meric) 정의 
correctness_metric = DiscreteMetric(
    name="correctness",
    prompt="""Compare the model response to the expected answer and determine if it's correct.

    Consider the response correct if it:
    1. Contains the key information from the expected answer
    2. Is factually accurate based on the provided context
    3. Adequately addresses the question asked

    Return 'pass' if the response is correct, 'fail' if it's incorrect.

    Question: {question}
    Expected Answer: {expected_answer}
    Model Response: {response}

    Evaluation:""",
    allowed_values=["pass", "fail"],
)

## 비동기 RAG 래퍼 클래스
class AsyncRAGWrapper:
    """
    공식 문서의 'await rag.query()' 형태를 지원하기 위해 기존 동기 챗봇을 비동기처럼 감싸주는 래퍼 
    """
    def __init__(self, bot):
        self.bot = bot

    async def query(self, question:str, top_k:int=4) -> Dict[str, Any]:
        # I/O 블로킹을 막기 위해 챗봇의 기존 동기 함수를 별도 쓰레드에서 실행 
        answer = await asyncio.to_thread(self.bot.ask, question)
        docs = await asyncio.to_thread(self.bot.vector_store.similarity_search, question, k=top_k)
        
        return {
            "answer": answer,
            "retrieved_documents": [{"content": doc.page_content} for doc in docs],
            "mlflow_trace_id": "N/A"  # MLflow 트레이스 ID는 현재 구현에서는 지원하지 않음
        }

## 평가 함수 
@experiment()
async def evaluate_rag(row: Dict[str, Any], rag: AsyncRAGWrapper, llm) -> Dict[str, Any]:
    """
    Run RAG evaluation on a single row.

    Args:
        row: Dictionary containing question and expected_answer
        rag: Pre-initialized RAG instance
        llm: Pre-initialized LLM client for evaluation

    Returns:
        Dictionary with evaluation results
    """
    question = row["question"]

    # Query the RAG system
    rag_response = await rag.query(question, top_k=4)
    model_response = rag_response.get("answer", "")

    # Evaluate correctness asynchronously
    score = await correctness_metric.ascore(
        question=question,
        expected_answer=row["expected_answer"],
        response=model_response,
        llm=llm
    )

    # Return evaluation results
    result = {
        **row,
        "model_response": model_response,
        "correctness_score": score.value,
        "correctness_reason": score.reason,
        "mlflow_trace_id": rag_response.get("mlflow_trace_id", "N/A"),  # MLflow trace ID for debugging (explained later)
        "retrieved_documents": [
            doc.get("content", "")[:200] + "..." if len(doc.get("content", "")) > 200 else doc.get("content", "")
            for doc in rag_response.get("retrieved_documents", [])
        ]
    }
    return result

## 메인 실행 블록 
async def main():
    print("Ragas 기반 JEDEC 챗봇 성능 평가 시작")

    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY 없음. env 파일 확인요망")
    
    openai_client = AsyncOpenAI()
    
    db_path = "./chroma_dbs/DRAM_JESD79-5_DDR5_db"
    base_bot = JEDECBot(db_path)
    rag = AsyncRAGWrapper(base_bot)
    eval_llm = llm_factory("gpt-4o-mini", client=openai_client)

    with open("test_dataset.json", "r", encoding='utf-8') as f:
        test_data = json.load(f)

    print(f"총 {len(test_data)}개의 질문을 처리중...")

    tasks = []
    for item in test_data:
        row = {
            "question": item["question"],
            "expected_answer": item["ground_truth"]
        }
        tasks.append(evaluate_rag(row, rag, eval_llm))

    results = await asyncio.gather(*tasks)

    print("\n ====최종 평가 결과 요약=====")

    df = pd.DataFrame(results)
    df.to_csv("rag_evaluation_results_v2.csv", index = False, encoding="utf-8-sig")
    print("\n 상세 결과 csv 파일로 저장 완료")
    pass_count = len(df[df['correctness_score'] == 'pass'])
    print(f"✅ Pass(정답) 비율: {pass_count}/{len(df)} ({pass_count/len(df)*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())