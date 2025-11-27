"""
TableInterprete.py - 기존 파일을 새로운 QueryBuilder 구조로 교체

이 파일은 기존 코드와의 호환성을 위해 유지되며, 
새로운 모듈화된 QueryBuilder 구조를 사용합니다.
"""

# 새로운 QueryBuilder 구조로 리다이렉트
from core.base.QueryBuilder import (
    QueryBuilder,
    TextOperator, NumberOperator, DateOperator, ListOperator, FilterFns, ColumnFilterFns,
    TEXT_OPERATORS, NUMBER_OPERATORS, DATE_OPERATORS, LIST_OPERATORS,
    ColumnFilter, Pagination, Sorting, TableRequest,
    BaseFilter, TextFilter, NumberFilter, DateFilter, ListFilter,
    RequestInterpreter
)

# 기존 코드와의 호환성을 위한 별칭
__all__ = [
    'QueryBuilder',
    'TextOperator', 'NumberOperator', 'DateOperator', 'ListOperator', 'FilterFns', 'ColumnFilterFns',
    'TEXT_OPERATORS', 'NUMBER_OPERATORS', 'DATE_OPERATORS', 'LIST_OPERATORS',
    'ColumnFilter', 'Pagination', 'Sorting', 'TableRequest',
    'BaseFilter', 'TextFilter', 'NumberFilter', 'DateFilter', 'ListFilter',
    'RequestInterpreter'
]

# 사용 예시 및 문서
"""
# 새로운 사용법 (권장)
from core.base.QueryBuilder import QueryBuilder
from models import User

# MRT 요청 JSON으로 쿼리 빌드
builder = QueryBuilder(User, mrt_request_json)
results = builder.execute(session)

# 또는 개별 필터 적용
builder = QueryBuilder(User)
query = (builder
    .add_filter("name", "contains", "john")
    .add_filter("age", "between", [20, 30])
    .add_sorting("created_at", descending=True)
    .add_pagination(0, 10)
    .build())

# 기존 사용법 (호환성 유지)
from core.internal.TableInterprete import QueryBuilder
# ... 동일한 사용법
"""