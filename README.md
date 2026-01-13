# JEDEC Insight

RAG-based chatbot for analyzing JEDEC specification documents with advanced table extraction, comparison features, and intelligent synonym handling.

## 🎯 Project Overview

JEDEC Insight is a sophisticated document analysis system designed specifically for JEDEC specification documents. The system excels at extracting and preserving complex table structures from PDF documents, converting them to Markdown format, and enabling intelligent querying through a RAG (Retrieval-Augmented Generation) architecture with enhanced comparison capabilities and technical term understanding.

## 🏗️ Architecture

### Technology Stack
- **Backend**: FastAPI (Python)
- **Frontend**: Streamlit Dashboard
- **AI Framework**: LangChain with OpenAI
- **Vector Database**: ChromaDB
- **PDF Processing**: PyMuPDF + Unstructured
- **Embeddings**: OpenAI text-embedding-ada-002
- **Comparison Engine**: Custom specification comparison
- **Synonym Dictionary**: Technical term normalization

### 🚀 Core Features
- 📄 **Advanced PDF Processing**: Dual extraction using PyMuPDF and Unstructured
- 📊 **Table Preservation**: Complex table structures converted to Markdown without data loss
- 🔍 **Intelligent Search**: Semantic search with MultiQueryRetriever and synonym expansion
- 💬 **Natural Language Queries**: Ask questions in natural language about JEDEC specs
- 📚 **Source Attribution**: All answers include source references with clickable page badges
- 🔄 **Specification Comparison**: Compare DDR4 vs DDR5 and other specifications
- 🎯 **Technical Term Understanding**: Handles unit conversions (ns↔ps, MHz↔MT/s)
- 📊 **Table Rendering**: Engineers can copy table data in DataFrame format
- ⚠️ **Enhanced Error Handling**: Comprehensive error recovery and user guidance

## 📁 Project Structure

```
jedec_chatbot_proj/
├── src/
│   ├── backend/           # FastAPI backend
│   │   ├── __init__.py
│   │   └── main.py       # API endpoints and server
│   ├── frontend/         # Streamlit dashboard
│   │   ├── __init__.py
│   │   ├── app.py        # Original interface
│   │   └── dashboard.py  # Enhanced dashboard
│   ├── models/           # AI and database models
│   │   ├── __init__.py
│   │   ├── rag_engine.py # Basic RAG implementation
│   │   ├── enhanced_rag_engine.py # Enhanced RAG with comparison
│   │   ├── comparison_engine.py # Specification comparison
│   │   └── vector_store.py # ChromaDB wrapper
│   ├── utils/            # Utility modules
│   │   ├── __init__.py
│   │   ├── pdf_processor.py # PDF processing logic
│   │   ├── synonym_dictionary.py # Technical term handling
│   │   └── error_handling.py # Enhanced error management
│   └── __init__.py
├── data/
│   ├── pdfs/             # Input PDF files
│   ├── processed/        # Processed Markdown files
│   └── chroma/           # Vector database storage
├── tests/                # Test files
├── config/               # Configuration files
├── requirements.txt      # Python dependencies
├── .env                 # Environment variables
├── run.py               # Main launcher script
├── ingest.py            # Data ingestion pipeline
├── test_enhanced_rag.py # Enhanced RAG tests
└── test_complete_system.py # Complete system tests
```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone the project
cd jedec_chatbot_proj

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows
source venv/bin/activate  # On Unix

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Edit the `.env` file with your settings:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo

# Application Configuration
APP_NAME=JEDEC Insight
DEBUG=True

# Database Configuration
CHROMA_DB_PATH=./data/chroma
CHROMA_COLLECTION_NAME=jepec_documents

# File Processing
PDF_INPUT_DIR=./data/pdfs
PROCESSED_DATA_DIR=./data/processed
```

### 3. Start the Services

#### Method 1: Complete System
```bash
python run.py all
```

#### Method 2: Individual Services
```bash
# Backend (FastAPI)
python run.py backend

# Frontend (Enhanced Dashboard)
python run.py frontend
```

#### Method 3: Process Documents First
```bash
# Process all PDFs and ingest to vector store
python run.py process

# Or just ingest already processed files
python run.py ingest
```

### 4. Access the Application

- **Enhanced Dashboard**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs

## 📖 Usage Examples

### Enhanced Query Capabilities

#### Basic Queries
```bash
# Technical specifications
"What is the minimum tCK for DDR4?"
"DDR4 voltage requirements"
"CAS latency specifications"

# With unit variations
"tCK in picoseconds"
"3200MT/s memory speed"
"1.2V operating voltage"
```

#### Comparison Queries
```bash
# Specification comparisons
"DDR4 vs DDR5 comparison"
"Compare DDR4 and DDR5 timing parameters"
"DDR4와 DDR5 전압 요구사항 비교"

