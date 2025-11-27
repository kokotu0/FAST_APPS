"""
TypeScript 생성기

Python FastAPI 라우터와 Pydantic 모델을 TypeScript 코드로 자동 변환하는 모듈
"""

from .file_manager import Generate_TsFile, Generate_specific_TsFile
from .base_types import BASE_TYPES, BASE_TYPES_STRING, format_types_to_export
from .type_converter import (
    get_type_name,
    generate_typescript_types,
    generate_enum_arrays,
    extract_enum_from_union,
)
from .router_extractor import (
    extract_all_routers,
    extract_schemas_from_router,
    extract_routes_from_router,
)
from .code_generator import generate_router_content
from .utils import (
    normalize_content_for_hash,
    extract_valid_params,
    extract_basemodel_types,
)

__all__ = [
    # Public API
    "Generate_TsFile",
    "Generate_specific_TsFile",
    # Constants
    "BASE_TYPES",
    "BASE_TYPES_STRING",
    # Type conversion
    "get_type_name",
    "generate_typescript_types",
    "generate_enum_arrays",
    "extract_enum_from_union",
    # Router extraction
    "extract_all_routers",
    "extract_schemas_from_router",
    "extract_routes_from_router",
    # Code generation
    "generate_router_content",
    # Utils
    "normalize_content_for_hash",
    "extract_valid_params",
    "extract_basemodel_types",
    "format_types_to_export",
]
