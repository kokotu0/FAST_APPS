"""
중첩된 관계 처리를 위한 유틸리티 함수들
"""

from typing import Any, Dict
from .types import InputData, HasModelDump
from sqlmodel import SQLModel
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

def is_dict_like(value: Any) -> bool:
    """딕셔너리 형태의 데이터인지 확인"""
    return isinstance(value, (dict, SQLModel, BaseModel)) or hasattr(value, 'model_dump')

def is_list_of_dicts(value: Any) -> bool:
    """딕셔너리들의 리스트인지 확인"""
    return isinstance(value, list) and all(is_dict_like(item) for item in value)

def to_dict(data: InputData) -> Dict[str, Any]:
    """데이터를 딕셔너리로 변환"""
    if isinstance(data, dict):
        return data
    elif isinstance(data, (SQLModel, BaseModel)):
        return data.model_dump()
    elif hasattr(data, 'model_dump'):
        return data.model_dump()
    else:
        raise ValueError(f"지원하지 않는 데이터 타입: {type(data)}")

def get_model_name(model: type) -> str:
    """모델의 전체 이름 반환 (모듈명 포함)"""
    return f"{model.__module__}.{model.__name__}"

def has_soft_delete_field(instance: Any, field_name: str) -> bool:
    """인스턴스가 soft delete 필드를 가지고 있는지 확인"""
    return hasattr(instance, field_name)

def is_soft_deleted(instance: Any, field_name: str) -> bool:
    """인스턴스가 soft delete 상태인지 확인"""
    if not has_soft_delete_field(instance, field_name):
        return False
    return bool(getattr(instance, field_name, False))

def safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    """안전한 속성 접근"""
    try:
        return getattr(obj, attr, default)
    except AttributeError:
        return default

def safe_setattr(obj: Any, attr: str, value: Any) -> bool:
    """안전한 속성 설정"""
    try:
        if hasattr(obj, attr):
            setattr(obj, attr, value)
            return True
        return False
    except (AttributeError, TypeError):
        logger.warning(f"속성 설정 실패: {attr} = {value}")
        return False

def extract_key_values(obj: Any, key_fields: set) -> Dict[str, Any]:
    """객체에서 키 필드들의 값을 추출"""
    key_values = {}
    for field in key_fields:
        if hasattr(obj, field):
            key_values[field] = getattr(obj, field)
    return key_values

def compare_key_values(obj1: Any, obj2: Any, key_fields: set) -> bool:
    """두 객체의 키 필드 값들이 같은지 비교"""
    key_values1 = extract_key_values(obj1, key_fields)
    key_values2 = extract_key_values(obj2, key_fields)
    return key_values1 == key_values2

def validate_relationship_config(config: Dict[str, Any]) -> bool:
    """관계 설정의 유효성 검증"""
    required_fields = ['key_fields', 'exclude_fields']
    return all(field in config for field in required_fields)

def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """설정 병합 (override_config가 우선)"""
    merged = base_config.copy()
    merged.update(override_config)
    return merged
























