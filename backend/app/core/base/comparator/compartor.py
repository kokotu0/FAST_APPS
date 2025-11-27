from typing import (
    List,
    Dict,
    Any,
    Literal,
    Set,
    Tuple,
    Union,
    Optional,
    TypedDict,
    Type,
    Protocol,
    TypeVar,
    Generic,
)
from pydantic import BaseModel
from sqlmodel import SQLModel
import inspect

from core.base.comparator.types import ComparisonResult, ModelComparisonError, DiffChange, ModifiedItem

# 제네릭 타입 변수들
T = TypeVar("T")
V = TypeVar("V")




class ModelComparator(Generic[T]):
    """모델 리스트 비교를 위한 제네릭 클래스"""

    def __init__(
        self,
        old_list: List[T],
        new_list: List[T],
        *,
        exclude_fields: Optional[Set[str]] = None,
        key_fields: Optional[Set[str]] = None,
    ):
        """
    Args:
        old_list: 이전 상태의 리스트
        new_list: 새로운 상태의 리스트
            key_fields: 비교 기준 필드명 리스트 (None이면 모든 필드 사용)
            exclude_fields: 비교에서 제외할 필드명 리스트
    팁 : 
        만약 keyfields가 없었는데 새로 생성될 경우에, duplicate 에러를 발생시킬 수 있습니다. 
        uuid 등 유일한 key를 생성하여 매핑하는 마이그레이션 과정을 거치거나
        key값의 duplicate 값들을 직접 db에서 중복된 key값을 업데이트하는 것이 좋습니다.
        
        이를테면 title을 새로이 키로 전달하고자 할 때,
        title값이 중복될 수 있습니다.
        이렇다면 중복되지 않게 마이그레이션을 바랍니다.
        
        마이그레이션의 경우 당장엔 현실적이지 않기때문에 구현하지 않고, 에러를 raise합니다.
        
        """
        self.exclude_fields = exclude_fields or set()
        self.key_fields = key_fields or set()
        self.old_list = old_list
        self.new_list = new_list
        
        # 3단계 타입 검증
        self._validate_all_types()
        self._check_key_duplicates(self.old_list, "old_list", self.key_fields)
        self._check_key_duplicates(self.new_list, "new_list", self.key_fields)
        # 초기화 시점에서 바로 비교 결과 계산
        self._result: ComparisonResult[T] = self._perform_comparison()

    def _validate_model_type(self, model: Any) -> Type:
        """모델 타입 검증 및 반환 - 정확한 클래스 타입 반환"""
        if isinstance(model, (SQLModel, BaseModel)):
            return type(model)
        else:
            raise ModelComparisonError(
                f"지원되지 않는 모델 타입입니다: {type(model)}. "
                "Pydantic BaseModel 또는 SQLModel만 지원됩니다."
            )

    def _validate_list_internal_consistency(self, model_list: List[Any], list_name: str) -> Optional[Type]:
        """리스트 내부의 모든 항목이 정확히 같은 타입인지 검증"""
        if not model_list:
            return None
        
        # 첫 번째 유효한 항목의 타입을 기준으로 설정
        reference_item = next((item for item in model_list if item is not None), None)
        if reference_item is None:
            return None
        
        reference_type = self._validate_model_type(reference_item)
        
        # 모든 항목이 정확히 같은 타입인지 확인 (type() 사용)
        for i, item in enumerate(model_list):
            if item is None:
                continue
            
            try:
                item_type = self._validate_model_type(item)
                if item_type != reference_type:
                    raise ModelComparisonError(
                        f"{list_name}[{i}]의 타입이 일치하지 않습니다: "
                        f"기준 타입={reference_type.__name__}, 현재 항목 타입={item_type.__name__}. "
                        f"모든 항목은 정확히 같은 클래스여야 합니다."
                    )
            except ModelComparisonError as e:
                raise ModelComparisonError(
                    f"{list_name}[{i}]에서 타입 검증 실패: {e}"
                )
        
        return reference_type
    
    def _validate_all_types(self) -> None:
        """3단계 타입 검증: 1) old_list 내부, 2) new_list 내부, 3) old-new 간 호환성"""
        
        # 1단계: old_list 내부 일관성 검증
        old_type = self._validate_list_internal_consistency(self.old_list, "old_list")
        
        # 2단계: new_list 내부 일관성 검증  
        new_type = self._validate_list_internal_consistency(self.new_list, "new_list")
        
        # 3단계: old_list와 new_list 간 호환성 검증 (정확한 타입 비교)
        if old_type and new_type and old_type != new_type:
            raise ModelComparisonError(
                f"old_list와 new_list의 모델 타입이 일치하지 않습니다: "
                f"old_list={old_type.__name__}, new_list={new_type.__name__}. "
                f"두 리스트는 정확히 같은 클래스의 모델을 포함해야 합니다."
            )
        
        # 둘 다 비어있는 경우는 허용
        if not old_type and not new_type:
            return
    
    def _check_key_duplicates(self, model_list: List[Any], list_name: str, key_fields: Set[str]) -> None:
        """리스트 내에서 키 중복 검사"""
        if not model_list:
            return
        
        # key_fields가 없으면 전체 필드를 사용
        if not key_fields:
            all_fields = set(self._get_all_fields(model_list))
            effective_key_fields = set(f for f in all_fields if f not in self.exclude_fields)
        else:
            effective_key_fields = key_fields
        
        if not effective_key_fields:
            return
        
        seen_keys = set()
        for i, item in enumerate(model_list):
            try:
                key = tuple(getattr(item, field) for field in effective_key_fields)
                if key in seen_keys:
                    raise ModelComparisonError(
                        f"{list_name}[{i}]에서 키 중복이 발견되었습니다: "
                        f"키 {dict(zip(effective_key_fields, key))}가 이미 존재합니다."
                    )
                seen_keys.add(key)
            except AttributeError as e:
                raise ModelComparisonError(f"{list_name}[{i}]에서 키 필드를 찾을 수 없습니다: {e}")

    def _extract_attributes(self, model: Any) -> Dict[str, Any]:
        """모델에서 속성 추출"""
        self._validate_model_type(model)  # 타입 검증만 수행
        # Pydantic과 SQLModel 모두 model_dump() 메서드 사용
        return model.model_dump()

    def _filter_attributes(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """제외 필드 필터링"""
        return {k: v for k, v in attrs.items() if k not in self.exclude_fields}

    def _get_all_fields(self, model_list: List[Any]) -> List[str]:
        """모델 리스트에서 모든 필드명 추출"""
        if not model_list:
            return []

        sample_model = next((item for item in model_list if item is not None), None)
        if sample_model is None:
            return []

        attrs = self._extract_attributes(sample_model)
        return list(attrs.keys())

    def _perform_comparison(self) -> ComparisonResult[T]:
        """
        내부적으로 모델 리스트 비교를 수행하는 메서드
        
        Returns:
            ComparisonResult: 비교 결과
        """
        # key_fields가 비어있으면 모든 필드를 사용
        key_fields = self.key_fields
        if not key_fields:
            all_fields = set()
            all_fields.update(self._get_all_fields(self.old_list))
            all_fields.update(self._get_all_fields(self.new_list))
            key_fields = set(f for f in all_fields if f not in self.exclude_fields)
        
        # 키 중복 검사
        # self._check_key_duplicates(self.old_list, "old_list", key_fields)
        # self._check_key_duplicates(self.new_list, "new_list", key_fields)

        def get_key(item: Any) -> Tuple[Any, ...]:
            try:
                return tuple(getattr(item, field) for field in key_fields)
            except AttributeError as e:
                raise ModelComparisonError(f"키 필드 '{key_fields}'를 찾을 수 없습니다: {e}")
    
        # 키로 매핑
        old_dict = {get_key(item): item for item in self.old_list}
        new_dict = {get_key(item): item for item in self.new_list}

        old_keys = set(old_dict.keys())
        new_keys = set(new_dict.keys())

        result: ComparisonResult[T] = {
            "added": [],
            "removed": [],
            "modified": [],
            "unchanged": [],
        }

        # 추가된 항목
        for key in new_keys - old_keys:
            result["added"].append(new_dict[key])

        # 삭제된 항목
        for key in old_keys - new_keys:
            result["removed"].append(old_dict[key])

        # 변경된 항목과 변경되지 않은 항목 구분
        for key in old_keys & new_keys:
            old_item = old_dict[key]
            new_item = new_dict[key]
            
            # 모델에서 속성 추출
            old_data = self._filter_attributes(self._extract_attributes(old_item))
            new_data = self._filter_attributes(self._extract_attributes(new_item))

            if old_data != new_data:
                # 변경된 필드 찾기
                changed_fields: Dict[str, DiffChange[Any]] = {}
                all_fields = set(old_data.keys()) | set(new_data.keys())

                for field in all_fields:
                    old_value = old_data.get(field)
                    new_value = new_data.get(field)

                    if old_value != new_value:
                        changed_fields[field] = DiffChange(old=old_value, new=new_value)

                modified_item: ModifiedItem[T] = {
                    "key": dict(zip(key_fields, key)),
                    "old_item": old_item,
                    "new_item": new_item,
                    "changed_fields": changed_fields,
                }
                result["modified"].append(modified_item)
            else:
                # 변경되지 않은 항목
                result["unchanged"].append(old_item)

        return result

    # ============================================================================
    # Properties (읽기 전용)
    # ============================================================================
    
    @property
    def result(self) -> ComparisonResult[T]:
        """전체 비교 결과"""
        return self._result
    
    @property
    def added(self) -> List[T]:
        """추가된 항목들"""
        return self._result["added"]
    
    @property
    def removed(self) -> List[T]:
        """삭제된 항목들"""
        return self._result["removed"]
    
    @property
    def modified(self) -> List[ModifiedItem[T]]:
        """변경된 항목들"""
        return self._result["modified"]
    
    @property
    def unchanged(self) -> List[T]:
        """변경되지 않은 항목들"""
        return self._result["unchanged"]
    
    @property
    def has_changes(self) -> bool:
        """변경사항이 있는지 여부"""
        return len(self.added) > 0 or len(self.removed) > 0 or len(self.modified) > 0
    
    @property
    def total_items_old(self) -> int:
        """이전 리스트의 총 항목 수"""
        return len(self.old_list)
    
    @property
    def total_items_new(self) -> int:
        """새 리스트의 총 항목 수"""
        return len(self.new_list)
    
    # ============================================================================
    # Setter 차단 (불변성 보장)
    # ============================================================================
    
    def __setattr__(self, name: str, value: Any) -> None:
        """속성 설정 차단 (초기화 시점 제외)"""
        # 초기화 중에만 속성 설정 허용
        if not hasattr(self, '_initialized'):
            super().__setattr__(name, value)
            if name == '_result':  # 결과 계산이 완료되면 초기화 완료로 표시
                super().__setattr__('_initialized', True)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' 객체는 불변입니다. '{name}' 속성을 수정할 수 없습니다.")
    
    # ============================================================================
    # 출력 메서드
    # ============================================================================
    
    def pretty(self, title: str = "Comparison Result") -> str:
        """보기 좋게 포맷된 비교 결과 문자열 반환"""
        lines = []
        lines.append(f"\n=== {title} ===")
        lines.append(f"Added: {len(self.added)} items")
        lines.append(f"Removed: {len(self.removed)} items")
        lines.append(f"Modified: {len(self.modified)} items")
        lines.append(f"Unchanged: {len(self.unchanged)} items")
        
        if self.added:
            lines.append("\n[ADDED ITEMS]")
            for item in self.added:
                lines.append(f"  + {item}")
        
        if self.removed:
            lines.append("\n[REMOVED ITEMS]")
            for item in self.removed:
                lines.append(f"  - {item}")
        
        if self.modified:
            lines.append("\n[MODIFIED ITEMS]")
            for mod in self.modified:
                lines.append(f"\n  Modified item with key {mod['key']}:")
                for field, changes in mod["changed_fields"].items():
                    lines.append(f"    {field}: {changes['old']} -> {changes['new']}")
        
        if self.unchanged:
            lines.append(f"\n[UNCHANGED ITEMS] ({len(self.unchanged)} items)")
            # 너무 많으면 처음 3개만 표시
            display_count = min(3, len(self.unchanged))
            for i, item in enumerate(self.unchanged[:display_count]):
                lines.append(f"  = {item}")
            if len(self.unchanged) > display_count:
                lines.append(f"  ... and {len(self.unchanged) - display_count} more unchanged items")
        
        return "\n".join(lines)
    
    def print_pretty(self, title: str = "Comparison Result") -> None:
        """보기 좋게 포맷된 비교 결과 출력"""
        print(self.pretty(title))


# ============================================================================
# 편의 함수들 (하위 호환성)
# ============================================================================


def compare_model_lists(
    old_list: List[T],
    new_list: List[T],
    key_fields: Optional[Set[str]] = None,
    exclude_fields: Optional[Set[str]] = None,
) -> ComparisonResult[T]:
    """
    편의 함수: ModelComparator를 사용한 모델 리스트 비교

    Args:
        old_list: 이전 상태의 리스트
        new_list: 새로운 상태의 리스트
        key_fields: 비교 기준 필드명 리스트. None이면 모든 필드를 비교
        exclude_fields: 비교에서 제외할 필드명 리스트

    Returns:
        ComparisonResult: 비교 결과
    """
    comparator: ModelComparator[T] = ModelComparator(
        old_list, new_list, exclude_fields=exclude_fields, key_fields=key_fields
    )
    return comparator.result


# ============================================================================
# 출력 헬퍼 함수
# ============================================================================



# ============================================================================
# 테스트 모델들
# ============================================================================


class User(BaseModel):
    """테스트용 Pydantic 모델"""

    id: int
    name: str
    email: str

class NotUser(BaseModel):
    """테스트용 Pydantic 모델"""

    id: int
    name: str

# ============================================================================
# 데모 함수들
# ============================================================================


# 사용
def demo_pydantic_comparison():
    """Pydantic 모델 비교 데모"""
    old_list = [
        User(id=1, name="John", email="john@example.com"),
        User(id=2, name="Jane", email="jane@example.com"),
        User(id=5, name="Bob", email="bob@example.com"),
    ]

    new_list = [
        User(id=1, name="John", email="john@example.com"),  # 변경
        User(id=3, name="Bob", email="bob@example.com"),  # 추가
        User(id=4, name="Charlie", email="charlie@example.com"),  # 추가
    ]

    comparator = ModelComparator(old_list, new_list, key_fields={'id','name'})
    comparator.print_pretty("Pydantic Model Comparison")
    print(f"\nUnchanged items: {comparator.unchanged}")
    return comparator


if __name__ == "__main__":
    print("=== ModelComparator 데모 ===")
    demo_pydantic_comparison()
