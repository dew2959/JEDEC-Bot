"""
Main entry point for JEDEC Insight
Provides convenient commands to start the application.
"""

import os
import sys
import argparse
import subprocess
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.pdf_processor import PDFProcessor
from src.models.rag_engine import create_rag_engine


def start_backend():
    """Start the FastAPI backend server."""
    print("🚀 Starting FastAPI backend...")
    try:
        import uvicorn
        from src.backend.main import app
        
        host = os.getenv("API_HOST", "0.0.0.0")
        port = int(os.getenv("API_PORT", "8000"))
        reload = os.getenv("API_RELOAD", "True").lower() == "true"
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload
        )
    except Exception as e:
        print(f"❌ Error starting backend: {e}")
        sys.exit(1)


def start_frontend():
    """Start the Streamlit frontend."""
    print("🚀 Starting Streamlit frontend dashboard...")
    try:
        subprocess.run([
            "streamlit", "run", "src/frontend/dashboard.py",
            "--server.port", os.getenv("STREAMLIT_PORT", "8501"),
            "--server.address", os.getenv("STREAMLIT_HOST", "localhost"),
            "--server.headless", "false",
            "--browser.gatherUsageStats", "false"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting frontend: {e}")
        sys.exit(1)


async def ingest_documents_only():
    """Run ingestion only for already processed documents."""
    print("📚 Running document ingestion...")
    
    try:
        from ingest import DataIngestor
        
        processed_dir = os.getenv("PROCESSED_DATA_DIR", "./data/processed")
        chroma_path = os.getenv("CHROMA_DB_PATH", "./data/chroma")
        collection_name = os.getenv("CHROMA_COLLECTION_NAME", "jepec_documents")
        
        ingestor = DataIngestor(processed_dir, chroma_path, collection_name)
        result = await ingestor.run_full_ingestion()
        
        if result['status'] == 'success':
            print("✅ Ingestion completed successfully!")
            print(f"📊 Statistics: {result['stats']}")
        else:
            print(f"❌ Ingestion failed: {result['message']}")
            
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        sys.exit(1)


async def process_documents():
    """Process all PDF documents and index them."""
    print("📄 Processing PDF documents...")
    
    try:
        # Initialize components
        pdf_dir = os.getenv("PDF_INPUT_DIR", "./data/pdfs")
        output_dir = os.getenv("PROCESSED_DATA_DIR", "./data/processed")
        
        processor = PDFProcessor(pdf_dir, output_dir)
        
        # Process all PDFs
        processed_files = processor.process_all_pdfs()
        print(f"✅ Processed {len(processed_files)} PDF files")
        
        # Run ingestion
        from ingest import DataIngestor
        chroma_path = os.getenv("CHROMA_DB_PATH", "./data/chroma")
        collection_name = os.getenv("CHROMA_COLLECTION_NAME", "jepec_documents")
        
        ingestor = DataIngestor(output_dir, chroma_path, collection_name)
        result = await ingestor.run_full_ingestion()
        
        if result['status'] == 'success':
            print("✅ All documents processed and indexed successfully!")
            print(f"📊 Statistics: {result['stats']}")
        else:
            print(f"❌ Ingestion failed: {result['message']}")
        
    except Exception as e:
        print(f"❌ Error processing documents: {e}")
        sys.exit(1)


def setup_environment():
    """Setup the environment and create necessary directories."""
    print("🔧 Setting up environment...")
    
    directories = [
        "data/pdfs",
        "data/processed", 
        "data/chroma",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {directory}")
    
    # Check .env file
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .env file not found. Please create it with your configuration.")
    else:
        print("✅ .env file found")
    
    print("✅ Environment setup complete!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="JEDEC Insight - RAG-based JEDEC Document Analyzer")
    parser.add_argument("command", choices=["backend", "frontend", "process", "ingest", "setup", "all"], 
                       help="Command to run")
    parser.add_argument("--no-reload", action="store_true", 
                       help="Disable auto-reload for development")
    
    args = parser.parse_args()
    
    if args.command == "backend":
        if args.no_reload:
            os.environ["API_RELOAD"] = "False"
        start_backend()
    
    elif args.command == "frontend":
        start_frontend()
    
    elif args.command == "process":
        asyncio.run(process_documents())
    
    elif args.command == "ingest":
        asyncio.run(ingest_documents_only())
    
    elif args.command == "setup":
        setup_environment()
    
    elif args.command == "all":
        print("🚀 Starting complete JEDEC Insight system...")
        print("This will start both backend and frontend in separate processes.")
        print("Press Ctrl+C to stop all services.")
        
        # Start backend in background
        backend_process = subprocess.Popen([
            sys.executable, "run.py", "backend"
        ])
        
        # Wait a bit for backend to start
        import time
        time.sleep(3)
        
        try:
            # Start frontend in foreground
            start_frontend()
        except KeyboardInterrupt:
            print("\n🛑 Stopping services...")
            backend_process.terminate()
            backend_process.wait()
            print("✅ All services stopped")


if __name__ == "__main__":
    main()
