from typing import Any, Union
from sqlalchemy import BinaryExpression, cast, String, and_, ColumnElement
from .base import BaseFilter
from ..types import TextOperator, TEXT_OPERATORS

class TextFilter(BaseFilter[TextOperator]):
    """텍스트 필터 구현"""
    
    def supports_operator(self, operator: str) -> bool:
        return operator in TEXT_OPERATORS
    
    def apply(self, column: ColumnElement, operator: TextOperator, value: Any) -> ColumnElement:
        """텍스트 필터 적용"""
        if not isinstance(operator, str) or operator not in TEXT_OPERATORS:
            operator = "contains"  # 기본값
        
        column_str = cast(column, String)
        str_value = str(value) if value is not None else ""
        
        if operator == "equals" or operator =='equals2':
            return column_str == str_value
        elif operator == "notEquals":
            return column_str != str_value
        elif operator == "contains":
            return column_str.ilike(f"%{str_value}%")
        elif operator == "notContains":
            return ~column_str.ilike(f"%{str_value}%")
        elif operator == "startsWith":
            return column_str.ilike(f"{str_value}%")
        elif operator == "endsWith":
            return column_str.ilike(f"%{str_value}")
        elif operator == "fuzzy":
            # fuzzy 검색 - 각 단어별로 매개변수화
            words = str_value.split()
            conditions = []
            for word in words:
                conditions.append(column_str.ilike(f"%{word}%"))
            return and_(*conditions)
        else:
            return column_str.ilike(f"%{str_value}%")  # 기본값 