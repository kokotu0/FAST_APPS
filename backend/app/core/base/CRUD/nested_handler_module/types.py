"""
중첩된 관계 처리를 위한 타입 정의
"""

from typing import Dict, Any, List, Union, Set, Optional, Protocol, runtime_checkable
from enum import Enum
from sqlmodel import SQLModel
from pydantic import BaseModel

# 기본 타입 정의
ProcessedData = Dict[str, Any]
NestedValue = Union[Dict[str, Any], List[Dict[str, Any]], Any]
InputData = Union[Dict[str, Any], SQLModel, BaseModel]

@runtime_checkable
class HasModelDump(Protocol):
    """model_dump 메서드를 가진 객체를 위한 프로토콜"""
    def model_dump(self) -> Dict[str, Any]: ...

