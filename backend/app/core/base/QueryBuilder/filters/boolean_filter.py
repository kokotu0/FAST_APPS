from .base import BaseFilter
from ..types import BOOLEAN_OPERATORS, BooleanOperator
from sqlalchemy.sql.elements import ColumnElement

class BooleanFilter(BaseFilter[BooleanOperator]):
    def __init__(self):
        super().__init__()

    def supports_operator(self, operator: str) -> bool:
        return operator in BOOLEAN_OPERATORS

    def apply(self, column :ColumnElement, operator: BooleanOperator, value):
        if operator == "equals": 
            print(f"BooleanFilter 적용: {column} == {value}")
            return column == value
        else:
            raise ValueError(f"지원하지 않는 필터 함수: {operator}")

