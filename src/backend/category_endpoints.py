"""
Category-specific API endpoints for JEDEC Insight
Provides endpoints for filtering and searching by document categories.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging

from ..utils.error_handling import handle_errors, ErrorType
from .main import rag_engine

logger = logging.getLogger(__name__)

# Create router for category endpoints
category_router = APIRouter(prefix="/categories", tags=["categories"])


@category_router.get("/", summary="Get all available categories")
@handle_errors(ErrorType.API_CONNECTION, reraise=True)
async def get_categories():
    """
    Get all available document categories.
    
    Returns:
        Dictionary with category information
    """
    try:
        if not rag_engine:
            raise HTTPException(status_code=500, detail="RAG engine not initialized")
        
        # Get all documents and extract unique categories
        all_docs = rag_engine.vector_store.get()
        categories = set()
        
        for doc in all_docs:
            if 'metadata' in doc and 'category' in doc['metadata']:
                categories.add(doc['metadata']['category'])
        
        # Count documents per category
        category_stats = {}
        for category in categories:
            category_docs = [
                doc for doc in all_docs 
                if 'metadata' in doc and doc['metadata'].get('category') == category
            ]
            category_stats[category] = len(category_docs)
        
        return {
            "categories": sorted(list(categories)),
            "statistics": category_stats,
            "total_documents": len(all_docs)
        }
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving categories: {str(e)}")


@category_router.get("/{category}/documents", summary="Get documents by category")
@handle_errors(ErrorType.API_CONNECTION, reraise=True)
async def get_documents_by_category(
    category: str,
    limit: Optional[int] = Query(50, description="Maximum number of documents to return"),
    offset: Optional[int] = Query(0, description="Number of documents to skip")
):
    """
    Get documents from a specific category.
    
    Args:
        category: Category name (DRAM, Storage, Package, Common, Others)
        limit: Maximum number of documents to return
        offset: Number of documents to skip
        
    Returns:
        Dictionary with category documents
    """
    try:
        if not rag_engine:
            raise HTTPException(status_code=500, detail="RAG engine not initialized")
        
        # Get all documents and filter by category
        all_docs = rag_engine.vector_store.get()
        category_docs = [
            doc for doc in all_docs 
            if 'metadata' in doc and doc['metadata'].get('category') == category
        ]
        
        # Apply pagination
        total = len(category_docs)
        end_index = min(offset + limit, total)
        paginated_docs = category_docs[offset:end_index]
        
        # Format documents for response
        formatted_docs = []
        for doc in paginated_docs:
            metadata = doc.get('metadata', {})
            formatted_docs.append({
                "content": doc.get('content', ''),
                "document_id": metadata.get('document_id', ''),
                "filename": metadata.get('filename', ''),
                "category": metadata.get('category', ''),
                "page": metadata.get('page', 'Unknown'),
                "section": metadata.get('section', 'Unknown'),
                "table_id": metadata.get('table_id', 'N/A'),
                "chunk_id": metadata.get('chunk_id', 0)
            })
        
        return {
            "category": category,
            "documents": formatted_docs,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": end_index < total
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting documents by category {category}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving category documents: {str(e)}")


@category_router.get("/{category}/search", summary="Search within category")
@handle_errors(ErrorType.API_CONNECTION, reraise=True)
async def search_within_category(
    category: str,
    query: str = Query(..., description="Search query"),
    k: Optional[int] = Query(5, description="Number of results to return"),
    similarity_threshold: Optional[float] = Query(0.7, description="Minimum similarity score")
):
    """
    Search for documents within a specific category.
    
    Args:
        category: Category name to search within
        query: Search query
        k: Number of results to return
        similarity_threshold: Minimum similarity score
        
    Returns:
        Dictionary with search results
    """
    try:
        if not rag_engine:
            raise HTTPException(status_code=500, detail="RAG engine not initialized")
        
        # Create category filter for search
        search_filter = {"category": category}
        
        # Perform search with category filter
        results = rag_engine.vector_store.similarity_search_with_score(
            query=query,
            k=k,
            filter=search_filter
        )
        
        # Filter by similarity threshold
        filtered_results = [
            (doc, score) for doc, score in results 
            if score >= similarity_threshold
        ]
        
        # Format results
        formatted_results = []
        for doc, score in filtered_results:
            metadata = doc.metadata
            formatted_results.append({
                "content": doc.page_content,
                "score": score,
                "document_id": metadata.get('document_id', ''),
                "filename": metadata.get('filename', ''),
                "category": metadata.get('category', ''),
                "page": metadata.get('page', 'Unknown'),
                "section": metadata.get('section', 'Unknown'),
                "table_id": metadata.get('table_id', 'N/A'),
                "chunk_id": metadata.get('chunk_id', 0)
            })
        
        return {
            "category": category,
            "query": query,
            "results": formatted_results,
            "total_found": len(formatted_results),
            "similarity_threshold": similarity_threshold
        }
        
    except Exception as e:
        logger.error(f"Error searching within category {category}: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching category: {str(e)}")


@category_router.get("/{category}/statistics", summary="Get category statistics")
@handle_errors(ErrorType.API_CONNECTION, reraise=True)
async def get_category_statistics(category: str):
    """
    Get detailed statistics for a specific category.
    
    Args:
        category: Category name
        
    Returns:
        Dictionary with category statistics
    """
    try:
        if not rag_engine:
            raise HTTPException(status_code=500, detail="RAG engine not initialized")
        
        # Get all documents and filter by category
        all_docs = rag_engine.vector_store.get()
        category_docs = [
            doc for doc in all_docs 
            if 'metadata' in doc and doc['metadata'].get('category') == category
        ]
        
        # Calculate statistics
        total_chunks = len(category_docs)
        unique_documents = len(set(
            doc['metadata'].get('document_id', '') 
            for doc in category_docs 
            if 'metadata' in doc
        ))
        
        # Page statistics
        pages = set()
        tables = set()
        sections = set()
        
        for doc in category_docs:
            metadata = doc.get('metadata', {})
            if metadata.get('page') and metadata['page'] != 'Unknown':
                pages.add(metadata['page'])
            if metadata.get('table_id') and metadata['table_id'] != 'N/A':
                tables.add(metadata['table_id'])
            if metadata.get('section') and metadata['section'] != 'Unknown':
                sections.add(metadata['section'])
        
        return {
            "category": category,
            "statistics": {
                "total_chunks": total_chunks,
                "unique_documents": unique_documents,
                "unique_pages": len(pages),
                "unique_tables": len(tables),
                "unique_sections": len(sections),
                "average_chunks_per_document": total_chunks / unique_documents if unique_documents > 0 else 0
            },
            "pages": sorted(list(pages))[:20],  # Show first 20 pages
            "tables": sorted(list(tables))[:10],  # Show first 10 tables
            "sections": sorted(list(sections))[:10]  # Show first 10 sections
        }
        
    except Exception as e:
        logger.error(f"Error getting category statistics for {category}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving category statistics: {str(e)}")


@category_router.delete("/{category}", summary="Delete category documents")
@handle_errors(ErrorType.API_CONNECTION, reraise=True)
async def delete_category(category: str):
    """
    Delete all documents from a specific category.
    
    Args:
        category: Category name to delete
        
    Returns:
        Dictionary with deletion result
    """
    try:
        if not rag_engine:
            raise HTTPException(status_code=500, detail="RAG engine not initialized")
        
        # Get documents to delete
        all_docs = rag_engine.vector_store.get()
        category_docs = [
            doc for doc in all_docs 
            if 'metadata' in doc and doc['metadata'].get('category') == category
        ]
        
        if not category_docs:
            return {
                "message": f"No documents found in category: {category}",
                "deleted_count": 0
            }
        
        # Get document IDs to delete
        doc_ids = [doc.id for doc in category_docs if hasattr(doc, 'id')]
        
        # Delete from vector store
        if doc_ids:
            rag_engine.vector_store.delete(ids=doc_ids)
        
        logger.info(f"Deleted {len(doc_ids)} documents from category: {category}")
        
        return {
            "message": f"Successfully deleted documents from category: {category}",
            "deleted_count": len(doc_ids)
        }
        
    except Exception as e:
        logger.error(f"Error deleting category {category}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting category: {str(e)}")
