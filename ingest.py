"""
Enhanced Data Ingestion Pipeline for JEDEC Insight
Processes PDF files and ingests them into ChromaDB with category metadata support.
Handles folder-based categorization (DRAM, Storage, Package, Common).
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any
import asyncio
from dotenv import load_dotenv

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from src.utils.pdf_processor import PDFProcessor
from src.models.enhanced_rag_engine import create_enhanced_rag_engine

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedDataIngestion:
    """Enhanced data ingestion with category metadata support."""
    
    def __init__(self, pdf_dir: str, processed_dir: str, chroma_path: str, collection_name: str):
        """
        Initialize enhanced data ingestion.
        
        Args:
            pdf_dir: Directory containing PDF files with category subfolders
            processed_dir: Directory for processed markdown files
            chroma_path: Path to ChromaDB storage
            collection_name: Name of the collection
        """
        self.pdf_dir = Path(pdf_dir)
        self.processed_dir = Path(processed_dir)
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        
        # Initialize components
        self.pdf_processor = PDFProcessor(pdf_dir, processed_dir)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,  # Optimized for table preservation
            chunk_overlap=300,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Category mapping
        self.category_mapping = {
            "dram": "DRAM",
            "storage": "Storage", 
            "package": "Package",
            "common": "Common",
            "others": "Others"
        }
        
        # Create directories
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Enhanced data ingestion initialized")
        logger.info(f"PDF directory: {self.pdf_dir}")
        logger.info(f"Processed directory: {self.processed_dir}")
        logger.info(f"ChromaDB path: {self.chroma_path}")
    
    def extract_category_from_path(self, file_path: Path) -> str:
        """
        Extract category from file path.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Category string
        """
        # Get relative path from pdf_dir
        relative_path = file_path.relative_to(self.pdf_dir)
        
        # Extract folder name (first level subdirectory)
        if len(relative_path.parts) > 1:
            folder_name = relative_path.parts[0].lower()
            
            # Map to standardized category
            for key, category in self.category_mapping.items():
                if key in folder_name:
                    return category
            
            # If no mapping found, use folder name as category
            return folder_name.title()
        
        # If file is in root directory, categorize as "Others"
        return self.category_mapping["others"]
    
    def extract_document_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract document information from file path.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary with document information
        """
        category = self.extract_category_from_path(file_path)
        filename = file_path.stem
        relative_path = file_path.relative_to(self.pdf_dir)
        
        return {
            "document_id": filename,
            "filename": file_path.name,
            "category": category,
            "relative_path": str(relative_path),
            "full_path": str(file_path),
            "file_size": file_path.stat().st_size if file_path.exists() else 0
        }
    
    def create_document_with_metadata(self, content: str, doc_info: Dict[str, Any], 
                                 chunk_id: int, page: str = "Unknown", 
                                 section: str = "Unknown", table_id: str = "N/A") -> Document:
        """
        Create a Document with enhanced metadata.
        
        Args:
            content: Text content
            doc_info: Document information
            chunk_id: Chunk identifier
            page: Page number
            section: Section title
            table_id: Table identifier
            
        Returns:
            Document with metadata
        """
        metadata = {
            "document_id": doc_info["document_id"],
            "filename": doc_info["filename"],
            "category": doc_info["category"],
            "relative_path": doc_info["relative_path"],
            "chunk_id": chunk_id,
            "page": page,
            "section": section,
            "table_id": table_id,
            "file_size": doc_info["file_size"]
        }
        
        return Document(page_content=content, metadata=metadata)
    
    def process_markdown_file(self, md_file: Path, doc_info: Dict[str, Any]) -> List[Document]:
        """
        Process a markdown file and create documents with metadata.
        
        Args:
            md_file: Path to markdown file
            doc_info: Document information
            
        Returns:
            List of Document objects
        """
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            documents = []
            
            # Split content into chunks
            chunks = self.text_splitter.split_text(content)
            
            for i, chunk in enumerate(chunks):
                # Extract metadata from chunk
                page = "Unknown"
                section = "Unknown"
                table_id = "N/A"
                
                # Try to extract page number from chunk
                lines = chunk.split('\n')
                for line in lines:
                    if line.strip().startswith('#'):
                        section = line.strip().lstrip('#').strip()
                    elif 'page' in line.lower() and any(char.isdigit() for char in line):
                        # Extract page number
                        import re
                        page_match = re.search(r'page\s*(\d+)', line, re.IGNORECASE)
                        if page_match:
                            page = page_match.group(1)
                    elif 'table' in line.lower() and any(char.isdigit() for char in line):
                        # Extract table ID
                        import re
                        table_match = re.search(r'table\s*(\d+)', line, re.IGNORECASE)
                        if table_match:
                            table_id = f"Table-{table_match.group(1)}"
                
                # Create document with metadata
                doc = self.create_document_with_metadata(
                    content=chunk,
                    doc_info=doc_info,
                    chunk_id=i,
                    page=page,
                    section=section,
                    table_id=table_id
                )
                documents.append(doc)
            
            logger.info(f"Processed {md_file.name}: {len(documents)} chunks")
            return documents
            
        except Exception as e:
            logger.error(f"Error processing markdown file {md_file}: {e}")
            return []
    
    async def ingest_all_files(self) -> Dict[str, Any]:
        """
        Ingest all PDF files with category metadata.
        
        Returns:
            Dictionary with ingestion statistics
        """
        logger.info("Starting enhanced data ingestion with category support...")
        
        # Initialize RAG engine
        rag_engine = await create_enhanced_rag_engine()
        
        # Statistics
        stats = {
            "total_files": 0,
            "processed_files": 0,
            "failed_files": [],
            "categories": {},
            "total_chunks": 0
        }
        
        # Find all PDF files
        pdf_files = list(self.pdf_dir.rglob("*.pdf"))
        stats["total_files"] = len(pdf_files)
        
        logger.info(f"Found {len(pdf_files)} PDF files")
        
        # Process each PDF file
        for pdf_file in pdf_files:
            try:
                # Extract document information
                doc_info = self.extract_document_info(pdf_file)
                category = doc_info["category"]
                
                # Update category statistics
                if category not in stats["categories"]:
                    stats["categories"][category] = {"files": 0, "chunks": 0}
                stats["categories"][category]["files"] += 1
                
                logger.info(f"Processing {doc_info['filename']} (Category: {category})")
                
                # Process PDF to markdown
                processed_files = self.pdf_processor.process_pdf(pdf_file)
                
                if processed_files:
                    # Process each markdown file
                    all_documents = []
                    for md_file in processed_files:
                        documents = self.process_markdown_file(md_file, doc_info)
                        all_documents.extend(documents)
                    
                    # Add documents to vector store
                    if all_documents:
                        await rag_engine.add_documents(all_documents)
                        stats["total_chunks"] += len(all_documents)
                        stats["categories"][category]["chunks"] += len(all_documents)
                        stats["processed_files"] += 1
                        
                        logger.info(f"Added {len(all_documents)} chunks from {doc_info['filename']}")
                    else:
                        logger.warning(f"No documents created from {doc_info['filename']}")
                else:
                    logger.warning(f"No processed files for {doc_info['filename']}")
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {e}")
                stats["failed_files"].append(str(pdf_file))
        
        # Log final statistics
        logger.info("Enhanced ingestion completed!")
        logger.info(f"Total files: {stats['total_files']}")
        logger.info(f"Processed files: {stats['processed_files']}")
        logger.info(f"Failed files: {len(stats['failed_files'])}")
        logger.info(f"Total chunks: {stats['total_chunks']}")
        logger.info("Categories processed:")
        for category, cat_stats in stats["categories"].items():
            logger.info(f"  {category}: {cat_stats['files']} files, {cat_stats['chunks']} chunks")
        
        return stats
    
    async def ingest_category(self, category: str) -> Dict[str, Any]:
        """
        Ingest files from a specific category.
        
        Args:
            category: Category to process (DRAM, Storage, Package, Common)
            
        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Ingesting files from category: {category}")
        
        # Find files in specific category folder
        category_dir = self.pdf_dir / category.lower()
        if not category_dir.exists():
            logger.error(f"Category directory not found: {category_dir}")
            return {"error": f"Category directory not found: {category}"}
        
        pdf_files = list(category_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in category: {category}")
            return {"message": f"No PDF files found in category: {category}"}
        
        # Initialize RAG engine
        rag_engine = await create_enhanced_rag_engine()
        
        stats = {
            "category": category,
            "total_files": len(pdf_files),
            "processed_files": 0,
            "failed_files": [],
            "total_chunks": 0
        }
        
        # Process files in this category
        for pdf_file in pdf_files:
            try:
                doc_info = self.extract_document_info(pdf_file)
                logger.info(f"Processing {doc_info['filename']} from {category}")
                
                # Process and ingest
                processed_files = self.pdf_processor.process_pdf(pdf_file)
                
                if processed_files:
                    all_documents = []
                    for md_file in processed_files:
                        documents = self.process_markdown_file(md_file, doc_info)
                        all_documents.extend(documents)
                    
                    if all_documents:
                        await rag_engine.add_documents(all_documents)
                        stats["total_chunks"] += len(all_documents)
                        stats["processed_files"] += 1
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {e}")
                stats["failed_files"].append(str(pdf_file))
        
        logger.info(f"Category {category} ingestion completed: {stats['processed_files']}/{stats['total_files']} files")
        return stats
    
    def get_category_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about files by category.
        
        Returns:
            Dictionary with category statistics
        """
        stats = {
            "categories": {},
            "total_files": 0
        }
        
        # Scan all category directories
        for category_key, category_name in self.category_mapping.items():
            if category_key == "others":
                continue  # Handle separately
            
            category_dir = self.pdf_dir / category_key
            if category_dir.exists():
                pdf_files = list(category_dir.glob("*.pdf"))
                stats["categories"][category_name] = len(pdf_files)
                stats["total_files"] += len(pdf_files)
        
        # Handle files in root directory (Others)
        root_files = list(self.pdf_dir.glob("*.pdf"))
        if root_files:
            stats["categories"][self.category_mapping["others"]] = len(root_files)
            stats["total_files"] += len(root_files)
        
        return stats


