"""
Comparison Engine for JEDEC Specifications
Handles comparison queries between different memory specifications.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ComparisonItem:
    """Represents an item in a comparison."""
    specification: str
    value: str
    unit: str
    document_id: str
    page: str
    section: str
    confidence: float


class ComparisonEngine:
    """Engine for comparing JEDEC specifications."""
    
    def __init__(self):
        """Initialize the comparison engine."""
        self.comparison_patterns = self._load_comparison_patterns()
        self.parameter_extractors = self._load_parameter_extractors()
        
        logger.info("ComparisonEngine initialized")
    
    def _load_comparison_patterns(self) -> List[re.Pattern]:
        """Load regex patterns for comparison queries."""
        patterns = [
            # DDR4 vs DDR5 patterns
            re.compile(r'(ddr4|ddr5|lpddr4|lpddr5)\s+(vs|versus|compared to|and|or)\s+(ddr4|ddr5|lpddr4|lpddr5)', re.IGNORECASE),
            # Generic comparison patterns
            re.compile(r'compare\s+(ddr4|ddr5|lpddr4|lpddr5)\s+(and|with|to)\s+(ddr4|ddr5|lpddr4|lpddr5)', re.IGNORECASE),
            re.compile(r'(ddr4|ddr5|lpddr4|lpddr5)\s+and\s+(ddr4|ddr5|lpddr4|lpddr5)\s+comparison', re.IGNORECASE),
            # Parameter comparison patterns
            re.compile(r'(tck|tras|trcd|trp|cas|vdd|vddq|speed|frequency|capacity|voltage)\s+(comparison|compare|vs|versus)', re.IGNORECASE),
        ]
        return patterns
    
    def _load_parameter_extractors(self) -> Dict[str, re.Pattern]:
        """Load regex patterns for parameter extraction."""
        return {
            'timing': re.compile(r'(tck|tras|trcd|trp|trc|cas|cl)\s*[:=]?\s*(\d+\.?\d*)\s*(ns|ps|us|ms)?', re.IGNORECASE),
            'voltage': re.compile(r'(vdd|vddq|vpp|voltage|supply)\s*[:=]?\s*(\d+\.?\d*)\s*(v|mv|uv)?', re.IGNORECASE),
            'frequency': re.compile(r'(speed|frequency|clock|data rate)\s*[:=]?\s*(\d+\.?\d*)\s*(mhz|ghz|mt/s|gt/s|hz|khz)?', re.IGNORECASE),
            'capacity': re.compile(r'(capacity|size|density)\s*[:=]?\s*(\d+\.?\d*)\s*(gb|mb|kb|tb|gib|mib|kib|tib)?', re.IGNORECASE),
        }
    
    def is_comparison_query(self, query: str) -> bool:
        """
        Check if query is a comparison request.
        
        Args:
            query: User query
            
        Returns:
            True if comparison query, False otherwise
        """
        query_lower = query.lower()
        return any(pattern.search(query_lower) for pattern in self.comparison_patterns)
    
    def extract_comparison_entities(self, query: str) -> List[str]:
        """
        Extract entities to compare from query.
        
        Args:
            query: User query
            
        Returns:
            List of entities to compare
        """
        entities = []
        query_lower = query.lower()
        
        # Extract memory types
        memory_types = ['ddr4', 'ddr5', 'lpddr4', 'lpddr5']
        for mem_type in memory_types:
            if mem_type in query_lower:
                entities.append(mem_type)
        
        # Extract parameters
        parameters = ['tck', 'tras', 'trcd', 'trp', 'cas', 'vdd', 'vddq', 'speed', 'frequency', 'capacity', 'voltage']
        for param in parameters:
            if param in query_lower:
                entities.append(param)
        
        return list(set(entities))
    
    def extract_parameters_from_text(self, text: str, document_id: str, page: str, section: str) -> List[ComparisonItem]:
        """
        Extract technical parameters from text.
        
        Args:
            text: Text to analyze
            document_id: Document identifier
            page: Page number
            section: Section name
            
        Returns:
            List of extracted parameters
        """
        parameters = []
        
        for param_type, pattern in self.parameter_extractors.items():
            matches = pattern.finditer(text)
            
            for match in matches:
                param_name = match.group(1).lower()
                value = match.group(2)
                unit = match.group(3) if match.group(3) else ""
                
                item = ComparisonItem(
                    specification=param_name,
                    value=value,
                    unit=unit,
                    document_id=document_id,
                    page=page,
                    section=section,
                    confidence=0.8  # Base confidence for regex matches
                )
                parameters.append(item)
        
        return parameters
    
    def create_comparison_table(self, comparison_results: Dict[str, List[ComparisonItem]]) -> pd.DataFrame:
        """
        Create comparison table from results.
        
        Args:
            comparison_results: Results grouped by entity
            
        Returns:
            Comparison DataFrame
        """
        table_data = []
        
        # Get all unique specifications
        all_specs = set()
        for entity, items in comparison_results.items():
            for item in items:
                all_specs.add(item.specification)
        
        # Create table rows
        for spec in sorted(all_specs):
            row = {"Specification": spec.upper()}
            
            for entity in comparison_results.keys():
                # Find matching parameter for this entity and specification
                matching_items = [
                    item for item in comparison_results[entity] 
                    if item.specification == spec
                ]
                
                if matching_items:
                    # Use the highest confidence match
                    best_match = max(matching_items, key=lambda x: x.confidence)
                    value_with_unit = f"{best_match.value} {best_match.unit}".strip()
                    row[entity.upper()] = value_with_unit
                    row[f"{entity.upper()}_source"] = f"{best_match.document_id} (p.{best_match.page})"
                else:
                    row[entity.upper()] = "N/A"
                    row[f"{entity.upper()}_source"] = "N/A"
            
            table_data.append(row)
        
        return pd.DataFrame(table_data)
    
    def generate_comparison_summary(self, comparison_df: pd.DataFrame, entities: List[str]) -> str:
        """
        Generate summary of comparison results.
        
        Args:
            comparison_df: Comparison DataFrame
            entities: List of compared entities
            
        Returns:
            Summary text
        """
        if comparison_df.empty:
            return "비교할 데이터를 찾을 수 없습니다."
        
        summary = f"## {entities[0].upper()} vs {entities[1].upper()} 비교 분석\n\n"
        
        # Key differences
        summary += "### 주요 차이점:\n\n"
        
        for _, row in comparison_df.iterrows():
            spec = row['Specification']
            values = []
            
            for entity in entities:
                entity_upper = entity.upper()
                if entity_upper in row and row[entity_upper] != "N/A":
                    values.append(f"{entity_upper}: {row[entity_upper]}")
            
            if len(values) > 1:
                summary += f"- **{spec}**: {', '.join(values)}\n"
        
        summary += "\n### 상세 비교 표:\n\n"
        summary += comparison_df.to_markdown(index=False)
        
        return summary
    
    async def compare_specifications(self, query: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform specification comparison.
        
        Args:
            query: User query
            search_results: Search results from RAG engine
            
        Returns:
            Comparison results
        """
        try:
            # Extract entities to compare
            entities = self.extract_comparison_entities(query)
            
            if len(entities) < 2:
                return {
                    "is_comparison": False,
                    "message": "비교할 대상을 2개 이상 찾을 수 없습니다.",
                    "comparison_table": None,
                    "summary": ""
                }
            
            # Group search results by entity
            entity_results = {}
            
            for result in search_results:
                content = result.get('content', '')
                document_id = result.get('document_id', 'Unknown')
                page = result.get('page', 'Unknown')
                section = result.get('section', 'Unknown')
                
                # Extract parameters from this result
                parameters = self.extract_parameters_from_text(content, document_id, page, section)
                
                # Determine which entity this result belongs to
                content_lower = content.lower()
                for entity in entities:
                    if entity in content_lower:
                        if entity not in entity_results:
                            entity_results[entity] = []
                        entity_results[entity].extend(parameters)
            
            # Create comparison table
            comparison_df = self.create_comparison_table(entity_results)
            
            # Generate summary
            summary = self.generate_comparison_summary(comparison_df, entities)
            
            return {
                "is_comparison": True,
                "entities": entities,
                "comparison_table": comparison_df.to_dict('records') if not comparison_df.empty else None,
                "summary": summary,
                "entity_results": {k: [{"specification": p.specification, "value": p.value, "unit": p.unit, 
                                      "document_id": p.document_id, "page": p.page} for p in v] 
                                 for k, v in entity_results.items()}
            }
            
        except Exception as e:
            logger.error(f"Error in comparison: {e}")
            return {
                "is_comparison": False,
                "message": f"비교 분석 중 오류가 발생했습니다: {str(e)}",
                "comparison_table": None,
                "summary": ""
            }


# Global instance
comparison_engine = ComparisonEngine()


def get_comparison_engine() -> ComparisonEngine:
    """Get global comparison engine instance."""
    return comparison_engine


async def perform_comparison(query: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Perform specification comparison using global engine.
    
    Args:
        query: User query
        search_results: Search results from RAG engine
        
    Returns:
        Comparison results
    """
    return await comparison_engine.compare_specifications(query, search_results)
