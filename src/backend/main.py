"""
FastAPI Backend for JEDEC Insight
Provides REST API endpoints for document processing and RAG queries.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel
import asyncio
from dotenv import load_dotenv

from ..utils.agentic_search import perform_agentic_search
from ..utils.category_detector import analyze_user_query
from ..utils.error_handling import handle_errors, ErrorType
from ..models.enhanced_rag_engine import EnhancedRAGEngine
from ..utils.pdf_processor import PDFProcessor

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=os.getenv("APP_NAME", "JEDEC Insight"),
    version=os.getenv("APP_VERSION", "1.0.0"),
    description="RAG-based chatbot for JEDEC specification documents"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
pdf_processor: Optional[PDFProcessor] = None
rag_engine: Optional[EnhancedRAGEngine] = None

# Pydantic models
class QueryRequest(BaseModel):
    query: str
    k: int = 5

class QueryResponse(BaseModel):
    answer: str
    specification: str
    additional_notes: str
    comparison: str = ""
    comparison_table: Optional[List[Dict[str, Any]]] = None
    sources: List[Dict[str, Any]]
    query: str
    raw_response: str
    expanded_queries: List[str] = []
    is_comparison: bool = False

class DocumentListResponse(BaseModel):
    documents: List[str]
    count: int

class ProcessResponse(BaseModel):
    message: str
    processed_files: List[str]

# Initialize components
def initialize_components():
    """Initialize PDF processor and RAG engine."""
    global pdf_processor, rag_engine
    
    pdf_dir = os.getenv("PDF_INPUT_DIR", "./data/pdfs")
    output_dir = os.getenv("PROCESSED_DATA_DIR", "./data/processed")
    
    pdf_processor = PDFProcessor(pdf_dir, output_dir)
    
    # Initialize RAG engine
    chroma_path = os.getenv("CHROMA_DB_PATH", "./data/chroma")
    collection_name = os.getenv("CHROMA_COLLECTION_NAME", "jepec_documents")
    
    rag_engine = EnhancedRAGEngine(
        chroma_path=chroma_path,
        collection_name=collection_name
    )
    
    logger.info("Components initialized successfully")

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    initialize_components()

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "JEDEC Insight API",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "components": {
            "pdf_processor": pdf_processor is not None,
            "rag_engine": rag_engine is not None
        }
    }

@app.post("/upload", response_model=ProcessResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload and process a PDF file.
    
    Args:
        background_tasks: FastAPI background tasks
        file: Uploaded PDF file
        
    Returns:
        Process response with status
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    if not pdf_processor:
        raise HTTPException(status_code=500, detail="PDF processor not initialized")
    
    try:
        # Save uploaded file
        pdf_dir = Path(os.getenv("PDF_INPUT_DIR", "./data/pdfs"))
        pdf_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = pdf_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process in background
        background_tasks.add_task(process_uploaded_pdf, file_path)
        
        return ProcessResponse(
            message=f"PDF '{file.filename}' uploaded successfully. Processing started.",
            processed_files=[str(file_path)]
        )
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

async def process_uploaded_pdf(file_path: Path):
    """Process uploaded PDF and update vector store."""
    try:
        if not rag_engine:
            logger.error("RAG engine not initialized")
            return
        
        # Process PDF
        content = pdf_processor.process_pdf(file_path)
        output_path = pdf_processor.save_processed_content(content, file_path)
        
        # Add to vector store
        await rag_engine.add_document(output_path)
        
        logger.info(f"Successfully processed and indexed: {file_path}")
        
    except Exception as e:
        logger.error(f"Error processing uploaded PDF: {e}")

@app.post("/process-all", response_model=ProcessResponse)
async def process_all_pdfs(background_tasks: BackgroundTasks):
    """
    Process all PDF files in the input directory.
    
    Args:
        background_tasks: FastAPI background tasks
        
    Returns:
        Process response with status
    """
    if not pdf_processor:
        raise HTTPException(status_code=500, detail="PDF processor not initialized")
    
    try:
        # Process in background
        background_tasks.add_task(process_all_pdfs_background)
        
        return ProcessResponse(
            message="Processing started for all PDF files.",
            processed_files=[]
        )
        
    except Exception as e:
        logger.error(f"Error processing PDFs: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing PDFs: {str(e)}")

async def process_all_pdfs_background():
    """Process all PDFs in background."""
    try:
        if not rag_engine:
            logger.error("RAG engine not initialized")
            return
        
        # Process all PDFs
        processed_files = pdf_processor.process_all_pdfs()
        
        # Add all processed files to vector store
        for file_path in processed_files:
            await rag_engine.add_document(file_path)
        
        logger.info(f"Successfully processed {len(processed_files)} PDF files")
        
    except Exception as e:
        logger.error(f"Error in background processing: {e}")

@app.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    """
    List all processed documents.
    
    Returns:
        List of processed documents
    """
    try:
        if not rag_engine:
            raise HTTPException(status_code=500, detail="RAG engine not initialized")
        
        documents = await rag_engine.list_documents()
        
        return DocumentListResponse(
            documents=documents,
            count=len(documents)
        )
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.post("/query", response_model=QueryResponse)
@handle_errors(ErrorType.API_CONNECTION, reraise=True)
async def query_documents(request: QueryRequest):
    """
    Enhanced query endpoint with agentic search workflow.
    
    Args:
        request: Query request with question and k value
        
    Returns:
        Query response with enhanced agentic search results
    """
    if not rag_engine:
        raise HTTPException(status_code=500, detail="RAG engine not initialized")
    
    try:
        # Perform agentic search with JESD21C knowledge integration
        result = await perform_agentic_search(
            request.query, 
            rag_engine, 
            analyze_user_query,  # Pass category detector
            k=request.k
        )
        
        # Format response for frontend
        final_result = result.get("final_result", {})
        
        return QueryResponse(
            answer=final_result.get("final_answer", ""),
            specification=final_result.get("specification", ""),
            additional_notes=final_result.get("additional_notes", ""),
            comparison=final_result.get("comparison", ""),
            comparison_table=final_result.get("comparison_table"),
            sources=final_result.get("sources", []),
            query=request.query,
            raw_response=final_result.get("final_answer", ""),
            expanded_queries=final_result.get("expanded_queries", []),
            is_comparison=final_result.get("is_comparison", False)
        )
        
    except Exception as e:
        logger.error(f"Error processing agentic query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document from the system.
    
    Args:
        document_id: ID of document to delete
        
    Returns:
        Deletion status
    """
    try:
        if not rag_engine:
            raise HTTPException(status_code=500, detail="RAG engine not initialized")
        
        await rag_engine.delete_document(document_id)
        
        return {"message": f"Document {document_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

# Include category router
app.include_router(category_router)

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "True").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload
    )
