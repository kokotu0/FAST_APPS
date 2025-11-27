"""
TypeScript 생성기 - 파일 I/O 및 관리 로직
"""

import os
import re
from typing import List, Tuple, Dict
from .utils import normalize_content_for_hash, extract_basemodel_types
from .base_types import BASE_TYPES, BASE_TYPES_STRING, format_types_to_export, BASE_URL
from .router_extractor import (
    extract_all_routers, 
    extract_schemas_from_router, 
    extract_routes_from_router
)
from .type_converter import (
    generate_typescript_types, 
    generate_enum_arrays
)
from .code_generator import generate_router_content
from core.internal.utils import get_file_hash


def analyze_routers_file(
    file_path: str = "api/product/routes.py",
    output_path: str = "../frontend/src/routers/product.ts",
    ts_path: str = "../frontend/src/api",
) -> str:
    """
    파일에서 모든 라우터를 분석하고 TypeScript로 변환
    
    Args:
        file_path: Python 라우터 파일 경로
        output_path: 출력 TypeScript 파일 경로
        ts_path: TypeScript 타입 경로
        
    Returns:
        TypeScript 파일 내용
    """
    all_schemas, all_routes = set(), dict()
    
    extracted_routers: Dict = extract_all_routers(file_path)
    
    for name, router in extracted_routers.items():
        schemas = extract_schemas_from_router(router)
        all_schemas.update(schemas)
        routes_dict = extract_routes_from_router(router)
        all_routes[name] = routes_dict
    
    routes_text = "\n\n"
    
    for route_name, routers in all_routes.items():
        routes_text += generate_router_content(routers, route_name, BASE_URL)
        routes_text += "\n\n"
    
    sorted_schemas = sorted(all_schemas, key=lambda x: (x.__module__, x.__name__))
    
    schemas_text = "\n".join(list(map(generate_typescript_types, sorted_schemas)))
    
    enum_arrays_text = ""
    
    for schema in sorted_schemas:
        enum_arrays_text += generate_enum_arrays(schema)
    
    import_base_types = format_types_to_export(BASE_TYPES, ts_path)
    
    # Create basic objects section
    basic_objects = f"""// Enum constant arrays for selection options
{enum_arrays_text}

// Default empty objects for forms
const token = localStorage.getItem('token');
"""
    
    import_base_types = format_types_to_export(BASE_TYPES, ts_path)
    File_content = f"""// This file is Auto-generated. Do not Edit Manually
{import_base_types}
const BASE_URL = {BASE_URL};
{basic_objects}
   
{schemas_text}

{routes_text}
    """
    return File_content


def find_route_files(
    base_dir: str = "api", ts_base_dir: str = "../frontend/src/routers"
) -> List[Tuple[str, str]]:
    """
    api 디렉토리 내의 routes.py 파일들을 찾아서 대응되는 TypeScript 파일 경로와 함께 반환
    
    Args:
        base_dir: Python api 디렉토리
        ts_base_dir: TypeScript 라우터 디렉토리
        
    Returns:
        [(py_path, ts_path), ...] 튜플 리스트
    """
    route_files = []
    pattern = re.compile(r"routes\.py$")
    
    if not os.path.exists(base_dir):
        raise FileNotFoundError(f"Directory '{base_dir}' does not exist")
    
    for root, _, files in os.walk(base_dir):
        for file in files:
            if pattern.search(file):
                # routes.py 파일 경로
                py_path = os.path.join(root, file).replace("\\", "/")
                
                # 모듈명 추출 (api/product/routes.py에서 product만 추출)
                folders = py_path.split("/")  # ['api', 'product', 'routes.py']
                module_name = folders[1]  # 'product'
                
                # TypeScript 파일 경로 생성
                ts_path = f"{ts_base_dir}/{module_name}.ts"
                
                route_files.append((py_path, ts_path))
    
    return sorted(route_files)


