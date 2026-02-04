import os 
import shutil
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma


# 벡터 DB가 저장될 로컬 폴더 경로 (프로적트 루트 기준)->  경로를 고정하지 않고 인자로 받기 위해 주석처리. 
#PERSIST_DIRECTORY = "./chroma_db"

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
        # print(f"warnning: '{persist_directory}' 폴더가 이미 존재합니다. 기존 데이터에 추가됩니다.")
        print(f"warnning: '{persist_directory}' 폴더가 이미 존재하여 삭제 후 재생성합니다.")

    #2. ChromaDB 생성 및 데이터 삽입 
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory,
    ) 

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

