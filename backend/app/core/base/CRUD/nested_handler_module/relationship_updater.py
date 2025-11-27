"""
관계 업데이터

OneToMany, OneToOne 관계의 업데이트를 처리하며, 
변화 감지, soft delete, 중복 해결 등을 지원합니다.
"""

from typing import List, Dict, Any, Set, Optional, Type, Callable, cast
from sqlmodel import SQLModel, Session
from core.base.CRUD.crud_types import RequestModel, ModelType
from core.base.comparator import ModelComparator, ModelComparisonError
from .metadata_manager import MetadataManager
from .model_inspector import ModelInspector
from .data_processor import DataProcessor
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
class RelationshipUpdater:
    """관계 업데이트 처리 클래스"""
    
    def __init__(
        self, 
        session: Session, 
        metadata_manager: MetadataManager,
        model_inspector: ModelInspector,
        data_processor: DataProcessor
    ):
        """
        Args:
            session: 데이터베이스 세션
            metadata_manager: 메타데이터 관리자
            model_inspector: 모델 검사기
            data_processor: 데이터 처리기
        """
        self.session = session
        self.metadata_manager = metadata_manager
        self.model_inspector = model_inspector
        self.data_processor = data_processor

    def update_one_to_many_relationship(
        self,
        instance: ModelType,
        relationship_key: str,
        new_data: List[Dict[str, Any]],
        model: Type[SQLModel],
        request_schema: RequestModel,
        is_soft_delete: bool = False,
        soft_delete_column: Optional[str] = None,
        key_fields: Set[str] = set(),
        exclude_fields: Set[str] = set(),
        create_nested_callback: Optional[Callable[[Type[SQLModel], Dict[str, Any]], SQLModel]] = None,
    ) -> None:
        """
        OneToMany 관계 업데이트 (ModelComparator 기반)
        
        Args:
            instance: 업데이트할 모델 인스턴스
            relationship_key: 관계 키
            new_data: 새로운 데이터 리스트
            model: 모델 클래스
            request_schema: Request 스키마
            config: 관계별 설정
            
        Note:
            이 메서드는 instance의 관계를 직접 수정하므로 반환값이 없습니다.
        """
        logger.debug(f"=== {relationship_key} 관계 업데이트 시작 ===")
        
        # 기존 관계 데이터 조회
        existing_items = getattr(instance, relationship_key, [])
        logger.debug(f"기존 {relationship_key}: {len(existing_items)}개")
        
        # 관련 모델 클래스 가져오기
        related_model = self.model_inspector.get_related_model(model, relationship_key)
        if not related_model:
            logger.warning(f"관련 모델을 찾을 수 없음: {relationship_key}")
            raise ValueError(f"{relationship_key}: 관련 모델을 찾을 수 없습니다.")
        
        if not isinstance(new_data, list):
            new_data = []
        
        # Base 스키마 추출 (request_schema에서)
        base_schema = self.model_inspector.get_base_schema(request_schema, relationship_key)
        logger.debug(f"Base 스키마: {base_schema}")
        logger.debug(f"request schema : {request_schema}")
        # 기존 아이템을 Base 형태로 변환
        existing_base_items = []
        final_items = []
        
        # soft delete가 활성화된 경우, 삭제되지 않은 항목들만 비교 대상으로 사용
        if is_soft_delete and soft_delete_column:
            # 삭제되지 않은 항목들 (비교 대상)
            active_items = list(filter(
                lambda x: hasattr(x, soft_delete_column) 
                and not getattr(x, soft_delete_column, False),
                existing_items,
            ))
            
            # 이미 삭제된 항목들 (final_items에 그대로 유지)
            already_deleted_items = list(filter(
                lambda x: hasattr(x, soft_delete_column) 
                and getattr(x, soft_delete_column, False),
                existing_items,
            ))
            
            logger.debug(f"활성 아이템: {len(active_items)}개, 이미 삭제된 아이템: {len(already_deleted_items)}개")
            
            # 이미 삭제된 항목들은 final_items에 먼저 추가 (변경하지 않음)
            final_items.extend(already_deleted_items)
            
            # 비교 대상은 활성 항목들만
            comparison_items = active_items
        else:
            # soft delete가 아닌 경우 모든 기존 항목들을 비교 대상으로 사용
            comparison_items = existing_items
        
        # 비교 대상 아이템들을 Base 형태로 변환
        for item in comparison_items:
            try:
                base_item = base_schema.model_validate(item.model_dump())
                existing_base_items.append(base_item)
            except Exception as e:
                logger.warning(f"기존 데이터 Base 스키마 변환 실패: {item}, 에러: {e}")
                continue

        # 새 데이터를 Base 형태로 변환
        new_base_items = []
        for item_dict in new_data:
            try:
                base_item = base_schema.model_validate(item_dict)
                new_base_items.append(base_item)
            except Exception as e:
                logger.warning(
                    f"새 데이터 Base 스키마 변환 실패: {item_dict}, 에러: {e}"
                )
                raise e
                continue
        
        # ModelComparator로 비교
        comparator = ModelComparator[request_schema](
            existing_base_items,
            new_base_items,
            key_fields=key_fields,
            exclude_fields=exclude_fields
        )
        
        logger.debug(f"비교 결과: 추가={len(comparator.added)}, 삭제={len(comparator.removed)}, "
                    f"수정={len(comparator.modified)}, 동일={len(comparator.unchanged)}")
        
        # 결과 처리

        # 1. 변경되지 않은 항목들 (기존 인스턴스 유지)
        for unchanged_base in comparator.unchanged:
            # Base 스키마와 매칭되는 기존 인스턴스 찾기 (비교 대상에서만 찾기)
            matching_instance = self._find_matching_instance(
                unchanged_base,
                comparison_items,
                key_fields,
            )
            if matching_instance:
                logger.debug(f"변경되지 않은 항목: {unchanged_base.model_dump()}")
                final_items.append(matching_instance)
        
        # 2. 수정된 항목들 (기존 인스턴스 업데이트)
        for modified_item in comparator.modified:
            old_base = modified_item["old_item"]
            new_base = modified_item["new_item"]

            # 기존 인스턴스 찾기 (비교 대상에서만 찾기)
            matching_instance = self._find_matching_instance(
                old_base,
                comparison_items,
                key_fields,
            )

            if matching_instance:
                logger.debug(f"수정된 항목: {old_base.model_dump()}")
                # 변경된 필드들 업데이트
                for field, change in modified_item["changed_fields"].items():
                    if (
                        hasattr(matching_instance, field)
                        and field not in exclude_fields
                    ):
                        setattr(matching_instance, field, change["new"])

                # 메타데이터 자동 업데이트 (Base 클래스의 공통 필드들)
                self.metadata_manager.update_instance_metadata(matching_instance)

                final_items.append(matching_instance)
                logger.debug(
                    f"✓ 업데이트: {old_base.model_dump()} → {new_base.model_dump()}"
                )

        # 3. 새로 추가된 항목들 (새 인스턴스 생성)
        for added_base in comparator.added:
            if create_nested_callback:
                # 새 인스턴스 데이터 준비
                new_item_data = added_base.model_dump()
                
                # 부모 관계 설정 (예: author_idx 설정)
                parent_foreign_key = self._get_parent_foreign_key(model, relationship_key, related_model)
                if parent_foreign_key and hasattr(instance, 'idx'):
                    new_item_data[parent_foreign_key] = cast(int,instance.idx)  # pyright: ignore[reportAttributeAccessIssue]
                    logger.debug(f"부모 관계 설정: {parent_foreign_key}={cast(int,instance.idx)}")  # pyright: ignore[reportAttributeAccessIssue]
                
                new_instance = create_nested_callback(
                    related_model,
                    new_item_data,
                )
                final_items.append(new_instance)
                logger.debug(f"✓ 신규 추가: {added_base.model_dump()}")
            else:
                logger.warning("create_nested_callback이 없어서 새 항목을 생성할 수 없습니다.")

        # 4. 삭제된 항목들 처리
        for removed_base in comparator.removed:
            logger.debug(f"✓ 삭제 처리: {removed_base.model_dump()}")
            matching_instance = self._find_matching_instance(
                removed_base,
                comparison_items,  # 비교 대상에서만 찾기
                key_fields,
            )
            if matching_instance:
                logger.debug(f"삭제할 항목 찾음: {matching_instance}")
                if is_soft_delete and soft_delete_column:
                    self.metadata_manager.add_soft_delete_metadata(matching_instance, soft_delete_column)
                    final_items.append(matching_instance)
                else:
                    self.session.delete(matching_instance)
                logger.debug(f"✓ 삭제 완료: {removed_base.model_dump()}")
            else:
                logger.warning(
                    f"삭제할 항목을 찾을 수 없음: {removed_base.model_dump()}"
                )
        
        # 최종 관계 설정
        setattr(instance, relationship_key, final_items)
        
        logger.debug(f"=== {relationship_key} 업데이트 완료: 총 {len(final_items)}개 ===")




    def _find_matching_instance(
        self,
        base_item: SQLModel,
        existing_instances: List[SQLModel],
        key_fields: Set[str],
    ) -> Optional[SQLModel]:
        """
        Base 스키마 아이템과 매칭되는 기존 인스턴스 찾기
        """
        base_key_values = {}
        if key_fields.__len__() == 0:
          key_fields = set(base_item.model_dump().keys())
        for field in key_fields:
            if hasattr(base_item, field):
                base_key_values[field] = getattr(base_item, field)

        for instance in existing_instances:

            instance_key_values = {}
            for field in key_fields:
                if hasattr(instance, field):
                    instance_key_values[field] = getattr(instance, field)

            if base_key_values == instance_key_values:
                return instance

        return None

    def _get_parent_foreign_key(
        self, 
        parent_model: Type[SQLModel], 
        relationship_key: str, 
        child_model: Type[SQLModel]
    ) -> Optional[str]:
        """
        자식 모델에서 부모 모델을 참조하는 외래키 필드명을 찾습니다.
        
        Args:
            parent_model: 부모 모델 클래스 (예: Author)
            relationship_key: 관계 키 (예: "articles")
            child_model: 자식 모델 클래스 (예: Article)
            
        Returns:
            외래키 필드명 (예: "author_idx") 또는 None
        """
        try:
            # 자식 모델의 모든 컬럼을 검사
            child_mapper = self.model_inspector.get_mapper(child_model)
            parent_table_name = self.model_inspector.get_table_name(parent_model)
            
            for column in child_mapper.columns:
                # 외래키인지 확인
                if column.foreign_keys:
                    for fk in column.foreign_keys:
                        # 부모 테이블을 참조하는 외래키인지 확인
                        if fk.column.table.name == parent_table_name:
                            logger.debug(f"외래키 발견: {column.name} -> {fk.column}")
                            return column.name
            
            logger.debug(f"외래키를 찾을 수 없음: {child_model.__name__} -> {parent_model.__name__}")
            return None
            
        except Exception as e:
            logger.error(f"외래키 검색 중 오류: {e}")
            return None
