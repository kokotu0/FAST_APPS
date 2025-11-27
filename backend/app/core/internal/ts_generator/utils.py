"""
TypeScript 생성기 - 유틸리티 함수
"""

import re
import inspect
from typing import Dict, Any, Set
from pydantic import BaseModel
from sqlmodel import SQLModel
from fastapi import Depends


def normalize_content_for_hash(content: str) -> str:
    """
    파일 내용을 정규화하여 일관된 해시 생성
    
    - 줄바꿈 문자 통일
    - import 문의 타입 순서 정렬
    - 끝 공백 제거
    """
    # 줄바꿈 문자 통일
    normalized_content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # import 문의 타입 순서 정렬
    lines = normalized_content.split('\n')
    normalized_lines = []
    
    for line in lines:
        # import type { ... } 형태의 줄 찾기
        import_match = re.match(r"(\s*)import type \{ ([^}]+) \} from '([^']+)'", line)
        if import_match:
            indent, types_str, from_path = import_match.groups()
            # 타입들을 분리하고 정렬
            types = [t.strip() for t in types_str.split(',')]
            sorted_types = sorted(types)
            # 정렬된 타입들로 다시 조합
            sorted_types_str = ', '.join(sorted_types)
            normalized_line = f"{indent}import type {{ {sorted_types_str} }} from '{from_path}'"
            normalized_lines.append(normalized_line)
        else:
            normalized_lines.append(line)
    
    # 각 줄의 끝 공백 제거
    normalized_lines = [line.rstrip() for line in normalized_lines]
    
    # 빈 줄들을 파일 끝에서 제거 (하지만 중간 빈 줄은 유지)
    while normalized_lines and not normalized_lines[-1]:
        normalized_lines.pop()
    
    # 하나의 줄바꿈으로 끝나도록 통일
    result = '\n'.join(normalized_lines)
    if result and not result.endswith('\n'):
        result += '\n'
    
    return result


def extract_valid_params(route) -> Dict[str, Any]:
    """
    라우터의 유효한 파라미터와 요청/응답 타입 추출
    
    Args:
        route: FastAPI APIRoute 인스턴스
        
    Returns:
        {param_name: param_type} 딕셔너리
    """
    sig = inspect.signature(route.endpoint)
    excluded_params = {"session", "request", "background_tasks"}
    
    valid_params = {}
    
    # path parameters와 query parameters
    for name, param in sig.parameters.items():
        if name not in excluded_params:
            # dependency 체크
            if (
                hasattr(param.default, "__class__")
                and param.default.__class__.__name__ == "Depends"
            ):
                continue
            if hasattr(param, "dependency") and param.default:
                dep_sig = inspect.signature(param.default.dependency)
                for dep_name, dep_param in dep_sig.parameters.items():
                    if dep_name not in excluded_params and hasattr(
                        dep_param, "annotation"
                    ):
                        valid_params[dep_name] = dep_param.annotation
            else:
                valid_params[name] = param.annotation
    
    return valid_params


def extract_basemodel_types(type_hint, processed_types: Set = None) -> Set:
    """
    타입 힌트에서 BaseModel 타입을 재귀적으로 추출
    
    Args:
        type_hint: 타입 힌트
        processed_types: 이미 처리한 타입 집합 (중복 방지)
        
    Returns:
        BaseModel 타입들의 Set
    """
    from typing import get_args, get_origin
    
    if processed_types is None:
        processed_types = set()
    
    schemas = set()
    
    if type_hint is None:
        return schemas
    
    # 이미 처리한 타입이면 스킵
    if isinstance(type_hint, type) and type_hint in processed_types:
        return schemas
    
    origin = get_origin(type_hint)
    
    # 제네릭 타입 처리 (List, Sequence 등)
    if origin is not None:
        # 제네릭의 타입 인자들을 재귀적으로 처리
        for arg in get_args(type_hint):
            schemas.update(extract_basemodel_types(arg, processed_types))
    
    # 일반 클래스 처리
    elif inspect.isclass(type_hint):
        # 처리한 타입으로 기록
        if issubclass(type_hint, (BaseModel, SQLModel)):
            processed_types.add(type_hint)
            schemas.add(type_hint)
            
            # 중첩된 필드 재귀 처리
            for field_name, field_type in type_hint.model_fields.items():
                field_schemas = extract_basemodel_types(
                    field_type.annotation, processed_types
                )
                schemas.update(field_schemas)
    
    return schemas
