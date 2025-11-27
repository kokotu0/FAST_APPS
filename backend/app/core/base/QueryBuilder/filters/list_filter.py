from typing import Any, Union, List
from sqlalchemy import ColumnElement, and_, or_
from .base import BaseFilter
from ..types import ListOperator, LIST_OPERATORS

class ListFilter(BaseFilter[ListOperator]):
    """리스트 필터 구현"""
    
    def supports_operator(self, operator: str) -> bool:
        return operator in LIST_OPERATORS
    
    def apply(self, column: ColumnElement, operator: ListOperator, value: Any) -> ColumnElement:
        """리스트 필터 적용"""
        # 빈 문자열 제거
        if isinstance(value, list):
            value = [v for v in value if v != '']
        if '' in value : value = value.pop('')
        
        if not isinstance(operator, str) or operator not in LIST_OPERATORS:
            operator = "in"  # 기본값
        
        if operator == "in" and isinstance(value, list):
            return column.in_(value)
        elif operator == "notIn" and isinstance(value, list):
            return ~column.in_(value)
        elif operator == "between" and isinstance(value, list) and len(value) == 2:
            return and_(column >= value[0], column <= value[1])
        elif operator == "arrIncludesAll" and isinstance(value, list):
            return column.in_(value)
        elif operator == "arrIncludesSome" and isinstance(value, list):
            return column.in_(value)
        elif operator == "arrIncludes" and isinstance(value, list):
            return column.in_(value)
        # 필요시 PostgreSQL의 JSON 연산자 사용
        else:
            values = value if isinstance(value, list) else [value]
            return column.in_(values) 