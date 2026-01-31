from enum import Enum
from typing import Dict, Any
from dataclasses import dataclass, field
import uuid

class NodeType(str, Enum):
    IDEA = "idea"
    ENTITY = "entity"
    CATEGORY = "category"
    SENDER = "sender"
    URL = "url"

class EdgeType(str, Enum):
    CONTAINS = "contains"
    MENTIONS = "mentions"
    RELATED_TO = "related_to"
    SENT_BY = "sent_by"
    CATEGORIZED_AS = "categorized_as"

@dataclass
class Node:
    id: uuid.UUID
    type: NodeType
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Edge:
    source: uuid.UUID
    target: uuid.UUID
    type: EdgeType
    properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def unique_id(self) -> str:
        return f"{self.source}-{self.target}-{self.type}" 