def Generate_TsFile(ts_base_dir: str = "../frontend/src/routers"):
    """
    모든 라우터 파일을 TypeScript로 변환하여 생성
    
    해시 기반 변경 감지를 통해 필요한 파일만 업데이트
    
    Args:
        ts_base_dir: TypeScript 라우터 디렉토리
    """
    try:
        base_dir = "api"
        routes = find_route_files(base_dir=base_dir, ts_base_dir=ts_base_dir)
        exclude_directory = f"{ts_base_dir}/protected"
        exclude_file_names = [
            "base_types.ts",  # 파일명으로 직접 체크
        ]
        new_ts_paths = []
        print("Found route files and their TypeScript paths:")
        for py_path, ts_path in routes:
            new_ts_paths.append(ts_path)
            
            # 새로 생성할 TypeScript 코드 생성
            new_ts_content = analyze_routers_file(
                file_path=py_path, output_path=ts_path, ts_path="./types/base_types"
            )
            # 정규화된 내용으로 해시 생성
            normalized_new_content = normalize_content_for_hash(new_ts_content)
            new_hash = get_file_hash(normalized_new_content)
            
            # 기존 파일이 존재하는지 확인
            if os.path.exists(ts_path):
                with open(ts_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
                
                # 기존 내용도 정규화해서 해시 생성
                normalized_existing_content = normalize_content_for_hash(existing_content)
                existing_hash = get_file_hash(normalized_existing_content)
                
                # 해시값이 같으면 스킵
                if existing_hash == new_hash:
                    continue
                else:
                    print(
                        f"Hash changed for {ts_path}: {existing_hash[:8]} -> {new_hash[:8]}"
                    )
            else:
                print(f"New file: {ts_path}")
            
            # 해시값이 다르거나 파일이 없는 경우에만 저장
            # 저장할 때도 정규화된 내용으로 저장 (일관성 보장)
            normalized_content = normalize_content_for_hash(new_ts_content)
            with open(ts_path, "w", encoding="utf-8") as f:
                f.write(normalized_content)
            print(f"Updated {ts_path}")
        
        if os.path.exists(ts_base_dir):
            existing_ts_files = []
            for root, _, files in os.walk(ts_base_dir):
                for file in files:
                    if file.endswith(".ts"):
                        full_path = os.path.join(root, file).replace("\\", "/")
                        existing_ts_files.append(full_path)
            
            # 더 이상 필요하지 않은 파일 찾아 삭제
            for existing_file in existing_ts_files:
                # 제외 폴더 내의 파일인지 확인
                is_in_exclude_dir = exclude_directory in existing_file
                # 제외할 파일명인지 확인
                is_excluded_file = any(
                    excluded in os.path.basename(existing_file)
                    for excluded in exclude_file_names
                )
                
                if (
                    existing_file not in new_ts_paths
                    and not is_in_exclude_dir
                    and not is_excluded_file
                ):
                    os.remove(existing_file)
                    print(f"Deleted: {existing_file}")
            
            print("File cleanup completed.")
    except FileNotFoundError as e:
        print(f"Error: {e}")


def Generate_specific_TsFile(ts_path: str = "../frontend/src/"):
    """
    base_types.ts 파일 생성
    
    Args:
        ts_path: TypeScript 출력 디렉토리
    """
    new_ts_content = BASE_TYPES_STRING
    new_hash = get_file_hash(new_ts_content)
    ts_path = f"{ts_path}/types/base_types.ts"
    
    if os.path.exists(ts_path):
        with open(ts_path, "r", encoding="utf-8") as f:
            existing_content = f.read()
        
        existing_hash = get_file_hash(existing_content)
        
        # 해시값이 같으면 스킵
        if existing_hash == new_hash:
            return
        else:
            print(
                f"Hash changed for base_types.ts: {existing_hash[:8]} -> {new_hash[:8]}"
            )
    else:
        print(f"New file: base_types.ts")
    
    # 해시값이 다르거나 파일이 없는 경우에만 저장
    with open(ts_path, "w", encoding="utf-8") as f:
        f.write(new_ts_content)
    print(f"Updated {ts_path}")
