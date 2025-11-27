"""
중첩된 관계(Nested Relationship) 처리 핸들러

SQLModel의 중첩된 관계를 재귀적으로 처리하여
POST/PUT 작업 시 하위 모델들까지 자동으로 생성/업데이트합니다.
"""

from datetime import datetime
from typing import (
    Type,
    Dict,
    Any,
    List,
    Optional,
    Set,
    Union,
    Generic,
    cast,
    TypeVar,
    Protocol,
    runtime_checkable,
    TYPE_CHECKING,
)
import logging
from pydantic import BaseModel
from sqlmodel import SQLModel, Session, select
from sqlalchemy import inspect
from sqlalchemy.orm import RelationshipProperty
from core.base.CRUD.crud_types import ModelType, RequestModel, ResponseModel
from core.base.comparator import ModelComparator, ModelComparisonError

if TYPE_CHECKING:
    from core.base import UserOut
# 모듈별 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)

# 타입 정의
ProcessedData = Dict[str, Any]
NestedValue = Union[Dict[str, Any], List[Dict[str, Any]], Any]
InputData = Union[Dict[str, Any], SQLModel]


@runtime_checkable
class HasModelDump(Protocol):
    """model_dump 메서드를 가진 객체를 위한 프로토콜"""

    def model_dump(self) -> Dict[str, Any]: ...


def is_dict_like(value: Any) -> bool:
    """딕셔너리 형태의 데이터인지 확인"""
    return isinstance(value, (dict, SQLModel)) or hasattr(value, "model_dump")


def is_list_of_dicts(value: Any) -> bool:
    """딕셔너리들의 리스트인지 확인"""
    return isinstance(value, list) and all(is_dict_like(item) for item in value)


def to_dict(data: InputData) -> Dict[str, Any]:
    """데이터를 딕셔너리로 변환"""
    if isinstance(data, dict):
        return data
    elif isinstance(data, (SQLModel, BaseModel)):
        return data.model_dump()
    elif hasattr(data, "model_dump"):
        return data.model_dump()
    else:
        raise ValueError(f"지원하지 않는 데이터 타입: {type(data)}")


