"""
Agentic Search Workflow for JEDEC Insight
Implements intelligent search with JESD21C as knowledge base and terminology resolution.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import re
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchStep:
    """Represents a step in the agentic search workflow."""
    step_type: str
    description: str
    query: str
    results: List[Dict[str, Any]]
    confidence: float
    terminology_found: List[str]


class AgenticSearchEngine:
    """Intelligent search engine with agentic workflow and terminology resolution."""
    
    def __init__(self, rag_engine, category_detector):
        """
        Initialize agentic search engine.
        
        Args:
            rag_engine: Enhanced RAG engine instance
            category_detector: Category detector instance
        """
        self.rag_engine = rag_engine
        self.category_detector = category_detector
        
        # JESD21C terminology knowledge base
        self.jesd21c_terms = self._load_jesd21c_knowledge()
        
        # Technical term patterns
        self.technical_patterns = {
            'abbreviations': r'\b(A|C|D|E|F|G|H|I|J|K|L|M|N|O|P|Q|R|S|T|U|V|W|X|Y|Z)\b',
            'parameters': r'\b(tCK|tRCD|tRP|tRAS|tRC|CL|CAS|VDD|VDDQ|VPP)\b',
            'units': r'\b(ns|ps|μs|ms|V|mV|μV|MHz|MT/s|GT/s|GB|MB|TB)\b',
            'standards': r'\b(JEDEC|JESD|IPC|EIA|ISO|IEC)\b'
        }
        
        # Search workflow steps
        self.workflow_steps = [
            "terminology_extraction",
            "knowledge_base_lookup", 
            "category_analysis",
            "query_expansion",
            "focused_search",
            "broad_search",
            "result_synthesis"
        ]
    
    def _load_jesd21c_knowledge(self) -> Dict[str, Any]:
        """
        Load JESD21C terminology knowledge base.
        
        Returns:
            Dictionary with JESD21C terms and definitions
        """
        return {
            # Handling and Sensitivity
            "handling": {
                "EIA": "Electrostatic Discharge Sensitivity",
                "ESD": "Electrostatic Discharge",
                "HBM": "Human Body Model",
                "CDM": "Charged Device Model",
                "MM": "Machine Model",
                "ECA": "Environmental Chamber Analysis"
            },
            
            # Test Levels
            "test_levels": {
                "Class 0": "Protected against discharge up to 125V",
                "Class 1": "Protected against discharge up to 250V", 
                "Class 2": "Protected against discharge up to 500V",
                "Class 3": "Protected against discharge up to 1000V",
                "Class 4": "Protected against discharge up to 2000V"
            },
            
            # Device Types
            "device_types": {
                "IC": "Integrated Circuit",
                "PCB": "Printed Circuit Board",
                "Assembly": "Complete electronic assembly",
                "Component": "Individual electronic component"
            },
            
            # Test Methods
            "test_methods": {
                "Contact Discharge": "Direct contact discharge test",
                "Air Discharge": "Air discharge test", 
                "Indirect Discharge": "Indirect discharge test",
                "Latch-up": "Latch-up testing",
                "ECA": "Environmental chamber analysis"
            },
            
            # Protection Requirements
            "protection": {
                "grounding": "Equipment grounding requirements",
                "personnel": "Personnel grounding procedures",
                "packaging": "ESD protective packaging requirements",
                "workplace": "Workplace ESD control measures"
            }
        }
    
    async def agentic_search(self, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Perform agentic search with JESD21C knowledge integration.
        
        Args:
            query: User query
            k: Number of documents to retrieve
            
        Returns:
            Dictionary with comprehensive search results
        """
        search_log = []
        
        try:
            # Step 1: Terminology Extraction
            step1_result = await self._extract_terminology(query)
            search_log.append(step1_result)
            
            # Step 2: Knowledge Base Lookup
            step2_result = await self._lookup_knowledge_base(step1_result['terminology_found'])
            search_log.append(step2_result)
            
            # Step 3: Category Analysis
            step3_result = await self._analyze_categories(query, step1_result, step2_result)
            search_log.append(step3_result)
            
            # Step 4: Query Expansion Strategy
            step4_result = await self._expand_query_strategy(query, step1_result, step2_result, step3_result)
            search_log.append(step4_result)
            
            # Step 5: Focused Search (if high confidence)
            step5_result = await self._perform_focused_search(query, step4_result, k)
            search_log.append(step5_result)
            
            # Step 6: Broad Search (fallback)
            step6_result = await self._perform_broad_search(query, step4_result, k)
            search_log.append(step6_result)
            
            # Step 7: Result Synthesis
            final_result = await self._synthesize_results(query, search_log)
            
            return {
                "original_query": query,
                "search_workflow": search_log,
                "final_result": final_result,
                "agentic_confidence": self._calculate_overall_confidence(search_log),
                "terminology_resolution": step1_result,
                "knowledge_base_used": step2_result,
                "category_analysis": step3_result,
                "query_strategy": step4_result,
                "focused_search": step5_result,
                "broad_search": step6_result
            }
            
        except Exception as e:
            logger.error(f"Error in agentic search: {e}")
            return {
                "original_query": query,
                "error": str(e),
                "search_workflow": search_log
            }
    
    async def _extract_terminology(self, query: str) -> Dict[str, Any]:
        """
        Extract technical terminology from user query.
        
        Args:
            query: User query string
            
        Returns:
            Dictionary with extracted terminology
        """
        terminology_found = []
        ambiguous_terms = []
        
        # Extract abbreviations
        abbrev_matches = re.findall(self.technical_patterns['abbreviations'], query)
        terminology_found.extend(abbrev_matches)
        
        # Extract technical parameters
        param_matches = re.findall(self.technical_patterns['parameters'], query)
        terminology_found.extend(param_matches)
        
        # Extract units
        unit_matches = re.findall(self.technical_patterns['units'], query)
        terminology_found.extend(unit_matches)
        
        # Extract standards
        standard_matches = re.findall(self.technical_patterns['standards'], query)
        terminology_found.extend(standard_matches)
        
        # Identify potentially ambiguous terms
        technical_terms = set(terminology_found)
        common_terms = {"handling", "test", "sensitivity", "protection", "level", "class"}
        ambiguous_terms = [term for term in technical_terms if term.lower() in common_terms]
        
        return {
            "step": "terminology_extraction",
            "terminology_found": list(set(terminology_found)),
            "ambiguous_terms": ambiguous_terms,
            "confidence": 0.8 if len(terminology_found) > 0 else 0.3,
            "jesd_relevant": any(term in ["ESD", "JESD", "EIA", "Class"] for term in terminology_found)
        }
    
    async def _lookup_knowledge_base(self, terminology: List[str]) -> Dict[str, Any]:
        """
        Look up terminology in JESD21C knowledge base.
        
        Args:
            terminology: List of technical terms
            
        Returns:
            Dictionary with knowledge base results
        """
        knowledge_found = {}
        context_provided = {}
        
        for term in terminology:
            term_lower = term.lower()
            
            # Search in JESD21C knowledge base
            for category, terms in self.jesd21c_terms.items():
                for key, value in terms.items():
                    if term_lower in key.lower() or key.lower() in term_lower:
                        knowledge_found[term] = {
                            "category": category,
                            "definition": value,
                            "source": "JESD21C"
                        }
                        break
            
            # Provide context for common ESD terms
            if term_upper := term.upper():
                if term_upper in self.jesd21c_terms["test_levels"]:
                    context_provided[term] = f"JESD21C {term_upper} test level"
                elif term_upper in ["ESD", "HBM", "CDM", "MM"]:
                    context_provided[term] = f"JESD21C {term_upper} test model"
        
        return {
            "step": "knowledge_base_lookup",
            "knowledge_found": knowledge_found,
            "context_provided": context_provided,
            "confidence": 0.9 if knowledge_found else 0.2
        }
    
    async def _analyze_categories(self, query: str, terminology_result: Dict[str, Any], 
                             knowledge_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze query with enhanced context from terminology and knowledge base.
        
        Args:
            query: Original user query
            terminology_result: Results from terminology extraction
            knowledge_result: Results from knowledge base lookup
            
        Returns:
            Enhanced category analysis
        """
        # Get base category analysis
        base_analysis = self.category_detector.analyze_query(query)
        
        # Enhance with JESD21C context
        if knowledge_result.get("knowledge_found"):
            # If JESD terms found, boost Common category confidence
            if "Common" not in base_analysis["detected_categories"]:
                base_analysis["detected_categories"].append("Common")
            
            # Boost confidence for ESD-related queries
            if terminology_result.get("jesd_relevant"):
                base_analysis["confidence"] = min(base_analysis["confidence"] + 0.2, 1.0)
        
        # Adjust search strategy based on terminology
        enhanced_strategy = base_analysis.copy()
        if terminology_result.get("jesd_relevant"):
            enhanced_strategy["search_strategy"] = {
                "approach": "jesd_focused",
                "priority_categories": ["Common"],
                "similarity_threshold": 0.8
            }
        
        return {
            "step": "category_analysis",
            "base_analysis": base_analysis,
            "enhanced_analysis": enhanced_strategy,
            "terminology_boost": terminology_result.get("jesd_relevant", False),
            "confidence": base_analysis["confidence"]
        }
    
    async def _expand_query_strategy(self, query: str, terminology_result: Dict[str, Any],
                                  knowledge_result: Dict[str, Any], 
                                  category_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Develop intelligent query expansion strategy.
        
        Args:
            query: Original query
            terminology_result: Terminology extraction results
            knowledge_result: Knowledge base lookup results
            category_result: Enhanced category analysis
            
        Returns:
            Query expansion strategy
        """
        expanded_queries = [query]
        
        # JESD21C-based expansions
        if knowledge_result.get("knowledge_found"):
            for term, info in knowledge_result["knowledge_found"].items():
                # Add definition-based queries
                if info.get("definition"):
                    definition_query = f"{info['definition']} {term}"
                    expanded_queries.append(definition_query)
                
                # Add category-based queries
                category = info.get("category")
                if category:
                    category_query = f"JESD21C {category} {term}"
                    expanded_queries.append(category_query)
        
        # Technical term expansions
        if terminology_result.get("terminology_found"):
            for term in terminology_result["terminology_found"]:
                # Add variations
                if term.upper() == "ESD":
                    expanded_queries.extend([
                        f"electrostatic discharge {term}",
                        f"{term} protection",
                        f"{term} sensitivity"
                    ])
                elif "Class" in term:
                    expanded_queries.append(f"{term} level requirements")
        
        # Remove duplicates
        expanded_queries = list(set(expanded_queries))
        
        return {
            "step": "query_expansion",
            "original_query": query,
            "expanded_queries": expanded_queries,
            "expansion_count": len(expanded_queries),
            "jesd_enhanced": len(knowledge_result.get("knowledge_found", {})) > 0
        }
    
    async def _perform_focused_search(self, query: str, strategy_result: Dict[str, Any], k: int) -> Dict[str, Any]:
        """
        Perform focused search based on strategy.
        
        Args:
            query: Original query
            strategy_result: Query expansion strategy
            k: Number of results
            
        Returns:
            Focused search results
        """
        try:
            # Use enhanced queries for search
            queries_to_search = strategy_result.get("expanded_queries", [query])
            
            all_results = []
            for expanded_query in queries_to_search[:3]:  # Limit to top 3 expansions
                result = await self.rag_engine.query(expanded_query, k=k//2)
                all_results.extend(result.get("sources", []))
            
            # Remove duplicates and sort by relevance
            unique_results = []
            seen_sources = set()
            
            for source in all_results:
                source_key = f"{source.get('document_id', '')}_{source.get('page', '')}"
                if source_key not in seen_sources:
                    unique_results.append(source)
                    seen_sources.add(source_key)
            
            return {
                "step": "focused_search",
                "search_queries": queries_to_search[:3],
                "results_found": len(unique_results),
                "unique_sources": len(set(s.get('document_id', '') for s in unique_results)),
                "confidence": 0.8
            }
            
        except Exception as e:
            logger.error(f"Error in focused search: {e}")
            return {
                "step": "focused_search",
                "error": str(e),
                "confidence": 0.1
            }
    
    async def _perform_broad_search(self, query: str, strategy_result: Dict[str, Any], k: int) -> Dict[str, Any]:
        """
        Perform broad search as fallback.
        
        Args:
            query: Original query
            strategy_result: Query expansion strategy
            k: Number of results
            
        Returns:
            Broad search results
        """
        try:
            # Use original query with standard search
            result = await self.rag_engine.query(query, k=k)
            
            sources = result.get("sources", [])
            unique_documents = len(set(s.get('document_id', '') for s in sources))
            
            return {
                "step": "broad_search",
                "results_found": len(sources),
                "unique_sources": unique_documents,
                "confidence": 0.6
            }
            
        except Exception as e:
            logger.error(f"Error in broad search: {e}")
            return {
                "step": "broad_search", 
                "error": str(e),
                "confidence": 0.1
            }
    
    async def _synthesize_results(self, query: str, search_log: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synthesize results from all search steps.
        
        Args:
            query: Original query
            search_log: Results from all search steps
            
        Returns:
            Synthesized final results
        """
        # Collect all sources from successful steps
        all_sources = []
        terminology_info = {}
        knowledge_info = {}
        
        for step_result in search_log:
            if "results" in step_result:
                all_sources.extend(step_result["results"])
            
            if step_result.get("step") == "knowledge_base_lookup":
                knowledge_info = step_result
            elif step_result.get("step") == "terminology_extraction":
                terminology_info = step_result
        
        # Remove duplicate sources
        unique_sources = []
        seen_sources = set()
        
        for source in all_sources:
            source_key = f"{source.get('document_id', '')}_{source.get('page', '')}"
            if source_key not in seen_sources:
                unique_sources.append(source)
                seen_sources.add(source_key)
        
        # Get final answer using the most successful approach
        final_answer = ""
        final_confidence = 0.0
        approach_used = "synthesis"
        
        # Try to get answer from focused search first
        for step_result in search_log:
            if step_result.get("step") == "focused_search" and step_result.get("confidence", 0) > 0.7:
                # Use focused search results for final answer
                try:
                    focused_query = step_result.get("search_queries", [query])[0]
                    result = await self.rag_engine.query(focused_query, k=5)
                    final_answer = result.get("answer", "")
                    final_confidence = step_result.get("confidence", 0.0)
                    approach_used = "focused_search"
                    break
                except:
                    continue
        
        # Fallback to broad search if focused search failed
        if not final_answer:
            for step_result in search_log:
                if step_result.get("step") == "broad_search":
                    try:
                        result = await self.rag_engine.query(query, k=5)
                        final_answer = result.get("answer", "")
                        final_confidence = step_result.get("confidence", 0.0)
                        approach_used = "broad_search"
                        break
                    except:
                        continue
        
        return {
            "step": "result_synthesis",
            "final_answer": final_answer,
            "sources": unique_sources,
            "confidence": final_confidence,
            "approach_used": approach_used,
            "terminology_enhanced": len(terminology_info.get("terminology_found", [])) > 0,
            "knowledge_used": len(knowledge_info.get("knowledge_found", {})) > 0,
            "workflow_steps": len(search_log)
        }
    
    def _calculate_overall_confidence(self, search_log: List[Dict[str, Any]]) -> float:
        """
        Calculate overall confidence from all workflow steps.
        
        Args:
            search_log: Search workflow results
            
        Returns:
            Overall confidence score
        """
        if not search_log:
            return 0.0
        
        # Weight different steps
        step_weights = {
            "terminology_extraction": 0.1,
            "knowledge_base_lookup": 0.2,
            "category_analysis": 0.1,
            "query_expansion": 0.1,
            "focused_search": 0.3,
            "broad_search": 0.2,
            "result_synthesis": 0.1
        }
        
        total_weight = 0.0
        total_confidence = 0.0
        
        for step_result in search_log:
            step_name = step_result.get("step", "")
            confidence = step_result.get("confidence", 0.0)
            weight = step_weights.get(step_name, 0.1)
            
            total_weight += weight
            total_confidence += confidence * weight
        
        return total_confidence / total_weight if total_weight > 0 else 0.0


# Global instance
agentic_search_engine = None


def get_agentic_search_engine(rag_engine, category_detector) -> AgenticSearchEngine:
    """Get global agentic search engine instance."""
    global agentic_search_engine
    if agentic_search_engine is None:
        agentic_search_engine = AgenticSearchEngine(rag_engine, category_detector)
    return agentic_search_engine


async def perform_agentic_search(query: str, rag_engine, category_detector, k: int = 5) -> Dict[str, Any]:
    """
    Perform agentic search using global engine.
    
    Args:
        query: User query
        rag_engine: RAG engine instance
        category_detector: Category detector instance
        k: Number of results
        
    Returns:
        Agentic search results
    """
    engine = get_agentic_search_engine(rag_engine, category_detector)
    return await engine.agentic_search(query, k)
