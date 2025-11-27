"""
에러 위치 추적 유틸리티
모든 에러 핸들러에서 공통으로 사용하는 위치 정보 추출 기능
"""
import traceback
import sys
from typing import Optional, Dict, Any
from pathlib import Path
import logging
logger = logging.getLogger(__name__)
def get_error_location() -> Optional[Dict[str, Any]]:
    """
    에러가 발생한 파일과 위치 정보를 추출
    
    우선순위:
    1. api/ 디렉토리의 routes.py (실제 라우터 정의)
    2. api/ 디렉토리의 다른 파일들 (service.py 등)
    3. 프로젝트 코드
    
    Returns:
        dict: 에러 위치 정보 {file, line, function, code}
    """
    tb = traceback.extract_tb(sys.exc_info()[2])
    
    if not tb:
        return None
    
    # 프로젝트 코드에서 발생한 에러 위치 찾기 (라이브러리 제외)
    exclude_patterns = [
        'sqlalchemy',
        '.venv',
        'site-packages',
        'fastapi',
        'starlette',
        'pydantic',
        'uvicorn',
        'eventsourcing',
        'anyio',
        'asyncio'
    ]
    
    # 최전선 우선순위 파일들
    priority_patterns = [
        'api',  # api 디렉토리의 모든 파일
    ]
    
    # 1순위: api/*/routes.py 찾기 (실제 라우터 정의)
    for frame in reversed(tb):
        if 'api' in frame.filename and 'routes.py' in frame.filename:
            should_exclude = any(pattern in frame.filename for pattern in exclude_patterns)
            if not should_exclude:
                try:
                    file_path = Path(frame.filename).relative_to(Path.cwd())
                except ValueError:
                    file_path = Path(frame.filename)
                
                return {
                    "file": str(file_path),
                    "line": frame.lineno,
                    "function": frame.name,
                    "code": frame.line
                }
    
    # 2순위: api 디렉토리의 파일 찾기
    for frame in reversed(tb):
        if 'api' in frame.filename:
            should_exclude = any(pattern in frame.filename for pattern in exclude_patterns)
            if not should_exclude:
                try:
                    file_path = Path(frame.filename).relative_to(Path.cwd())
                except ValueError:
                    file_path = Path(frame.filename)
                
                return {
                    "file": str(file_path),
                    "line": frame.lineno,
                    "function": frame.name,
                    "code": frame.line
                }
    
    # 3순위: 프로젝트 코드 찾기
    for frame in reversed(tb):
        should_exclude = any(pattern in frame.filename for pattern in exclude_patterns)
        
        if not should_exclude:
            try:
                file_path = Path(frame.filename).relative_to(Path.cwd())
            except ValueError:
                file_path = Path(frame.filename)
            
            return {
                "file": str(file_path),
                "line": frame.lineno,
                "function": frame.name,
                "code": frame.line
            }
    
    # 최후의 수단: 마지막 프레임 반환
    last_frame = tb[-1]
    try:
        file_path = Path(last_frame.filename).relative_to(Path.cwd())
    except ValueError:
        file_path = Path(last_frame.filename)
    
    return {
        "file": str(file_path),
        "line": last_frame.lineno,
        "function": last_frame.name,
        "code": last_frame.line
    }

def format_error_location(location: Optional[Dict[str, Any]]) -> str:
    """
    에러 위치 정보를 보기 좋은 문자열로 포맷팅
    
    Args:
        location: get_error_location()의 반환값
    
    Returns:
        str: 포맷팅된 위치 정보
    """
    if not location:
        return ""
    
    return f"{location['file']}:{location['line']} in {location['function']}"

def _clean_file_path(file_path: str) -> str:
    """
    파일 경로를 정제하여 최전선 정보만 표시
    
    Args:
        file_path: 원본 파일 경로
    
    Returns:
        str: 정제된 파일 경로 (프로젝트 상대 경로)
    """
    # Windows 경로를 Unix 경로로 통일
    normalized_path = file_path.replace('\\', '/')
    
    # .venv 경로는 무시 (라이브러리)
    if '.venv' in normalized_path:
        return ""  # 빈 문자열을 반환하여 제외
    
    return normalized_path


def log_error_with_location(
    error_type: str,
    request,
    exc: Exception,
    location: Optional[Dict[str, Any]] = None
) -> None:
    """
    에러 정보와 위치를 함께 로깅
    
    Args:
        error_type: 에러 타입 문자열
        request: FastAPI Request 객체
        exc: 발생한 예외
        location: 에러 위치 정보
    """
    
    logger.error(f"=== {error_type} ===")
    logger.error(f"Request: {request.method} {request.url}")
    
    # 에러 위치 정보 출력 (노란색 강조) - 최전선 정보만 표시
    if location:
        cleaned_file = _clean_file_path(location['file'])
        # .venv가 포함된 경로는 표시하지 않음
        if cleaned_file:
            # ANSI 노란색 코드: \033[93m (bright yellow), 리셋: \033[0m
            location_info = f"  \033[93m→ {cleaned_file}:{location['line']} in {location['function']}\033[0m"
            logger.error(location_info)
    

def add_location_to_details(
    details: Optional[str],
    location: Optional[Dict[str, Any]],
    show_diag: bool = True
) -> Optional[str]:
    """
    에러 상세 정보에 위치 정보 추가
    
    Args:
        details: 기존 상세 정보
        location: 에러 위치 정보
        show_diag: 진단 정보 표시 여부
    
    Returns:
        str: 위치 정보가 추가된 상세 정보
    """
    if not show_diag:
        return None
    
    if location:
        location_str = format_error_location(location)
        if details:
            return f"{details}\n\n🔍 발생 위치: {location_str}"
        else:
            return f"🔍 발생 위치: {location_str}"
    
    return details