from typing import Dict, List, Literal, Type, TypeVar, Generic, Optional
from sqlmodel import SQLModel, select
from sqlalchemy import ColumnElement, and_, any_, inspect

from ..core.path_resolver import PathResolver
from .base import BaseFilter
from ..types import RelationOperator
from sqlmodel.sql._expression_select_cls import SelectOfScalar

from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@dataclass
class RelationFilterValue:
    """관계 필터 값 구조"""

    column: str  # 관련 테이블의 컬럼명
    operator: Literal[
        "equals",
        "notEquals",
        "contains",
        "notContains",
        "greaterThan",
        "lessThan",
        "greaterThanOrEqual",
        "lessThanOrEqual",
        "in",
        "notIn",
        "isNull",
    ]
    value: str | int | float | bool | list[str | int | float | bool]

    def __post_init__(self):
        """유효성 검증"""
        if not self.column:
            raise ValueError("관계 필터에서 column은 필수입니다.")


T = TypeVar("T", bound=SQLModel)


class RelationFilter(BaseFilter[RelationOperator], Generic[T]):
    """1:N 관계 필터링 구현 - hasAny만 우선 구현"""

    def __init__(
        self,
        model: type[T],
    ):

        self.model = model

    def supports_operator(self, operator: str) -> bool:
        """지원하는 연산자인지 확인"""
        # hasAny, hasAll, hasChild, hasNotChild 지원
        supported_ops = ["hasAny", "hasAll", "hasChild", "hasNotChild"]
        supported = operator in supported_ops
        return supported

    def apply(  # type: ignore
        self,
        column: ColumnElement,
        operator: RelationOperator,
        value: List[Dict],
        current_query: SelectOfScalar[T],
    ) -> SelectOfScalar[T]:
        """관계 필터 적용 - 기존 쿼리에 조건 추가"""
        logger.debug("RelationFilter 적용")
        related_model = self._get_related_model_from_relationship(
            model=self.model, relationship_attr_name=str(column).split(".")[-1]
        )

        if not related_model:
            raise ValueError(f"관계 속성 {related_model}을 찾을 수 없습니다.")

        # 관계 필터 적용
        if operator == "hasAny":
            logger.debug("hasAny 연산자 적용")
            condition = self._apply_has_any(related_model, column, value)
            return current_query.where(condition)
        elif operator == "hasAll":
            logger.debug("hasAll 연산자 적용")
            condition = self._apply_has_all(related_model, column, value)
            return current_query.where(condition)
        elif operator == "hasChild":
            logger.debug("hasChild 연산자 적용")
            condition = self._apply_has_child(column)
            return current_query.where(condition)
        elif operator == "hasNotChild":
            logger.debug("hasNotChild 연산자 적용")
            condition = self._apply_has_not_child(column)
            return current_query.where(condition)
        else:
            raise ValueError(f"지원하지 않는 연산자: {operator}")

    def _get_related_model_from_relationship(
        self, model: type[T], relationship_attr_name: str
    ) -> Type[T]:
        """관계 속성에서 연결된 모델 클래스를 추출"""
        from sqlalchemy import inspect

        mapper = inspect(model)
        relationship_prop = mapper.relationships.get(relationship_attr_name)

        if relationship_prop:
            return relationship_prop.mapper.class_
        else:
            raise ValueError(f"관계 속성 {relationship_attr_name}을 찾을 수 없습니다.")

    def _apply_join_conditions(
        self, related_model: type[T], values: List[RelationFilterValue]
    ) -> ColumnElement | bool:
        """JOIN 조건만 적용"""
        from sqlalchemy import inspect

        all_join_conditions = []

        for value in values:
            split_column = value.column.split(".")

            if len(split_column) > 1:  # 중첩된 관계가 있을 때만
                current_model = related_model

                # 관계 경로를 따라가며 JOIN 조건 수집
                for path_part in split_column[:-1]:
                    mapper = inspect(current_model)
                    if (
                        mapper
                        and hasattr(mapper, "relationships")
                        and path_part in mapper.relationships
                    ):
                        relationship = mapper.relationships[path_part]

                        # Foreign key 관계에 따른 JOIN 조건 생성
                        for local_col, remote_col in relationship.local_remote_pairs:
                            all_join_conditions.append(local_col == remote_col)

                        current_model = relationship.mapper.class_
                    else:
                        raise AttributeError(
                            f"Relationship '{path_part}' not found in {current_model}"
                        )

        # JOIN 조건이 없으면 True 반환
        return and_(*all_join_conditions) if all_join_conditions else True

    def _apply_operator_conditions(
        self,
        related_model: type[T],
        values: List[RelationFilterValue],
        invert_condition: bool = False,
    ) -> ColumnElement:
        """Operator 조건만 적용 - 자기 참조와 일반 관계 분리 처리"""
        from sqlalchemy import inspect

        operator_conditions = []

        for value in values:
            split_column = value.column.split(".")

            if len(split_column) == 1:
                # 단일 컬럼인 경우 - related_model의 컬럼 직접 사용
                inner_column = getattr(related_model, value.column)
                condition = self._create_operator_condition(
                    inner_column, value, invert_condition
                )
                operator_conditions.append(condition)
            else:
                # 중첩된 관계인 경우 - 자기 참조 vs 일반 관계 구분
                current_model = related_model
                current_attr = None

                # 관계 경로를 따라가기
                for i, path_part in enumerate(split_column[:-1]):
                    mapper = inspect(current_model)
                    if (
                        mapper
                        and hasattr(mapper, "relationships")
                        and path_part in mapper.relationships
                    ):
                        relationship = mapper.relationships[path_part]
                        current_model = relationship.mapper.class_

                        # 첫 번째 관계 속성 저장
                        if i == 0:
                            current_attr = getattr(related_model, path_part)
                    else:
                        raise AttributeError(
                            f"Relationship '{path_part}' not found in {current_model}"
                        )

                # 최종 컬럼
                final_column_name = split_column[-1]
                final_column = getattr(current_model, final_column_name)

                # 자기 참조 관계인지 확인 (related_model과 최종 모델이 같은 경우)
                if current_attr is not None and current_model == self.model:
                    # 자기 참조 관계 - has() 사용하여 별칭 생성
                    nested_condition = self._create_operator_condition(
                        final_column, value, invert_condition
                    )
                    condition = current_attr.has(nested_condition)
                else:
                    # 일반 관계 - 최종 컬럼으로 직접 조건 생성 (기존 방식)
                    condition = self._create_operator_condition(
                        final_column, value, invert_condition
                    )

                operator_conditions.append(condition)

        return and_(*operator_conditions)

    def _create_operator_condition(
        self,
        inner_column: ColumnElement,
        filterValue: RelationFilterValue,
        invert_condition: bool = False,
    ) -> ColumnElement:
        """연산자에 따른 필터 조건 생성"""

        # 기본 조건 생성
        if filterValue.operator == "equals":
            base_condition = inner_column == filterValue.value
        elif filterValue.operator == "notEquals":
            base_condition = inner_column != filterValue.value
        elif filterValue.operator == "contains":
            base_condition = inner_column.like(f"%{filterValue.value}%")
        elif filterValue.operator == "notContains":
            base_condition = ~inner_column.like(f"%{filterValue.value}%")
        elif filterValue.operator == "greaterThan":
            base_condition = inner_column > filterValue.value
        elif filterValue.operator == "lessThan":
            base_condition = inner_column < filterValue.value
        elif filterValue.operator == "greaterThanOrEqual":
            base_condition = inner_column >= filterValue.value
        elif filterValue.operator == "lessThanOrEqual":
            base_condition = inner_column <= filterValue.value
        elif filterValue.operator == "in":
            base_condition = inner_column.in_(
                filterValue.value
                if isinstance(filterValue.value, list)
                else [filterValue.value]
            )
        elif filterValue.operator == "notIn":
            base_condition = ~inner_column.in_(
                filterValue.value
                if isinstance(filterValue.value, list)
                else [filterValue.value]
            )
        elif filterValue.operator == "isNull":
            if filterValue.value is True:
                base_condition = inner_column.is_(None)
            else:
                base_condition = inner_column.isnot(None)
            
        else:
            raise ValueError(f"Unsupported operator: {filterValue.operator}")

        # hasAll에서는 조건을 반전시켜서 "조건을 만족하지 않는" 케이스를 찾음
        if invert_condition:
            return ~base_condition
        else:
            return base_condition

    def _is_self_reference_relation(
        self, related_model: type[T], values: List[RelationFilterValue]
    ) -> bool:
        """자기 참조 관계인지 확인"""
        from sqlalchemy import inspect

        for value in values:
            split_column = value.column.split(".")
            if len(split_column) > 1:
                # 중첩된 관계에서 최종 모델 확인
                current_model = related_model
                for path_part in split_column[:-1]:
                    mapper = inspect(current_model)
                    if (
                        mapper
                        and hasattr(mapper, "relationships")
                        and path_part in mapper.relationships
                    ):
                        relationship = mapper.relationships[path_part]
                        current_model = relationship.mapper.class_
                    else:
                        break

                # 최종 모델이 기본 모델과 같으면 자기 참조
                if current_model == self.model:
                    return True

        return False

    def _apply_has_any(
        self,
        related_model: type[T],
        column: ColumnElement,
        values: List[Dict],
    ) -> ColumnElement:
        """hasAny 연산자 적용 - 자기 참조 vs 일반 관계 구분 처리"""
        normalized_values = list(map(lambda x: RelationFilterValue(**x), values))

        # 자기 참조 관계인지 확인
        is_self_ref = self._is_self_reference_relation(related_model, normalized_values)

        if is_self_ref:
            # 자기 참조 관계: 각 조건을 개별 EXISTS로 처리 (AND 연산)
            conditions = []
            for value in normalized_values:
                single_condition = self._apply_operator_conditions(
                    related_model, [value]
                )
                conditions.append(column.any(single_condition))

            # 모든 조건을 AND로 결합
            return and_(*conditions) if len(conditions) > 1 else conditions[0]
        else:
            # 일반 관계: JOIN 조건과 operator 조건 결합 (기존 방식)
            join_condition = self._apply_join_conditions(
                related_model, normalized_values
            )
            operator_condition = self._apply_operator_conditions(
                related_model, normalized_values
            )

            if join_condition is True:
                full_condition = operator_condition
            else:
                if isinstance(join_condition, bool):
                    full_condition = operator_condition
                else:
                    full_condition = and_(join_condition, operator_condition)

            return column.any(full_condition)

    def _apply_has_all(
        self, related_model: type[T], column: ColumnElement, values: List[Dict]
    ) -> ColumnElement:
        """hasAll 연산자 적용 - 모든 조건을 개별적으로 만족해야 함"""
        normalized_values = list(map(lambda x: RelationFilterValue(**x), values))

        # 자기 참조 관계인지 확인
        is_self_ref = self._is_self_reference_relation(related_model, normalized_values)

        conditions = [column.any()]  # 자식이 존재해야 함

        if is_self_ref:
            # 자기 참조 관계: 각 조건마다 "그 조건을 만족하지 않는 자식이 없어야" 함
            for value in normalized_values:
                # 개별 조건을 반전시켜서 적용
                inverted_operator = self._get_inverted_operator(value.operator)
                inverted_value = RelationFilterValue(
                    column=value.column,
                    operator=inverted_operator,  # type: ignore
                    value=value.value,
                )
                single_condition = self._apply_operator_conditions(
                    related_model, [inverted_value]
                )
                # "이 조건을 만족하지 않는 자식이 없어야" 함
                conditions.append(~column.any(single_condition))
        else:
            # 일반 관계: 기존 방식 유지
            join_condition = self._apply_join_conditions(
                related_model, normalized_values
            )
            operator_condition = self._apply_operator_conditions(
                related_model, normalized_values, invert_condition=True
            )

            if join_condition is True:
                full_condition = operator_condition
            else:
                if isinstance(join_condition, bool):
                    full_condition = operator_condition
                else:
                    full_condition = and_(join_condition, operator_condition)

            conditions.append(~column.any(full_condition))

        return and_(*conditions)

    def _get_inverted_operator(self, operator: str) -> str:
        """연산자를 반전시킴"""
        invert_map = {
            "equals": "notEquals",
            "notEquals": "equals",
            "contains": "notContains",
            "notContains": "contains",
            "greaterThan": "lessThanOrEqual",
            "lessThan": "greaterThanOrEqual",
            "greaterThanOrEqual": "lessThan",
            "lessThanOrEqual": "greaterThan",
            "in": "notIn",
            "notIn": "in",
        }
        return invert_map.get(operator, operator)

    def _apply_has_child(self, column: ColumnElement) -> ColumnElement:
        """hasChild 연산자 적용 - 조건만 반환"""
        return column.any()

    def _apply_has_not_child(self, column: ColumnElement) -> ColumnElement:
        """hasNotChild 연산자 적용 - 자식이 없는 경우"""
        return ~column.any()
