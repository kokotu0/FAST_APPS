
from typing import Any, Dict, Generic, Type, List, Optional, Set, Tuple, TypeVar
from typing_extensions import deprecated
from fastapi import Query, Depends, HTTPException
from sqlmodel import SQLModel, select, or_, and_, col, inspect
from sqlalchemy.orm import joinedload, aliased
from pydantic import BaseModel
import json
from urllib.parse import unquote

ModelType = TypeVar("ModelType", bound=SQLModel)

# @deprecated("RelationFilter는 더 이상 사용되지 않습니다. RelationFilter_v2를 사용하세요.")
class RelationFilter:
    """관계 필터링이 가능한 고급 필터 시스템"""
    """
    RelationFilter를 사용하여 상품을 필터링합니다.
    고급필터고, 일부 한정적으로 사용될 것이라 생각하여, CRUD_Router에는 등록하지 않았습니다.
    
    필터 예시:
    {
        "product_name": {"like": "원피스"},
        "large_category.name": {"equals": "패션"},
        "medium_category.name": {"equals": "여성의류"},
        "small_category.name": {"equals": "원피스"},
        'item_composition': {'arrIncludesAll': ['원단1', '원단2']},
        "useYN": {"equals": true}
    }
    """

    @staticmethod
    def apply_filters(model_class: Type[ModelType], filter_data: Optional[dict], query=None):
        """
        필터 데이터로부터 필터 적용 (중첩된 관계에 대한 필터링 지원)
        
        Parameters:
        - model_class: SQLModel 클래스
        - filter_data: 필터링 데이터 딕셔너리
        
        Returns:
        - SQLModel select 쿼리 객체
        
        Raises:
        - ValueError: 잘못된 컬럼/관계 이름
        """
        if not filter_data:
            return select(model_class)
        
        # 기본 쿼리 생성
        if query is None:
            query = select(model_class)
        
        # 조건 목록
        conditions = []
        
        # 조인 필요한 테이블과 별칭 추적
        joins = {}  # {relation_path: (relation, alias)}
        
        # 잘못된 컬럼/관계 목록
        invalid_paths = []
        
        # 각 컬럼/관계 경로에 대한 필터 처리
        for path, operators in filter_data.items():
            # 점(.)으로 분리된 경로 처리 (예: user.team.name)
            if "." in path:
                # 경로 분할
                parts = path.split(".")
                attr_name = parts[-1]  # 실제 필터링할 속성명
                relation_path = parts[:-1]  # 관계 경로
                # 관계 경로가 유효한지 확인하고 필요한 조인 정보 및 대상 컬럼 가져오기
                try:
                    column, joins_needed = RelationFilter._get_relation_column(
                        model_class, relation_path, attr_name
                    )
                    for relation in joins_needed:
                        relation_str = str(relation)
                        if relation_str not in joins:
                            # 관계 대상 모델의 별칭 생성
                            target_model = relation.property.mapper.class_ # type: ignore
                            alias = aliased(target_model, name=f"{target_model.__name__}_{len(joins)}")
                            joins[relation_str] = (relation, alias)
                except ValueError as e:
                    invalid_paths.append(path)
                    continue
            else:
                # 직접 모델 속성
                if not hasattr(model_class, path):
                    invalid_paths.append(path)
                    continue
                column = getattr(model_class, path)
            # 각 연산자 처리
            for operator, value in operators.items():
                # 관계 컬럼인 경우 별칭된 테이블의 컬럼 사용
                if "." in path:
                    parts = path.split(".")
                    relation_str = str(getattr(model_class, parts[0]))
                    if relation_str in joins:
                        alias = joins[relation_str][1]
                        column = getattr(alias, parts[-1])

                condition = RelationFilter._create_condition(column, operator, value)
                if condition is not None:
                    conditions.append(condition)
        
        # 잘못된 경로가 있으면 예외 발생
        if invalid_paths:
            raise ValueError(f"유효하지 않은 필터 경로: {', '.join(invalid_paths)}")
        
        # 필요한 조인 적용 (별칭 사용)
        for relation, alias in joins.values():
            query = query.join(alias, relation)
        
        # 조건이 있으면 적용
        if conditions:
            # 기본적으로 AND 조건으로 결합
            query = query.where(and_(*conditions))
            
        # 디버깅을 위한 쿼리 출력
        return query
    
    @staticmethod
    def _get_relation_column(model_class:type[SQLModel], relation_path:list[str], attr_name:str) -> Tuple[Any, Set[str]]:
        """
        관계 경로를 통해 컬럼 가져오기
        
        Parameters:
        - model_class: 시작 모델 클래스
        - relation_path: 관계 경로 목록 (예: ['user', 'team'])
        - attr_name: 최종 속성 이름 (예: 'name')
        
        Returns:
        - 컬럼 객체, 필요한 조인 목록
        
        Raises:
        - ValueError: 관계 경로가 유효하지 않을 경우
        """
        from sqlalchemy.orm import Mapper
        model_mapper :Mapper[model_class] = inspect(model_class)
        current_model = model_class
        joins_needed = set()
        # 관계 경로 탐색
        for relation_name in relation_path:
            # 현재 모델에 해당 관계가 있는지 확인
            if not hasattr(current_model, relation_name):
                raise ValueError(f"{current_model.__name__}에 '{relation_name}' 관계가 없습니다")
            
            # 관계 가져오기
            relation = getattr(current_model, relation_name)
            joins_needed.add(relation)
            
            # 관계를 통해 다음 모델 가져오기
            relationship = model_mapper.relationships.get(relation_name)
            if not relationship:
                raise ValueError(f"{current_model.__name__}에 '{relation_name}' 관계가 없습니다")
            
            current_model = relationship.mapper.class_
            model_mapper = inspect(current_model)
        
        # 최종 모델에서 속성 가져오기
        if not hasattr(current_model, attr_name):
            raise ValueError(f"{current_model.__name__}에 '{attr_name}' 속성이 없습니다")
        
        column = getattr(current_model, attr_name)
        return column, joins_needed
    from sqlalchemy.sql import ColumnElement
    @staticmethod
    def _create_condition(column:ColumnElement, operator:str, value:Any | list[Any])->bool | None | ColumnElement[bool]:
        """연산자와 값을 기반으로 조건 생성"""
        
        # 연산자 유형 분류
        SCALAR_OPERATORS = {"equals", "notEquals", "lessThan", "lessThanOrEqualTo", 
                            "greaterThan", "greaterThanOrEqualTo", "contains", 
                            "notContains", "startsWith", "endsWith", "weakEquals"}
        
        LIST_OPERATORS = {"in", "notIn", "between", "arrIncludes", "arrIncludesSome", "arrIncludesAll"}
        
        # 연산자 유형에 따른 값 타입 확인 및 전처리
        if operator in SCALAR_OPERATORS:
                # 스칼라 값이 필요한 연산자
                if isinstance(value, list):
                    if not value:
                        raise ValueError(f"'{operator}' 연산자에 빈 리스트가 전달되었습니다.")
                    if len(value) > 1:
                        raise ValueError(f"'{operator}' 연산자는 단일 값만 허용하지만, 리스트가 전달되었습니다: {value}")
                    value = value[0]  # 리스트의 첫 번째 요소만 사용
            
        elif operator in LIST_OPERATORS:
            # 리스트 값이 필요한 연산자 (단일 값도 리스트로 변환)
            if not isinstance(value, list):
                value = [value]
            
            # between 연산자는 정확히 2개의 요소가 필요
            if operator == "between":
                if len(value) != 2:
                    raise ValueError(f"'between' 연산자에는 정확히 2개의 요소가 필요합니다. 현재: {len(value)}개")
        # 실제 조건 생성 로직
        if operator == "fuzzy":
            if type(value) == str:
                return column.ilike(f"%{value.upper()}%") 
            else:
                return None
        elif operator == "equals":
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
        elif operator == "in":
            return column.in_(value)
        elif operator == "notIn":
            return ~column.in_(value)
        elif operator == "contains":
            return column.like(f"%{value}%")
        elif operator == "notContains":
            return ~column.like(f"%{value}%")
        elif operator == "startsWith":
            return column.like(f"{value}%")
        elif operator == "endsWith":
            return column.like(f"%{value}")
        elif operator == "between":
            
            if (value[0] is None or value[0] == "") and (value[1] is None or value[1] == "")    :
                return True
            if value[0] is None or value[0] == "":
                return column <= value[1]
            if value[1] is None or value[1] == "":
                return column >= value[0]
            if value[0] is not None and value[1] is not None:
                return column.between(value[0], value[1])
        elif operator == "empty":
            return column.is_(None)
        elif operator == "notEmpty":
            return column.isnot(None)
        elif operator == "arrIncludes":
            if len(value)==0:
                return
            # 문자열 컬럼에 대해서는 일반 equals 또는 in 사용
            return column.in_(value)
        elif operator == "arrIncludesSome":
            from sqlalchemy import or_
            conditions = []
            conditions.append(column.in_(value))
            
            return or_(*conditions)
        elif operator == "arrIncludesAll":
            return column.in_(value)
        elif operator == "weakEquals":
            from sqlalchemy import cast, String
            return cast(column, String) == str(value)
        
        print(f"지원하지 않는 연산자: {operator} - custom함수로 넘어감")
        return None
