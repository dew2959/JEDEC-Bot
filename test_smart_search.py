"""
Test Smart Category-Based Search for JEDEC Insight
Tests the enhanced query analysis and category detection system.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.models.enhanced_rag_engine import create_enhanced_rag_engine
from src.utils.category_detector import analyze_user_query, get_search_strategy


async def test_smart_search():
    """Test the smart category-based search system."""
    print("🧠 JEDEC Insight Smart Search Test")
    print("=" * 60)
    
    try:
        # Initialize enhanced RAG engine
        engine = await create_enhanced_rag_engine()
        
        # Test queries with different categories and intents
        test_queries = [
            # DRAM-specific queries
            {
                "query": "DDR4의 tCK 최솟값은?",
                "expected_category": "DRAM",
                "description": "DRAM 타이밍 파라미터 질의"
            },
            {
                "query": "CAS latency 12-15-15 규격",
                "expected_category": "DRAM",
                "description": "DRAM CAS 레이턴시 질의"
            },
            {
                "query": "메모리 클럭 속도 3200MHz",
                "expected_category": "DRAM",
                "description": "DRAM 주파수 관련 질의"
            },
            
            # Storage-specific queries
            {
                "query": "SSD의 내구성 평가 방법",
                "expected_category": "Storage",
                "description": "저장장치 내구성 질의"
            },
            {
                "query": "NVMe 프로토콜 사양",
                "expected_category": "Storage",
                "description": "저장장치 인터페이스 질의"
            },
            {
                "query": "플래시 메모리 wear leveling",
                "expected_category": "Storage",
                "description": "플래시 저장장치 질의"
            },
            
            # Package-specific queries
            {
                "query": "BGA 패키지 핀 수 계산",
                "expected_category": "Package",
                "description": "패키징 관련 질의"
            },
            {
                "query": "QFN 패키지 치수",
                "expected_category": "Package",
                "description": "패키징 형태 질의"
            },
            {
                "query": "PCB 기판 설계 규격",
                "expected_category": "Package",
                "description": "패키징 기판 관련 질의"
            },
            
            # Common/JEDEC queries
            {
                "query": "JEDEC 동작 전압 규격",
                "expected_category": "Common",
                "description": "일반 JEDEC 규격 질의"
            },
            {
                "query": "전력 소비량 테스트 방법",
                "expected_category": "Common",
                "description": "전력 관련 질의"
            },
            {
                "query": "온도 사이클 테스트",
                "expected_category": "Common",
                "description": "열적 특성 질의"
            },
            
            # Comparison queries
            {
                "query": "DDR4 vs DDR5 성능 비교",
                "expected_category": ["DRAM", "DRAM"],
                "expected_comparison": True,
                "description": "DRAM 규격 비교 질의"
            },
            {
                "query": "SSD와 HDD의 차이점",
                "expected_category": ["Storage", "Storage"],
                "expected_comparison": True,
                "description": "저장장치 비교 질의"
            },
            {
                "query": "BGA와 QFN 패키지 비교",
                "expected_category": ["Package", "Package"],
                "expected_comparison": True,
                "description": "패키징 비교 질의"
            },
            
            # Ambiguous queries
            {
                "query": "메모리 규격 요약",
                "expected_category": "DRAM",
                "description": "모호한 메모리 질의"
            },
            {
                "query": "저장장치 인터페이스 종류",
                "expected_category": "Storage",
                "description": "모호한 저장장치 질의"
            }
        ]
        
        print(f"📋 총 {len(test_queries)}개 테스트 쿼리 실행")
        print()
        
        results = []
        
        for i, test_case in enumerate(test_queries, 1):
            print(f"🔍 테스트 {i}: {test_case['description']}")
            print(f"질의: {test_case['query']}")
            print("-" * 40)
            
            # Analyze query
            analysis = analyze_user_query(test_case['query'])
            strategy = get_search_strategy(test_case['query'])
            
            print(f"📊 쿼리 분석:")
            print(f"  감지된 카테고리: {analysis['detected_categories']}")
            print(f"  주요 카테고리: {analysis['primary_category']}")
            print(f"  신뢰도: {analysis['confidence']:.2f}")
            print(f"  비교 질의: {analysis['is_comparison']}")
            print(f"  검색 전략: {strategy['approach']}")
            
            # Execute search
            try:
                result = await engine.query(test_case['query'], k=5)
                
                # Evaluate results
                success = True
                issues = []
                
                # Check if expected category matches detected
                if 'expected_category' in test_case:
                    expected = test_case['expected_category']
                    if isinstance(expected, list):
                        # For comparison queries, check if all expected categories are detected
                        if not all(cat in analysis['detected_categories'] for cat in expected):
                            success = False
                            issues.append(f"카테고리 검출 실패: 기대 {expected}, 감지 {analysis['detected_categories']}")
                    else:
                        if expected not in analysis['detected_categories']:
                            success = False
                            issues.append(f"카테고리 검출 실패: 기대 {expected}, 감지 {analysis['detected_categories']}")
                
                # Check comparison detection
                if test_case.get('expected_comparison', False) != analysis['is_comparison']:
                    success = False
                    issues.append("비교 질의 감지 실패")
                
                # Store result
                test_result = {
                    "test_id": i,
                    "query": test_case['query'],
                    "description": test_case['description'],
                    "expected_category": test_case.get('expected_category'),
                    "analysis": analysis,
                    "strategy": strategy,
                    "result": result,
                    "success": success,
                    "issues": issues
                }
                
                results.append(test_result)
                
                # Display results
                status_icon = "✅" if success else "❌"
                print(f"{status_icon} 검색 결과:")
                print(f"  답변 길이: {len(result['answer'])}자")
                print(f"  출처 수: {len(result['sources'])}개")
                print(f"  확장 쿼리: {len(result.get('expanded_queries', []))}개")
                
                if result.get('comparison'):
                    print(f"  🔄 비교 분석 포함됨")
                
                if issues:
                    print(f"  ⚠️ 문제점:")
                    for issue in issues:
                        print(f"    - {issue}")
                
                print()
                
            except Exception as e:
                print(f"❌ 검색 오류: {e}")
                results.append({
                    "test_id": i,
                    "query": test_case['query'],
                    "description": test_case['description'],
                    "error": str(e),
                    "success": False
                })
            
            print("=" * 60)
            print()
        
        # Summary
        successful_tests = sum(1 for r in results if r.get('success', False))
        total_tests = len(results)
        
        print("📊 테스트 결과 요약")
        print("=" * 60)
        print(f"총 테스트: {total_tests}")
        print(f"성공: {successful_tests}")
        print(f"실패: {total_tests - successful_tests}")
        print(f"성공률: {(successful_tests/total_tests)*100:.1f}%")
        print()
        
        # Category detection accuracy
        category_accuracy = {}
        for test_case in test_queries:
            if 'expected_category' in test_case and 'analysis' in results[test_case['test_id']-1]:
                expected = test_case['expected_category']
                detected = results[test_case['test_id']-1]['analysis']['detected_categories']
                if isinstance(expected, list):
                    # For comparison queries
                    category_accuracy['comparison'] = category_accuracy.get('comparison', 0) + 1
                    if all(cat in detected for cat in expected):
                        category_accuracy['comparison_success'] = category_accuracy.get('comparison_success', 0) + 1
                else:
                    category_accuracy[expected] = category_accuracy.get(expected, 0) + 1
                    if expected in detected:
                        category_accuracy[f'{expected}_success'] = category_accuracy.get(f'{expected}_success', 0) + 1
        
        print("📂 카테고리별 정확도:")
        for category, total in category_accuracy.items():
            if category.endswith('_success'):
                continue
            success_key = f'{category}_success'
            success_count = category_accuracy.get(success_key, 0)
            accuracy = (success_count / total) * 100 if total > 0 else 0
            print(f"  {category}: {accuracy:.1f}% ({success_count}/{total})")
        
        print()
        print("🎉 스마트 검색 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_smart_search())
