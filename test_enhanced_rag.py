"""
Test script for Enhanced RAG Engine
Demonstrates the enhanced features with structured responses.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.models.enhanced_rag_engine import create_enhanced_rag_engine


async def test_enhanced_rag():
    """Test the enhanced RAG engine with various queries."""
    print("🚀 JEDEC Insight Enhanced RAG Engine Test")
    print("=" * 60)
    
    try:
        # Initialize engine
        print("📚 Initializing Enhanced RAG Engine...")
        engine = await create_enhanced_rag_engine()
        
        # Get stats
        stats = engine.get_stats()
        print(f"📊 Vector Store Stats:")
        print(f"   Total Chunks: {stats.get('total_chunks', 0)}")
        print(f"   Table Chunks: {stats.get('table_chunks', 0)}")
        print(f"   Text Chunks: {stats.get('text_chunks', 0)}")
        print(f"   Documents: {stats.get('total_documents', 0)}")
        print(f"   Embedding Model: {stats.get('embedding_model', 'Unknown')}")
        print(f"   Retriever Type: {stats.get('retriever_type', 'Unknown')}")
        print()
        
        # Test queries
        test_queries = [
            "tCK min이 뭐야?",
            "DDR4의 전압 요구사항은?",
            "JEDEC 메모리 규격의 주요 특징은?",
            "CAS latency에 대해 설명해줘",
            "메모리 타이밍 파라미터들의 관계는?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"🔍 Test {i}: {query}")
            print("-" * 40)
            
            # Get answer
            result = await engine.query(query, k=5)
            
            # Display structured response
            print("🤖 [답변]")
            print(result['answer'])
            print()
            
            print("📋 [근거 규격]")
            print(result['specification'])
            print()
            
            print("📝 [추가 참고사항]")
            print(result['additional_notes'])
            print()
            
            # Show sources
            if result['sources']:
                print("📚 출처:")
                for j, source in enumerate(result['sources'][:3], 1):  # Show top 3 sources
                    print(f"   {j}. {source.get('document_id', 'Unknown')}")
                    print(f"      테이블 ID: {source.get('table_id', 'N/A')}")
                    print(f"      페이지: {source.get('page', 'Unknown')}")
                    print(f"      섹션: {source.get('section', 'Unknown')}")
                    print()
            
            # Show multi-query analysis
            analysis = await engine.multi_query_analysis(query)
            if analysis['generated_queries']:
                print("🔄 생성된 검색 쿼리:")
                for j, gen_query in enumerate(analysis['generated_queries'], 1):
                    print(f"   {j}. {gen_query}")
                print()
            
            print("=" * 60)
            print()
    
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenAI API key in the .env file")
    else:
        asyncio.run(test_enhanced_rag())
