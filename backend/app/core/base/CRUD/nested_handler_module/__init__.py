"""
중첩된 관계(Nested Relationship) 처리 모듈

기존 nested_handler.py의 기능을 모듈화하여 분리한 패키지입니다.
각 컴포넌트별로 책임을 분리하여 테스트 용이성과 재사용성을 높였습니다.
"""

from .handler import NestedRelationshipHandler
from .metadata_manager import MetadataManager
from .data_processor import DataProcessor
from .relationship_updater import RelationshipUpdater
from .model_inspector import ModelInspector
from .types import (
    ProcessedData,
    NestedValue,
    InputData,
    HasModelDump,
)

__all__ = [
    # Main handler
    "NestedRelationshipHandler",
    
    # Components
    "MetadataManager",
    "DataProcessor", 
    "RelationshipUpdater",
    "ModelInspector",
    
    # Types
    "ProcessedData",
    "NestedValue",
    "InputData",
    "HasModelDump",
]

__version__ = "1.0.0"
