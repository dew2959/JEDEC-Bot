"""
Category Detection and Query Analysis for JEDEC Insight
Analyzes user queries to determine relevant categories and applies smart filtering.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class QueryCategory(Enum):
    """Query categories for JEDEC specifications."""
    DRAM = "DRAM"
    STORAGE = "Storage"
    PACKAGE = "Package"
    COMMON = "Common"
    GENERAL = "General"


class CategoryDetector:
    """Detects relevant categories from user queries and applies smart filtering."""
    
    def __init__(self):
        """Initialize category detector."""
        # Category-specific keywords
        self.category_keywords = {
            QueryCategory.DRAM: [
                # Memory types
                "ddr4", "ddr5", "ddr3", "ddr2", "lpddr4", "lpddr5",
                "sdram", "dimm", "sodimm", "rdimm", "udimm", "lrdimm",
                
                # Timing parameters
                "tck", "tras", "trcd", "trp", "trc", "cas", "cl",
                "latency", "timing", "clock", "frequency", "speed",
                
                # Memory operations
                "refresh", "precharge", "activate", "write", "read",
                "burst", "access", "cycle",
                
                # Memory characteristics
                "bandwidth", "throughput", "data rate", "mt/s", "mhz",
                "capacity", "density", "size", "gb", "mb", "tb"
            ],
            
            QueryCategory.STORAGE: [
                # Storage types
                "ssd", "hdd", "nvme", "sata", "pcie", "sas",
                "flash", "nand", "nor", "emmc", "ufs",
                
                # Storage characteristics
                "storage", "drive", "disk", "capacity", "performance",
                "endurance", "wear leveling", "garbage collection",
                "read/write", "iops", "sequential", "random",
                "mb/s", "gb/s", "tb", "pb"
            ],
            
            QueryCategory.PACKAGE: [
                # Package types
                "bga", "qfn", "lga", "pga", "tsop", "csp",
                "package", "packaging", "封装", "封装", "패키지",
                
                # Package characteristics
                "pin", "ball", "pad", "lead", "footprint",
                "pcb", "substrate", "die", "wafer",
                "solder", "reflow", "bumping", "encapsulation"
            ],
            
            QueryCategory.COMMON: [
                # General JEDEC terms
                "jedec", "standard", "specification", "spec", "standard",
                "규격", "사양", "표준", "명세",
                
                # Common parameters
                "voltage", "vdd", "vddq", "vpp", "power", "consumption",
                "temperature", "thermal", "junction", "case", "operating",
                "reliability", "testing", "qualification", "certification"
            ]
        }
        
        # Cross-category keywords (may indicate multiple categories)
        self.cross_category_keywords = [
            "interface", "protocol", "signal", "electrical", "mechanical",
            "form factor", "connector", "pinout", "compatibility"
        ]
        
        # Comparison indicators
        self.comparison_indicators = [
            "vs", "versus", "compare", "comparison", "비교", "차이",
            "difference", "차이점", "advantage", "단점", "pros", "cons"
        ]
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze user query to determine relevant categories and intent.
        
        Args:
            query: User query string
            
        Returns:
            Dictionary with analysis results
        """
        query_lower = query.lower()
        
        # Initialize analysis results
        analysis = {
            "original_query": query,
            "normalized_query": query_lower,
            "detected_categories": [],
            "category_scores": {},
            "is_comparison": False,
            "comparison_entities": [],
            "primary_category": None,
            "confidence": 0.0,
            "keywords_found": []
        }
        
        # Extract keywords found in query
        keywords_found = self._extract_keywords(query_lower)
        analysis["keywords_found"] = keywords_found
        
        # Score each category
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword in query_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            # Weight exact matches higher
            for keyword in matched_keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', query_lower):
                    score += 2
            
            category_scores[category] = {
                "score": score,
                "matched_keywords": matched_keywords,
                "confidence": min(score / len(keywords), 1.0)
            }
        
        analysis["category_scores"] = category_scores
        
        # Determine detected categories (those with score > 0)
        detected_categories = [
            category for category, score_data in category_scores.items()
            if score_data["score"] > 0
        ]
        analysis["detected_categories"] = detected_categories
        
        # Determine primary category (highest score)
        if detected_categories:
            primary_category = max(
                detected_categories,
                key=lambda cat: category_scores[cat]["score"]
            )
            analysis["primary_category"] = primary_category
            analysis["confidence"] = category_scores[primary_category]["confidence"]
        
        # Check for comparison intent
        comparison_info = self._detect_comparison_intent(query_lower)
        analysis.update(comparison_info)
        
        return analysis
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract keywords from query.
        
        Args:
            query: Lowercase query string
            
        Returns:
            List of found keywords
        """
        keywords_found = []
        
        # Extract from all category keywords
        all_keywords = []
        for keywords in self.category_keywords.values():
            all_keywords.extend(keywords)
        
        for keyword in all_keywords:
            if keyword in query:
                keywords_found.append(keyword)
        
        return keywords_found
    
    def _detect_comparison_intent(self, query: str) -> Dict[str, Any]:
        """
        Detect if query is asking for comparison.
        
        Args:
            query: Lowercase query string
            
        Returns:
            Dictionary with comparison analysis
        """
        comparison_info = {
            "is_comparison": False,
            "comparison_entities": [],
            "comparison_type": None
        }
        
        # Check for comparison indicators
        for indicator in self.comparison_indicators:
            if indicator in query:
                comparison_info["is_comparison"] = True
                break
        
        # Extract comparison entities (DDR4, DDR5, etc.)
        entity_pattern = r'(ddr[2-5]|lpddr[4-5]|ssd|hdd|nvme|bga|qfn|lga)'
        entities = re.findall(entity_pattern, query)
        comparison_info["comparison_entities"] = list(set(entities))
        
        # Determine comparison type
        if len(entities) >= 2:
            comparison_info["comparison_type"] = "multi_entity"
        elif len(entities) == 1:
            comparison_info["comparison_type"] = "single_entity"
        
        return comparison_info
    
    def get_search_strategy(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine optimal search strategy based on query analysis.
        
        Args:
            analysis: Query analysis results
            
        Returns:
            Dictionary with search strategy
        """
        strategy = {
            "approach": "standard",
            "categories": analysis["detected_categories"],
            "primary_category": analysis["primary_category"],
            "use_metadata_filter": False,
            "filter_criteria": {},
            "boost_relevant_categories": True,
            "expand_query": True,
            "similarity_threshold": 0.7
        }
        
        # High confidence in single category -> use metadata filter
        if (analysis["confidence"] > 0.6 and 
            len(analysis["detected_categories"]) == 1 and
            not analysis["is_comparison"]):
            
            strategy["approach"] = "category_focused"
            strategy["use_metadata_filter"] = True
            strategy["filter_criteria"] = {
                "category": analysis["primary_category"]
            }
            strategy["similarity_threshold"] = 0.8  # Higher threshold for focused search
        
        # Comparison query -> broader search
        elif analysis["is_comparison"]:
            strategy["approach"] = "comparison"
            strategy["expand_query"] = True
            strategy["similarity_threshold"] = 0.6  # Lower threshold for comparison
        
        # Low confidence or multiple categories -> standard search
        else:
            strategy["approach"] = "broad"
            strategy["expand_query"] = True
            strategy["similarity_threshold"] = 0.7
        
        return strategy
    
    def create_enhanced_query(self, original_query: str, analysis: Dict[str, Any]) -> str:
        """
        Create enhanced query based on analysis.
        
        Args:
            original_query: Original user query
            analysis: Query analysis results
            
        Returns:
            Enhanced query string
        """
        enhanced_query = original_query
        
        # Add category context for high-confidence single category queries
        if (analysis["confidence"] > 0.7 and 
            len(analysis["detected_categories"]) == 1 and
            analysis["primary_category"]):
            
            category = analysis["primary_category"]
            category_context = f"JEDEC {category} specifications"
            
            # Add context if not already present
            if category.lower() not in original_query.lower():
                enhanced_query = f"{category_context}: {original_query}"
        
        return enhanced_query
    
    def format_category_summary(self, analysis: Dict[str, Any]) -> str:
        """
        Format category analysis summary for user feedback.
        
        Args:
            analysis: Query analysis results
            
        Returns:
            Formatted summary string
        """
        summary_parts = []
        
        # Primary category
        if analysis["primary_category"]:
            confidence_pct = int(analysis["confidence"] * 100)
            summary_parts.append(
                f"🎯 주요 카테고리: {analysis['primary_category']} "
                f"(신뢰도: {confidence_pct}%)"
            )
        
        # Detected categories
        if len(analysis["detected_categories"]) > 1:
            categories_str = ", ".join(analysis["detected_categories"])
            summary_parts.append(f"📂 관련 카테고리: {categories_str}")
        
        # Comparison intent
        if analysis["is_comparison"]:
            if analysis["comparison_entities"]:
                entities_str = ", ".join(analysis["comparison_entities"])
                summary_parts.append(f"🔄 비교 대상: {entities_str}")
            else:
                summary_parts.append("🔄 비교 질의로 감지됨")
        
        # Keywords found
        if analysis["keywords_found"]:
            keywords_str = ", ".join(analysis["keywords_found"][:5])  # Show first 5
            if len(analysis["keywords_found"]) > 5:
                keywords_str += f" 외 {len(analysis['keywords_found']) - 5}개"
            summary_parts.append(f"🔍 키워드: {keywords_str}")
        
        return " | ".join(summary_parts)
    
    def suggest_category_filter(self, analysis: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Suggest category filter for search.
        
        Args:
            analysis: Query analysis results
            
        Returns:
            Filter criteria or None
        """
        # Only suggest filter if high confidence in single category
        if (analysis["confidence"] > 0.7 and 
            len(analysis["detected_categories"]) == 1 and
            analysis["primary_category"] and
            not analysis["is_comparison"]):
            
            return {"category": analysis["primary_category"]}
        
        return None


# Global instance
category_detector = CategoryDetector()


def get_category_detector() -> CategoryDetector:
    """Get global category detector instance."""
    return category_detector


def analyze_user_query(query: str) -> Dict[str, Any]:
    """
    Analyze user query using global detector.
    
    Args:
        query: User query string
        
    Returns:
        Query analysis results
    """
    return category_detector.analyze_query(query)


def get_search_strategy(query: str) -> Dict[str, Any]:
    """
    Get optimal search strategy for query.
    
    Args:
        query: User query string
        
    Returns:
        Search strategy recommendations
    """
    analysis = analyze_user_query(query)
    return category_detector.get_search_strategy(analysis)
