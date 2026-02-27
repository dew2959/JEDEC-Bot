import os 

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools import DuckDuckGoSearchResults

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.tools import Tool

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 벡터 DB 저장 경로 
PERSIST_DIRECTORY = "./chroma_db_agentic"

class JEDECBot:
    def __init__(self, db_path):
        """
        챗봇 엔진 초기화 : LLM, 임베딩, 벡터DB, 에이전트 설정
        """
        # 1. 모델 설정
        self.llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

        # 2. 임베딩 모델 설정 
        self.embedding = OpenAIEmbeddings(model="text-embedding-3-large")

        # 3. 벡터 DB 로드 
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Vector DB not found at {db_path}")
        
        self.vector_store = Chroma(
            persist_directory=db_path,
            embedding_function=self.embedding
        )

        # 4. 검색기 설정
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})

        # 5. 챗봇에게 쥐어줄 도구(Tools) 생성
        web_search_tool = DuckDuckGoSearchResults(num_results=3)

        self.tools = [
            Tool(
                name="JEDEC_Document_Search",
                func=self.search_documents,
                description="JEDEC DDR5/DRAM 표준 문서에서 스펙, 전압, 핀 배열 등 공식 규격을 찾을 때 반드시 가장 먼저 사용하세요."
            ),
            Tool(
                name="Web_Search",
                func=web_search_tool.run,
                description="JEDEC 문서에 내용이 없거나, DDR4와의 비교, 최신 메모리 시장 동향 등 일반적인 반도체 웹 지식이 필요할 때 보조용으로 사용하세요."
            )
        ]

        # 6. 에이전트 프롬프트 및 초기화 (Agentic RAG)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 삼성전자, SK하이닉스 수준의 지식을 갖춘 메모리 반도체 및 JEDEC 표준 전문가입니다.
            
            규칙:
            1. 질문이 묻는 핵심 요구사항에 대해 빙빙 돌리지 말고 '결론'부터 직접적으로 답변하세요.
            2. 무조건 JEDEC_Document_Search 도구를 먼저 사용하여 공식 문서를 확인하세요.
            3. 공식 문서에 내용이 없거나, 과거 세대(DDR4 등)와의 비교 등 추가 정보가 필요하면 Web_Search 도구를 사용하여 완벽한 답변을 구성하세요.
            4. 참조한 문서 페이지나 웹 출처(URL)가 있다면 답변 마지막에 출처를 명시해주세요.
            """),
            ("human", "{input}"),
            # 에이전트가 도구를 사용한 기록(Scratchpad)을 기억하는 공간
            ("placeholder", "{agent_scratchpad}"), 
        ])

        # 도구를 사용할 줄 아는 에이전트 생성 (최신 OpenAI 권장 방식)
        agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        
        # 에이전트를 실행하는 Executor (verbose=True로 설정하면 도구 선택 과정을 터미널에서 볼 수 있습니다)
        self.agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)

    def search_documents(self, query: str):
        """
        내부 JEDEC DB 검색용 헬퍼 함수 (에이전트가 호출함)
        """
        docs = self.retriever.invoke(query)
        return self._format_docs(docs)

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
        사용자 질문을 받아 Agent가 답변을 반환하는 함수 
        """
        # 기존 체인은 invoke(query) 였으나, 에이전트는 딕셔너리 형태로 input을 전달합니다.
        response = self.agent_executor.invoke({"input": query})
        return response["output"]

# 테스트 실행 코드 
if __name__ == "__main__":
    print("JEDEC Agentic Chatbot Engine Loading...")
    
    bot = JEDECBot(PERSIST_DIRECTORY) 

    # 테스트 질문 (JEDEC 문서에 없는 최신 트렌드를 물어봄)
    test_query = "DDR5의 기본 전압은 얼마인가요? 그리고 최근 DDR5 메모리 시장의 주요 트렌드나 기사는 어떤게 있나요?"
    print(f"\n 질문 : {test_query} ")
    print(" 답변 생성 중 (에이전트 동작 확인)...")
    
    response = bot.ask(test_query)
    print(f"\n✅ 최종 답변: \n{response}")