from abc import ABC, abstractmethod
from typing import Any, Union, TYPE_CHECKING, TypeVar, Generic
from sqlalchemy import ColumnElement
from sqlmodel.sql._expression_select_cls import SelectOfScalar

if TYPE_CHECKING:
    from sqlalchemy.orm import RelationshipProperty
    from ..types import RelationOperator

OperatorType = TypeVar("OperatorType")


class BaseFilter(ABC, Generic[OperatorType]):
    """필터의 기본 인터페이스"""

    @abstractmethod
    def apply(
        self, column: ColumnElement, operator: OperatorType, value: Any
    ) -> ColumnElement | SelectOfScalar:
        """일반 컬럼 필터를 적용하고 SQLAlchemy 조건을 반환"""
        pass

    def apply_relation(
        self, relation: "RelationshipProperty", operator: "RelationOperator", value: Any
    ) -> ColumnElement:
        """관계 필터를 적용하고 SQLAlchemy 조건을 반환"""
        raise NotImplementedError("이 필터는 관계 필터를 지원하지 않습니다")

    @abstractmethod
    def supports_operator(self, operator: str) -> bool:
        """해당 연산자를 지원하는지 확인"""
        pass
