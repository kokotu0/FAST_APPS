from datetime import datetime
import os



import logging
logger = logging.getLogger(__name__)
from dotenv import load_dotenv
load_dotenv()

"""환경변수관리"""
PERSISTENCE_MODULE = os.getenv("PERSISTENCE_MODULE",'None')
POSTGRES_DBNAME = os.getenv("POSTGRES_DBNAME",'None')
POSTGRES_HOST = os.getenv("POSTGRES_HOST",'None')
POSTGRES_PORT = os.getenv("POSTGRES_PORT", '5432')
POSTGRES_USER = os.getenv("POSTGRES_USER",'None')
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD",'None')

# 환경변수에서 DATABASE_URL 가져오기, 없으면 개별 설정으로 생성
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # 개별 PostgreSQL 환경 변수로 URL 생성
    if POSTGRES_HOST != 'None' and POSTGRES_USER != 'None':
        DATABASE_URL = f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DBNAME}"
        logger.info(f"DATABASE_URL constructed from individual env vars: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DBNAME}")
    else:
        logger.warning("DATABASE_URL not set and individual PostgreSQL env vars not configured")
HOLIDAY_API_KEY = os.getenv("HOLIDAY_API_KEY",'None')
BACKEND_URL = os.getenv("BACKEND_URL",'None')
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY",'None')
ALLOW_ALL_ORIGINS = os.getenv("ALLOW_ALL_ORIGINS",'None')
CORS_ORIGINS = os.getenv("CORS_ORIGINS",'None')
FRONTEND_URL = os.getenv("FRONTEND_URL",'None')
DATA_CO_KR_API_KEY=os.getenv("DATA_CO_KR_API_KEY",'None')
ENVIRONMENT=os.getenv("ENVIRONMENT",'development')