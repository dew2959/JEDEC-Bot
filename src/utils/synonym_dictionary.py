"""
Synonym Dictionary for JEDEC Technical Terms
Handles unit conversions and technical term synonyms for better search accuracy.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class SynonymDictionary:
    """Manages technical term synonyms and unit conversions for JEDEC specifications."""
    
    def __init__(self):
        """Initialize the synonym dictionary."""
        self.synonyms = self._load_synonyms()
        self.unit_conversions = self._load_unit_conversions()
        self.technical_terms = self._load_technical_terms()
        
        logger.info("SynonymDictionary initialized")
    
    def _load_synonyms(self) -> Dict[str, List[str]]:
        """Load technical term synonyms."""
        return {
            # Memory types
            "ddr4": ["ddr4", "dimm4", "pc4", "pc-4"],
            "ddr5": ["ddr5", "dimm5", "pc5", "pc-5"],
            "lpddr4": ["lpddr4", "low-power ddr4", "lp4"],
            "lpddr5": ["lpddr5", "low-power ddr5", "lp5"],
            
            # Timing parameters
            "tck": ["tck", "clock cycle time", "cycle time", "clock period"],
            "tras": ["tras", "activate to precharge delay", "row active time"],
            "trcd": ["trcd", "activate to read/write delay", "row to column delay"],
            "trp": ["trp", "precharge time", "row precharge time"],
            "trc": ["trc", "row cycle time", "refresh cycle time"],
            "cas": ["cas", "cas latency", "cl", "column address strobe"],
            "cl": ["cl", "cas", "cas latency", "column address strobe"],
            
            # Voltage terms
            "vdd": ["vdd", "supply voltage", "operating voltage", "voltage"],
            "vddq": ["vddq", "i/o voltage", "output voltage", "dq voltage"],
            "vpp": ["vpp", "programming voltage", "high voltage"],
            
            # Temperature
            "temperature": ["temperature", "temp", "thermal", "operating temperature"],
            "tcase": ["tcase", "case temperature", "ambient temperature"],
            "tjunction": ["tjunction", "junction temperature", "die temperature"],
            
            # Speed terms
            "speed": ["speed", "frequency", "clock speed", "data rate", "transfer rate"],
            "bandwidth": ["bandwidth", "throughput", "data bandwidth", "memory bandwidth"],
            
            # Capacity
            "capacity": ["capacity", "size", "memory size", "storage capacity", "density"],
            
            # Form factors
            "sodimm": ["sodimm", "small outline dimm", "laptop memory"],
            "udimm": ["udimm", "unbuffered dimm", "desktop memory"],
            "rdimm": ["rdimm", "registered dimm", "server memory"],
            "lrdimm": ["lrdimm", "load-reduced dimm", "server memory"],
            
            # Features
            "ecc": ["ecc", "error correction", "error correcting code", "parity"],
            "xmp": ["xmp", "extreme memory profile", "memory profile"],
            "dmp": ["dmp", "dimm memory profile", "jedec memory profile"],
        }
    
    def _load_unit_conversions(self) -> Dict[str, Dict[str, float]]:
        """Load unit conversion factors."""
        return {
            # Time units
            "time": {
                "ns": 1.0,
                "ps": 0.001,  # 1 ps = 0.001 ns
                "us": 1000.0,  # 1 us = 1000 ns
                "ms": 1000000.0,  # 1 ms = 1000000 ns
            },
            
            # Frequency units
            "frequency": {
                "hz": 1.0,
                "khz": 1000.0,
                "mhz": 1000000.0,
                "ghz": 1000000000.0,
                "mt/s": 1000000.0,  # Mega transfers per second
                "gt/s": 1000000000.0,  # Giga transfers per second
            },
            
            # Voltage units
            "voltage": {
                "v": 1.0,
                "mv": 0.001,  # millivolts
                "uv": 0.000001,  # microvolts
            },
            
            # Temperature units
            "temperature": {
                "c": 1.0,  # Celsius
                "f": lambda c: (c * 9/5) + 32,  # Fahrenheit
                "k": lambda c: c + 273.15,  # Kelvin
            },
            
            # Data units
            "data": {
                "b": 1.0,  # bytes
                "kb": 1024.0,  # kilobytes
                "mb": 1024.0**2,  # megabytes
                "gb": 1024.0**3,  # gigabytes
                "tb": 1024.0**4,  # terabytes
                "bit": 0.125,  # bits to bytes
                "kbit": 128.0,  # kilobits to bytes
                "mbit": 131072.0,  # megabits to bytes
                "gbit": 134217728.0,  # gigabits to bytes
            }
        }
    
    def _load_technical_terms(self) -> Dict[str, str]:
        """Load technical term definitions."""
        return {
            "tck": "Clock cycle time - the minimum time between two consecutive clock edges",
            "tras": "Row Active Time - minimum time between row activate and precharge commands",
            "trcd": "Row to Column Delay - minimum time between activate and read/write commands",
            "trp": "Row Precharge Time - minimum time between precharge and activate commands",
            "trc": "Row Cycle Time - minimum time between activate commands to same row",
            "cas": "Column Address Strobe latency - number of clock cycles between read command and data availability",
            "vdd": "Supply voltage - main operating voltage for the memory device",
            "vddq": "I/O voltage - voltage for data input/output signals",
            "ecc": "Error Correcting Code - technology for detecting and correcting memory errors",
            "xmp": "Extreme Memory Profile - Intel's memory overclocking profile standard",
            "jedec": "Joint Electron Device Engineering Council - standards organization for memory"
        }
    
    def expand_query(self, query: str) -> List[str]:
        """
        Expand query with synonyms and related terms.
        
        Args:
            query: Original query string
            
        Returns:
            List of expanded queries
        """
        expanded_queries = [query.lower()]
        query_lower = query.lower()
        
        # Find and replace with synonyms
        for term, synonyms in self.synonyms.items():
            for synonym in synonyms:
                if synonym in query_lower:
                    # Create variations with different synonyms
                    for alt_synonym in synonyms:
                        if alt_synonym != synonym:
                            expanded_query = query_lower.replace(synonym, alt_synonym)
                            if expanded_query not in expanded_queries:
                                expanded_queries.append(expanded_query)
        
        return expanded_queries
    
    def normalize_units(self, text: str) -> str:
        """
        Normalize units in text to standard form.
        
        Args:
            text: Text containing units
            
        Returns:
            Text with normalized units
        """
        normalized_text = text.lower()
        
        # Time unit normalization (convert ps to ns, etc.)
        time_pattern = r'(\d+\.?\d*)\s*(ns|ps|us|ms)'
        def normalize_time(match):
            value = float(match.group(1))
            unit = match.group(2)
            # Convert to nanoseconds
            ns_value = value * self.unit_conversions["time"][unit]
            return f"{ns_value:.3f}ns"
        
        normalized_text = re.sub(time_pattern, normalize_time, normalized_text)
        
        # Frequency unit normalization (convert MHz to MT/s, etc.)
        freq_pattern = r'(\d+\.?\d*)\s*(hz|khz|mhz|ghz|mt/s|gt/s)'
        def normalize_freq(match):
            value = float(match.group(1))
            unit = match.group(2)
            # Convert to MT/s for memory frequencies
            if unit in ['mhz', 'khz', 'hz', 'ghz']:
                mt_value = value * self.unit_conversions["frequency"][unit] / 1000000
                return f"{mt_value:.0f}MT/s"
            else:
                return match.group(0)
        
        normalized_text = re.sub(freq_pattern, normalize_freq, normalized_text)
        
        # Voltage unit normalization
        voltage_pattern = r'(\d+\.?\d*)\s*(v|mv|uv)'
        def normalize_voltage(match):
            value = float(match.group(1))
            unit = match.group(2)
            # Convert to volts
            v_value = value * self.unit_conversions["voltage"][unit]
            return f"{v_value:.3f}V"
        
        normalized_text = re.sub(voltage_pattern, normalize_voltage, normalized_text)
        
        return normalized_text
    
    def extract_parameters(self, query: str) -> Dict[str, List[str]]:
        """
        Extract technical parameters from query.
        
        Args:
            query: Query string
            
        Returns:
            Dictionary of extracted parameters
        """
        parameters = {
            "timing": [],
            "voltage": [],
            "frequency": [],
            "memory_type": [],
            "capacity": [],
            "features": []
        }
        
        query_lower = query.lower()
        
        # Extract timing parameters
        timing_terms = ["tck", "tras", "trcd", "trp", "trc", "cas", "cl"]
        for term in timing_terms:
            if term in query_lower:
                parameters["timing"].append(term)
        
        # Extract voltage parameters
        voltage_terms = ["vdd", "vddq", "vpp", "voltage"]
        for term in voltage_terms:
            if term in query_lower:
                parameters["voltage"].append(term)
        
        # Extract frequency terms
        freq_terms = ["frequency", "speed", "mhz", "mt/s", "ghz", "clock"]
        for term in freq_terms:
            if term in query_lower:
                parameters["frequency"].append(term)
        
        # Extract memory types
        memory_types = ["ddr4", "ddr5", "lpddr4", "lpddr5", "sodimm", "udimm", "rdimm"]
        for mem_type in memory_types:
            if mem_type in query_lower:
                parameters["memory_type"].append(mem_type)
        
        # Extract features
        features = ["ecc", "xmp", "dmp", "registered", "unbuffered"]
        for feature in features:
            if feature in query_lower:
                parameters["features"].append(feature)
        
        return parameters
    
    def get_definition(self, term: str) -> Optional[str]:
        """
        Get definition for technical term.
        
        Args:
            term: Technical term
            
        Returns:
            Definition if found, None otherwise
        """
        return self.technical_terms.get(term.lower())
    
    def convert_unit(self, value: float, from_unit: str, to_unit: str, unit_type: str) -> Optional[float]:
        """
        Convert between units.
        
        Args:
            value: Numeric value to convert
            from_unit: Source unit
            to_unit: Target unit
            unit_type: Type of unit (time, frequency, etc.)
            
        Returns:
            Converted value if successful, None otherwise
        """
        if unit_type not in self.unit_conversions:
            return None
        
        conversions = self.unit_conversions[unit_type]
        
        if from_unit not in conversions or to_unit not in conversions:
            return None
        
        # Convert to base unit first
        if callable(conversions[from_unit]):
            base_value = conversions[from_unit](value)
        else:
            base_value = value * conversions[from_unit]
        
        # Then convert to target unit
        if callable(conversions[to_unit]):
            return conversions[to_unit](base_value)
        else:
            return base_value / conversions[to_unit]
    
    def save_synonyms(self, file_path: str):
        """
        Save synonyms to file.
        
        Args:
            file_path: Path to save file
        """
        try:
            data = {
                "synonyms": self.synonyms,
                "unit_conversions": self.unit_conversions,
                "technical_terms": self.technical_terms
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Synonyms saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving synonyms: {e}")
    
    def load_synonyms(self, file_path: str):
        """
        Load synonyms from file.
        
        Args:
            file_path: Path to load file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.synonyms = data.get("synonyms", self.synonyms)
            self.unit_conversions = data.get("unit_conversions", self.unit_conversions)
            self.technical_terms = data.get("technical_terms", self.technical_terms)
            
            logger.info(f"Synonyms loaded from {file_path}")
            
        except Exception as e:
            logger.error(f"Error loading synonyms: {e}")


# Global instance
synonym_dict = SynonymDictionary()


def get_synonym_dictionary() -> SynonymDictionary:
    """Get global synonym dictionary instance."""
    return synonym_dict


def expand_query_with_synonyms(query: str) -> List[str]:
    """
    Expand query using global synonym dictionary.
    
    Args:
        query: Original query
        
    Returns:
        List of expanded queries
    """
    return synonym_dict.expand_query(query)


def normalize_text_units(text: str) -> str:
    """
    Normalize units in text using global synonym dictionary.
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    return synonym_dict.normalize_units(text)
