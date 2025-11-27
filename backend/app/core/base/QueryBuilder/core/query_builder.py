import logging
from typing import Optional, Any, Sequence, List, Dict, Generic, TypeVar
from sqlmodel import SQLModel, select, Session
from sqlalchemy import or_, desc, asc, func
from sqlalchemy.inspection import inspect
from typing import cast

from ..types import (
    BooleanOperator,
    DateOperator,
    FilterFns,
    ListOperator,
    RelationOperator,
    NumberOperator,
    TableRequest,
    TextOperator,
)
from ..filters import (
    TextFilter,
    NumberFilter,
    DateFilter,
    ListFilter,
    RelationFilter,
    BooleanFilter,
)
from .column_inspector import ColumnInspector, PathInfo
from sqlmodel.sql._expression_select_cls import SelectOfScalar
from .path_resolver import PathResolver
from ..interpreters.request_interpreter import RequestInterpreter

T = TypeVar("T", bound=SQLModel)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class QueryBuilder(Generic[T]):
    """재설계된 QueryBuilder 클래스"""
    request: TableRequest  # 타입 명시
    row_count_query: SelectOfScalar[int]
    def __init__(
        self,
        model: type[T],
        request_json: Optional[str] = None,
        request: Optional[TableRequest] = None,
        session: Optional[Session] = None,
    ):
        self.model = model
        self.query = select(model)
        self.table_state = None
        self.row_count_query = None  # pyright: ignore[reportAttributeAccessIssue]
        # 컴포넌트 초기화
        self.column_inspector = ColumnInspector(model)
        self.path_resolver = PathResolver(model)
        self.request_interpreter = RequestInterpreter()
        # 필터들 초기화

        # 상태 추적
        self.invalid_paths = []
        self.applied_filters = []  # 적용된 필터 추적
        self.applied_joins = set()  # 적용된 JOIN 추적 (중복 방지)
        self.text_filter = TextFilter()
        self.boolean_filter = BooleanFilter()
        self.date_filter = DateFilter()
        self.number_filter = NumberFilter()
        self.list_filter = ListFilter()
        self.relation_filter = RelationFilter(model)
        # 요청 데이터 파싱
        if request_json:
            self.request = self.request_interpreter.interpret(request_json)
        elif request:
            self.request = request
        else:
            self.request = TableRequest()
            
    def _is_valid_filter_value(self, value) -> bool:
        """필터 값이 유효한지 확인"""
        if value is None:
            return False

        if isinstance(value, list):
            valid_items = [
                item for item in value if item is not None and str(item).strip() != ""
            ]
            return len(valid_items) > 0

        if isinstance(value, str):
            return value.strip() != ""

        return True

    # ===== Public API: TableRequest 변형 =====
    def add_column_filter(
        self, path: str, filter_fn: FilterFns, value: Any
    ) -> "QueryBuilder[T]":
        """TableRequest에 컬럼 필터 추가 (중복 가능)"""
        from ..types import ColumnFilter
        self.request.columnFilters.append(ColumnFilter(id=path, value=value))
        self.request.columnFilterFns[path] = filter_fn
        logger.debug(f"컬럼 필터 추가: {path} {filter_fn} {value}")
        return self
    
    # ===== Internal API: Query 직접 변경 =====
    def _apply_filter(
        self, path: str, filter_fn: FilterFns, value: Any
    ) -> "QueryBuilder[T]":
        """Query에 필터를 직접 적용 (내부용)"""
        try:
            # 1. 경로 분석
            path_info = self.column_inspector.analyze_path(path)

            # 2. SQLAlchemy 컬럼 해결
            column, aliases_needed = self.path_resolver.resolve_nested_path(path)

            logger.debug(f"필터 적용:")
            logger.debug(f"  경로: {path}")
            logger.debug(f"  타입: {path_info.column_type}")
            logger.debug(f"  연산자: {filter_fn}")
            logger.debug(f"  값: {value}")

            # 2.5. JOIN 추가 (중첩된 경로인 경우)
            for relationship_attr, alias, join_path in aliases_needed:
                if join_path not in self.applied_joins:
                    logger.debug(f"  JOIN 추가: {join_path} -> {alias}")
                    self.query = self.query.join(alias, relationship_attr)
                    self.applied_joins.add(join_path)
                else:
                    logger.debug(f"  JOIN 스킵 (이미 추가됨): {join_path}")

            # 3. Query에 필터 적용
            self.query = self._apply_filter_by_type(
                column=column,
                path_info=path_info,
                filter_fn=filter_fn,
                value=value,
                path=path,
            )

        except ValueError as e:
            error_msg = f"{path}: {str(e)}"
            self.invalid_paths.append(error_msg)
            logger.debug(f"  ✗ 경로 오류: {str(e)}")

        except Exception as e:
            error_msg = f"{path}: 예상치 못한 오류 - {str(e)}"
            self.invalid_paths.append(error_msg)
            logger.debug(f"  ✗ 예상치 못한 오류: {str(e)}")
            raise e
        return self

    def _apply_filter_by_type(
        self, column, path_info: PathInfo, filter_fn: FilterFns, value: Any, path: str
    ) -> SelectOfScalar:
        """타입에 따른 필터 적용"""
        try:
            column_type = path_info.column_type
            logger.debug("column_type: " + column_type)
            logger.debug("filter_fn: " + filter_fn)
            logger.debug("value: " + str(value))
            logger.debug("path: " + path)
            # 관계 필터 (우선순위 최고) - 모든 관계 연산자 지원 확인
            if filter_fn =='custom':
                return self.query
            if column_type == "relation" and self.relation_filter.supports_operator(
                filter_fn
            ):
                logger.debug(f"관계 필터 적용: {column} {filter_fn} {value}")
                filter_fn = cast(RelationOperator, filter_fn)
                return self.relation_filter.apply(column, filter_fn, value, self.query)

            # 숫자 타입 필터
            elif column_type == "number" and self.number_filter.supports_operator(
                filter_fn
            ):
                logger.debug(f"숫자 필터 적용: {column} {filter_fn} {value}")
                filter_fn = cast(NumberOperator, filter_fn)
                return self.query.where(
                    self.number_filter.apply(column, filter_fn, value)
                )

            # 날짜 타입 필터
            elif column_type == "date" and self.date_filter.supports_operator(
                filter_fn
            ):
                logger.debug(f"날짜 필터 적용: {column} {filter_fn} {value}")
                filter_fn = cast(DateOperator, filter_fn)
                return self.query.where(
                    self.date_filter.apply(column, filter_fn, value)
                )

            # 불린 타입 필터
            elif column_type == "boolean" and self.boolean_filter.supports_operator(
                filter_fn
            ):
                logger.debug(f"불린 필터 적용: {column} {filter_fn} {value}")
                filter_fn = cast(BooleanOperator, filter_fn)
                return self.query.where(
                    self.boolean_filter.apply(column, filter_fn, value)
                )

            # 리스트 연산자 (in, not_in 등)
            elif self.list_filter.supports_operator(filter_fn):
                logger.debug(f"리스트 필터 적용: {column} {filter_fn} {value}")
                filter_fn = cast(ListOperator, filter_fn)
                return self.query.where(
                    self.list_filter.apply(column, filter_fn, value)
                )

            # 텍스트 필터 (기본)
            elif self.text_filter.supports_operator(filter_fn):
                logger.debug(f"텍스트 필터 적용: {column} {filter_fn} {value}")
                filter_fn = cast(TextOperator, filter_fn)
                return self.query.where(
                    self.text_filter.apply(column, filter_fn, value)
                )

            else:
                # 전부 미해당시 기본 -> 임시조치임.
                filter_fn = "fuzzy"
                return self.query.where(
                    self.text_filter.apply(column, filter_fn, value)
                )

        except Exception as e:
            logger.debug(f"    필터 적용 중 오류: {e}")
            raise e
            return self.query.where(False)

    # ===== Public API: TableRequest 변형 =====
    def set_global_filter(
        self, global_filter: str, filter_fn: FilterFns = "contains"
    ) -> "QueryBuilder":
        """TableRequest의 전역 필터를 설정 (기존 값 대체)"""
        self.request.globalFilter = global_filter
        self.request.globalfilterFns = filter_fn
        logger.debug(f"전역 필터 설정: '{global_filter}' ({filter_fn})")
        return self
    
    # ===== Internal API: Query 직접 변경 =====
    def _apply_global_filter(
        self, global_filter: str, filter_fn: FilterFns = "contains"
    ) -> "QueryBuilder":
        """Query에 전역 필터를 직접 적용 (내부용)"""
        if not global_filter:
            return self

        logger.debug(f"전역 필터 적용: '{global_filter}' ({filter_fn})")
        conditions = []

        # 현재 모델의 모든 텍스트 컬럼에서 검색
        for column in inspect(self.model).columns:
            try:
                # 텍스트 계열 컬럼만 대상
                path_info = PathInfo(
                    column.name,
                    self.column_inspector._get_sqlalchemy_column_type(column),
                )
                if path_info.column_type in ["text"]:
                    conditions.append(column.ilike(f"%{global_filter}%"))
            except Exception:
                continue

        if conditions:
            self.query = self.query.where(or_(*conditions))
            logger.debug(f"  ✓ {len(conditions)}개 컬럼에 전역 필터 적용")
        else:
            logger.debug(f"  ○ 적용 가능한 컬럼이 없음")

        return self

    # ===== Public API: TableRequest 변형 =====
    def add_sorting(self, column_path: str, descending: bool = False) -> "QueryBuilder":
        """TableRequest에 정렬 추가 (중복 가능)"""
        from ..types import Sorting
        self.request.sorting.append(Sorting(id=column_path, desc=descending))
        logger.debug(f"정렬 추가: {column_path} ({'내림차순' if descending else '오름차순'})")
        return self
    
    # ===== Internal API: Query 직접 변경 =====
    def _apply_sorting(self, column_path: str, descending: bool = False) -> "QueryBuilder":
        """Query에 정렬을 직접 적용 (내부용)"""
        try:
            # 경로 분석
            path_info = self.column_inspector.analyze_path(column_path)

            # 관계 컬럼은 정렬할 수 없음
            if path_info.column_type == "relation":
                raise ValueError(f"관계 컬럼 {column_path}는 정렬할 수 없습니다.")

            # SQLAlchemy 컬럼 해결
            column, aliases_needed = self.path_resolver.resolve_nested_path(column_path)

            # JOIN 추가 (중첩된 경로인 경우)
            for relationship_attr, alias, join_path in aliases_needed:
                if join_path not in self.applied_joins:
                    logger.debug(f"  정렬을 위한 JOIN 추가: {join_path} -> {alias}")
                    self.query = self.query.join(alias, relationship_attr)
                    self.applied_joins.add(join_path)
                else:
                    logger.debug(f"  JOIN 스킵 (이미 추가됨): {join_path}")

            if descending:
                self.query = self.query.order_by(desc(column))
            else:
                self.query = self.query.order_by(asc(column))

            logger.debug(
                f"정렬 적용: {column_path} ({'내림차순' if descending else '오름차순'})"
            )

        except (ValueError, AttributeError) as e:
            error_msg = f"정렬 경로 오류 - {column_path}: {str(e)}"
            self.invalid_paths.append(error_msg)
            logger.error(f"  ✗ {error_msg}")

        return self

    # ===== Public API: TableRequest 변형 =====
    def set_pagination(self, page_index: int, page_size: int) -> "QueryBuilder":
        """TableRequest의 페이지네이션을 설정 (기존 값 대체)"""
        self.request.pagination.pageIndex = page_index
        self.request.pagination.pageSize = page_size
        logger.debug(
            f"페이지네이션 설정: 페이지 {page_index}, {page_size}개/페이지"
        )
        return self
    
    # ===== Internal API: Query 직접 변경 =====
    def _apply_pagination(self, page_index: int, page_size: int) -> "QueryBuilder":
        """Query에 페이지네이션을 직접 적용 (내부용)"""
        offset = page_index * page_size
        self.query = self.query.offset(offset).limit(page_size)
        
        logger.debug(
            f"페이지네이션 적용: 페이지 {page_index}, {page_size}개/페이지 (오프셋: {offset})"
        )
        return self
    def apply_column_filter(self)->"QueryBuilder":
        """TableRequest의 컬럼 필터를 Query에 적용"""
        logger.debug(f"컬럼 필터 {len(self.request.columnFilters)}개 적용 시작")
        for column_filter in self.request.columnFilters:
            filter_fn = (
                self.request.columnFilterFns[column_filter.id]
                if column_filter.id in self.request.columnFilterFns.keys()
                else None
            )
            if filter_fn is None:
                logger.debug(
                    f"  ✗ 필터 함수 찾을 수 없음: {column_filter.id} - fuzzy 적용"
                )
                filter_fn = "fuzzy"
            self._apply_filter(column_filter.id, filter_fn, column_filter.value)
        return self
    
    def apply_global_filter(self)->"QueryBuilder":
        """TableRequest의 전역 필터를 Query에 적용"""
        if not self.request:
            self.request = TableRequest()
        if self.request.globalFilter:
            global_filter_fn = self.request.globalfilterFns or "contains"
            self._apply_global_filter(self.request.globalFilter, global_filter_fn)
        return self
    
    def apply_sorting(self)->"QueryBuilder":
        """TableRequest의 정렬을 Query에 적용"""
        logger.debug(f"정렬 {len(self.request.sorting)}개 적용 시작")
        for sort in self.request.sorting:
            self._apply_sorting(sort.id, sort.desc)
        return self
    
    def apply_pagination(self)->"QueryBuilder":
        """TableRequest의 페이지네이션을 Query에 적용"""
        self._apply_pagination(self.request.pagination.pageIndex, self.request.pagination.pageSize)
        return self
    
    def apply_table_request(self , apply_pagination: bool = True) -> "QueryBuilder":
        """TableRequest 기반으로 모든 필터링 적용"""
        if not self.request:
            self.request = TableRequest()

        logger.debug("=== TableRequest 적용 시작 ===")
        self.apply_global_filter()
        self.apply_column_filter()
        self.apply_sorting()
        self.row_count_query = self.get_row_count_query()
        if apply_pagination:
            self.apply_pagination()
        return self

    def get_row_count_query(self) -> SelectOfScalar[int]:
        
        return select(func.count()).select_from(self.query.subquery())
    
    def build(self) -> SelectOfScalar[T]:
        return self.query

    def execute_query(
        self,
        session: Session,
    ) -> Sequence[T]:
        return session.exec(self.query).all()
    
    # ===== Property 추가 =====
    @property
    def pagination(self) -> Dict:
        """페이지네이션 정보 반환"""
        return {
            "pageIndex": self.request.pagination.pageIndex,
            "pageSize": self.request.pagination.pageSize,
            "offset": self.request.pagination.pageIndex * self.request.pagination.pageSize,
        }
    
    @property
    def sorting(self) -> List[Dict]:
        """정렬 정보 반환"""
        return [
            {"id": sort.id, "desc": sort.desc}
            for sort in self.request.sorting
        ]
    
    @property
    def column_filters(self) -> List[Dict]:
        """컬럼 필터 정보 반환"""
        return [
            {
                "id": f.id,
                "value": f.value,
                "filterFn": self.request.columnFilterFns.get(f.id, "fuzzy")
            }
            for f in self.request.columnFilters
        ]
    
    @property
    def global_filter(self) -> Dict:
        """글로벌 필터 정보 반환"""
        return {
            "filter": self.request.globalFilter,
            "filterFn": self.request.globalfilterFns,
        }
    @property
    def get_compiled_query(self) -> str:
        return str(self.query.compile(compile_kwargs={"literal_binds": True}))
    
    def validate_paths(self, paths: List[str]) -> Dict[str, Any]:
        """경로들의 유효성을 검증하고 분석 결과 반환"""
        validation_results = {"valid_paths": [], "invalid_paths": [], "warnings": []}

        for path in paths:
            try:
                path_info = self.column_inspector.analyze_path(path)

                validation_results["valid_paths"].append(
                    {
                        "path": path,
                        "type": path_info.column_type,
                        "is_nested": path_info.is_nested,
                        "relationships": (
                            path_info.relationships if path_info.is_nested else None
                        ),
                    }
                )

                # 경고 검사
                if path_info.is_nested:
                    has_one_to_many = any(
                        rel["cardinality"] in ["1:N", "N:N"]
                        for rel in path_info.relationships
                    )
                    if has_one_to_many:
                        validation_results["warnings"].append(
                            {
                                "path": path,
                                "message": "1:N 관계가 포함된 중첩 경로입니다. 결과가 예상과 다를 수 있습니다.",
                            }
                        )

            except Exception as e:
                validation_results["invalid_paths"].append(
                    {"path": path, "error": str(e)}
                )

        return validation_results


# 사용 예시와 개선된 패턴
"""
# 기본 사용법
builder = QueryBuilder(User)
results = builder.add_filter("name", "contains", "John")
                .add_filter("user.profile.bio", "contains", "developer")
                .add_sorting("created_at", descending=True)
                .add_pagination(0, 10)
                .execute(session)

# 디버깅 정보 확인
debug_info = builder.get_debug_info()
print(f"적용된 필터들: {debug_info['applied_filters']}")
print(f"사용 가능한 경로들: {debug_info['available_paths']}")

# 경로 유효성 검증
paths_to_check = ["name", "user.profile.bio", "invalid.path"]
validation = builder.validate_paths(paths_to_check)
print(f"유효한 경로: {len(validation['valid_paths'])}개")
print(f"무효한 경로: {len(validation['invalid_paths'])}개")
print(f"경고: {len(validation['warnings'])}개")
"""
