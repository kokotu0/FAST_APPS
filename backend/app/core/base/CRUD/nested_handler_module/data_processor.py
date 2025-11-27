"""
중첩 데이터 처리기

중첩된 관계 데이터를 재귀적으로 처리하여 타입 안전한 딕셔너리로 변환합니다.
"""

from typing import Type, List, Optional, Any
from fastapi import HTTPException
from sqlmodel import SQLModel
from .types import InputData, ProcessedData
from .utils import to_dict, is_dict_like
from .model_inspector import ModelInspector
import logging
import textwrap

logger = logging.getLogger(__name__)


class DataProcessor:
    """중첩된 데이터 처리 클래스"""

    def __init__(self, model_inspector: ModelInspector):
        self.model_inspector = model_inspector

    def process_nested_data(
        self,
        data: InputData,
        model: Type[SQLModel],
        parent_model: Optional[Type[SQLModel]] = None,
        visited_models: Optional[set] = None,
        depth: int = 0,
        max_depth: int = 10,
    ) -> ProcessedData:
        """
        중첩된 데이터를 재귀적으로 처리하여 타입 안전한 딕셔너리로 변환

        Args:
            data: 처리할 데이터 (dict, SQLModel 인스턴스, 또는 model_dump 메서드를 가진 객체)
            model: 대상 모델 클래스 (관계 정보 추출용)
            parent_model: 부모 모델 (순환 참조 방지용)
            visited_models: 방문한 모델 추적 (순환 참조 방지용)
            depth: 현재 재귀 깊이
            max_depth: 최대 재귀 깊이 (무한 재귀 방지)

        Returns:
            ProcessedData: 처리된 데이터 딕셔너리
                - 일반 컬럼: 원본 값 유지
                - OneToMany 관계: List[ProcessedData] 형태로 변환
                - OneToOne 관계: Optional[ProcessedData] 형태로 변환

        Raises:
            ValueError: 지원하지 않는 데이터 타입인 경우

        Note:
            - 순환 참조 감지 시 현재 데이터를 그대로 반환
            - 최대 깊이 도달 시 처리 중단
            - 타입 가드 함수를 통한 런타임 안전성 확보
        """
        if visited_models is None:
            visited_models = set()

        # 깊이 제한 체크
        if depth >= max_depth:
            logger.warning(f"최대 깊이 {max_depth}에 도달")
            return data if isinstance(data, dict) else {}

        # 데이터를 dict로 변환 (타입 안전성 확보)
        try:
            data_dict = to_dict(data)
        except ValueError as e:
            logger.error(f"데이터 변환 실패: {e}")
            return {}

        # 모델 정보 추출
        model_name = f"{model.__module__}.{model.__name__}"

        # 순환 참조 체크
        if model_name in visited_models:
            logger.debug(f"순환 참조 감지: {model.__name__}")
            return data_dict

        visited_models.add(model_name)

        # 모델의 관계와 컬럼 분리
        relationships = self.model_inspector.get_relationships(model)
        columns = self.model_inspector.get_columns(model)

        # 처리된 데이터
        processed_data: ProcessedData = {}

        # 데이터 분류 및 처리
        for key, value in data_dict.items():
            if key in columns:
                # 일반 컬럼
                processed_data[key] = value

            elif key in relationships:
                # 관계 데이터
                relationship = relationships[key]
                related_model = self.model_inspector.get_related_model(model, key)

                if not related_model:
                    logger.warning(f"관련 모델을 찾을 수 없음: {key}")
                    continue

                # 부모 참조는 건너뛰기
                if parent_model and related_model == parent_model:
                    logger.debug(f"부모 참조 건너뛰기: {key}")
                    continue

                # 관계 방향 확인
                direction = relationship.direction.name
                
                # Many-to-One은 무시 (FK 참조만 사용)
                if direction == "MANYTOONE":
                    logger.debug(
                        f"관계 '{key}' (Many-to-One) 무시됨 - FK 참조만 사용"
                    )
                    continue
                
                # Many-to-Many는 미지원
                if direction == "MANYTOMANY":
                    logger.warning(
                        f"관계 '{key}' (Many-to-Many)는 현재 미지원 - 무시됨"
                    )
                    continue
                
                # One-to-Many, One-to-One 처리
                if direction == "ONETOMANY":
                    processed_data[key] = self._process_one_to_many_value(
                        value, related_model, model, visited_models, depth, max_depth
                    )
                elif direction == "ONETOONE":
                    processed_data[key] = self._process_one_to_one_value(
                        value, related_model, model, visited_models, depth, max_depth
                    )
                else:
                    logger.warning(f"처리되지 않은 관계 방향: {direction}")
                    processed_data[key] = value

        return processed_data
    def _process_one_to_many_value(
        self,
        value: Any,
        related_model: Type[SQLModel],
        parent_model: Type[SQLModel],
        visited_models: set,
        depth: int,
        max_depth: int,
    ) -> List[ProcessedData]:
        """OneToMany 관계의 값을 처리"""
        if not isinstance(value, list):
            logger.warning(f"OneToMany 관계에 리스트가 아닌 값: {type(value)}")
            return []

        processed_list: List[ProcessedData] = []

        for item in value:
            if is_dict_like(item):
                # 재귀 처리 (dict로 반환)
                processed_item = self.process_nested_data(
                    item,
                    related_model,
                    parent_model=parent_model,
                    visited_models=visited_models.copy(),
                    depth=depth + 1,
                    max_depth=max_depth,
                )
                processed_list.append(processed_item)
            else:
                # 원시 값은 에러 발생
                raise ValueError(f"OneToMany 관계에 원시값을 허용하지 않습니다: {type(item)}")

        return processed_list

    def _process_one_to_one_value(
        self,
        value: Any,
        related_model: Type[SQLModel],
        parent_model: Type[SQLModel],
        visited_models: set,
        depth: int,
        max_depth: int,
    ) -> Optional[ProcessedData]:
        """OneToOne 관계의 값을 처리"""
        if value is None:
            return None

        if is_dict_like(value):
            return self.process_nested_data(
                value,
                related_model,
                parent_model=parent_model,
                visited_models=visited_models.copy(),
                depth=depth + 1,
                max_depth=max_depth,
            )
        else:
            # 원시 값인 경우 에러 발생
            raise ValueError(f"OneToOne 관계에 원시 값: {type(value)}")

    def validate_processed_data(
        self, data: ProcessedData, model: Type[SQLModel]
    ) -> bool:
        """
        처리된 데이터의 유효성 검증

        Args:
            data: 검증할 데이터
            model: 대상 모델 클래스

        Returns:
            유효성 여부
        """
        try:
            # 필수 필드 체크 (기본 키 등)
            pk_fields = self.model_inspector.get_primary_key_fields(model)

            # 자동 생성되는 기본 키는 제외 (예: idx)
            required_pk_fields = {
                field
                for field in pk_fields
                if field not in ["idx"] or data.get(field) is not None
            }

            missing_fields = required_pk_fields - set(data.keys())
            if missing_fields:
                logger.warning(f"필수 필드 누락: {missing_fields}")
                return False

            return True
        except Exception as e:
            logger.error(f"데이터 유효성 검증 실패: {e}")
            return False
