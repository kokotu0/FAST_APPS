from datetime import datetime
import os



import logging
logger = logging.getLogger(__name__)
from dotenv import load_dotenv
load_dotenv()

"""환경변수관리"""
# 환경변수에서 DATABASE_URL 가져오기
DATABASE_URL = os.getenv(
    "DATABASE_URL",
)


PERSISTENCE_MODULE = os.getenv("PERSISTENCE_MODULE",'None')
POSTGRES_DBNAME = os.getenv("POSTGRES_DBNAME",'None')
POSTGRES_HOST = os.getenv("POSTGRES_HOST",'None')
POSTGRES_PORT = os.getenv("POSTGRES_PORT",'None')
POSTGRES_USER = os.getenv("POSTGRES_USER",'None')
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD",'None')
HOLIDAY_API_KEY = os.getenv("HOLIDAY_API_KEY",'None')
BACKEND_URL = os.getenv("BACKEND_URL",'None')
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY",'None')
ALLOW_ALL_ORIGINS = os.getenv("ALLOW_ALL_ORIGINS",'None')
CORS_ORIGINS = os.getenv("CORS_ORIGINS",'None')
FRONTEND_URL = os.getenv("FRONTEND_URL",'None')
DATA_CO_KR_API_KEY=os.getenv("DATA_CO_KR_API_KEY",'None')
ENVIRONMENT=os.getenv("ENVIRONMENT",'development')