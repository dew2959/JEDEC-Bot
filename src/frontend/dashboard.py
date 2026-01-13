"""
Enhanced Streamlit Dashboard for JEDEC Insight
Features sidebar document management, interactive chat with clickable sources,
comparison tables, and enhanced error handling.
"""

import os
import streamlit as st
import requests
import pandas as pd
import re
import io
import base64
from typing import List, Dict, Any, Optional
from pathlib import Path
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="JEDEC Insight Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API configuration
API_BASE_URL = "http://localhost:8000"

# Custom CSS for enhanced styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        max-width: 90%;
    }
    
    .user-message {
        background-color: #e3f2fd;
        margin-left: auto;
        text-align: right;
    }
    
    .bot-message {
        background-color: #f5f5f5;
        margin-right: auto;
    }
    
    .source-badge {
        display: inline-block;
        background-color: #2196f3;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        margin: 0.25rem;
        font-size: 0.875rem;
        cursor: pointer;
        text-decoration: none;
    }
    
    .source-badge:hover {
        background-color: #1976d2;
        text-decoration: none;
    }
    
    .response-section {
        margin: 1rem 0;
        padding: 1rem;
        border-left: 4px solid #2196f3;
        background-color: #fafafa;
    }
    
    .section-title {
        font-weight: bold;
        color: #1976d2;
        margin-bottom: 0.5rem;
    }
    
    .dataframe-container {
        margin: 1rem 0;
        overflow-x: auto;
    }
    
    .sidebar-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    
    .upload-area {
        border: 2px dashed #ccc;
        border-radius: 0.5rem;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    
    .upload-area.dragover {
        border-color: #2196f3;
        background-color: #e3f2fd;
    }
    
    .comparison-highlight {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.25rem;
        padding: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

def api_request(endpoint: str, method: str = "GET", data: Dict = None, files: Dict = None, 
               timeout: int = 30, max_retries: int = 3):
    """
    Make API request to backend with enhanced error handling.
    
    Args:
        endpoint: API endpoint
        method: HTTP method
        data: Request data
        files: Uploaded files
        timeout: Request timeout
        max_retries: Maximum retry attempts
        
    Returns:
        Response JSON or None
    """
    url = f"{API_BASE_URL}{endpoint}"
    
    for attempt in range(max_retries + 1):
        try:
            if method == "GET":
                response = requests.get(url, timeout=timeout)
            elif method == "POST":
                if files:
                    response = requests.post(url, files=files, timeout=timeout)
                else:
                    response = requests.post(url, json=data, timeout=timeout)
            elif method == "DELETE":
                response = requests.delete(url, timeout=timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"API Error: {response.status_code} - {response.text}"
                if attempt < max_retries:
                    st.warning(f"재시도 중... ({attempt + 1}/{max_retries + 1})")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    st.error(error_msg)
                return None
                
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                st.warning(f"타임아웃 재시도 중... ({attempt + 1}/{max_retries + 1})")
                time.sleep(2 ** attempt)
            else:
                st.error("서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.")
                return None
                
        except requests.exceptions.ConnectionError:
            if attempt < max_retries:
                st.warning(f"연결 재시도 중... ({attempt + 1}/{max_retries + 1})")
                time.sleep(2 ** attempt)
            else:
                st.error("서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.")
                return None
                
        except Exception as e:
            st.error(f"예기치 않은 오류: {str(e)}")
            return None
    
    return None

def check_api_health():
    """Check if API is running."""
    health = api_request("/health")
    return health is not None

def parse_table_from_response(response_text: str) -> Optional[pd.DataFrame]:
    """
    Parse table data from response text.
    
    Args:
        response_text: Text response that might contain table data
        
    Returns:
        DataFrame if table found, None otherwise
    """
    # Look for markdown table patterns
    table_pattern = r'\|(.+)\|\n\|[-\s\|]+\|\n((?:\|.+\|\n?)*)'
    matches = re.findall(table_pattern, response_text, re.MULTILINE)
    
    if matches:
        try:
            # Parse the first table found
            headers = [h.strip() for h in matches[0][0].split('|') if h.strip()]
            rows = []
            
            for line in matches[0][1].strip().split('\n'):
                if line.strip():
                    row_data = [cell.strip() for cell in line.split('|') if cell.strip()]
                    if row_data:
                        rows.append(row_data)
            
            if rows and headers:
                df = pd.DataFrame(rows, columns=headers[:len(rows[0])])
                return df
        except Exception as e:
            st.warning(f"표 파싱 오류: {e}")
    
    return None

def render_source_badges(sources: List[Dict[str, Any]]):
    """
    Render clickable source badges with page numbers.
    
    Args:
        sources: List of source documents
    """
    if not sources:
        return
    
    st.markdown("### 📚 출처")
    
    # Group sources by document
    doc_sources = {}
    for source in sources:
        doc_name = source.get('document_id', 'Unknown')
        if doc_name not in doc_sources:
            doc_sources[doc_name] = []
        doc_sources[doc_name].append(source)
    
    for doc_name, doc_sources_list in doc_sources.items():
        with st.expander(f"📄 {doc_name}", expanded=False):
            # Create clickable page badges
            pages = list(set(source.get('page') for source in doc_sources_list if source.get('page')))
            
            if pages:
                st.markdown("**페이지:**")
                page_html = ""
                for page in sorted(pages):
                    if page and page != 'Unknown':
                        # Create a clickable badge
                        page_html += f'<a href="#page-{page}" class="source-badge">페이지 {page}</a>'
                
                st.markdown(page_html, unsafe_allow_html=True)
            
            # Show table IDs if available
            table_ids = list(set(source.get('table_id') for source in doc_sources_list 
                               if source.get('table_id') and source.get('table_id') != 'N/A'))
            
            if table_ids:
                st.markdown("**테이블 ID:**")
                for table_id in table_ids:
                    st.markdown(f"- `{table_id}`")
            
            # Show sections
            sections = list(set(source.get('section') for source in doc_sources_list 
                               if source.get('section') and source.get('section') != 'Unknown'))
            
            if sections:
                st.markdown("**관련 섹션:**")
                for section in sections[:3]:  # Show top 3 sections
                    st.markdown(f"- {section}")

def render_structured_response(response: Dict[str, Any]):
    """
    Render structured response with tables in DataFrame format.
    
    Args:
        response: Response dictionary from API
    """
    # Answer section
    if response.get('answer'):
        st.markdown('<div class="response-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🤖 답변</div>', unsafe_allow_html=True)
        
        # Check if answer contains table data
        table_df = parse_table_from_response(response['answer'])
        
        if table_df is not None:
            st.markdown("**표 데이터:**")
            st.dataframe(table_df, use_container_width=True)
            
            # Also provide copy-friendly format
            st.markdown("**복사용 텍스트:**")
            st.code(table_df.to_string(index=False), language='text')
        else:
            st.markdown(response['answer'])
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Comparison section (new)
    if response.get('comparison'):
        st.markdown('<div class="comparison-highlight">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📊 규격 비교</div>', unsafe_allow_html=True)
        
        # Render comparison summary
        st.markdown(response['comparison'])
        
        # Render comparison table if available
        if response.get('comparison_table'):
            comparison_df = pd.DataFrame(response['comparison_table'])
            if not comparison_df.empty:
                st.markdown("**상세 비교 표:**")
                st.dataframe(comparison_df, use_container_width=True)
                
                # Copy-friendly format
                st.markdown("**복사용 텍스트:**")
                st.code(comparison_df.to_string(index=False), language='text')
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Specification section
    if response.get('specification'):
        st.markdown('<div class="response-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📋 근거 규격</div>', unsafe_allow_html=True)
        
        # Check if specification contains table data
        table_df = parse_table_from_response(response['specification'])
        
        if table_df is not None:
            st.markdown("**규격 표:**")
            st.dataframe(table_df, use_container_width=True)
        else:
            st.markdown(response['specification'])
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Additional notes section
    if response.get('additional_notes'):
        st.markdown('<div class="response-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📝 추가 참고사항</div>', unsafe_allow_html=True)
        
        # Check if additional notes contains table data
        table_df = parse_table_from_response(response['additional_notes'])
        
        if table_df is not None:
            st.markdown("**참고 표:**")
            st.dataframe(table_df, use_container_width=True)
        else:
            st.markdown(response['additional_notes'])
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Show expanded queries if available
    if response.get('expanded_queries') and len(response['expanded_queries']) > 1:
        st.markdown('<div class="response-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🔍 확장된 검색어</div>', unsafe_allow_html=True)
        
        for i, query in enumerate(response['expanded_queries'], 1):
            st.markdown(f"{i}. {query}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Render source badges
    if response.get('sources'):
        render_source_badges(response['sources'])

def render_chat_message(role: str, content: str, sources: List[Dict[str, Any]] = None):
    """
    Render a chat message with proper styling.
    
    Args:
        role: 'user' or 'assistant'
        content: Message content
        sources: Source documents for assistant messages
    """
    if role == 'user':
        st.markdown(f'<div class="chat-message user-message"><strong>👤 사용자:</strong><br>{content}</div>', 
                   unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-message bot-message"><strong>🤖 JEDEC Insight:</strong></div>', 
                   unsafe_allow_html=True)
        
        # Parse response if it's a structured response
        try:
            if isinstance(content, dict):
                render_structured_response(content)
            else:
                st.markdown(content)
        except Exception as e:
            st.markdown(content)
        
        if sources:
            render_source_badges(sources)

def main():
    """Main dashboard application."""
    # Header
    st.markdown('<div class="main-header">🔬 JEDEC Insight Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666;">JEDEC 규격 문서 분석 및 질의응답 시스템</p>', unsafe_allow_html=True)
    
    # Check API health
    if not check_api_health():
        st.error("❌ Backend API가 실행되고 있지 않습니다. FastAPI 서버를 먼저 시작해주세요.")
        st.info("실행 명령어: `python -m src.backend.main`")
        return
    
    # Initialize session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'documents' not in st.session_state:
        st.session_state.documents = []
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 📚 문서 관리")
        
        # Document list section
        with st.container():
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.markdown("### 📄 학습된 문서")
            
            # Refresh button
            if st.button("🔄 문서 새로고침", key="refresh_docs", use_container_width=True):
                with st.spinner("문서 목록을 새로고침 중..."):
                    documents = api_request("/documents")
                    if documents:
                        st.session_state.documents = documents['documents']
                        st.success(f"{documents['count']}개 문서를 찾았습니다")
            
            # Display documents
            if st.session_state.documents:
                for i, doc in enumerate(st.session_state.documents):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"📄 {doc}")
                    with col2:
                        if st.button("🗑️", key=f"delete_{doc}", help="문서 삭제"):
                            result = api_request(f"/documents/{doc}", method="DELETE")
                            if result:
                                st.success(result['message'])
                                st.rerun()
            else:
                st.info("학습된 문서가 없습니다.")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Upload section
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### 📤 PDF 업로드")
        
        uploaded_file = st.file_uploader(
            "JEDEC PDF 파일 선택",
            type="pdf",
            key="pdf_upload",
            help="JEDEC 규격 PDF 파일을 업로드하세요"
        )
        
        if uploaded_file:
            st.markdown(f"**선택된 파일:** {uploaded_file.name}")
            
            if st.button("📤 업로드 및 처리", key="upload_btn", use_container_width=True, type="primary"):
                with st.spinner("PDF 업로드 및 처리 중..."):
                    files = {"file": uploaded_file}
                    result = api_request("/upload", method="POST", files=files)
                    if result:
                        st.success(result['message'])
                        # Refresh documents list
                        documents = api_request("/documents")
                        if documents:
                            st.session_state.documents = documents['documents']
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Batch processing section
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### ⚙️ 일괄 처리")
        
        if st.button("📁 모든 PDF 처리", key="process_all", use_container_width=True):
            with st.spinner("모든 PDF 파일을 처리 중..."):
                result = api_request("/process-all", method="POST")
                if result:
                    st.success(result['message'])
                    # Refresh documents list
                    time.sleep(2)  # Give time for processing
                    documents = api_request("/documents")
                    if documents:
                        st.session_state.documents = documents['documents']
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Statistics
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### 📊 통계")
        
        if st.session_state.documents:
            st.metric("총 문서 수", len(st.session_state.documents))
        
        # Get API stats
        health = api_request("/health")
        if health and health.get('components', {}).get('rag_engine'):
            st.markdown("**시스템 상태:**")
            st.markdown("✅ RAG 엔진 정상")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Main chat interface
    st.markdown("---")
    
    # Chat history
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for i, message in enumerate(st.session_state.chat_history):
            render_chat_message(
                role=message['role'],
                content=message['content'],
                sources=message.get('sources')
            )
    
    # Chat input
    st.markdown("---")
    
    # Input area
    col1, col2 = st.columns([4, 1])
    
    with col1:
        query = st.text_input(
            "JEDEC 규격에 대해 질문하세요:",
            placeholder="예: DDR4 vs DDR5 비교, tCK min이 뭐야?",
            key="chat_input",
            label_visibility="collapsed"
        )
    
    with col2:
        k_value = st.number_input(
            "검색 문서 수",
            min_value=1,
            max_value=10,
            value=5,
            key="k_value"
        )
    
    # Send button
    if st.button("🔍 질문하기", key="send_btn", type="primary", use_container_width=True):
        if query:
            # Add user message to chat history
            st.session_state.chat_history.append({
                'role': 'user',
                'content': query
            })
            
            # Get AI response
            with st.spinner("🔍 JEDEC 문서에서 검색 중..."):
                result = api_request(
                    "/query",
                    method="POST",
                    data={"query": query, "k": k_value}
                )
                
                if result:
                    # Add assistant response to chat history
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': result,
                        'sources': result.get('sources', [])
                    })
                    
                    # Rerun to display new messages
                    st.rerun()
        else:
            st.warning("질문을 입력해주세요.")
    
    # Clear chat button
    if st.button("💬 대화 기록 지우기", key="clear_chat"):
        st.session_state.chat_history = []
        st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(
        '<div style="text-align: center; color: #666; font-size: 0.875rem;">'
        'JEDEC Insight - RAG-based JEDEC Specification Analyzer | '
        'Powered by OpenAI & LangChain'
        '</div>', 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()