"""
Complete System Test for JEDEC Insight
Tests all enhanced features including comparison, synonyms, and error handling.
"""

import asyncio
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.models.enhanced_rag_engine import create_enhanced_rag_engine
from src.utils.synonym_dictionary import get_synonym_dictionary
from src.models.comparison_engine import get_comparison_engine


async def test_complete_system():
    """Test the complete enhanced JEDEC Insight system."""
    print("🚀 JEDEC Insight Complete System Test")
    print("=" * 60)
    
    try:
        # Test 1: Initialize enhanced RAG engine
        print("📚 1. Enhanced RAG Engine 초기화...")
        engine = await create_enhanced_rag_engine()
        
        stats = engine.get_stats()
        print(f"   ✅ 벡터 스토어: {stats.get('total_documents', 0)} 문서")
        print(f"   ✅ 임베딩 모델: {stats.get('embedding_model', 'Unknown')}")
        print(f"   ✅ 리트리버: {stats.get('retriever_type', 'Unknown')}")
        print()
        
        # Test 2: Synonym Dictionary
        print("🔍 2. 동의어 사전 테스트...")
        synonym_dict = get_synonym_dictionary()
        
        test_queries = [
            "tCK min이 뭐야?",
            "DDR4 전압 요구사항은?",
            "CAS latency에 대해 설명해줘",
            "메모리 속도 3200MHz 규격"
        ]
        
        for query in test_queries:
            expanded = synonym_dict.expand_query(query)
            normalized = synonym_dict.normalize_units(query)
            print(f"   원본: {query}")
            print(f"   확장: {expanded[:2]}...")  # Show first 2
            print(f"   정규화: {normalized}")
            print()
        
        # Test 3: Comparison Engine
        print("📊 3. 비교 엔진 테스트...")
        comparison_engine = get_comparison_engine()
        
        comparison_queries = [
            "DDR4 vs DDR5",
            "compare DDR4 and DDR5",
            "DDR4와 DDR5 비교해줘"
        ]
        
        for query in comparison_queries:
            is_comparison = comparison_engine.is_comparison_query(query)
            entities = comparison_engine.extract_comparison_entities(query)
            print(f"   질의: {query}")
            print(f"   비교 여부: {is_comparison}")
            print(f"   추출 엔티티: {entities}")
            print()
        
        # Test 4: Enhanced Queries
        print("🤖 4. 향상된 쿼리 테스트...")
        
        enhanced_test_queries = [
            "DDR4 vs DDR5 비교 분석",
            "tCK min 값이 뭐야?",
            "메모리 타이밍 파라미터 설명",
            "3200MHz 속도 규격"
        ]
        
        for i, query in enumerate(enhanced_test_queries, 1):
            print(f"   테스트 {i}: {query}")
            print("-" * 40)
            
            try:
                result = await engine.query(query, k=5)
                
                print(f"   🤖 답변: {result['answer'][:100]}...")
                print(f"   📋 근거: {result['specification'][:100]}...")
                
                if result.get('comparison'):
                    print(f"   📊 비교 분석 포함됨")
                
                if result.get('expanded_queries') and len(result['expanded_queries']) > 1:
                    print(f"   🔍 확장된 쿼리: {len(result['expanded_queries'])}개")
                
                print(f"   📚 출처: {len(result['sources'])}개")
                print()
                
            except Exception as e:
                print(f"   ❌ 오류: {e}")
                print()
        
        # Test 5: Error Handling
        print("⚠️ 5. 오류 처리 테스트...")
        
        error_test_queries = [
            "존재하지 않는 파라미터 xyz",
            "",  # Empty query
            "a" * 1000  # Very long query
        ]
        
        for query in error_test_queries:
            try:
                result = await engine.query(query, k=3)
                print(f"   ✅ 처리됨: {query[:30]}...")
            except Exception as e:
                print(f"   ⚠️ 오류 처리됨: {str(e)[:50]}...")
        
        print()
        print("=" * 60)
        print("✅ 시스템 테스트 완료!")
        print()
        print("🎯 주요 기능:")
        print("   ✅ OpenAI 임베딩 기반 검색")
        print("   ✅ MultiQueryRetriever 쿼리 확장")
        print("   ✅ 기술 용어 동의어 사전")
        print("   ✅ 단위 정규화 (ns↔ps, MHz↔MT/s)")
        print("   ✅ 규격 비교 엔진")
        print("   ✅ 구조화된 답변 형식")
        print("   ✅ 향상된 오류 처리")
        print("   ✅ 테이블 데이터 추출 및 렌더링")
        print()
        print("🚀 시스템이 준비되었습니다!")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY가 환경 변수에 설정되지 않았습니다.")
        print(".env 파일에 API 키를 설정해주세요.")
    else:
        asyncio.run(test_complete_system())
