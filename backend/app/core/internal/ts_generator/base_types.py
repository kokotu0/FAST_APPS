"""
TypeScript 생성기 - 기본 타입 및 상수 정의
"""

from dotenv import load_dotenv
import os
from core.base.CRUD.schemas import StandardResponse, StandardResponseMeta
from core.dependencies import BACKEND_URL
import logging
logger = logging.getLogger(__name__)
from core.internal.ts_generator.type_converter import generate_typescript_types
from core.state_machine.schema import StateMachineSchema

load_dotenv()

# 기본 TypeScript 타입 집합
BASE_TYPES = {"ISODateString", "Email", "PhoneNumber", "StandardResponse", "UUID", "NoneType"}
standard_response_meta_types = generate_typescript_types(
    StandardResponseMeta, includes_standard_response=True
)
state_machine_schema_types = generate_typescript_types(
    StateMachineSchema, includes_standard_response=True
)

standard_response_types = '''
export type StandardResponse<T> = {
    success: boolean;
    message: string;
    data: T;
    meta?: StandardResponseMeta;
}
'''

# 기본 TypeScript 타입 정의
BASE_TYPES_STRING = """
export type ISODateString = string
export type Email = `${string}@${string}.${string}`
export type PhoneNumber = `${number}-${number}-${number}`
export type nullish<T> = T | null | undefined;
export type UUID = string
export type NoneType = null
%s
%s
%s
""" % (
    standard_response_meta_types,
    standard_response_types,
    state_machine_schema_types,
)

# API 요청 설정
BASE_URL = BACKEND_URL
Authorization = "localStorage.getItem('token')? `Bearer ${token}` : '',"


def format_types_to_export(base_types: set, ts_path: str) -> str:
    """기본 타입들을 import 문으로 변환"""
    sorted_types = sorted(base_types)
    types_string = f"import type {{ {', '.join(sorted_types)} }} from '{ts_path}'"
    return types_string
