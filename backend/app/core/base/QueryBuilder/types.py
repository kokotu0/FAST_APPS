from typing import Dict, List, Union, Literal, TypeVar, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass
from typing import Literal, Union, Dict

# Material React Table 필터 연산자들
TextOperator = Literal["equals", "notEquals", "lessThan", "lessThanOrEqualTo",
                       "greaterThan", "greaterThanOrEqualTo", 
                       "contains", "notContains", "startsWith", "endsWith", "fuzzy"]

NumberOperator = Literal["equals", "notEquals", "lessThan", "lessThanOrEqualTo",
                         "greaterThan", "greaterThanOrEqualTo", "between", "betweenInclusive"]
BooleanOperator = Literal["equals"]
DateOperator = Literal["equals", "notEquals", "lessThan", "lessThanOrEqualTo",
                       "greaterThan", "greaterThanOrEqualTo", "between", "betweenInclusive"]

ListOperator = Literal["in", "notIn", "between", "arrIncludes", "arrIncludesSome", "arrIncludesAll"]

# 1:M 관계 필터링을 위한 연산자들
RelationOperator = Literal[
    "hasAny", "hasAll", "hasChild", "hasNotChild"
]
PassOperator=Literal["auto","custom"]

FilterFns = Union[TextOperator, NumberOperator, DateOperator, ListOperator, RelationOperator, BooleanOperator, PassOperator]

# 컬럼별 필터 함수 매핑 타입# Literal 타입들의 값들을 리스트로 정의 (런타임 체크용)
TEXT_OPERATORS = ["equals", "notEquals", "lessThan", "lessThanOrEqualTo",
                  "greaterThan", "greaterThanOrEqualTo", 
                  "contains", "notContains", "startsWith", "endsWith", "fuzzy"]

NUMBER_OPERATORS = ["equals", "notEquals", "lessThan", "lessThanOrEqualTo",
                    "greaterThan", "greaterThanOrEqualTo", "between", "betweenInclusive"]

DATE_OPERATORS = ["equals", "notEquals", "lessThan", "lessThanOrEqualTo",
                  "greaterThan", "greaterThanOrEqualTo", "between", "betweenInclusive"]

LIST_OPERATORS = ["in", "notIn", "between", "arrIncludes", "arrIncludesSome", "arrIncludesAll"]

RELATION_OPERATORS = [
    "hasAny", "hasAll", "hasChild", "hasNotChild"
] 
BOOLEAN_OPERATORS=["equals",]

ColumnFilterFns = Dict[str, FilterFns]
@dataclass
class ColumnFilter:
    id: str
    value: Any

@dataclass
class Pagination:
    pageIndex: int = Field(ge=0,default=0)
    pageSize: int = Field(gt=0,default=10)

@dataclass
class Sorting:
    id: str
    desc: bool = False

class TableRequest(BaseModel):
    columnFilterFns: ColumnFilterFns = Field(default={})  # 컬럼명을 키로 사용
    columnFilters: List[ColumnFilter] = Field(default=[])
    pagination: Pagination = Field(default=Pagination(pageIndex=0, pageSize=10))    
    sorting: List[Sorting] = Field(default=[])  
    globalFilter: str = Field(default="")
    globalfilterFns: FilterFns = Field(default="contains")