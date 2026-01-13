"""
Test Agentic Search Workflow for JEDEC Insight
Tests the complete agentic search system with JESD21C knowledge integration.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.models.enhanced_rag_engine import create_enhanced_rag_engine
from src.utils.agentic_search import perform_agentic_search
from src.utils.category_detector import analyze_user_query


async def test_agentic_workflow():
    """Test the complete agentic search workflow."""
    print("🤖 JEDEC Insight Agentic Workflow Test")
    print("=" * 70)
    
    try:
        # Initialize enhanced RAG engine
        engine = await create_enhanced_rag_engine()
        
        # Test agentic search scenarios
        test_scenarios = [
            {
                "name": "JESD21C 기본 용어 검색",
                "query": "ESD Class 1 요구사항",
                "expected_behavior": "JESD21C 지식베이스에서 용어 정의 후 검색",
                "test_focus": "knowledge_base_lookup"
            },
            {
                "name": "모호한 기술 용어 해결",
                "query": "HBM 테스트 방법",
                "expected_behavior": "용어 분석 후 여러 검색 전략 시도",
                "test_focus": "terminology_resolution"
            },
            {
                "name": "JESD 관련 비교 질의",
                "query": "ESD와 CDM의 차이점 비교",
                "expected_behavior": "비교 분석과 관련 문서 검색",
                "test_focus": "comparison_analysis"
            },
            {
                "name": "일반 JEDEC 규격 검색",
                "query": "JEDEC 동작 전압 규격",
                "expected_behavior": "Common 카테고리 검색 및 JESD21C 지식 활용",
                "test_focus": "category_integration"
            },
            {
                "name": "복합 기술 질의",
                "query": "IC 패키징과 ESD 보호 요구사항",
                "expected_behavior": "Package와 Common 카테고리 통합 검색",
                "test_focus": "multi_category_search"
            },
            {
                "name": "실무 시나리오",
                "query": "제품 출하 시 ESD 보호 절차",
                "expected_behavior": "실무 상황에 맞는 검색 전략",
                "test_focus": "practical_application"
            }
        ]
        
        print(f"🧪 총 {len(test_scenarios)}개 시나리오 테스트")
        print()
        
        results = []
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"🔍 시나리오 {i}: {scenario['name']}")
            print(f"질의: {scenario['query']}")
            print(f"예상 동작: {scenario['expected_behavior']}")
            print("-" * 50)
            
            try:
                # Perform agentic search
                start_time = asyncio.get_event_loop().time()
                
                result = await perform_agentic_search(
                    scenario['query'], 
                    engine, 
                    analyze_user_query,
                    k=5
                )
                
                end_time = asyncio.get_event_loop().time()
                search_time = end_time - start_time
                
                # Analyze results
                workflow = result.get("search_workflow", [])
                final_result = result.get("final_result", {})
                
                # Evaluate success based on expected behavior
                success_criteria = {
                    "terminology_found": len(final_result.get("terminology_enhanced", [])) > 0,
                    "knowledge_used": final_result.get("knowledge_used", False),
                    "multiple_steps": len(workflow) > 3,
                    "sources_found": len(final_result.get("sources", [])) > 0,
                    "confidence_adequate": final_result.get("confidence", 0) > 0.6
                }
                
                # Scenario-specific success criteria
                scenario_success = True
                issues = []
                
                if scenario["test_focus"] == "knowledge_base_lookup":
                    if not success_criteria["knowledge_used"]:
                        scenario_success = False
                        issues.append("JESD21C 지식베이스 미활용")
                
                elif scenario["test_focus"] == "terminology_resolution":
                    if not success_criteria["terminology_found"]:
                        scenario_success = False
                        issues.append("기술 용어 분석 실패")
                
                elif scenario["test_focus"] == "comparison_analysis":
                    if not final_result.get("is_comparison", False):
                        scenario_success = False
                        issues.append("비교 분석 미수행")
                
                elif scenario["test_focus"] == "category_integration":
                    if "Common" not in [s.get("document_id", "") for s in final_result.get("sources", [])]:
                        scenario_success = False
                        issues.append("Common 카테고리 문서 미검색")
                
                # Overall quality assessment
                quality_score = 0
                if success_criteria["terminology_found"]:
                    quality_score += 25
                if success_criteria["knowledge_used"]:
                    quality_score += 25
                if success_criteria["multiple_steps"]:
                    quality_score += 20
                if success_criteria["sources_found"]:
                    quality_score += 20
                if success_criteria["confidence_adequate"]:
                    quality_score += 10
                
                # Store test result
                test_result = {
                    "scenario_id": i,
                    "scenario_name": scenario["name"],
                    "query": scenario['query'],
                    "expected_behavior": scenario['expected_behavior'],
                    "search_time": search_time,
                    "workflow_steps": len(workflow),
                    "success": scenario_success,
                    "quality_score": quality_score,
                    "confidence": final_result.get("confidence", 0),
                    "sources_count": len(final_result.get("sources", [])),
                    "terminology_enhanced": final_result.get("terminology_enhanced", False),
                    "knowledge_used": final_result.get("knowledge_used", False),
                    "issues": issues,
                    "workflow": result.get("search_workflow", {}),
                    "final_result": final_result
                }
                
                results.append(test_result)
                
                # Display results
                status_icon = "✅" if scenario_success else "❌"
                print(f"{status_icon} 시나리오 결과:")
                print(f"  검색 시간: {search_time:.2f}초")
                print(f"  워크플로우 단계: {len(workflow)}")
                print(f"  신뢰도: {final_result.get('confidence', 0):.2f}")
                print(f"  품질 점수: {quality_score}/100")
                print(f"  출처 문서: {len(final_result.get('sources', []))}개")
                
                if final_result.get("terminology_enhanced"):
                    print(f"  🧠 용어 향상 적용됨")
                
                if final_result.get("knowledge_used"):
                    print(f"  📚 JESD21C 지식 활용됨")
                
                if issues:
                    print(f"  ⚠️ 문제점:")
                    for issue in issues:
                        print(f"    - {issue}")
                
                # Show workflow steps summary
                if workflow:
                    print(f"  🔄 워크플로우:")
                    for step in workflow:
                        step_name = step.get("step", "Unknown")
                        step_confidence = step.get("confidence", 0)
                        step_desc = step.get("description", "")
                        print(f"    {step_name}: 신뢰도 {step_confidence:.2f}")
                
                print()
                
            except Exception as e:
                print(f"❌ 시나리오 오류: {e}")
                results.append({
                    "scenario_id": i,
                    "scenario_name": scenario['name'],
                    "query": scenario['query'],
                    "error": str(e),
                    "success": False
                })
            
            print("=" * 50)
            print()
        
        # Summary analysis
        successful_scenarios = sum(1 for r in results if r.get('success', False))
        total_scenarios = len(results)
        
        print("📊 에전트 워크플로우 테스트 결과 요약")
        print("=" * 70)
        print(f"총 시나리오: {total_scenarios}")
        print(f"성공: {successful_scenarios}")
        print(f"실패: {total_scenarios - successful_scenarios}")
        print(f"성공률: {(successful_scenarios/total_scenarios)*100:.1f}%")
        print()
        
        # Workflow step analysis
        step_analysis = {}
        for result in results:
            if "workflow" in result:
                workflow = result["workflow"]
                for step in workflow:
                    step_name = step.get("step", "Unknown")
                    if step_name not in step_analysis:
                        step_analysis[step_name] = {
                            "total": 0,
                            "success": 0,
                            "avg_confidence": 0
                        }
                    
                    step_analysis[step_name]["total"] += 1
                    if step.get("confidence", 0) > 0.5:
                        step_analysis[step_name]["success"] += 1
                    
                    step_analysis[step_name]["avg_confidence"] += step.get("confidence", 0)
        
        print("📈 워크플로우 단계별 성능:")
        for step_name, stats in step_analysis.items():
            if stats["total"] > 0:
                success_rate = (stats["success"] / stats["total"]) * 100
                avg_conf = stats["avg_confidence"] / stats["total"]
                print(f"  {step_name}: 성공률 {success_rate:.1f}%, 평균 신뢰도 {avg_conf:.2f}")
        
        print()
        print("🎉 에전트 워크플로우 테스트 완료!")
        
        # Recommendations
        if successful_scenarios < total_scenarios:
            print("\n💡 개선 제언:")
            failed_scenarios = [r for r in results if not r.get('success', False)]
            
            if failed_scenarios:
                common_issues = {}
                for result in failed_scenarios:
                    for issue in result.get("issues", []):
                        common_issues[issue] = common_issues.get(issue, 0) + 1
                
                print("가장 많은 문제:")
                for issue, count in sorted(common_issues.items(), key=lambda x: x[1], reverse=True):
                    print(f"  - {issue}: {count}회")
                
                print("\n개선 방안:")
                print("  1. JESD21C 지식베이스 확장")
                print("  2. 용어 분석 정확도 향상")
                print("  3. 워크플로우 단계별 오류 처리 강화")
        
    except Exception as e:
        print(f"❌ 테스트 중 치명적 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_agentic_workflow())
