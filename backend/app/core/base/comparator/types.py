from typing import (
    List,
    Dict,
    Any,
    Literal,
    Set,
    Tuple,
    Union,
    Optional,
    TypedDict,
    Type,
    Protocol,
    TypeVar,
    Generic,
)
from pydantic import BaseModel
from sqlmodel import SQLModel
import inspect

# 제네릭 타입 변수들
T = TypeVar("T")
V = TypeVar("V")


class DiffChange(TypedDict, Generic[V]):
    """변경된 필드 정보"""

    old: V
    new: V


class ModifiedItem(TypedDict, Generic[T]):
    """변경된 항목 정보"""

    key: Dict[str, Any]
    old_item: T
    new_item: T
    changed_fields: Dict[str, DiffChange[Any]]


class ComparisonResult(TypedDict, Generic[T]):
    """비교 결과"""

    added: List[T]
    removed: List[T]
    modified: List[ModifiedItem[T]]
    unchanged: List[T]


class ModelComparisonError(Exception):
    """모델 비교 중 발생하는 오류"""

    pass
