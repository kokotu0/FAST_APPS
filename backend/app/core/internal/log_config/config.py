"""
Uvicorn용 컬러 로깅 설정
pytest와 유사한 색상 스타일 적용
"""

import logging

from pydantic import BaseModel
from sqlmodel import SQLModel
import black

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(asctime)s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "use_colors": None,  # auto-detect
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(asctime)s | %(client_addr)s | "%(request_line)s" | %(status_code)s',
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "use_colors": None,  # auto-detect
        },
        "colored": {
            "()": "core.internal.log_config.custom_formatter.CustomColorFormatter",
            "fmt": "%(levelprefix)s %(filename)s:%(lineno)d | %(message)s",
            "datefmt": "%H:%M:%S",
            "use_colors": True,
        },
        "detailed": {
            "()": "core.internal.log_config.custom_formatter.DetailedColorFormatter",
            "fmt": "%(levelprefix)s %(asctime)s %(filename)s:%(lineno)d [%(funcName)s] | %(message)s",
            "datefmt": "%H:%M:%S",
            "use_colors": True,
        },
    },
    "handlers": {
        "default": {
            "formatter": "detailed",  # colored 또는 detailed 중 선택 가능
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            # "level": "DEBUG",  # 핸들러 레벨 설정 (중요!)
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "level": "INFO",
        },
    },
    "loggers": {
        # uvicorn 로거
        "uvicorn": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "INFO",
        },
        "uvicorn.access": {
            "handlers": ["access"],
            "level": "INFO",
            "propagate": False,
        },
        # FastAPI 앱 로거
        "api": {
            "handlers": ["default"],
            "level": "DEBUG",
            "propagate": False,
        },
        "models": {
            "handlers": ["default"],
            "level": "DEBUG",
            "propagate": False,
        },
        # SQLAlchemy 로거 (필요시)
        "sqlalchemy": {
            "handlers": ["default"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["default"],
    },
}

# 로깅 설정은 __init__.py에서 수행됨
# LOGGER도 __init__.py에서 생성됨

def format_model(model: BaseModel | SQLModel) -> str:
    s = repr(model)
    return black.format_str(s, mode=black.FileMode(line_length=40))


