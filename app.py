import streamlit as st
import os
import shutil # 파일/폴더 삭제용
import gc
import time 

# 기존에 만든 모듈들을 가져옵니다.
from app2.utils.pdf_parser import load_and_split_pdf
from app2.utils.vector_store import create_vector_db
from app2.chain.rag_engine import JEDECBot

# --- 설정 ---
st.set_page_config(page_title="JEDEC Specs Navigator", page_icon="💾", layout="wide")
PRELOAD_DIR = "data/pdfs"  # 미리 넣어둔 PDF 폴더
DB_ROOT = "chroma_dbs"     # DB들이 저장될 상위 폴더

# 폴더 없으면 생성
if not os.path.exists(PRELOAD_DIR):
    os.makedirs(PRELOAD_DIR)
if not os.path.exists(DB_ROOT):
    os.makedirs(DB_ROOT)

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


# --- 유틸리티 함수: 폴더 스캔 ---
def get_file_structure(root_dir):
    """
    root_dir 하위의 모든 폴더와 PDF 파일을 스캔하여 딕셔너리로 반환합니다.
    예: {'DRAM': ['DDR5.pdf', ...], 'Storage': ['UFS4.pdf']}
    """
    structure = {}
    # os.walk로 하위 폴더까지 싹 훑습니다.
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 현재 폴더명 (예: DRAM) - root_dir 기준 상대 경로
        category = os.path.relpath(dirpath, root_dir)
        
        # PDF 파일만 필터링
        pdf_files = [f for f in filenames if f.endswith(".pdf")]
        
        if pdf_files:
            # 루트 폴더('.')인 경우 'Uncategorized' 등으로 표시하거나 그냥 루트로 표시
            cat_name = "Root" if category == "." else category
            structure[cat_name] = pdf_files
            
    return structure


# --- 사이드바: 파일 업로드 및 설정 ---
with st.sidebar:
    st.title("💾 JEDEC Navigator")
    
    # 1. 모드 선택 (미리 넣어둔 문서 vs 직접 업로드)
    mode = st.radio("문서 선택 방식", ["기본 문서 목록", "직접 업로드"], index=0)
    
    selected_db_path = None
    
    # [Mode 1] 폴더에 정리된 문서 선택
    if mode == "카테고리별 문서":
        file_struct = get_file_structure(PRELOAD_DIR)
        
        if not file_struct:
            st.warning(f"'{PRELOAD_DIR}' 폴더 안에 PDF 파일이 없습니다.")
        else:
            # 1. 카테고리(폴더) 선택
            # 정렬해서 보여주기 (Common, DRAM, Package, Storage 등)
            categories = sorted(file_struct.keys())
            selected_category = st.selectbox("📂 카테고리 (Category)", categories)
            
            # 2. 파일 선택
            if selected_category:
                files = sorted(file_struct[selected_category])
                selected_file = st.selectbox("📄 문서 (Document)", files)
                
                # 실제 파일 경로 재구성
                # Root인 경우와 하위 폴더인 경우 경로 처리가 다름
                if selected_category == "Root":
                    real_pdf_path = os.path.join(PRELOAD_DIR, selected_file)
                    # DB 이름 충돌 방지를 위해 폴더명_파일명
                    db_name = f"Root_{os.path.splitext(selected_file)[0]}_db"
                else:
                    real_pdf_path = os.path.join(PRELOAD_DIR, selected_category, selected_file)
                    db_name = f"{selected_category}_{os.path.splitext(selected_file)[0]}_db"
                
                target_db_path = os.path.join(DB_ROOT, db_name)
                
                # 학습 여부 확인
                if not os.path.exists(target_db_path):
                    st.info("이 문서는 아직 학습되지 않았습니다.")
                    if st.button(f"'{selected_file}' 학습 시작"):
                        with st.spinner("문서 구조를 파악하고 학습 중입니다..."):
                            chunks = load_and_split_pdf(real_pdf_path)
                            create_vector_db(chunks, target_db_path)
                            
                            # 봇 재로딩을 위해 캐시 삭제
                            st.cache_resource.clear()
                            st.success("학습 완료! DB가 생성되었습니다.")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.success(f"✅ Ready: {selected_category} / {selected_file}")
                    selected_db_path = target_db_path

    # [Mode 2] 1회성 직접 업로드
    elif mode == "직접 업로드":
        uploaded_file = st.file_uploader("PDF 파일 업로드", type=["pdf"])
        if uploaded_file:
            target_db_path = os.path.join(DB_ROOT, "temp_uploaded_db")
            
            if st.button("문서 학습 시작"):
                with st.spinner("처리 중..."):
                    # 임시 파일 저장
                    if not os.path.exists("temp_pdf"): os.makedirs("temp_pdf")
                    temp_pdf_path = os.path.join("temp_pdf", uploaded_file.name)
                    
                    with open(temp_pdf_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    chunks = load_and_split_pdf(temp_pdf_path)
                    create_vector_db(chunks, target_db_path)
                    
                    st.cache_resource.clear()
                    st.success("완료!")
                    st.rerun()
            
            if os.path.exists(target_db_path):
                 selected_db_path = target_db_path
    
    st.markdown("---")
    # DB 전체 초기화 버튼 (필요 시 복구용)
    if st.button("⚠️ 모든 학습 데이터 삭제"):
        st.cache_resource.clear()
        gc.collect()
        if os.path.exists(DB_ROOT):
            try:
                shutil.rmtree(DB_ROOT)
                os.makedirs(DB_ROOT) # 폴더 다시 생성
                st.warning("모든 데이터베이스가 삭제되었습니다.")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"삭제 실패 (폴더가 열려있을 수 있음): {e}")

# --- 봇 엔진 로드 (캐싱 적용) ---
# DB 경로(path)가 바뀌면 자동으로 봇을 새로 만듭니다.
@st.cache_resource
def get_bot(db_path):
    return JEDECBot(db_path)

# --- 메인 화면 로직 ---
st.header("🔍 JEDEC Standard Q&A")

if selected_db_path and os.path.exists(selected_db_path):
    # 선택된 DB로 봇 생성
    bot = get_bot(selected_db_path)

    # 현재 보고 있는 문서 표시
    db_label = os.path.basename(selected_db_path).replace("_db", "")
    st.caption(f"📚 현재 문서: **{db_label}**")
    
    # 채팅 인터페이스
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "선택하신 문서에 대해 물어보세요."}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("질문 입력..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            msg_placeholder = st.empty()
            full_response = ""
            with st.spinner("검색 중..."):
                try:
                    resp = bot.ask(prompt)
                    # 타자기 효과
                    for chunk in resp.split():
                        full_response += chunk + " "
                        time.sleep(0.02)
                        msg_placeholder.markdown(full_response + "▌")
                    msg_placeholder.markdown(full_response)
                except Exception as e:
                    msg_placeholder.error(f"오류: {e}")
        st.session_state.messages.append({"role": "assistant", "content": full_response})

else:
    # 문서가 선택되지 않았을 때
    st.info("👈 왼쪽 사이드바에서 [카테고리]와 [문서]를 선택하고 학습을 시작해주세요.")
    
    # 초기 화면 가이드
    st.markdown("""
    ### 사용 방법
    1. 왼쪽 사이드바에서 **DRAM**, **Storage** 등 카테고리를 선택하세요.
    2. 원하는 문서를 선택하세요 (예: `JESD79-5_DDR5.pdf`).
    3. **'학습 시작'** 버튼을 누르면 AI가 문서를 읽고 기억합니다. (최초 1회만 필요)
    4. 학습이 끝나면 채팅창에 질문을 입력하세요.
    """)
