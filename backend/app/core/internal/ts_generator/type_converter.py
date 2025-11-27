"""
TypeScript 생성기 - 타입 변환 로직
"""

from typing import (
    Dict,
    Any,
    Type,
    get_args,
    get_origin,
    Union,
    List,
    Sequence,
    Optional,
)
from enum import Enum
import types
from datetime import datetime
from fastapi import UploadFile
from pydantic import BaseModel, EmailStr
from pydantic2ts import generate_typescript_defs
from typing import NewType
import uuid
import sqlalchemy

from core.state_machine.base import Never

PhoneNumber = NewType("PhoneNumber", str)

TYPE_MAPPING = {
    int: "number",
    float: "number",
    str: "string",
    EmailStr: "Email",
    bool: "boolean",
    dict: "Record<string, any>",
    list: "any[]",
    List: "any[]",
    Dict: "Record<string, any>",
    UploadFile: "File",
    None: "null",
    datetime: "ISODateString",
    types.NoneType: "null",
    PhoneNumber: "PhoneNumber",
    uuid.UUID: "UUID",
    types.NoneType: "null",
    Never: "null",  # 전이 불가능한 상태
}


def get_type_name(field_type) -> tuple[str, bool]:
    """
    필드 타입을 TypeScript 타입 문자열로 변환

    Args:
        field_type: Python 타입

    Returns:
        tuple[str, bool]: (타입 문자열, nullable 여부)
    """
    origin = get_origin(field_type)
    args = get_args(field_type)

    # Union 타입 처리
    if origin is Union or (isinstance(field_type, types.UnionType)):
        union_args = args if args else getattr(field_type, "__args__", [])
        has_none = any(arg in (None, types.NoneType) for arg in union_args)
        valid_types = [arg for arg in union_args if arg not in (None, types.NoneType)]

        if len(valid_types) == 1:
            inner_type, _ = get_type_name(valid_types[0])
            return inner_type, has_none
        else:
            types_str = [get_type_name(arg)[0] for arg in valid_types]
            return " | ".join(types_str), has_none

    # List, Sequence 타입 처리
    try:
        from collections.abc import Sequence as ABCSequence
        from typing import Sequence as TypingSequence

        is_list_like = (
            origin in (list, List)
            or origin is ABCSequence
            or origin is TypingSequence
            or (
                origin is not None
                and isinstance(origin, type)
                and issubclass(origin, ABCSequence)
            )
        )
    except (TypeError, AttributeError):
        is_list_like = origin in (list, List)

    if is_list_like:
        if args:
            # List[Enum]의 경우 특별히 처리 (동적 Enum)
            inner_arg = args[0]
            if isinstance(inner_arg, type) and issubclass(inner_arg, Enum):
                # Enum의 모든 값을 Union으로 변환
                enum_values = " | ".join([f"'{v.value}'" for v in inner_arg])
                return f"({enum_values})[]", False

            inner_type, _ = get_type_name(args[0])
            return f"{inner_type}[]", False
        return "any[]", False

    # Dict 타입 처리
    if origin in (dict, Dict):
        if len(args) == 2:
            key_type, _ = get_type_name(args[0])
            value_type, _ = get_type_name(args[1])
            return f"Record<{key_type}, {value_type}>", False
        return "Record<string, any>", False

    # Enum 처리
    if isinstance(field_type, type) and issubclass(field_type, Enum):
        if hasattr(field_type, "__qualname__") and "." in field_type.__qualname__:
            model_name = field_type.__qualname__.split(".")[0]
            field_name = field_type.__name__
            return f"{model_name}_{field_name}Type", False
        else:
            # Enum의 value를 사용
            return " | ".join([f"'{v.value}'" for v in field_type]), False

    # BaseModel 처리 (제네릭 타입 포함)
    if isinstance(field_type, type) and issubclass(field_type, BaseModel):
        field_type_name = field_type.__name__

        # Python 기본 타입 → TypeScript 타입 매핑 (문자열 기반)
        PYTHON_TO_TS_STR_MAPPING = {
            "int": "number",
            "float": "number",
            "str": "string",
            "bool": "boolean",
            "dict": "Record<string, any>",
            "list": "any[]",
            "None": "null",
            "NoneType": "null",
        }

        def convert_python_to_typescript(python_type: str) -> str:
            """Python 타입 힌트를 TypeScript 제네릭 형식으로 변환"""
            result = []
            i = 0
            current_word = []

            while i < len(python_type):
                if python_type[i:].startswith("List[") or python_type[i:].startswith(
                    "Sequence["
                ):
                    # 현재까지 모은 단어 처리
                    if current_word:
                        word = "".join(current_word)
                        result.append(PYTHON_TO_TS_STR_MAPPING.get(word, word))
                        current_word = []
                    
                    if python_type[i:].startswith("List["):
                        i += 4
                    else:
                        i += 8

                    i += 1
                    bracket_count = 1
                    inner_start = i

                    while i < len(python_type) and bracket_count > 0:
                        if python_type[i] == "[":
                            bracket_count += 1
                        elif python_type[i] == "]":
                            bracket_count -= 1
                        i += 1

                    inner_type = python_type[inner_start : i - 1]
                    converted_inner = convert_python_to_typescript(inner_type)
                    result.append(converted_inner)
                    result.append("[]")

                elif python_type[i] == "[":
                    # 현재까지 모은 단어 처리
                    if current_word:
                        word = "".join(current_word)
                        result.append(PYTHON_TO_TS_STR_MAPPING.get(word, word))
                        current_word = []
                    result.append("<")
                    i += 1
                elif python_type[i] == "]":
                    # 현재까지 모은 단어 처리
                    if current_word:
                        word = "".join(current_word)
                        result.append(PYTHON_TO_TS_STR_MAPPING.get(word, word))
                        current_word = []
                    result.append(">")
                    i += 1
                elif python_type[i] in (",", " "):
                    # 현재까지 모은 단어 처리
                    if current_word:
                        word = "".join(current_word)
                        result.append(PYTHON_TO_TS_STR_MAPPING.get(word, word))
                        current_word = []
                    if python_type[i] == ",":
                        result.append(", ")
                    i += 1
                else:
                    current_word.append(python_type[i])
                    i += 1
            
            # 마지막 단어 처리
            if current_word:
                word = "".join(current_word)
                result.append(PYTHON_TO_TS_STR_MAPPING.get(word, word))

            return "".join(result)

        clean_name = convert_python_to_typescript(field_type_name)
        return clean_name, False

    # 기본 타입 매핑 확인
    if field_type in TYPE_MAPPING:
        return TYPE_MAPPING[field_type], False

    return "any", True


