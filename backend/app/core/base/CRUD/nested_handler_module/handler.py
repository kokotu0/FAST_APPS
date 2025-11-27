"""
중첩된 관계 처리 메인 핸들러

기존 nested_handler.py의 기능을 모듈화한 메인 클래스입니다.
각 컴포넌트를 조합하여 중첩된 관계를 처리합니다.
"""

from typing import Type, Dict, Any, List, Optional, Set, Generic, TYPE_CHECKING
from fastapi import HTTPException
from sqlmodel import SQLModel, Session
from core.base.CRUD.crud_types import ModelType, RequestModel, ResponseModel

from .types import ProcessedData, InputData
from .metadata_manager import MetadataManager
from .data_processor import DataProcessor
from .relationship_updater import RelationshipUpdater
from .model_inspector import ModelInspector

if TYPE_CHECKING:
    from core.base import UserOut

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class NestedRelationshipHandler(Generic[ModelType, RequestModel, ResponseModel]):
    """중첩된 관계를 처리하는 메인 핸들러 클래스 (모듈화 버전)"""

    def __init__(
        self,
        session: Session,
        user: "UserOut",
        relationship_key_fields: Dict[str, Set[str]] = {},
        relationship_exclude_fields: Dict[str, Set[str]] = {},
        relationship_deleted_columns: Dict[str, str] = {},
    ):
        """
        Args:
            session: 데이터베이스 세션
            user: 현재 사용자 정보
            relationship_key_fields: 관계별 키 필드 설정 {relationship_name: {field1, field2}}
            relationship_exclude_fields: 관계별 제외 필드 설정 {relationship_name: {field1, field2}}
            relationship_deleted_columns: 관계별 soft delete 컬럼 설정 {relationship_name: column_name}
        """
        self.session = session
        self.user = user
        self.relationship_key_fields = relationship_key_fields
        self.relationship_exclude_fields = relationship_exclude_fields
        self.relationship_deleted_columns = relationship_deleted_columns

        # 컴포넌트 초기화
        self.metadata_manager = MetadataManager(user)
        self.model_inspector = ModelInspector()
        self.data_processor = DataProcessor(self.model_inspector)
        self.relationship_updater = RelationshipUpdater(
            session=session,
            metadata_manager=self.metadata_manager,
            model_inspector=self.model_inspector,
            data_processor=self.data_processor,
        )

    def process_nested_data(
        self,
        data: InputData,
        model: Type[SQLModel],
        parent_model: Optional[Type[SQLModel]] = None,
        visited_models: Optional[Set[str]] = None,
        depth: int = 0,
        max_depth: int = 10,
    ) -> ProcessedData:
        """
        중첩된 데이터를 재귀적으로 처리하여 타입 안전한 딕셔너리로 변환
        """
        return self.data_processor.process_nested_data(
            data=data,
            model=model,
            parent_model=parent_model,
            visited_models=visited_models,
            depth=depth,
            max_depth=max_depth,
        )

    def _add_creation_metadata(self, data: ProcessedData) -> None:
        """생성 시 메타데이터 자동 추가"""
        self.metadata_manager.add_creation_metadata(data)

    def _add_update_metadata(self, data: ProcessedData) -> None:
        """업데이트 시 메타데이터 자동 추가"""
        self.metadata_manager.add_update_metadata(data)

    def _update_instance_metadata(self, instance: SQLModel) -> None:
        """인스턴스의 메타데이터 직접 업데이트"""
        self.metadata_manager.update_instance_metadata(instance)

    def _get_relationships(self, model: Type[SQLModel]):
        """모델의 관계 속성 추출"""
        return self.model_inspector.get_relationships(model)

    def _get_columns(self, model: Type[SQLModel]):
        """모델의 컬럼 이름 추출"""
        return self.model_inspector.get_columns(model)

    def _get_related_model(self, model: Type[SQLModel], relationship_key: str):
        """관계에서 연결된 모델 클래스 추출"""
        return self.model_inspector.get_related_model(model, relationship_key)

    def _get_base_schema(self, request_schema: RequestModel, relationship_key: str):
        """Request 스키마에서 relationship의 Base 스키마 추출"""
        return self.model_inspector.get_base_schema(request_schema, relationship_key)

    def _find_matching_instance(
        self,
        base_item: SQLModel,
        existing_instances: List[SQLModel],
        key_fields: Set[str],
        soft_delete: bool,
        soft_delete_column: Optional[str] = None,
    ):
        """Base 스키마 아이템과 매칭되는 기존 인스턴스 찾기"""
        return self.relationship_updater._find_matching_instance(
            base_item, existing_instances, key_fields
        )

    def create_with_nested(
        self,
        model: Type[SQLModel],
        data: Dict[str, Any],
    ) -> SQLModel:
        """
        중첩된 관계를 포함한 모델 생성

        Args:
            model: 생성할 모델 클래스
            data: 생성할 데이터

        Returns:
            생성된 모델 인스턴스
        """
        # 중첩 데이터 처리
        processed_data = self.process_nested_data(data, model)

        # 메타데이터 자동 추가 (Base 클래스의 공통 필드들)
        self._add_creation_metadata(processed_data)

        # 관계 데이터 분리
        relationships = self._get_relationships(model)
        nested_data = {}
        clean_data = {}
        for key, value in processed_data.items():
            if key in relationships:
                nested_data[key] = value
            else:
                clean_data[key] = value

        # 메인 모델 생성
        instance = model(**clean_data)

        # 중첩 관계 생성
        for key, value in nested_data.items():
            if isinstance(value, list):
                # ONETOMANY 관계
                related_model = self._get_related_model(model, key)
                if related_model:
                    related_instances = []
                    for item_data in value:
                        if isinstance(item_data, dict):
                            # 재귀적으로 하위 모델 생성
                            related_instance = self.create_with_nested(
                                related_model, item_data
                            )
                            related_instances.append(related_instance)
                    setattr(instance, key, related_instances)

            elif isinstance(value, dict):
                # ONETOONE 관계
                related_model = self._get_related_model(model, key)
                if related_model:
                    related_instance = self.create_with_nested(related_model, value)
                    setattr(instance, key, related_instance)

        # 세션에 추가
        self.session.add(instance)
        return instance

    def update_with_nested(
        self,
        instance: ModelType,
        data: Dict[str, Any],
        request_schema: RequestModel,
    ) -> ModelType:
        """
        중첩된 관계를 포함한 모델 업데이트 (변화 감지 및 soft delete 지원)

        Args:
            instance: 업데이트할 모델 인스턴스
            data: 업데이트할 데이터
            request_schema: Request 스키마 (Base 스키마 추출용, 예: AuthorRequest)

        Returns:
            업데이트된 모델 인스턴스
        """
        model = instance.__class__

        # 중첩 데이터 처리
        processed_data = self.process_nested_data(data, model)

        # 메타데이터 자동 추가 (Base 클래스의 공통 필드들)
        self._add_update_metadata(processed_data)
        # 관계 데이터 분리
        relationships = self._get_relationships(model)
        nested_data = {}
        clean_data = {}

        for key, value in processed_data.items():
            if key in relationships:
                nested_data[key] = value
            else:
                clean_data[key] = value

        # 메인 모델 업데이트
        for key, value in clean_data.items():
            setattr(instance, key, value)

        # 중첩 관계 업데이트 (변화 감지 및 soft delete 지원)
        for key, value in nested_data.items():
            relationship = relationships[key]
            direction = relationship.direction.name

            # Many-to-One: 명시적으로 스킵 (FK 참조만 사용)
            if direction == "MANYTOONE":
                logger.debug(f"관계 '{key}' (Many-to-One) 스킵됨 - FK 참조만 사용")
                continue

            # One-to-Many 처리
            if direction == "ONETOMANY":
                # 관계별 설정 가져오기
                relationship_key_fields = self.relationship_key_fields.get(key, set())
                relationship_exclude_fields = self.relationship_exclude_fields.get(
                    key, set()
                )
                is_soft_delete = bool(self.relationship_deleted_columns.get(key, False))
                if is_soft_delete:
                    soft_delete_column = self.relationship_deleted_columns.get(key)
                else:
                    soft_delete_column = None
                self.relationship_updater.update_one_to_many_relationship(
                    instance=instance,
                    relationship_key=key,
                    new_data=value,
                    model=model,
                    request_schema=request_schema,
                    is_soft_delete=is_soft_delete,
                    soft_delete_column=soft_delete_column,
                    key_fields=relationship_key_fields,
                    exclude_fields=relationship_exclude_fields,
                    create_nested_callback=self.create_with_nested,
                )

            # One-to-One 처리 (향후 확장)
            elif direction == "ONETOONE":
                logger.debug(f"관계 '{key}' (One-to-One) 처리 미구현")
                # TODO: One-to-One 관계 처리 구현
                raise NotImplementedError("One-to-One 관계 처리 미구현")

        # instance는 이미 세션에서 추적되고 있으므로 add 불필요
        return instance

    def delete_with_nested(
        self,
        instance: ModelType,
        deleted_column: str,
        is_soft_delete: bool,
    ) -> ModelType:
        """
        중첩된 관계를 포함하여 삭제 처리

        Args:
            instance: 삭제할 메인 인스턴스
            deleted_column: soft delete에 사용할 컬럼명 (기본: "deleted")
            is_soft_delete: soft delete 여부 (True: deleted=True 설정, False: 실제 삭제)

        Returns:
            삭제 처리된 인스턴스
        """
        logger.debug(
            f"Delete with nested: {instance.__class__.__name__}, soft={is_soft_delete}"
        )

        # Soft delete 처리
        if is_soft_delete:
            # 메인 인스턴스 soft delete
            if not hasattr(instance, deleted_column):
                raise HTTPException(
                    status_code=400,
                    detail=f"{instance.__class__.__name__}에 {deleted_column} 컬럼이 없습니다.",
                )

            # 메인 인스턴스 soft delete 및 메타데이터 추가
            setattr(instance, deleted_column, True)
            self.metadata_manager.add_soft_delete_metadata(instance, deleted_column)
            logger.debug(f"Soft deleted: {instance.__class__.__name__}")

            # 중첩 관계들 순회
            relationships = self._get_relationships(instance.__class__)
            for rel_name, rel_prop in relationships.items():
                if not hasattr(instance, rel_name):
                    continue

                related_items = getattr(instance, rel_name)
                if related_items is None:
                    continue

                direction = rel_prop.direction.name

                # Many-to-One: 명시적으로 스킵 (FK 참조만 사용, 공유 리소스 보호)
                if direction == "MANYTOONE":
                    logger.debug(f"관계 '{rel_name}' (Many-to-One) 스킵됨 - FK 참조만 사용")
                    continue

                # One-to-Many 처리
                if direction == "ONETOMANY":
                    rel_deleted_column = self.relationship_deleted_columns.get(
                        rel_name, deleted_column
                    )
                    if isinstance(related_items, (list, tuple)):
                        for related_item in related_items:
                            if hasattr(related_item, rel_deleted_column):
                                setattr(related_item, rel_deleted_column, True)
                                self.metadata_manager.add_soft_delete_metadata(
                                    related_item, rel_deleted_column
                                )
                                logger.debug(
                                    f"Soft deleted nested: {rel_name}."
                                    f"{related_item.__class__.__name__}"
                                )
                            else:
                                logger.warning(
                                    f"{related_item.__class__.__name__}에 "
                                    f"{rel_deleted_column} 컬럼이 없습니다."
                                )
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"{related_item.__class__.__name__}에 {rel_deleted_column} 컬럼이 없습니다.",
                                )

                # One-to-One 처리 (향후 확장)
                elif direction == "ONETOONE":
                    logger.debug(f"관계 '{rel_name}' (One-to-One) 처리 미구현")
                    # TODO: One-to-One 관계 처리 구현
                    raise NotImplementedError("One-to-One 관계 처리 미구현")

        # Hard delete 처리
        else:
            # 중첩 관계의 hard delete는 cascade 설정에 따라 자동 처리됨
            logger.debug(f"Hard delete: {instance.__class__.__name__}")
            self.session.delete(instance)

        return instance

    def restore_with_nested(
        self,
        instance: ModelType,
        deleted_column: str,
        is_soft_delete: bool,
    ) -> ModelType:
        """
        중첩된 관계를 포함하여 복구 처리
        """
        logger.debug(
            f"Restore with nested: {instance.__class__.__name__}, soft={is_soft_delete}"
        )

        # Soft delete 복구
        if is_soft_delete:
            # 메인 인스턴스 soft delete 복구
            if not hasattr(instance, deleted_column):
                raise HTTPException(
                    status_code=400,
                    detail=f"{instance.__class__.__name__}에 {deleted_column} 컬럼이 없습니다.",
                )
            setattr(instance, deleted_column, False)
            self.metadata_manager.restore_soft_deleted_metadata(
                instance, deleted_column
            )

            relationships = self._get_relationships(instance.__class__)
            for rel_name, rel_prop in relationships.items():
                if not hasattr(instance, rel_name):
                    continue

                related_items = getattr(instance, rel_name)
                if related_items is None:
                    continue

                direction = rel_prop.direction.name

                # Many-to-One: 명시적으로 스킵 (FK 참조만 사용, 공유 리소스 보호)
                if direction == "MANYTOONE":
                    logger.debug(f"관계 '{rel_name}' (Many-to-One) 스킵됨 - FK 참조만 사용")
                    continue

                # One-to-Many 처리
                if direction == "ONETOMANY":
                    rel_deleted_column = self.relationship_deleted_columns.get(
                        rel_name, deleted_column
                    )
                    if isinstance(related_items, (list, tuple)):
                        for related_item in related_items:
                            if hasattr(related_item, rel_deleted_column):
                                setattr(related_item, rel_deleted_column, False)
                                self.metadata_manager.restore_soft_deleted_metadata(
                                    related_item, rel_deleted_column
                                )
                                logger.debug(
                                    f"Restore soft deleted nested: {rel_name}."
                                    f"{related_item.__class__.__name__}"
                                )
                            else:
                                logger.warning(
                                    f"{related_item.__class__.__name__}에 "
                                    f"{rel_deleted_column} 컬럼이 없습니다."
                                )
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"{related_item.__class__.__name__}에 {rel_deleted_column} 컬럼이 없습니다.",
                                )

                # One-to-One 처리 (향후 확장)
                elif direction == "ONETOONE":
                    logger.debug(f"관계 '{rel_name}' (One-to-One) 처리 미구현")
                    # TODO: One-to-One 관계 처리 구현
                    raise NotImplementedError("One-to-One 관계 처리 미구현")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Soft delete가 아닙니다.",
            )
        logger.debug(f"Restore with nested completed: {instance.__class__.__name__}")
        return instance
