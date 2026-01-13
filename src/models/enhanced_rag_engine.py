"""
Enhanced RAG Engine for JEDEC Insight
Features OpenAI embeddings, MultiQueryRetriever, comparison engine, and synonym dictionary.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import asyncio
from pathlib import Path
import json

from langchain.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from ..utils.synonym_dictionary import get_synonym_dictionary
from ..utils.category_detector import get_search_strategy, analyze_user_query
from .comparison_engine import get_comparison_engine, perform_comparison

logger = logging.getLogger(__name__)


class EnhancedRAGEngine:
    """Enhanced RAG Engine with OpenAI embeddings, MultiQueryRetriever, comparison, and synonym support."""
    
    def __init__(self, chroma_path: str, collection_name: str):
        """
        Initialize Enhanced RAG engine.
        
        Args:
            chroma_path: Path to ChromaDB storage
            collection_name: Name of the collection
        """
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        
        # Initialize synonym dictionary
        self.synonym_dict = get_synonym_dictionary()
        
        # Initialize comparison engine
        self.comparison_engine = get_comparison_engine()
        
        # Initialize OpenAI embeddings
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=openai_api_key,
            model="text-embedding-ada-002"
        )
        
        # Initialize ChatOpenAI for better responses
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            model_name=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            temperature=0.1
        )
        
        # Initialize vector store
        self.vector_store = None
        self.multi_query_retriever = None
        self.qa_chain = None
        
        # Create directories
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self._initialize_vector_store()
        self._initialize_multi_query_retriever()
        self._initialize_qa_chain()
    
    def _initialize_vector_store(self):
        """Initialize ChromaDB vector store with OpenAI embeddings."""
        try:
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.chroma_path
            )
            logger.info(f"Vector store initialized with OpenAI embeddings: {self.chroma_path}")
        except Exception as e:
            logger.error(f"Error initializing vector store: {e}")
            raise
    
    def _initialize_multi_query_retriever(self):
        """Initialize MultiQueryRetriever for better query expansion."""
        try:
            # Create base retriever
            base_retriever = self.vector_store.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={
                    "k": 10,
                    "score_threshold": 0.3
                }
            )
            
            # Create MultiQueryRetriever
            self.multi_query_retriever = MultiQueryRetriever.from_llm(
                retriever=base_retriever,
                llm=self.llm
            )
            
            logger.info("MultiQueryRetriever initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing MultiQueryRetriever: {e}")
            raise
    
    def _initialize_qa_chain(self):
        """Initialize QA chain with structured response format."""
        try:
            # System message for hallucination prevention
            system_message = """당신은 JEDEC 규격 문서 전문가입니다. 다음 규칙을 반드시 따르세요:

1. 오직 제공된 문서 내용만을 기반으로 답변하세요.
2. 제공된 문서에 정보가 없으면 "제공된 문서에서 해당 정보를 찾을 수 없습니다"라고 답변하세요.
3. 절대로 문서에 없는 내용을 지어내지 마세요.
4. 답변은 반드시 아래 세 부분으로 구조화하세요:

[답변]
- 질문에 대한 직접적인 답변

[근거 규격]
- 정보 출처 JEDEC 규격명
- 관련 Table ID (있는 경우)
- 구체적인 페이지 번호나 섹션

[추가 참고사항]
- 관련 기술적 배경
- 주의사항이나 제약 조건
- 관련 규격 간의 관계"""

            # Create prompt template
            template = """다음 JEDEC 규격 문서 내용을 바탕으로 질문에 답변하세요.

문서 내용:
{context}

질문: {question}

