from dataclasses import asdict, dataclass
from typing import List, Optional

@dataclass
class JedecSection:
    id: str
    standard: str
    version: str
    section: str
    title: str
    page_start: int
    page_end: int
    text: str
    tokens: Optional[List[str]] = None

    def to_dict(self):
        return asdict(self)

@dataclass
class JedecDocument:
    standard: str
    version: str
    source: str
    parser: str
    created_at: str
    sections: List[JedecSection]

    def to_dict(self):
        return {
            **asdict(self),
            "sections": [s.to_dict() for s in self.sections]
        }