class NestedRelationshipHandler(Generic[ModelType, RequestModel, ResponseModel]):
    """중첩된 관계를 처리하는 핸들러 클래스"""

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
            relationship_key_fields: 관계별 키 필드 설정 {relationship_name: {field1, field2}}
            relationship_exclude_fields: 관계별 제외 필드 설정 {relationship_name: {field1, field2}}
            default_key_fields: 기본 키 필드 (관계별 설정이 없을 때 사용)
            default_exclude_fields: 기본 제외 필드 (관계별 설정이 없을 때 사용)
        """
        self.session = session
        self.relationship_key_fields = relationship_key_fields
        self.relationship_exclude_fields = relationship_exclude_fields
        self.relationship_deleted_columns = relationship_deleted_columns
        self.user = user

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
        relationships = self._get_relationships(model)
        columns = self._get_columns(model)

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
                related_model = self._get_related_model(model, key)

                if not related_model:
                    logger.warning(f"관련 모델을 찾을 수 없음: {key}")
                    continue

                # 부모 참조는 건너뛰기
                if parent_model and related_model == parent_model:
                    logger.debug(f"부모 참조 건너뛰기: {key}")
                    continue
                # 관계 방향에 따른 처리
                direction = relationship.direction.name
                if direction == "ONETOMANY":
                    # 리스트 처리 - dict를 그대로 반환
                    processed_data[key] = self._process_one_to_many_value(
                        value, related_model, model, visited_models, depth, max_depth
                    )
                elif direction == "ONETOONE":
                    # 단일 객체 처리
                    processed_data[key] = self._process_one_to_one_value(
                        value, related_model, model, visited_models, depth, max_depth
                    )

        return processed_data

    def _process_one_to_many_value(
        self,
        value: Any,
        related_model: Type[SQLModel],
        parent_model: Type[SQLModel],
        visited_models: Set[str],
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
                # 원시 값은 그대로 추가 (하지만 이는 일반적이지 않음)
                logger.warning(f"OneToMany 관계에 dict가 아닌 항목: {type(item)}")
                raise ValueError(f"OneToMany 관계에 dict가 아닌 항목: {type(item)}")
                processed_list.append({"value": item})

        return processed_list

    def _process_one_to_one_value(
        self,
        value: Any,
        related_model: Type[SQLModel],
        parent_model: Type[SQLModel],
        visited_models: Set[str],
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
            # 원시 값인 경우 (예: ID만 있는 경우)
            logger.debug(f"OneToOne 관계에 원시 값: {value}")
            raise ValueError(f"OneToOne 관계에 원시 값: {type(value)}")
            return {"id": value} if isinstance(value, (int, str)) else {"value": value}

    def _add_creation_metadata(
        self,
        data: ProcessedData,
    ) -> None:
        """생성 시 메타데이터 자동 추가"""
        from datetime import datetime

        # created_at은 Base 클래스에서 default_factory로 자동 설정되므로
        # 명시적으로 설정하지 않음 (이미 설정된 경우만 유지)
        if "created_at" not in data:
            data["created_at"] = datetime.now()

        # created_by 설정
        data["created_by"] = self.user.idx

        # updated_at과 updated_by는 생성 시에는 None으로 유지
        # (업데이트 시에만 설정)

    def _add_update_metadata(self, data: ProcessedData) -> None:
        """업데이트 시 메타데이터 자동 추가"""
        from datetime import datetime

        # updated_at 항상 현재 시간으로 설정
        data["updated_at"] = datetime.now()

        # updated_by 설정 (user_idx가 있는 경우만)
        data["updated_by"] = self.user.idx

    def _update_instance_metadata(self, instance: SQLModel) -> None:
        """인스턴스의 메타데이터 직접 업데이트"""
        from datetime import datetime

        # updated_at 항상 현재 시간으로 설정
        if hasattr(instance, "updated_at"):
            setattr(instance, "updated_at", datetime.now())

        # updated_by 설정 (user_idx가 있는 경우만)
        if hasattr(instance, "updated_by"):
            setattr(instance, "updated_by", self.user.idx)

    def create_with_nested(
        self,
        model: Type[SQLModel],
        data: Dict[str, Any],
    ) -> ModelType:
        """
        중첩된 관계를 포함한 모델 생성

        Args:
            model: 생성할 모델 클래스
            data: 생성할 데이터
            user_idx: 생성자 사용자 ID

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
            user_idx: 수정자 사용자 ID
            soft_delete_children: 자식 관계 삭제 시 soft delete 사용 여부
            soft_delete_column: soft delete에 사용할 컬럼명
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

            if relationship.direction.name == "ONETOMANY":
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
                self._update_one_to_many_relationship(
                    instance=instance,
                    relationship_key=key,
                    new_data=value,
                    model=model,
                    request_schema=request_schema,
                    is_soft_delete=is_soft_delete,
                    soft_delete_column=soft_delete_column,
                    key_fields=relationship_key_fields,
                    exclude_fields=relationship_exclude_fields,
                )

        # instance는 이미 세션에서 추적되고 있으므로 add 불필요
        # self.session.add(instance) - 제거
        logger.debug(f"업데이트 완료: {instance}")
        return instance

    def _update_one_to_many_relationship(
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
    ) -> None:
        """
        OneToMany 관계 업데이트 (ModelComparator 기반)

        Note:
            이 메서드는 instance의 관계를 직접 수정하므로 반환값이 없습니다.
        """
        logger.debug(f"=== {relationship_key} 관계 업데이트 시작 ===")

        # 기존 관계 데이터 조회
        existing_items = getattr(instance, relationship_key, [])
        logger.debug(f"기존 {relationship_key}: {len(existing_items)}개")

        # 관련 모델 클래스 가져오기
        related_model = self._get_related_model(model, relationship_key)
        if not related_model:
            logger.warning(f"관련 모델을 찾을 수 없음: {relationship_key}")
            raise ValueError(f"{relationship_key}: 관련 모델을 찾을 수 없습니다.")

        # Base 스키마 추출 (request_schema에서)
        base_schema = self._get_base_schema(request_schema, relationship_key)

        logger.debug(f"Base 스키마: {base_schema}")


        try:

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
                    continue
            logger.debug(f"existing_base_items: {existing_base_items}")
            logger.debug(f"new_base_items: {new_base_items}")
            comparator = ModelComparator[request_schema](
                existing_base_items,
                new_base_items,
                key_fields=key_fields,
                exclude_fields=exclude_fields,
            )

            logger.debug(
                f"비교 결과: 추가={len(comparator.added)}, 삭제={len(comparator.removed)}, "
                f"수정={len(comparator.modified)}, 동일={len(comparator.unchanged)}"
            )

            # 결과 처리

            # 1. 변경되지 않은 항목들 (기존 인스턴스 유지)
            for unchanged_base in comparator.unchanged:
                # Base 스키마와 매칭되는 기존 인스턴스 찾기 (비교 대상에서만 찾기)
                matching_instance = self._find_matching_instance(
                    unchanged_base,
                    comparison_items,
                    key_fields,
                    is_soft_delete,
                    soft_delete_column,
                )
                if matching_instance:
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
                    is_soft_delete,
                    soft_delete_column,
                )

                if matching_instance:
                    # 변경된 필드들 업데이트
                    for field, change in modified_item["changed_fields"].items():
                        if (
                            hasattr(matching_instance, field)
                            and field not in exclude_fields
                        ):
                            setattr(matching_instance, field, change["new"])

                    # 메타데이터 자동 업데이트 (Base 클래스의 공통 필드들)
                    self._update_instance_metadata(matching_instance)

                    final_items.append(matching_instance)
                    logger.debug(
                        f"✓ 업데이트: {old_base.model_dump()} → {new_base.model_dump()}"
                    )

            # 3. 새로 추가된 항목들 (새 인스턴스 생성)
            for added_base in comparator.added:
                new_instance = self.create_with_nested(
                    related_model,
                    added_base.model_dump(),
                )
                final_items.append(new_instance)
                logger.debug(f"✓ 신규 추가: {added_base.model_dump()}")

            # 4. 삭제된 항목들 처리
            for removed_base in comparator.removed:
                logger.debug(f"✓ 삭제 처리: {removed_base.model_dump()}")
                matching_instance = self._find_matching_instance(
                    removed_base,
                    comparison_items,  # 비교 대상에서만 찾기
                    key_fields,
                    is_soft_delete,
                    soft_delete_column,
                )
                if matching_instance:
                    logger.debug(f"matching_instance: {matching_instance}")
                    logger.debug(f"is_soft_delete: {is_soft_delete}")
                    logger.debug(f"soft_delete_column: {soft_delete_column}")
                    if is_soft_delete and soft_delete_column:
                        logger.debug(f"soft delete 적용: {matching_instance}")
                        setattr(matching_instance, soft_delete_column, True)
                        # 메타데이터 자동 업데이트
                        self._update_instance_metadata(matching_instance)
                        final_items.append(matching_instance)
                    else:
                        logger.debug(f"hard delete 적용: {matching_instance}")
                        self.session.delete(matching_instance)
                    logger.debug(f"✓ 삭제 완료: {removed_base.model_dump()}")
                else:
                    logger.warning(
                        f"삭제할 항목을 찾을 수 없음: {removed_base.model_dump()}"
                    )

            # 최종 관계 설정
            setattr(instance, relationship_key, final_items)

            logger.debug(
                f"=== {relationship_key} 업데이트 완료: 총 {len(final_items)}개 ==="
            )

        except ModelComparisonError as e:
            logger.error(f"ModelComparator 에러: {e}")
            raise e

    def _find_matching_instance(
        self,
        base_item: SQLModel,
        existing_instances: List[SQLModel],
        key_fields: Set[str],
        soft_delete: bool,
        soft_delete_column: Optional[str] = None,
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

    def _handle_item_deletion(
        self,
        item: SQLModel,
        soft_delete: bool,
        soft_delete_column: str,
    ):
        """항목 삭제 처리 (soft delete 또는 hard delete)"""
        if soft_delete and hasattr(item, soft_delete_column):
            # Soft delete
            setattr(item, soft_delete_column, True)
            # 메타데이터 자동 업데이트 (Base 클래스의 공통 필드들)
            self._update_instance_metadata(item)
            logger.debug(f"Soft delete: {item}")
        else:
            # Hard delete
            self.session.delete(item)
            logger.debug(f"Hard delete: {item}")

    def _get_relationships(
        self, model: Type[SQLModel]
    ) -> Dict[str, RelationshipProperty]:
        """모델의 관계 속성 추출"""
        mapper = inspect(model)
        return {rel.key: rel for rel in mapper.relationships}

    def _get_columns(self, model: Type[SQLModel]) -> Set[str]:
        """모델의 컬럼 이름 추출"""
        mapper = inspect(model)
        return {col.key for col in mapper.columns}

    def _get_related_model(
        self, model: Type[SQLModel], relationship_key: str
    ) -> Optional[Type[SQLModel]]:
        """관계에서 연결된 모델 클래스 추출"""
        try:
            mapper = inspect(model)
            relationship = mapper.relationships.get(relationship_key)
            if relationship:
                return relationship.mapper.class_
        except Exception as e:
            logger.error(f"관련 모델 추출 실패: {e}")
        return None

    def _get_base_schema(
        self, request_schema: RequestModel, relationship_key: str
    ) -> Type[SQLModel]:
        """
        Request 스키마에서 relationship의 Base 스키마 추출
        예: AuthorRequest.articles → List[ArticleBase] → ArticleBase
        """
        from typing import get_args, get_origin

        logger.debug(
            f"Base 스키마 추출 시도: request_schema={request_schema}, key={relationship_key}"
        )

        # request_schema의 model_fields에서 relationship_key의 타입 가져오기
        field_info = request_schema.model_fields.get(relationship_key)
        if not field_info or not hasattr(field_info, "annotation"):
            raise ValueError(f"{relationship_key}: field_info 또는 annotation 없음")
        field_type = field_info.annotation
        # List[ArticleBase], Optional[List[ArticleBase]] 등 처리
        origin = get_origin(field_type)
        # Optional[List[...]]인 경우 내부 추출
        if origin is Union:
            args = get_args(field_type)
            for arg in args:
                if arg is not type(None) and get_origin(arg) is list:
                    field_type = arg
                    origin = list
                    break

        if origin is list:
            args = get_args(field_type)
            logger.debug(f"list args: {args}")
            if args and len(args) > 0:
                base_schema = args[0]
                logger.debug(f"✓ Base 스키마 추출 성공: {base_schema}")
                return base_schema

        logger.debug(f"Base 스키마 추출 실패: origin={origin}")
        raise ValueError(f"{relationship_key}: Base 스키마 추출 실패")

    def delete_with_nested(
        self,
        instance: ModelType,
        deleted_column: str = "deleted",
        is_soft_delete: bool = True,
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
        logger.debug(f"Delete with nested: {instance.__class__.__name__}, soft={is_soft_delete}")
        
        # Soft delete 처리
        if is_soft_delete:
            # 메인 인스턴스 soft delete
            if not hasattr(instance, deleted_column):
                logger.warning(
                    f"{instance.__class__.__name__}에 {deleted_column} 컬럼이 없습니다. "
                    "Hard delete로 전환됩니다."
                )
                self.session.delete(instance)
                return instance
            
            setattr(instance, deleted_column, True)
            logger.debug(f"Soft deleted: {instance.__class__.__name__}")
            
            # 중첩 관계들 순회
            mapper = inspect(instance.__class__)
            for rel_name, rel_prop in mapper.relationships.items():
                if not hasattr(instance, rel_name):
                    continue
                
                related_items = getattr(instance, rel_name)
                if related_items is None:
                    continue
                
                # 관계별 deleted 컬럼명 가져오기
                rel_deleted_column = self.relationship_deleted_columns.get(
                    rel_name, 
                    deleted_column  # 기본값
                )
                
                # 컬렉션인 경우 (One-to-Many, Many-to-Many)
                if isinstance(related_items, (list, tuple)):
                    for related_item in related_items:
                        if hasattr(related_item, rel_deleted_column):
                            setattr(related_item, rel_deleted_column, True)
                            logger.debug(
                                f"Soft deleted nested: {rel_name}."
                                f"{related_item.__class__.__name__}"
                            )
                        else:
                            logger.warning(
                                f"{related_item.__class__.__name__}에 "
                                f"{rel_deleted_column} 컬럼이 없습니다."
                            )
                # 단일 객체인 경우 (Many-to-One)
                elif hasattr(related_items, rel_deleted_column):
                    setattr(related_items, rel_deleted_column, True)
                    logger.debug(
                        f"Soft deleted nested: {rel_name}."
                        f"{related_items.__class__.__name__}"
                    )
        
        # Hard delete 처리
        else:
            # 중첩 관계의 hard delete는 cascade 설정에 따라 자동 처리됨
            # 필요하면 명시적으로 처리 가능
            logger.debug(f"Hard delete: {instance.__class__.__name__}")
            self.session.delete(instance)
        
        return instance