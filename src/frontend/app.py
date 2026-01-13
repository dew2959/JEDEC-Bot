"""
Streamlit Frontend for JEDEC Insight
Provides user interface for document processing and RAG queries.
"""

import os
import streamlit as st
import requests
from typing import List, Dict, Any
import pandas as pd
from pathlib import Path
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="JEDEC Insight",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API configuration
API_BASE_URL = "http://localhost:8000"

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .query-input {
        font-size: 1.1rem;
    }
    .source-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

def api_request(endpoint: str, method: str = "GET", data: Dict = None, files: Dict = None):
    """Make API request to backend."""
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            if files:
                response = requests.post(url, files=files)
            else:
                response = requests.post(url, json=data)
        elif method == "DELETE":
            response = requests.delete(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error: {str(e)}")
        return None

def check_api_health():
    """Check if API is running."""
    health = api_request("/health")
    return health is not None

def main():
    """Main application."""
    # Header
    st.markdown('<div class="main-header">🔬 JEDEC Insight</div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666;">RAG-based Chatbot for JEDEC Specification Documents</p>', unsafe_allow_html=True)
    
    # Check API health
    if not check_api_health():
        st.error("❌ Backend API is not running. Please start the FastAPI server first.")
        st.info("Run: `python -m src.backend.main`")
        return
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🛠️ Controls")
        
        # Document Management Section
        st.markdown("### 📄 Document Management")
        
        if st.button("🔄 Refresh Documents", key="refresh_docs"):
            with st.spinner("Refreshing document list..."):
                documents = api_request("/documents")
                if documents:
                    st.success(f"Found {documents['count']} documents")
                    st.session_state.documents = documents['documents']
        
        if st.button("📁 Process All PDFs", key="process_all"):
            with st.spinner("Processing all PDF files..."):
                result = api_request("/process-all", method="POST")
                if result:
                    st.success(result['message'])
        
        # File Upload
        st.markdown("### 📤 Upload PDF")
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type="pdf",
            key="pdf_upload"
        )
        
        if uploaded_file and st.button("Upload & Process", key="upload_btn"):
            with st.spinner("Uploading and processing..."):
                files = {"file": uploaded_file}
                result = api_request("/upload", method="POST", files=files)
                if result:
                    st.success(result['message'])
        
        # Statistics
        st.markdown("### 📊 Statistics")
        if 'documents' not in st.session_state:
            documents = api_request("/documents")
            if documents:
                st.session_state.documents = documents['documents']
        
        if 'documents' in st.session_state:
            st.metric("Total Documents", len(st.session_state.documents))
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📄 Documents", "⚙️ Settings"])
    
    with tab1:
        st.markdown('<div class="section-header">💬 Ask Questions</div>', unsafe_allow_html=True)
        
        # Query input
        col1, col2 = st.columns([4, 1])
        with col1:
            query = st.text_input(
                "JEDEC 규격에 대해 질문하세요:",
                placeholder="예: tCK min이 뭐야?",
                key="query_input",
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
        
        # Query button
        if st.button("🔍 Search", key="search_btn", type="primary"):
            if query:
                with st.spinner("Searching documents..."):
                    result = api_request(
                        "/query",
                        method="POST",
                        data={"query": query, "k": k_value}
                    )
                    
                    if result:
                        # Display structured answer
                        st.markdown("### 🤖 [답변]")
                        st.markdown(result['answer'])
                        
                        st.markdown("### 📋 [근거 규격]")
                        st.markdown(result['specification'])
                        
                        st.markdown("### 📝 [추가 참고사항]")
                        st.markdown(result['additional_notes'])
                        
                        # Display sources
                        st.markdown("### 📚 출처")
                        for i, source in enumerate(result['sources'], 1):
                            with st.expander(f"출처 {i}: {source.get('document_id', 'Unknown')}"):
                                st.markdown(f"**테이블 ID:** {source.get('table_id', 'N/A')}")
                                st.markdown(f"**페이지:** {source.get('page', 'Unknown')}")
                                st.markdown(f"**섹션:** {source.get('section', 'Unknown')}")
                                st.markdown(f"**내용:**")
                                st.markdown(source.get('content', 'No content available'))
            else:
                st.warning("Please enter a question.")
        
        # Chat history
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        if st.session_state.chat_history:
            st.markdown("### 💬 Chat History")
            for i, (q, a) in enumerate(st.session_state.chat_history, 1):
                with st.expander(f"Q{i}: {q[:50]}..."):
                    st.markdown(f"**Question:** {q}")
                    st.markdown(f"**Answer:** {a}")
    
    with tab2:
        st.markdown('<div class="section-header">📄 Document Library</div>', unsafe_allow_html=True)
        
        if 'documents' in st.session_state and st.session_state.documents:
            # Document list
            for doc_id in st.session_state.documents:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"📄 {doc_id}")
                with col2:
                    if st.button("🗑️", key=f"delete_{doc_id}"):
                        result = api_request(f"/documents/{doc_id}", method="DELETE")
                        if result:
                            st.success(result['message'])
                            st.rerun()
        else:
            st.info("No documents found. Upload and process PDF files to get started.")
    
    with tab3:
        st.markdown('<div class="section-header">⚙️ Settings</div>', unsafe_allow_html=True)
        
        st.markdown("### API Configuration")
        api_url = st.text_input(
            "API Base URL",
            value=API_BASE_URL,
            key="api_url"
        )
        
        st.markdown("### System Information")
        health = api_request("/health")
        if health:
            st.json(health)
        
        st.markdown("### About")
        st.markdown("""
        **JEDEC Insight** is a RAG-based chatbot designed to help you analyze and query JEDEC specification documents.
        
        **Features:**
        - 📄 PDF document processing with table extraction
        - 🔍 Intelligent search across documents
        - 💬 Natural language queries
        - 📊 Source attribution with scores
        
        **Technologies:**
        - Backend: FastAPI
        - Frontend: Streamlit
        - AI: LangChain + OpenAI
        - Vector DB: ChromaDB
        - PDF Processing: PyMuPDF + Unstructured
        """)

if __name__ == "__main__":
    main()
