"""
Test Category-Based Ingestion for JEDEC Insight
Tests the enhanced ingestion system with folder-based categorization.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from ingest import EnhancedDataIngestion


async def test_category_ingestion():
    """Test the enhanced category-based ingestion system."""
    print("🧪 Testing Category-Based Ingestion")
    print("=" * 60)
    
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
    
    # Test 1: Category Statistics
    print("📊 Test 1: Category Statistics")
    print("-" * 30)
    
    stats = ingestion.get_category_statistics()
    print(f"Total files: {stats['total_files']}")
    print("Categories:")
    for category, count in stats["categories"].items():
        print(f"  {category}: {count} files")
    print()
    
    # Test 2: Category Extraction
    print("🔍 Test 2: Category Extraction")
    print("-" * 30)
    
    # Create test file paths
    test_paths = [
        Path(pdf_dir) / "dram" / "test_ddr4.pdf",
        Path(pdf_dir) / "storage" / "test_ssd.pdf",
        Path(pdf_dir) / "package" / "test_package.pdf",
        Path(pdf_dir) / "common" / "test_common.pdf",
        Path(pdf_dir) / "root_file.pdf"
    ]
    
    for test_path in test_paths:
        try:
            category = ingestion.extract_category_from_path(test_path)
            doc_info = ingestion.extract_document_info(test_path)
            print(f"Path: {test_path}")
            print(f"  Category: {category}")
            print(f"  Document Info: {doc_info['category']}")
            print()
        except Exception as e:
            print(f"Error with {test_path}: {e}")
    
    # Test 3: Document Creation with Metadata
    print("📝 Test 3: Document Metadata Creation")
    print("-" * 30)
    
    test_content = """
    # Test Section
    
    This is a test document for JEDEC specifications.
    
    ## Timing Parameters
    
    Page 1: This page contains timing information.
    
    | Parameter | Value | Unit |
    |-----------|--------|------|
    | tCK       | 0.75   | ns   |
    | tRCD      | 18     | ns   |
    | tRP       | 18     | ns   |
    
    Table 1: DDR4 timing parameters
    
    ## Voltage Specifications
    
    Page 2: Voltage requirements for DDR4.
    
    | Parameter | Value | Unit |
    |-----------|--------|------|
    | VDD       | 1.2    | V    |
    | VDDQ      | 1.2    | V    |
    """
    
    test_doc_info = {
        "document_id": "test_document",
        "filename": "test_document.pdf",
        "category": "DRAM",
        "relative_path": "dram/test_document.pdf",
        "full_path": str(Path(pdf_dir) / "dram" / "test_document.pdf"),
        "file_size": 1024
    }
    
    try:
        # Test document creation
        doc = ingestion.create_document_with_metadata(
            content=test_content,
            doc_info=test_doc_info,
            chunk_id=0,
            page="1",
            section="Timing Parameters",
            table_id="Table-1"
        )
        
        print("✅ Document created successfully:")
        print(f"  Content length: {len(doc.page_content)}")
        print("  Metadata:")
        for key, value in doc.metadata.items():
            print(f"    {key}: {value}")
        print()
        
    except Exception as e:
        print(f"❌ Error creating document: {e}")
    
    # Test 4: Markdown Processing
    print("📄 Test 4: Markdown Processing")
    print("-" * 30)
    
    # Create a test markdown file
    test_md_path = Path(processed_dir) / "test_processed.md"
    
    try:
        with open(test_md_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # Process the markdown file
        documents = ingestion.process_markdown_file(test_md_path, test_doc_info)
        
        print(f"✅ Markdown processed successfully:")
        print(f"  Chunks created: {len(documents)}")
        
        for i, doc in enumerate(documents[:2]):  # Show first 2 chunks
            print(f"  Chunk {i+1}:")
            print(f"    Page: {doc.metadata.get('page', 'Unknown')}")
            print(f"    Section: {doc.metadata.get('section', 'Unknown')}")
            print(f"    Table ID: {doc.metadata.get('table_id', 'N/A')}")
            print(f"    Category: {doc.metadata.get('category', 'Unknown')}")
            print(f"    Content preview: {doc.page_content[:100]}...")
            print()
        
        # Clean up test file
        test_md_path.unlink()
        
    except Exception as e:
        print(f"❌ Error processing markdown: {e}")
    
    # Test 5: Single Category Ingestion
    print("📂 Test 5: Single Category Ingestion")
    print("-" * 30)
    
    try:
        # Test ingestion for DRAM category
        result = await ingestion.ingest_category("DRAM")
        
        if "error" in result:
            print(f"❌ Category ingestion error: {result['error']}")
        elif "message" in result:
            print(f"ℹ️ {result['message']}")
        else:
            print(f"✅ Category ingestion completed:")
            print(f"  Category: {result['category']}")
            print(f"  Files processed: {result['processed_files']}/{result['total_files']}")
            print(f"  Total chunks: {result['total_chunks']}")
            if result['failed_files']:
                print(f"  Failed files: {len(result['failed_files'])}")
        
    except Exception as e:
        print(f"❌ Error in category ingestion: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Category Ingestion Tests Completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_category_ingestion())
