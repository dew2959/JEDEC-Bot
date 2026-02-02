import streamlit as st
import os
import shutil # 파일/폴더 삭제용

# 기존에 만든 모듈들을 가져옵니다.
from app2.utils.pdf_parser import load_and_split_pdf
from app2.utils.vector_store import create_vector_db
from app2.chain.rag_engine import JEDECBot

# --- 페이지 설정 ---
st.set_page_config(
    page_title="JEDEC Specs Navigator",
    page_icon="💾",
    layout="wide"
)

# --- CSS 스타일링 ---
st.markdown("""
<style>
    .stChatMessage {
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 전역 상수 ---
TEMP_DIR = "temp_pdf"  # 업로드된 파일을 잠시 저장할 폴더

# temp 폴더가 없으면 미리 생성
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# --- 사이드바: 파일 업로드 및 설정 ---
with st.sidebar:
    st.title("💾 JEDEC Navigator")
    st.markdown("---")
    
    # 1. 파일 업로드 기능 추가
    st.subheader("📂 문서 업로드")
    uploaded_file = st.file_uploader("PDF 파일을 올려주세요", type=["pdf"])
    
    if uploaded_file is not None:
        # '업로드 & 처리' 버튼
        if st.button("문서 학습 시작"):
            with st.spinner("문서를 분석하고 데이터베이스에 저장 중입니다..."):
                try:
                    # 1. 파일을 임시 폴더에 저장 (PyPDFLoader는 파일 경로가 필요함)
                    temp_file_path = os.path.join(TEMP_DIR, uploaded_file.name)
                    with open(temp_file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # 2. PDF 파싱 및 청킹 (기존 모듈 재사용)
                    st.info("텍스트 추출 중...")
                    chunks = load_and_split_pdf(temp_file_path)
                    
                    # 3. 벡터 DB 생성/갱신 (기존 모듈 재사용)
                    st.info(f"{len(chunks)}개의 정보 블록을 DB에 저장 중...")
                    create_vector_db(chunks)
                    
                    # 4. 중요: 캐시된 봇을 날려서, 봇이 새 데이터를 다시 불러오게 함
                    st.cache_resource.clear()
                    
                    st.success("학습 완료! 이제 질문해보세요.")
                    
                except Exception as e:
                    st.error(f"오류 발생: {e}")

    st.markdown("---")
    st.markdown("""
    - **Tech Stack:** LangChain, ChromaDB, GPT-4o-mini
    - **Note:** 새로운 문서를 올리면 기존 DB에 데이터가 **누적**됩니다.
    """)
    
    # DB 초기화 버튼 (선택 사항)
    if st.button("⚠️ DB 초기화 (기억 삭제)"):
        if os.path.exists("./chroma_db"):
            shutil.rmtree("./chroma_db") # 폴더 강제 삭제
            st.cache_resource.clear()
            st.warning("데이터베이스가 초기화되었습니다. 문서를 다시 업로드해주세요.")
            st.rerun()

# --- 봇 엔진 초기화 ---
@st.cache_resource
def get_bot():
    # DB 폴더가 없으면 봇을 생성할 수 없음 (ingest가 안 된 상태)
    if not os.path.exists("./chroma_db"):
        return None
    return JEDECBot()

# --- 메인 화면 로직 ---
st.header("🔍 JEDEC Standard Q&A")

bot = get_bot()

# DB가 없는 경우 (처음 실행 시) 안내 메시지
if bot is None:
    st.info("👈 왼쪽 사이드바에서 PDF 문서를 업로드하고 '학습 시작'을 눌러주세요.")
    st.stop() # 이후 코드 실행 중단

# 채팅창 설명
st.caption("현재 학습된 문서를 기반으로 답변합니다.")

# 1. 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 문서 내용을 바탕으로 답변해 드릴게요."}]

# 2. 대화 내용 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 3. 입력 처리
if prompt := st.chat_input("질문을 입력하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        with st.spinner("답변 생성 중..."):
            try:
                # 봇 답변 요청
                response_text = bot.ask(prompt)
                message_placeholder.markdown(response_text)
                full_response = response_text
            except Exception as e:
                message_placeholder.error(f"Error: {e}")
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})