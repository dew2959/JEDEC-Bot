import streamlit as st
import os
import json
import time 

from app.utils.pdf_parser2 import load_and_split_pdf
from app.utils.vector_store import create_vector_db
from app.chain.rag_engine import JEDECBot

# --- 설정 ---
st.set_page_config(page_title="JEDEC Specs Navigator", page_icon="💾", layout="wide")

# 경로 설정 (절대 경로 사용)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRELOAD_DIR = os.path.join(BASE_DIR, "data", "pdfs")            # 미리 넣어둔 PDF 폴더
DB_ROOT = os.path.join(BASE_DIR, "chroma_dbs")                  # DB들이 저장될 상위 폴더
USER_UPLOAD_DIR = os.path.join(PRELOAD_DIR, "User_Uploads")     # 사용자가 올린 파일이 저장될 곳

# 폴더 없으면 생성
for d in [PRELOAD_DIR, USER_UPLOAD_DIR, DB_ROOT]:
    if not os.path.exists(d):
        os.makedirs(d)

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


# --- 유틸리티 함수 ---
def get_file_structure(root_dir):
    structure = {}
    if not os.path.exists(root_dir):
        return {}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        category = os.path.relpath(dirpath, root_dir)
        pdf_files = [f for f in filenames if f.lower().endswith(".pdf")]
        
        if pdf_files:
            # 카테고리 이름 정리 (Root, User_Uploads 등)
            if category == ".":
                cat_name = "Uncategorized"
            else:
                cat_name = category
            structure[cat_name] = pdf_files
            
    return structure

