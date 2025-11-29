# database/connection.py
from typing import Annotated, Optional
from fastapi import Depends
from sqlmodel import Session, create_engine, SQLModel
from app.core.dependencies import DATABASE_URL
import logging
logger = logging.getLogger(__name__)
import traceback
# 지연 초기화를 위한 전역 변수
_engine = None

def get_engine():
    """데이터베이스 엔진을 지연 초기화하여 반환"""
    global _engine
    if _engine is None:
        from sqlalchemy import event
        
        # DATABASE_URL 검증
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not configured. "
                "Please set DATABASE_URL environment variable or configure "
                "POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DBNAME."
            )
        
        logger.info(f"Connecting to database...")
        
        # Engine 생성
        _engine = create_engine(
            DATABASE_URL, 
            echo=False,
            pool_timeout=30,
            # PostgreSQL 전용 설정
            connect_args={
                "options": "-c lock_timeout=5000"  # 5초 (밀리초 단위)
            }
        )
        
        # 또는 connection pool 레벨에서 설정
        @event.listens_for(_engine, "connect")
        def set_lock_timeout(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            # PostgreSQL: 5초 lock timeout
            cursor.execute("SET lock_timeout = '5s'")
            # PostgreSQL: 30초 statement timeout (선택사항)
            cursor.execute("SET statement_timeout = '30s'")
            cursor.close()
        
    return _engine


engine = get_engine()

def create_tables():
    SQLModel.metadata.create_all(get_engine())

def session_generator():
    with Session(get_engine(),autocommit=False, ) as session:
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            # 에러 발생 위치와 상세 정보 로깅
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Session rollbacked due to error: {e}")
            raise e
def get_session():
    return next(session_generator())
SessionDep = Annotated[Session, Depends(session_generator)]


# SQLModel의 Session 직접 사용
if __name__ == '__main__':
    from sqlmodel import Session, select
    session = Session(get_engine())
