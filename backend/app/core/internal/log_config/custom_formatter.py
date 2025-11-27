"""
커스텀 컬러 로그 포매터
파일명, 줄번호, 함수명을 포함한 상세 정보 제공
"""

import logging
import re
from uvicorn.logging import ColourizedFormatter

MAX_LENGTH = 10000  # 최대 메시지 길이 (문자 수)


class CustomColorFormatter(ColourizedFormatter):
    """커스텀 컬러 포매터 - 파일 위치 정보 포함"""

    def __init__(self, fmt=None, datefmt=None, style="%", use_colors=True):
        if fmt is None:
            # 기본 포맷 설정
            fmt = "%(levelprefix)s [%(filename)s:%(lineno)d] %(message)s"
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, use_colors=use_colors)

    def _clean_file_path(self, file_path: str) -> str:
        """파일 경로에서 .venv 제거하고 프로젝트 상대 경로로 변환"""
        if ".venv" in file_path:
            # .venv 이후의 라이브러리 경로만 표시
            parts = file_path.split(".venv")
            if len(parts) > 1:
                lib_path = parts[1].lstrip("\\/").replace("\\", "/")
                return f"[LIB] {lib_path}"

        return file_path.replace("\\", "/")

    def format(self, record: logging.LogRecord) -> str:
        # 전체 경로를 정제된 경로로 변환
        record.filename = self._clean_file_path(record.pathname)

        # 메시지 길이 제한
        message = str(record.msg)
        if len(message) > MAX_LENGTH:
            truncated = message[:MAX_LENGTH]
            remaining_chars = len(message) - MAX_LENGTH
            record.msg = f"{truncated}\n... (truncated {remaining_chars} more characters) core/internal/log_config/custom_formatter.py "

        return super().format(record)


class DetailedColorFormatter(ColourizedFormatter):
    """상세 컬러 포매터 - 함수명까지 포함"""


    def __init__(self, fmt=None, datefmt=None, style="%", use_colors=True):
        if fmt is None:
            # 더 상세한 포맷
            fmt = "%(levelprefix)s [%(filename)s:%(lineno)d in %(funcName)s()] %(name)s | %(message)s"
        if datefmt is None:
            datefmt = "%H:%M:%S"
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, use_colors=use_colors)

    def _clean_file_path(self, file_path: str) -> str:
        """파일 경로에서 .venv 제거하고 프로젝트 상대 경로로 변환"""
        if ".venv" in file_path:
            # .venv 이후의 라이브러리 경로만 표시
            parts = file_path.split(".venv")
            if len(parts) > 1:
                lib_path = parts[1].lstrip("\\/").replace("\\", "/")
                return f"[LIB] {lib_path}"

        return file_path.replace("\\", "/")

    def _highlight_location(self, message: str) -> str:
        """Location 정보를 노란색으로 강조"""
        # "File: path line_number" 패턴을 노란색으로 강조
        pattern = r"(File: [^\n]+)"
        return re.sub(pattern, r"\033[93m\1\033[0m", message)

    def format(self, record: logging.LogRecord) -> str:
        # 전체 경로를 정제된 경로로 변환
        record.filename = self._clean_file_path(record.pathname)

        # 함수명이 너무 길면 축약
        if len(record.funcName) > 20:
            record.funcName = record.funcName[:17] + "..."

        # 메시지 길이 제한
        message = str(record.msg)
        if len(message) > MAX_LENGTH:
            truncated = message[:MAX_LENGTH]
            remaining_chars = len(message) - MAX_LENGTH
            record.msg = f"{truncated}\n... (truncated {remaining_chars} more characters)  core/internal/log_config/custom_formatter.py "

        # 기본 포맷팅 수행
        formatted = super().format(record)

        # Location 정보 강조
        formatted = self._highlight_location(formatted)

        return formatted