# --- 메타데이터 로드 함수 ---
def load_doc_metadata(db_path):
    meta_path = os.path.join(db_path, "doc_info.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# --- 사이드바 ---
with st.sidebar:
    st.title("💾 JEDEC Navigator")
    
    # 탭으로 기능 분리
    tab1, tab2 = st.tabs(["📚 라이브러리", "➕ 새 문서 추가"])
    
    selected_db_path = None
    
    # [Tab 1] 기존 라이브러리 선택
    with tab1:
        file_struct = get_file_structure(PRELOAD_DIR)
        
        if not file_struct:
            st.warning("등록된 문서가 없습니다.")
        else:
            # 카테고리 선택
            categories = sorted(file_struct.keys())
            
            # User_Uploads가 있으면 맨 위로, 없으면 알파벳순
            if "User_Uploads" in categories:
                categories.insert(0, categories.pop(categories.index("User_Uploads")))
                
            selected_category = st.selectbox("카테고리 선택", categories)
            
            # 파일 선택
            if selected_category:
                files = sorted(file_struct[selected_category])
                selected_file = st.selectbox("문서 선택", files)
                
                # 경로 계산
                if selected_category == "Uncategorized":
                    real_pdf_path = os.path.join(PRELOAD_DIR, selected_file)
                    db_name = f"Root_{os.path.splitext(selected_file)[0]}_db"
                else:
                    real_pdf_path = os.path.join(PRELOAD_DIR, selected_category, selected_file)
                    clean_cat = selected_category.replace(os.sep, "_")
                    db_name = f"{clean_cat}_{os.path.splitext(selected_file)[0]}_db"
                
                target_db_path = os.path.join(DB_ROOT, db_name)
                
                # 상태 확인 및 버튼 표시
                if not os.path.exists(target_db_path):
                    st.info("⚠️ 아직 학습되지 않은 문서입니다.")
                    if st.button(f"🚀 '{selected_file}' 학습 시작", key="train_btn"):
                        with st.spinner("AI가 문서를 읽고 있습니다..."):
                            chunks = load_and_split_pdf(real_pdf_path)
                            create_vector_db(chunks, target_db_path)
                            st.cache_resource.clear()
                            st.success("학습 완료!")
                            time.sleep(0.5)
                            st.rerun()
                else:
                    st.success("✅ 준비 완료")
                    selected_db_path = target_db_path

    # [Tab 2] 파일 영구 추가 (업로드)
    with tab2:
        st.write("새 PDF를 업로드하면 **'User_Uploads'** 카테고리에 영구 저장됩니다.")
        uploaded_file = st.file_uploader("PDF 드래그 & 드롭", type=["pdf"])
        
        if uploaded_file:
            # 저장 버튼
            if st.button("저장 및 학습 시작"):
                with st.spinner("파일 저장 및 분석 중..."):
                    # 1. 파일 영구 저장
                    save_path = os.path.join(USER_UPLOAD_DIR, uploaded_file.name)
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # 2. DB 바로 생성
                    db_name = f"User_Uploads_{os.path.splitext(uploaded_file.name)[0]}_db"
                    target_db_path = os.path.join(DB_ROOT, db_name)
                    
                    chunks = load_and_split_pdf(save_path)
                    create_vector_db(chunks, target_db_path)
                    
                    # 3. 리프레시
                    st.cache_resource.clear()
                    st.success(f"'{uploaded_file.name}' 등록 완료!")
                    time.sleep(1)
                    st.rerun()

    st.markdown("---")
    st.caption(f"Total Cached DBs: {len(os.listdir(DB_ROOT)) if os.path.exists(DB_ROOT) else 0}")

# --- 메인 로직 ---
@st.cache_resource
def get_bot(db_path):
    return JEDECBot(db_path)

st.header("🔍 JEDEC Standard Q&A")

if selected_db_path and os.path.exists(selected_db_path):
    bot = get_bot(selected_db_path)
    
    # 1. 문서 메타데이터 로드 및 표시
    metadata = load_doc_metadata(selected_db_path)

    clicked_q = None

    if metadata:
        # 제목 및 리비전
        st.markdown(f"### 📄 {metadata.get('title', 'Document')} <span style='font-size:0.8em; color:gray'>({metadata.get('revision', '')})</span>", unsafe_allow_html=True)
        
        # 핵심 파라미터 (뱃지 형태)
        params = metadata.get('key_params', [])
        if params:
            st.markdown("**Key Specs:** " + " ".join([f"`{p}`" for p in params]))
            
        # [NEW] 추천 질문 버튼 영역
        st.markdown("#### 💡 Recommended Questions")
        cols = st.columns(3)
        questions = metadata.get('recommended_questions', [])
        
        # 버튼을 누르면 해당 질문이 채팅창에 입력되도록 처리
        for i, q in enumerate(questions[:3]): # 최대 3개
            if cols[i].button(q, key=f"q_btn_{i}"):
                clicked_q = q
    else:
        # 구버전 DB라 메타데이터가 없는 경우
        st.caption(f"📚 현재 문서: {os.path.basename(selected_db_path)}")

    st.divider()

    # 현재 문서 이름 표시 (예쁘게)
    current_doc_name = os.path.basename(selected_db_path).replace("_db", "").split("_")[-1] + ".pdf"
    st.markdown(f"#### 📖 Current Document: `{current_doc_name}`")
    
    # 채팅 인터페이스 
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "선택하신 문서에 대해 질문해주세요."}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 사용자 입력 처리 (버튼 클릭 or 직접 입력)
    prompt = None
    if clicked_q:
        prompt = clicked_q # 버튼 클릭 시
    elif input_text := st.chat_input("질문 입력..."):
        prompt = input_text # 직접 입력 시

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # (중요) 버튼 클릭 시 화면 갱신을 위해 rerun이 필요할 수 있지만, 
        # Streamlit 흐름상 메시지 append 후 아래 로직을 타게 함.
        if clicked_q:
             st.rerun() # 버튼 클릭 효과를 즉시 반영하기 위해 리프레시

    # 마지막 메시지가 유저라면 답변 생성 (버튼 클릭 후 리런되면 이리로 옴)
    if st.session_state.messages[-1]["role"] == "user":
        last_prompt = st.session_state.messages[-1]["content"]
        
        with st.chat_message("user"):
            st.markdown(last_prompt)

        with st.chat_message("assistant"):
            ph = st.empty()
            full_res = ""
            with st.spinner("답변 생성 중..."):
                try:
                    resp = bot.ask(last_prompt)
                    for chunk in resp.split():
                        full_res += chunk + " "
                        time.sleep(0.02)
                        ph.markdown(full_res + "▌")
                    ph.markdown(full_res)
                except Exception as e:
                    ph.error(f"Error: {e}")
        
        st.session_state.messages.append({"role": "assistant", "content": full_res})

else:
    # 문서 미선택 시 안내 화면
    st.info("👈 왼쪽 '라이브러리' 탭에서 문서를 선택해주세요.")
    st.markdown("""
    ### 💡 팁
    - **라이브러리**: 이미 `data/pdfs` 폴더에 있는 문서들을 선택해서 대화합니다.
    - **새 문서 추가**: PDF 파일을 업로드하면 자동으로 저장되고 학습됩니다.
    - **한 번 학습하면**: 다음부터는 기다릴 필요 없이 바로 대화할 수 있습니다.
    """)