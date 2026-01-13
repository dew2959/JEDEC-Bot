"""
ChromaDB Vector Store Module for JEDEC Insight
Handles vector database operations for document storage and retrieval.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import json
from pathlib import Path
import uuid

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """ChromaDB wrapper for JEDEC Insight."""
    
    def __init__(self, persist_directory: str, collection_name: str = "jepec_documents"):
        """
        Initialize ChromaDB vector store.
        
        Args:
            persist_directory: Directory to persist the database
            collection_name: Name of the collection
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.collection_name = collection_name
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding function
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        )
        
        # Get or create collection
        self.collection = self._get_or_create_collection()
        
        logger.info(f"ChromaDB initialized at {self.persist_directory}")
    
    def _get_or_create_collection(self):
        """Get existing collection or create new one."""
        try:
            # Try to get existing collection
            collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Using existing collection: {self.collection_name}")
        except Exception:
            # Create new collection if it doesn't exist
            collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "JEDEC specification documents"}
            )
            logger.info(f"Created new collection: {self.collection_name}")
        
        return collection
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Add documents to the collection.
        
        Args:
            documents: List of document dictionaries with 'content' and 'metadata'
            
        Returns:
            List of document IDs
        """
        try:
            ids = []
            contents = []
            metadatas = []
            
            for doc in documents:
                # Generate unique ID
                doc_id = str(uuid.uuid4())
                ids.append(doc_id)
                
                # Extract content and metadata
                content = doc.get('content', '')
                contents.append(content)
                
                metadata = doc.get('metadata', {})
                metadata['document_id'] = doc_id
                metadatas.append(metadata)
            
            # Add to collection
            self.collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas
            )
            
            logger.info(f"Added {len(documents)} documents to collection")
            return ids
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise
    
    def query(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Query the collection for similar documents.
        
        Args:
            query_text: Query text
            n_results: Number of results to return
            
        Returns:
            Dictionary with query results
        """
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
            
            return {
                'query': query_text,
                'results': formatted_results,
                'total_results': len(formatted_results)
            }
            
        except Exception as e:
            logger.error(f"Error querying collection: {e}")
            return {'query': query_text, 'results': [], 'total_results': 0}
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by its ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document dictionary or None if not found
        """
        try:
            results = self.collection.get(ids=[doc_id])
            
            if results['ids']:
                return {
                    'id': results['ids'][0],
                    'content': results['documents'][0],
                    'metadata': results['metadatas'][0]
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {e}")
            return None
    
    def get_documents_by_metadata(self, metadata_filter: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get documents by metadata filter.
        
        Args:
            metadata_filter: Metadata filter dictionary
            
        Returns:
            List of matching documents
        """
        try:
            results = self.collection.get(
                where=metadata_filter
            )
            
            documents = []
            for i in range(len(results['ids'])):
                documents.append({
                    'id': results['ids'][i],
                    'content': results['documents'][i],
                    'metadata': results['metadatas'][i]
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error getting documents by metadata: {e}")
            return []
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False
    
    def delete_documents_by_metadata(self, metadata_filter: Dict[str, Any]) -> int:
        """
        Delete documents by metadata filter.
        
        Args:
            metadata_filter: Metadata filter dictionary
            
        Returns:
            Number of deleted documents
        """
        try:
            # Get documents to delete
            documents = self.get_documents_by_metadata(metadata_filter)
            doc_ids = [doc['id'] for doc in documents]
            
            if doc_ids:
                self.collection.delete(ids=doc_ids)
                logger.info(f"Deleted {len(doc_ids)} documents matching filter")
                return len(doc_ids)
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Error deleting documents by metadata: {e}")
            return 0
    
    def list_all_documents(self) -> List[Dict[str, Any]]:
        """
        List all documents in the collection.
        
        Returns:
            List of all documents
        """
        try:
            results = self.collection.get()
            
            documents = []
            for i in range(len(results['ids'])):
                documents.append({
                    'id': results['ids'][i],
                    'content': results['documents'][i],
                    'metadata': results['metadatas'][i]
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error listing all documents: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            
            # Get unique filenames
            documents = self.list_all_documents()
            filenames = set()
            for doc in documents:
                filename = doc['metadata'].get('filename', 'Unknown')
                filenames.add(filename)
            
            return {
                'collection_name': self.collection_name,
                'total_documents': count,
                'unique_files': len(filenames),
                'files': list(filenames),
                'persist_directory': str(self.persist_directory)
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {
                'collection_name': self.collection_name,
                'total_documents': 0,
                'unique_files': 0,
                'files': [],
                'persist_directory': str(self.persist_directory)
            }
    
    def reset_collection(self) -> bool:
        """
        Reset the entire collection.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete the collection
            self.client.delete_collection(name=self.collection_name)
            
            # Recreate it
            self.collection = self._get_or_create_collection()
            
            logger.info(f"Reset collection {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            return False
    
    def backup_collection(self, backup_path: str) -> bool:
        """
        Backup the collection to a file.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all documents
            documents = self.list_all_documents()
            
            # Save to JSON file
            backup_data = {
                'collection_name': self.collection_name,
                'documents': documents,
                'backup_timestamp': str(uuid.uuid4())
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Collection backed up to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error backing up collection: {e}")
            return False
    
    def restore_collection(self, backup_path: str) -> bool:
        """
        Restore collection from backup file.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load backup data
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Reset current collection
            self.reset_collection()
            
            # Restore documents
            if backup_data['documents']:
                self.add_documents(backup_data['documents'])
            
            logger.info(f"Collection restored from {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring collection: {e}")
            return False


# Utility functions
def create_vector_store(persist_directory: str, 
                       collection_name: str = "jepec_documents") -> ChromaVectorStore:
    """
    Create and initialize a ChromaDB vector store.
    
    Args:
        persist_directory: Directory to persist the database
        collection_name: Name of the collection
        
    Returns:
        Initialized ChromaVectorStore instance
    """
    return ChromaVectorStore(persist_directory, collection_name)


def load_document_chunks(file_path: str, 
                        chunk_size: int = 1000, 
                        chunk_overlap: int = 200) -> List[Dict[str, Any]]:
    """
    Load a document and split it into chunks.
    
    Args:
        file_path: Path to the document file
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of document chunks
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple chunking by paragraphs
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Create document dictionaries
        documents = []
        for i, chunk in enumerate(chunks):
            documents.append({
                'content': chunk,
                'metadata': {
                    'source': file_path,
                    'chunk_id': i,
                    'filename': Path(file_path).name
                }
            })
        
        return documents
        
    except Exception as e:
        logger.error(f"Error loading document chunks from {file_path}: {e}")
        return []
