from typing import Any, Union, List
from sqlalchemy import ColumnElement, and_
from .base import BaseFilter
from ..types import NumberOperator, NUMBER_OPERATORS, FilterFns

class NumberFilter(BaseFilter[NumberOperator]):
    """숫자 필터 구현"""
    
    def supports_operator(self, operator: str) -> bool:
        return operator in NUMBER_OPERATORS
    
    def apply(self, column: ColumnElement, operator: FilterFns, value: Any) -> ColumnElement:
        """숫자 필터 적용"""
        if not isinstance(operator, str) or operator not in NUMBER_OPERATORS:
            operator = "equals"  # 기본값
        
        # 값 타입 검증 및 변환
        if isinstance(value, list):
            if len(value) == 2 and (operator == "between" or operator == "betweenInclusive"):
                val1, val2 = value[0], value[1]
                
                # 둘 다 None이거나 공백이면 조건 없음
                if (val1 is None or str(val1).strip() == "") and (val2 is None or str(val2).strip() == ""):
                    return column == column  # 항상 참인 조건
                
                # 첫 번째 값만 있으면 >= 조건
                elif (val2 is None or str(val2).strip() == "") and (val1 is not None and str(val1).strip() != ""):
                    return column >= val1
                
                # 두 번째 값만 있으면 <= 조건  
                elif (val1 is None or str(val1).strip() == "") and (val2 is not None and str(val2).strip() != ""):
                    return column <= val2
                # 둘 다 있으면 BETWEEN 조건
                else:
                    if operator == "between":
                        return and_(column > val1, column < val2)
                    else:  # betweenInclusive
                        return and_(column >= val1, column <= val2)
            else:
                # 리스트가 아니면 첫 번째 값 사용
                value = value[0] if value else None
        
        if operator == "equals":
            return column == value
        elif operator == "notEquals":
            return column != value
        elif operator == "lessThan":
            return column < value
        elif operator == "lessThanOrEqualTo":
            return column <= value
        elif operator == "greaterThan":
            return column > value
        elif operator == "greaterThanOrEqualTo":
            return column >= value
        else:
            return column == value  # 기본값 