async def main():
    """Main ingestion function."""
    # Configuration
    pdf_dir = os.getenv("PDF_INPUT_DIR", "./data/pdfs")
    processed_dir = os.getenv("PROCESSED_DATA_DIR", "./data/processed")
    chroma_path = os.getenv("CHROMA_DB_PATH", "./data/chroma")
    collection_name = os.getenv("CHROMA_COLLECTION_NAME", "jepec_documents")
    
    # Initialize ingestion
    ingestion = EnhancedDataIngestion(
        pdf_dir=pdf_dir,
        processed_dir=processed_dir,
        chroma_path=chroma_path,
        collection_name=collection_name
    )
    
    # Show category statistics
    print("📊 Category Statistics:")
    stats = ingestion.get_category_statistics()
    for category, count in stats["categories"].items():
        print(f"  {category}: {count} files")
    print(f"  Total: {stats['total_files']} files")
    print()
    
    # Ingest all files
    print("🚀 Starting enhanced ingestion...")
    result = await ingestion.ingest_all_files()
    
    print("\n✅ Ingestion completed!")
    print(f"📄 Processed: {result['processed_files']}/{result['total_files']} files")
    print(f"📚 Total chunks: {result['total_chunks']}")
    
    if result['failed_files']:
        print(f"❌ Failed files: {len(result['failed_files'])}")
        for failed_file in result['failed_files']:
            print(f"  - {failed_file}")


if __name__ == "__main__":
    asyncio.run(main())
