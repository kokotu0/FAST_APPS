from typing import Any, Union, List
from sqlalchemy import ColumnElement, and_
from datetime import datetime
from .base import BaseFilter
from ..types import DateOperator, DATE_OPERATORS

class DateFilter(BaseFilter[DateOperator]):
    """날짜 필터 구현"""
    
    def supports_operator(self, operator: str) -> bool:
        return operator in DATE_OPERATORS
    
    def apply(self, column: ColumnElement, operator, value: Any) -> ColumnElement:
        """날짜 필터 적용"""
        if not isinstance(operator, str) or operator not in DATE_OPERATORS:
            operator = "equals"  # 기본값
        
        try:
            # between 또는 betweenInclusive 연산자가 아닌 경우 단일 날짜 처리
            if operator not in ["between", "betweenInclusive"]:
                if isinstance(value, str):
                    date_value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    # 날짜 파싱 실패시 문자열로 처리
                    return column == value
                
                if operator == "equals":
                    return column == date_value
                elif operator == "notEquals":
                    return column != date_value
                elif operator == "lessThan":
                    return column < date_value
                elif operator == "lessThanOrEqualTo":
                    return column <= date_value
                elif operator == "greaterThan":
                    return column > date_value
                elif operator == "greaterThanOrEqualTo":
                    return column >= date_value
                else:
                    return column == date_value  # 기본값
            
            # between 또는 betweenInclusive 연산자 처리
            elif operator in ["between", "betweenInclusive"] and isinstance(value, list) and len(value) == 2:
                val1, val2 = value[0], value[1]
                date_values = []
                
                if val1 is not None:
                    date_values.append(datetime.fromisoformat(val1.replace('Z', '+00:00')))
                else:
                    date_values.append(None)
                    
                if val2 is not None:
                    date_values.append(datetime.fromisoformat(val2.replace('Z', '+00:00')))
                else:
                    date_values.append(None)
                
                # between 날짜 필터에서 None 값 처리
                parsed_val1, parsed_val2 = date_values[0], date_values[1]
                
                # 둘 다 None이면 조건 없음
                if parsed_val1 is None and parsed_val2 is None:
                    return column == column  # 항상 참인 조건
                
                # 첫 번째 값만 있으면 >= 조건
                elif parsed_val2 is None and parsed_val1 is not None:
                    return column >= parsed_val1
                
                # 두 번째 값만 있으면 <= 조건  
                elif parsed_val1 is None and parsed_val2 is not None:
                    return column <= parsed_val2
                
                # 둘 다 있으면 BETWEEN 조건
                else:
                    if operator == "between":
                        return and_(column > parsed_val1, column < parsed_val2)
                    else:  # betweenInclusive
                        return and_(column >= parsed_val1, column <= parsed_val2)
            else:
                # 기본값
                return column == value
        except (ValueError, AttributeError):
            # 날짜 파싱 실패시 문자열로 처리
            return column == value 