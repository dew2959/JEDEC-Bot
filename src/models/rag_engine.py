"""
RAG Engine for JEDEC Insight
Integrates LangChain with ChromaDB for document retrieval and question answering.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import asyncio
from pathlib import Path
import json

from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
import openai

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG Engine for document processing and question answering."""
    
    def __init__(self, chroma_path: str, collection_name: str):
        """
        Initialize RAG engine.
        
        Args:
            chroma_path: Path to ChromaDB storage
            collection_name: Name of the collection
        """
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        
        # Initialize embeddings
        embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'}
        )
        
        # Initialize text splitter
        chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize vector store
        self.vector_store = None
        self.qa_chain = None
        
        # Create directories
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self._initialize_vector_store()
        self._initialize_qa_chain()
    
    def _initialize_vector_store(self):
        """Initialize ChromaDB vector store."""
        try:
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.chroma_path
            )
            logger.info(f"Vector store initialized: {self.chroma_path}")
        except Exception as e:
            logger.error(f"Error initializing vector store: {e}")
            raise
    
    def _initialize_qa_chain(self):
        """Initialize QA chain with LangChain."""
        try:
            # Initialize OpenAI LLM
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            
            llm = OpenAI(
                openai_api_key=openai_api_key,
                model_name=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                temperature=0.1
            )
            
            # Create prompt template
            template = """You are an expert assistant specializing in JEDEC specification documents. 
Use the following pieces of context to answer the question at the end. 
If you don't know the answer from the context, just say that you don't know. 
Try to provide detailed and technical answers based on the JEDEC specifications.

Context:
{context}

Question: {question}

Helpful Answer:"""
            
            prompt = PromptTemplate(
                template=template,
                input_variables=["context", "question"]
            )
            
            # Create QA chain
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=self.vector_store.as_retriever(),
                chain_type_kwargs={"prompt": prompt},
                return_source_documents=True
            )
            
            logger.info("QA chain initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing QA chain: {e}")
            raise
    
    def _load_markdown_document(self, file_path: str) -> List[Document]:
        """
        Load and parse markdown document.
        
        Args:
            file_path: Path to markdown file
            
        Returns:
            List of Document objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split content into chunks
            chunks = self.text_splitter.split_text(content)
            
            documents = []
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "source": file_path,
                        "chunk_id": i,
                        "filename": Path(file_path).name
                    }
                )
                documents.append(doc)
            
            logger.info(f"Loaded {len(documents)} chunks from {file_path}")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {e}")
            return []
    
    async def add_document(self, file_path: str):
        """
        Add a document to the vector store.
        
        Args:
            file_path: Path to processed markdown file
        """
        try:
            # Load document
            documents = self._load_markdown_document(file_path)
            
            if not documents:
                logger.warning(f"No documents loaded from {file_path}")
                return
            
            # Add to vector store
            self.vector_store.add_documents(documents)
            self.vector_store.persist()
            
            logger.info(f"Added {len(documents)} chunks from {file_path} to vector store")
            
        except Exception as e:
            logger.error(f"Error adding document {file_path}: {e}")
            raise
    
    async def query(self, question: str, k: int = 5) -> Dict[str, Any]:
        """
        Query the RAG system.
        
        Args:
            question: User question
            k: Number of documents to retrieve
            
        Returns:
            Dictionary with answer and sources
        """
        try:
            # Update retriever k value
            self.vector_store.retriever.search_kwargs['k'] = k
            
            # Query the QA chain
            result = self.qa_chain({"query": question})
            
            # Format sources
            sources = []
            if 'source_documents' in result:
                for doc in result['source_documents']:
                    sources.append({
                        "content": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                        "metadata": doc.metadata,
                        "document_id": doc.metadata.get("filename", "Unknown"),
                        "score": 0.0  # ChromaDB doesn't provide scores in this setup
                    })
            
            return {
                "answer": result.get("result", "No answer available"),
                "sources": sources,
                "question": question
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "answer": f"Error processing query: {str(e)}",
                "sources": [],
                "question": question
            }
    
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
            # Update retriever k value
            self.vector_store.retriever.search_kwargs['k'] = k
            
            # Search for similar documents
            docs = self.vector_store.similarity_search(query, k=k)
            
            results = []
            for doc in docs:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "document_id": doc.metadata.get("filename", "Unknown")
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar documents: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with statistics
        """
        try:
            docs = self.vector_store.get()
            
            return {
                "total_chunks": len(docs['ids']),
                "total_documents": len(set(metadata.get('filename', '') for metadata in docs['metadatas'])),
                "collection_name": self.collection_name,
                "embedding_model": os.getenv("EMBEDDING_MODEL", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}


# Standalone functions for easier usage
async def create_rag_engine(chroma_path: str = "./data/chroma", 
                           collection_name: str = "jepec_documents") -> RAGEngine:
    """
    Create and initialize RAG engine.
    
    Args:
        chroma_path: Path to ChromaDB storage
        collection_name: Name of the collection
        
    Returns:
        Initialized RAG engine
    """
    return RAGEngine(chroma_path, collection_name)


async def process_and_index_document(file_path: str, rag_engine: RAGEngine):
    """
    Process and index a single document.
    
    Args:
        file_path: Path to markdown file
        rag_engine: RAG engine instance
    """
    await rag_engine.add_document(file_path)


async def batch_process_documents(file_paths: List[str], rag_engine: RAGEngine):
    """
    Process and index multiple documents.
    
    Args:
        file_paths: List of file paths
        rag_engine: RAG engine instance
    """
    tasks = [rag_engine.add_document(file_path) for file_path in file_paths]
    await asyncio.gather(*tasks)
