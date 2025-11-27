"""
TypeScript 생성기 - 라우터 추출 로직
"""

import sys
import importlib.util
import inspect
from typing import Dict, List, Tuple
from fastapi.routing import APIRoute
from fastapi import APIRouter
from pydantic import BaseModel

from .utils import extract_valid_params, extract_basemodel_types


class RouteDefinition:
    """라우트 정의 타입"""
    path: str
    request: dict
    response: str | None
    method: str
    description: str | None


def extract_all_routers(file_path: str) -> Dict[str, APIRouter]:
    """
    Python 파일을 동적으로 로드하여 모든 APIRouter 추출
    
    Args:
        file_path: Python 파일 경로
        
    Returns:
        {router_name: APIRouter} 딕셔너리
    """
    module_name = f"dynamic_module_{file_path.replace('/', '_')}"
    if module_name in sys.modules:
        del sys.modules[module_name]
    
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    spec.origin.split("/")[-2]  # type: ignore
    
    module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore
    result: dict = {}
    for name, obj in inspect.getmembers(module):
        # obj.router 속성을 가진 경우 (기존 방식)
        if hasattr(obj, "router") and isinstance(obj.router, APIRouter):
            result[name] = obj.router
        # 직접 APIRouter 인스턴스인 경우 (새로 추가)
        elif isinstance(obj, APIRouter):
            result[name] = obj
    return result


def extract_schemas_from_router(router: APIRouter) -> set:
    """
    라우터에서 사용되는 모든 BaseModel 스키마 추출
    
    Args:
        router: APIRouter 인스턴스
        
    Returns:
        BaseModel 클래스들의 Set
    """
    if not isinstance(router, APIRouter):
        raise ValueError("Expected APIRouter instance")
    schemas = set()
    
    for route in router.routes:
        if isinstance(route, APIRoute):
            valid_params = extract_valid_params(route)
            # 요청 파라미터의 스키마 수집
            for param_type in valid_params.values():
                schemas.update(extract_basemodel_types(param_type))
            
            # 응답 모델의 스키마 수집
            response_model = getattr(route, "response_model", None)
            schemas.update(extract_basemodel_types(response_model))
            
            # 요청 모델의 스키마 수집
            request = getattr(route, "request", None)
            schemas.update(extract_basemodel_types(request))
    return schemas


def extract_routes_from_router(router: APIRouter) -> Dict:
    """
    라우터에서 모든 라우트 정의 추출
    
    Args:
        router: APIRouter 인스턴스
        
    Returns:
        {route_name: route_definition} 딕셔너리
    """
    routes_dict = {}
    for route in router.routes:
        if isinstance(route, APIRoute):
            valid_params = extract_valid_params(route)
            if len(route.methods) != 1:
                raise ValueError(
                    f"{route}의 route.method 가 여러개 정의되어 있습니다. "
                )
            
            route_def = {
                "path": route.path,
                "method": list(route.methods)[0],
                "request": valid_params,
                "response": getattr(route, "response_model", None),
                "description": getattr(route, "description", None),
            }
            routes_dict[route.name] = route_def
    return routes_dict
