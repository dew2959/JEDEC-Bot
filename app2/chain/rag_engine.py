import os 
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

# 벡터 DB가 저장 경로 
PERSIST_DIRECTORY = "./chroma_db"

class JEDECBot:
    def __init__(self, db_path):
        """
        챗봇 엔진 초기화 : LLM, 임베딩, 벡터DB, 프롬프트 설정
        """
        #1. 모델 설정
        self.llm = ChatOpenAI(model_name = "gpt-5-nano", temperature=0)

        #2. 임베딩 모델 설정 
        self.embedding = OpenAIEmbeddings(model="text-embedding-3-large")

        #3. 벡터 DB 로드 
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Vector DB not found at {db_path}")
        
        # 지정된 경로의 DB를 로드
        self.vector_store = Chroma(
            persist_directory= db_path,
            embedding_function= self.embedding
        )

        #4. 검색기 설정. k=3으로 설정하여 가장 유사한 문서 조각 3개를 가져오기로 함 
        self.retriever = self.vector_store.as_retriever(search_kwags={"k":3})

        #5. 프롬프트 템플릿 설정 
        self.prompt = ChatPromptTemplate.from_template(
            """
            당신은 반도체 JEDEC 표준 문서 전문가입니다. 
            아래의 [Context]를 바탕으로 사용자의 질문에 답변하세요. 

            규칙:
            1. 반드시 제공된 [Context] 내용에 기반해서만 답변하세요. 
            2. [Context]에 없는 내용이라면, "문서에서 관련 내용을 찾을 수 없습니다." 라고 솔직하게 말하세요. 
            3. 답변 끝에 참조한 정보가 포함된 페이지 정보가 있다면 언급해주세요. (Context 메타데이터 활용)

            [Context]: {context}
            [Question] : {question}
            [Answer]: 
            """
        )

        #6. chain 구성 (LCEL 방식). 문서 포맷팅 -> 프롬프트 주입 -> LLM 생성 -> 문자열 파싱 
        self.chain = (
            {
                "context" : self.retriever | self._format_docs,
                "question" : RunnablePassthrough()
            }
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def _format_docs(self, docs):
        """
        검색된 문서들을 하나의 텍스트로 합치고, 출처(page)를 남기는 함수 
        """
        formatted_text = ""
        for doc in docs:
            page = doc.metadata.get('page', 'Unknown')
            source = doc.metadata.get('source', 'Unknown File')
            formatted_text += f"\n--- [Page {page} of {source}] --- \n{doc.page_content}\n"
        return formatted_text
    
    def ask(self, query: str):
        """
        사용자 질문을 받아 답변을 반환하는 함수 
        """
        return self.chain.invoke(query)

# 테스트 실행 코드 
if __name__ == "__main__":
    print("JEDEC Chatbot Engine Loading...")
    bot = JEDECBot()

    #테스트 질문 
    test_query = "DDR5의 tRFC 타이밍 제약조건에 대해 알려줘"
    print(f"\n 질문 : {test_query} ")
    print("답변 생성 중...")
    response = bot.ask(test_query)
    print(f"\n 답변: {response}")