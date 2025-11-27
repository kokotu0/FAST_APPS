"""
QueryBuilder - Material React Table 호환 쿼리 빌더

이 패키지는 Material React Table의 상태를 SQLAlchemy 쿼리로 변환하는 기능을 제공합니다.
모듈화된 구조로 설계되어 유지보수와 확장이 용이합니다.

사용 예시:
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
"""

from .core.query_builder import QueryBuilder
from .types import (
    TextOperator, NumberOperator, DateOperator, ListOperator, RelationOperator, FilterFns, ColumnFilterFns,
    TEXT_OPERATORS, NUMBER_OPERATORS, DATE_OPERATORS, LIST_OPERATORS, RELATION_OPERATORS,
    ColumnFilter, Pagination, Sorting, TableRequest
)
from .filters import (
    BaseFilter, TextFilter, NumberFilter, DateFilter, ListFilter, RelationFilter
)
from .interpreters import RequestInterpreter

__version__ = "1.0.0"

__all__ = [
    # 메인 클래스
    'QueryBuilder',
    
    # 모델들
    'TextOperator', 'NumberOperator', 'DateOperator', 'ListOperator', 'RelationOperator', 'FilterFns', 'ColumnFilterFns',
    'TEXT_OPERATORS', 'NUMBER_OPERATORS', 'DATE_OPERATORS', 'LIST_OPERATORS', 'RELATION_OPERATORS',
    'ColumnFilter', 'Pagination', 'Sorting', 'TableRequest',
    
    # 필터들
    'BaseFilter', 'TextFilter', 'NumberFilter', 'DateFilter', 'ListFilter', 'RelationFilter',
    
    # 인터프리터
    'RequestInterpreter'
] 