import logging
import logging.config

# 먼저 formatter 클래스들을 import
from .custom_formatter import CustomColorFormatter, DetailedColorFormatter

# config에서 LOGGING_CONFIG dict만 가져오기 (LOGGER는 나중에)
from .config import LOGGING_CONFIG as _LOGGING_CONFIG

# formatter를 문자열 경로 대신 직접 클래스로 교체
LOGGING_CONFIG = _LOGGING_CONFIG.copy()
LOGGING_CONFIG["formatters"]["colored"]["()"] = CustomColorFormatter
LOGGING_CONFIG["formatters"]["detailed"]["()"] = DetailedColorFormatter

# 이제 안전하게 dictConfig 실행
logging.config.dictConfig(LOGGING_CONFIG)

# logger 생성
logger = logging.getLogger("core.internal.log_config.config")
logger.setLevel(logging.DEBUG)

__all__ = ["LOGGING_CONFIG", "logger", "CustomColorFormatter", "DetailedColorFormatter"]