def extract_enum_from_union(field_type):
    """
    Union 타입에서 Enum을 추출하는 헬퍼 함수

    Returns:
        tuple[Enum|None, bool]: (Enum 타입, nullable 여부)
    """
    origin = get_origin(field_type)
    if origin is Union or (isinstance(field_type, types.UnionType)):
        args = (
            get_args(field_type)
            if get_args(field_type)
            else getattr(field_type, "__args__", [])
        )
        has_none = any(arg in (None, types.NoneType) for arg in args)
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, Enum):
                return arg, has_none
    return None, False



def generate_typescript_types(
    model: Type[BaseModel], includes_standard_response: bool = False
    ) -> str:
    """
    단일 모델을 TypeScript 인터페이스 정의로 변환

    Args:
        model: Pydantic BaseModel 클래스

    Returns:
        TypeScript 인터페이스 정의 문자열
    """
    typescript_definition = []
    base_model_name = model.__name__
    if "StandardResponse" in base_model_name and not includes_standard_response:
        return ""

    clean_model_name = base_model_name
    typescript_definition.append(f"\nexport interface {clean_model_name} {{")

    # 모든 가능한 필드 속성 확인
    all_fields = {}

    # model_fields 확인 (Pydantic v2)
    if hasattr(model, "model_fields"):
        all_fields.update(model.model_fields)

    # __fields__ 확인 (Pydantic v1)
    if hasattr(model, "__fields__"):
        all_fields.update(model.__fields__)

    # __annotations__ 확인 (SQLModel)
    if hasattr(model, "__annotations__"):
        for field_name, field_type in model.__annotations__.items():
            if field_name not in all_fields:
                all_fields[field_name] = {"annotation": field_type, "required": True}

    # 각 필드 처리
    for field_name, field in all_fields.items():
        if isinstance(field, dict):
            field_type = field["annotation"]
            required = field.get("required", True)
        else:
            field_type = (
                field.annotation if hasattr(field, "annotation") else field.outer_type_
            )
            required = (
                field.is_required
                if hasattr(field, "is_required")
                else not field.allow_none
            )

        if hasattr(field_type, "__origin__"):
            if field_type.__origin__ == sqlalchemy.orm.base.Mapped:
                continue

        # Enum 타입인 경우 생성된 타입 이름 사용
        enum_type = None
        enum_nullable = False
        if isinstance(field_type, type) and issubclass(field_type, Enum):
            enum_type = field_type
            enum_nullable = False
        else:
            enum_type, enum_nullable = extract_enum_from_union(field_type)

        if enum_type:
            type_str = f"{clean_model_name}_{field_name}_Type"
            # Optional enum인 경우 null도 허용
            if enum_nullable:
                type_str = f"{type_str} | null"
            is_nullable = enum_nullable
        else:
            type_str, is_nullable = get_type_name(field_type)

        optional = "?" if (not required or is_nullable) else ""
        typescript_definition.append(
            f"    {field_name}{optional}: {type_str} {'| null' if is_nullable else ''} ;"
        )

    typescript_definition.append("}")
    return "\n".join(typescript_definition)


def generate_enum_arrays(model: Type[BaseModel]) -> str:
    """
    모델의 Enum 필드에 대한 TypeScript 상수 배열 생성

    Args:
        model: Pydantic BaseModel 클래스

    Returns:
        TypeScript enum 배열 정의 문자열
    """
    enum_arrays = []
    clean_model_name = model.__name__.split("[")[0]

    all_fields = {}

    if hasattr(model, "model_fields"):
        all_fields.update(model.model_fields)

    if hasattr(model, "__fields__"):
        all_fields.update(model.__fields__)

    if hasattr(model, "__annotations__"):
        for field_name, field_type in model.__annotations__.items():
            if field_name not in all_fields:
                all_fields[field_name] = {"annotation": field_type}

    for field_name, field in all_fields.items():
        if isinstance(field, dict):
            field_type = field["annotation"]
        else:
            field_type = (
                field.annotation if hasattr(field, "annotation") else field.outer_type_
            )

        # Enum 타입 확인
        enum_type = None
        if isinstance(field_type, type) and issubclass(field_type, Enum):
            enum_type = field_type
        else:
            enum_type, _ = extract_enum_from_union(field_type)

        if enum_type:
            array_name = f"{clean_model_name}_{field_name}_Options"
            type_name = f"{clean_model_name}_{field_name}_Type"
            enum_values = [f"'{v.value}'" for v in enum_type]
            enum_values_str = " | ".join([f"'{v.value}'" for v in enum_type])
            enum_arrays.append(f"export type {type_name} = {enum_values_str};")
            enum_arrays.append(
                f"export const {array_name}: {type_name}[] = [{', '.join(enum_values)}]; \n"
            )

    return "\n".join(enum_arrays) if enum_arrays else ""
