import os 
import shutil
import json
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

def generate_jedec_summary(chunks):
    """
    문서의 앞부분(초록/목차)을 읽고 JEDEC 문서의 핵심 정보를 추출합니다.
    """
    # 문서의 앞쪽 5개 청크만 사용하여 요약 (전체를 다 읽으면 돈이 많이 드니까요)
    sample_text = "\n".join([chunk.page_content for chunk in chunks[:5]])
    
    llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
    
    prompt = ChatPromptTemplate.from_template(
        """
        당신은 반도체 JEDEC 표준 분석가입니다.
        아래 제공된 문서의 앞부분을 읽고 다음 정보를 JSON 형식으로 추출하세요.
        
        1. title: 문서의 공식 제목 (예: DDR5 SDRAM)
        2. revision: 리비전 정보 (찾을 수 없다면 'Unknown' 표시)
        3. key_params: 이 표준에서 가장 중요한 기술적 파라미터 3~5개 나열 (문자열 리스트)
        4. recommended_questions: 실무 엔지니어가 이 문서에 대해 물어볼 만한 핵심 질문 3개 (한국어)
        
        [Document Text Preview]:
        {text}
        
        Output JSON:
        """
    )
    
    try:
        chain = prompt | llm
        response = chain.invoke({"text": sample_text})
        
        # JSON 파싱 (가끔 마크다운 ```json ... ``` 이 포함될 수 있어 제거 처리)
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "")
        
        return json.loads(content)
    except Exception as e:
        print(f"Summary Generation Failed: {e}")
        return {
            "title": "JEDEC Standard", 
            "revision": "Unknown", 
            "key_params": [], 
            "recommended_questions": ["이 문서의 주요 내용은 무엇인가요?", "주요 타이밍 스펙은?", "동작 전압은?"]
        }
    

def create_vector_db(chunks, persist_directory):
    """
    텍스트 chunk list를 받아서 벡터 DB를 생성하고 로컬에 저장하는 함수 
    이미 DB가 존재하면 삭제하고 새로 만드는 초기 구축용도 
    """
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ OPENAI_API_KEY가 설정되지 않았습니다.")
        return None
    
    #0. OpenAI 임베딩 모델 사용 
    embeddings = OpenAIEmbeddings(model = 'text-embedding-3-large')


    #1. 기존 DB가 있다면 충돌 방지를 위해 삭제 
    if os.path.exists(persist_directory):
        shutil.rmtree(persist_directory)
        print(f"warnning: '{persist_directory}' 폴더가 이미 존재하여 삭제 후 재생성합니다.")

    #2. ChromaDB 생성 및 데이터 삽입 
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory,
    ) 

    # 2. [추가된 기능] 문서 요약 및 추천 질문 생성
    print("Generating Document Metadata (Summary & FAQs)...")
    metadata = generate_jedec_summary(chunks)
    
    # 3. 메타데이터를 JSON 파일로 DB 폴더 안에 저장
    meta_path = os.path.join(persist_directory, "doc_info.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    #3. 저장 (자동 저장되므로 메시지만 표시)
    print(f"Finished! Vector DB created with {len(chunks)} chunks.")
    return vectordb

    

def load_vector_db(persist_directory):
    """
    저장된 로컬 벡터 DB를 불러오는 함수 (챗봇 실행 시 사용)
    """
    if not os.path.exists(persist_directory):
        print("저장된 벡터DB가 없습니다. 먼저 create_vector_db를 실행하세요.")
        return None
    
    embeddings = OpenAIEmbeddings(model = "text_embedding_3_small")
    vectordb = Chroma(
        persist_directory= persist_directory,
        embedding_function= embeddings,
    )
    return vectordb