위 지시사항에 따라 구조화된 답변을 제공하세요."""

            prompt = PromptTemplate(
                template=template,
                input_variables=["context", "question"]
            )
            
            # Create QA chain
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.multi_query_retriever,
                chain_type_kwargs={"prompt": prompt},
                return_source_documents=True
            )
            
            logger.info("Enhanced QA chain initialized with structured response format")
            
        except Exception as e:
            logger.error(f"Error initializing QA chain: {e}")
            raise
    
    def _extract_table_info(self, doc: Document) -> Dict[str, str]:
        """
        Extract table information from document metadata.
        
        Args:
            doc: Document object
            
        Returns:
            Dictionary with table information
        """
        metadata = doc.metadata
        table_info = {}
        
        # Extract table ID if available
        if metadata.get('is_table', False):
            table_info['table_id'] = metadata.get('element_id', 'Unknown')
            table_info['table_type'] = 'Table'
        else:
            table_info['table_id'] = 'N/A'
            table_info['table_type'] = 'Text'
        
        # Extract document and section info
        table_info['document_name'] = metadata.get('document_name', 'Unknown')
        table_info['section_title'] = metadata.get('section_title', 'Unknown')
        table_info['page'] = metadata.get('page', 'Unknown')
        
        return table_info
    
    def _format_sources(self, source_docs: List[Document]) -> List[Dict[str, Any]]:
        """
        Format source documents with table information.
        
        Args:
            source_docs: List of source documents
            
        Returns:
            Formatted sources list
        """
        formatted_sources = []
        
        for doc in source_docs:
            table_info = self._extract_table_info(doc)
            
            source = {
                "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                "metadata": doc.metadata,
                "document_id": table_info['document_name'],
                "table_id": table_info['table_id'],
                "table_type": table_info['table_type'],
                "section": table_info['section_title'],
                "page": table_info['page']
            }
            formatted_sources.append(source)
        
        return formatted_sources
    
    def _parse_structured_response(self, response: str) -> Dict[str, str]:
        """
        Parse structured response into components.
        
        Args:
            response: Raw response from LLM
            
        Returns:
            Dictionary with parsed components
        """
        components = {
            "answer": "",
            "specification": "",
            "additional_notes": ""
        }
        
        # Parse response sections
        sections = {
            "[답변]": "answer",
            "[근거 규격]": "specification", 
            "[추가 참고사항]": "additional_notes"
        }
        
        current_section = None
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Check for section headers
            for header, key in sections.items():
                if line.startswith(header):
                    current_section = key
                    # Remove the header from the line
                    line = line.replace(header, "").strip()
                    break
            
            # Add content to current section
            if current_section and line:
                if components[current_section]:
                    components[current_section] += "\n" + line
                else:
                    components[current_section] = line
        
        # If no structured format found, put everything in answer
        if not any(components.values()):
            components["answer"] = response
        
        return components
    
    async def query(self, question: str, k: int = 5) -> Dict[str, Any]:
        """
        Query the enhanced RAG system with smart category detection and filtering.
        
        Args:
            question: User question
            k: Number of documents to retrieve
            
        Returns:
            Dictionary with structured answer and sources
        """
        try:
            # Analyze query to determine optimal search strategy
            query_analysis = analyze_user_query(question)
            search_strategy = get_search_strategy(question)
            
            # Expand query with synonyms
            expanded_queries = self.synonym_dict.expand_query(question)
            normalized_query = self.synonym_dict.normalize_units(question)
            
            # Use enhanced query if suggested
            search_query = self.category_detector.create_enhanced_query(question, query_analysis)
            
            # Update retriever k value (increase for comparison queries)
            effective_k = k * 2 if query_analysis["is_comparison"] else k
            self.multi_query_retriever.search_kwargs['k'] = effective_k
            
            # Get search results for comparison analysis
            search_results = []
            if query_analysis["is_comparison"]:
                # Get more documents for comparison
                docs = self.multi_query_retriever.get_relevant_documents(search_query)[:effective_k]
                search_results = self._format_sources(docs)
            
            # Apply category filter if high confidence
            if search_strategy.get("use_metadata_filter", False):
                filter_criteria = search_strategy["filter_criteria"]
                # Note: ChromaDB filtering would need to be implemented here
                # For now, we'll filter after retrieval
                docs = self.multi_query_retriever.get_relevant_documents(search_query)
                filtered_docs = [
                    doc for doc in docs 
                    if doc.metadata.get("category") == filter_criteria.get("category")
                ]
                search_results = self._format_sources(filtered_docs)
            
            # Query the QA chain
            result = self.qa_chain({"query": search_query})
            
            # Parse structured response
            structured_response = self._parse_structured_response(result.get("result", ""))
            
            # Handle comparison if detected
            comparison_result = None
            if query_analysis["is_comparison"] and search_results:
                comparison_result = await perform_comparison(question, search_results)
                
                # Add comparison to response
                if comparison_result.get('is_comparison'):
                    structured_response['comparison'] = comparison_result['summary']
                    structured_response['comparison_table'] = comparison_result.get('comparison_table')
            
            # Format sources
            sources = []
            if 'source_documents' in result:
                sources = self._format_sources(result['source_documents'])
            
            return {
                "answer": structured_response["answer"],
                "specification": structured_response["specification"],
                "additional_notes": structured_response["additional_notes"],
                "comparison": structured_response.get('comparison', ''),
                "comparison_table": structured_response.get('comparison_table'),
                "sources": sources,
                "question": question,
                "raw_response": result.get("result", ""),
                "expanded_queries": expanded_queries,
                "is_comparison": query_analysis["is_comparison"],
                "query_analysis": query_analysis,
                "search_strategy": search_strategy
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "answer": f"쿼리 처리 중 오류가 발생했습니다: {str(e)}",
                "specification": "",
                "additional_notes": "",
                "comparison": "",
                "comparison_table": None,
                "sources": [],
                "question": question,
                "raw_response": "",
                "expanded_queries": [],
                "is_comparison": False,
                "query_analysis": {},
                "search_strategy": {}
            }
    
    async def multi_query_analysis(self, question: str) -> Dict[str, Any]:
        """
        Analyze what queries are generated by MultiQueryRetriever.
        
        Args:
            question: Original question
            
        Returns:
            Dictionary with generated queries and analysis
        """
        try:
            # Get generated queries
            queries = []
            for query in self.multi_query_retriever.generate_queries(question):
                queries.append(query)
            
            # Get results for each query
            query_results = []
            for query in queries:
                docs = await self.vector_store.similarity_search(query, k=3)
                query_results.append({
                    "query": query,
                    "documents": [doc.page_content[:200] + "..." for doc in docs]
                })
            
            return {
                "original_question": question,
                "generated_queries": queries,
                "query_results": query_results,
                "total_queries": len(queries)
            }
            
        except Exception as e:
            logger.error(f"Error in multi-query analysis: {e}")
            return {
                "original_question": question,
                "generated_queries": [],
                "query_results": [],
                "total_queries": 0,
                "error": str(e)
            }
    
    async def search_similar(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar documents without generating an answer.
        
        Args:
            query: Search query
            k: Number of documents to retrieve
            
        Returns:
            List of similar documents
        """
        try:
            # Use multi-query retriever for better results
            docs = self.multi_query_retriever.get_relevant_documents(query)[:k]
            
            results = []
            for doc in docs:
                table_info = self._extract_table_info(doc)
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "document_id": table_info['document_name'],
                    "table_id": table_info['table_id'],
                    "table_type": table_info['table_type'],
                    "section": table_info['section_title'],
                    "page": table_info['page']
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar documents: {e}")
            return []
    
    async def list_documents(self) -> List[str]:
        """
        List all documents in the vector store.
        
        Returns:
            List of document filenames
        """
        try:
            # Get all documents from vector store
            docs = self.vector_store.get()
            
            # Extract unique filenames
            filenames = set()
            for metadata in docs['metadatas']:
                if 'filename' in metadata:
                    filenames.add(metadata['filename'])
            
            return list(filenames)
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []
    
    async def delete_document(self, document_id: str):
        """
        Delete a document from the vector store.
        
        Args:
            document_id: Filename of document to delete
        """
        try:
            # Get all documents
            docs = self.vector_store.get()
            
            # Find IDs to delete
            ids_to_delete = []
            for i, metadata in enumerate(docs['metadatas']):
                if metadata.get('filename') == document_id:
                    ids_to_delete.append(docs['ids'][i])
            
            if ids_to_delete:
                self.vector_store.delete(ids=ids_to_delete)
                self.vector_store.persist()
                logger.info(f"Deleted {len(ids_to_delete)} chunks for document {document_id}")
            else:
                logger.warning(f"No chunks found for document {document_id}")
                
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with statistics
        """
        try:
            docs = self.vector_store.get()
            
            # Count table vs text chunks
            table_chunks = 0
            text_chunks = 0
            for metadata in docs['metadatas']:
                if metadata.get('is_table', False):
                    table_chunks += 1
                else:
                    text_chunks += 1
            
            return {
                "total_chunks": len(docs['ids']),
                "table_chunks": table_chunks,
                "text_chunks": text_chunks,
                "total_documents": len(set(metadata.get('filename', '') for metadata in docs['metadatas'])),
                "collection_name": self.collection_name,
                "embedding_model": "OpenAI text-embedding-ada-002",
                "retriever_type": "MultiQueryRetriever"
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}


# Standalone functions for easier usage
async def create_enhanced_rag_engine(chroma_path: str = "./data/chroma", 
                                   collection_name: str = "jepec_documents") -> EnhancedRAGEngine:
    """
    Create and initialize enhanced RAG engine.
    
    Args:
        chroma_path: Path to ChromaDB storage
        collection_name: Name of the collection
        
    Returns:
        Initialized Enhanced RAG engine
    """
    return EnhancedRAGEngine(chroma_path, collection_name)


# Example usage
async def main():
    """Example usage of enhanced RAG engine."""
    try:
        # Initialize engine
        engine = await create_enhanced_rag_engine()
        
        # Example queries
        questions = [
            "tCK min이 뭐야?",
            "DDR4의 전압 요구사항은?",
            "JEDEC 메모리 규격의 주요 특징은?"
        ]
        
        for question in questions:
            print(f"\n질문: {question}")
            print("="*50)
            
            # Get answer
            result = await engine.query(question, k=5)
            
            print(f"[답변]\n{result['answer']}")
            print(f"\n[근거 규격]\n{result['specification']}")
            print(f"\n[추가 참고사항]\n{result['additional_notes']}")
            
            # Show multi-query analysis
            analysis = await engine.multi_query_analysis(question)
            print(f"\n생성된 쿼리: {analysis['generated_queries']}")
            
            print("="*50)
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