# Feature comparisons
"ECC vs non-ECC performance"
"Registered vs unbuffered DIMM"
```

#### API Usage

##### Upload and Process PDF
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

##### Enhanced Query with Comparison
```bash
curl -X POST "http://localhost:8000/query" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "DDR4 vs DDR5 comparison",
    "k": 5
  }'
```

##### Response Structure
```json
{
  "answer": "DDR5 offers significant improvements over DDR4...",
  "specification": "Based on JEDEC standards...",
  "additional_notes": "Key differences include...",
  "comparison": "## DDR4 vs DDR5 비교 분석\n\n### 주요 차이점...",
  "comparison_table": [
    {"Specification": "TCK", "DDR4": "0.75ns", "DDR5": "0.5ns"},
    {"Specification": "VDD", "DDR4": "1.2V", "DDR5": "1.1V"}
  ],
  "sources": [...],
  "expanded_queries": ["ddr4 vs ddr5", "compare ddr4 and ddr5"],
  "is_comparison": true
}
```

## 🔧 Advanced Features

### 1. Synonym Dictionary & Unit Conversion

The system automatically understands and converts:

- **Timing units**: ns ↔ ps, μs, ms
- **Frequency units**: MHz ↔ MT/s, GHz ↔ GT/s  
- **Voltage units**: V ↔ mV ↔ μV
- **Technical terms**: tCK, CAS latency, DDR4 ↔ PC4, etc.

### 2. Comparison Engine

Automatic detection and analysis of comparison queries:

- Identifies entities to compare (DDR4, DDR5, etc.)
- Extracts technical parameters from documents
- Generates structured comparison tables
- Provides detailed analysis summaries

### 3. Enhanced Error Handling

Comprehensive error management with:

- **PDF Processing Errors**: File validation, size limits, corruption detection
- **API Errors**: Timeout handling, retry logic, connection recovery
- **User Guidance**: Friendly error messages and suggestions
- **System Monitoring**: Error tracking and threshold alerts

### 4. Table Data Rendering

Engineers can easily copy technical data:

- **DataFrame Display**: Clean, sortable table format
- **Copy-Friendly Text**: Plain text format for easy copying
- **Source Attribution**: Direct links to original document pages

## 🧪 Testing

### Run Complete System Test
```bash
python test_complete_system.py
```

### Test Enhanced RAG Features
```bash
python test_enhanced_rag.py
```

### Test Individual Components
```bash
# Test PDF processing
python -c "from src.utils.pdf_processor import PDFProcessor; print('PDF processor OK')"

# Test synonym dictionary
python -c "from src.utils.synonym_dictionary import get_synonym_dictionary; print('Synonym dict OK')"

# Test comparison engine
python -c "from src.models.comparison_engine import get_comparison_engine; print('Comparison engine OK')"
```

## 📊 Performance Optimization

### Vector Database Optimization
- Use OpenAI embeddings for better semantic understanding
- Implement similarity score thresholds for relevance filtering
- Regular maintenance and optimization of ChromaDB

### Query Enhancement
- MultiQueryRetriever for better query expansion
- Synonym dictionary for technical term normalization
- Unit conversion for consistent parameter matching

### Error Recovery
- Exponential backoff for API retries
- Graceful degradation on service failures
- User-friendly error messages with actionable suggestions

## 🔒 Security Considerations

- API keys loaded from environment variables only
- No sensitive data logged or exposed
- File upload validation and sanitization
- CORS configuration for production environments
- Error information sanitization for user responses

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests for new functionality
4. Ensure all tests pass
5. Submit a pull request with detailed description

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

#### PDF Processing Errors
- Ensure PDFs are not password-protected
- Check file permissions on input/output directories
- Verify sufficient disk space for processed files
- Maximum file size: 50MB

#### API Connection Issues
- Check if FastAPI server is running on port 8000
- Verify OpenAI API key validity and quota
- Check network connectivity and firewall settings
- Monitor API rate limits and usage

#### Memory/Performance Issues
- Reduce chunk size for large documents (default: 1500)
- Monitor ChromaDB memory usage
- Consider using smaller embedding models for resource constraints
- Implement document batching for large datasets

#### Comparison Query Issues
- Ensure both entities exist in the indexed documents
- Check spelling of technical terms (DDR4, DDR5, etc.)
- Verify sufficient context for parameter extraction
- Review comparison results for accuracy

### Debug Mode

Enable debug logging:
```env
LOG_LEVEL=DEBUG
DEBUG=True
```

### System Health Check

```bash
# Check API health
curl http://localhost:8000/health

# Check vector store stats
python -c "
from src.models.enhanced_rag_engine import create_enhanced_rag_engine
import asyncio
async def check():
    engine = await create_enhanced_rag_engine()
    print(engine.get_stats())
asyncio.run(check())
"
```

---

**JEDEC Insight** - Making JEDEC specifications accessible, comparable, and searchable through advanced AI technology.
