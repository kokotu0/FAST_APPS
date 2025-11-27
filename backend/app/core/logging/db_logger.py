"""
데이터베이스 로거
모든 로그를 PostgreSQL에 저장
"""
import time
import traceback
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
import inspect

from sqlmodel import Session, select
from eventsourcing.domain import DomainEventProtocol
from eventsourcing.application import ProcessingEvent
from eventsourcing.dispatch import singledispatchmethod
from eventsourcing.system import ProcessApplication

from models.LogModels import (
    SystemLog, SystemLogBase, LogLevel, LogCategory,
    EventLog, EventLogBase,
    APILog, APILogBase,
    AuditLog, AuditLogBase,
    PerformanceLog, PerformanceLogBase
)


class DatabaseLogger:
    """데이터베이스 로거 - 모든 로그를 DB에 저장"""
    
    def __init__(self, session: Session):
        self.session = session
        self.batch_logs: List[Any] = []
        self.batch_size = 100  # 배치 크기
        
    # ================= 시스템 로그 =================
    
    def log_system(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        category: LogCategory = LogCategory.SYSTEM,
        extra_data: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ):
        """시스템 로그 기록"""
        # 호출 정보 추출
        frame = inspect.currentframe().f_back
        module = frame.f_globals.get('__name__', '')
        function = frame.f_code.co_name
        line_number = frame.f_lineno
        
        log = SystemLog(
            level=level,
            category=category,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            extra_data=extra_data
        )
        
        # 에러 정보 추가
        if error:
            log.error_type = type(error).__name__
            log.error_message = str(error)
            log.traceback = traceback.format_exc()
        
        self._save_log(log)
    
    def debug(self, message: str, **kwargs):
        """디버그 로그"""
        self.log_system(message, LogLevel.DEBUG, extra_data=kwargs)
    
    def info(self, message: str, **kwargs):
        """정보 로그"""
        self.log_system(message, LogLevel.INFO, extra_data=kwargs)
    
    def warning(self, message: str, **kwargs):
        """경고 로그"""
        self.log_system(message, LogLevel.WARNING, extra_data=kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """에러 로그"""
        self.log_system(message, LogLevel.ERROR, extra_data=kwargs, error=error)
    
    def critical(self, message: str, error: Optional[Exception] = None, **kwargs):
        """치명적 에러 로그"""
        self.log_system(message, LogLevel.CRITICAL, extra_data=kwargs, error=error)
    
    # ================= 이벤트 로그 =================
    
    def log_event(
        self,
        event: DomainEventProtocol,
        pipe_from: Optional[str] = None,
        pipe_to: Optional[str] = None,
        correlation_id: Optional[str] = None,
        processing_time_ms: Optional[float] = None
    ):
        """이벤트 로그 기록"""
        event_data = {}
        
        # 이벤트 데이터 추출
        for attr in dir(event):
            if not attr.startswith('_'):
                value = getattr(event, attr, None)
                if not callable(value):
                    # JSON 직렬화 가능한 형태로 변환
                    if isinstance(value, UUID):
                        event_data[attr] = str(value)
                    elif isinstance(value, datetime):
                        event_data[attr] = value.isoformat()
                    elif isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        event_data[attr] = value
                    else:
                        event_data[attr] = str(value)
        
        log = EventLog(
            event_type=type(event).__module__,
            event_name=type(event).__name__,
            aggregate_type=getattr(event, 'aggregate_type', None),
            aggregate_id=str(getattr(event, 'originator_id', '')),
            event_data=event_data,
            pipe_from=pipe_from,
            pipe_to=pipe_to,
            correlation_id=correlation_id,
            processing_time_ms=processing_time_ms,
            processed=processing_time_ms is not None
        )
        
        if processing_time_ms:
            log.processed_at = datetime.now()
        
        self._save_log(log)
    
    # ================= API 로그 =================
    
    def log_api(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time_ms: float,
        request_headers: Optional[Dict] = None,
        request_body: Optional[Dict] = None,
        query_params: Optional[Dict] = None,
        response_body: Optional[Dict] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        user_id: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """API 로그 기록"""
        log = APILog(
            method=method,
            path=path,
            status_code=status_code,
            response_time_ms=response_time_ms,
            request_headers=request_headers,
            request_body=request_body,
            query_params=query_params,
            response_body=response_body,
            client_ip=client_ip,
            user_agent=user_agent,
            user_id=user_id,
            error_message=error_message
        )
        
        self._save_log(log)
    
    # ================= 감사 로그 =================
    
    def log_audit(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: int,
        entity_name: Optional[str] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        changes: Optional[Dict] = None,
        user_name: Optional[str] = None,
        user_ip: Optional[str] = None,
        reason: Optional[str] = None,
        tags: Optional[Dict] = None
    ):
        """감사 로그 기록"""
        log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            old_value=old_value,
            new_value=new_value,
            changes=changes,
            user_id=user_id,
            user_name=user_name,
            user_ip=user_ip,
            reason=reason,
            tags=tags
        )
        
        self._save_log(log)
    
    # ================= 성능 로그 =================
    
    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        cpu_usage: Optional[float] = None,
        memory_usage_mb: Optional[float] = None,
        query_count: Optional[int] = None,
        query_time_ms: Optional[float] = None,
        metrics: Optional[Dict] = None,
        context: Optional[Dict] = None
    ):
        """성능 로그 기록"""
        log = PerformanceLog(
            operation=operation,
            duration_ms=duration_ms,
            cpu_usage=cpu_usage,
            memory_usage_mb=memory_usage_mb,
            query_count=query_count,
            query_time_ms=query_time_ms,
            metrics=metrics,
            context=context
        )
        
        self._save_log(log)
    
    # ================= 유틸리티 메서드 =================
    
    def _save_log(self, log):
        """로그 저장"""
        try:
            self.session.add(log)
            self.session.commit()
        except Exception as e:
            # 로깅 실패시 콘솔에 출력
            print(f"Failed to save log: {e}")
            self.session.rollback()
    
    def save_batch(self, logs: List[Any]):
        """배치 로그 저장"""
        try:
            self.session.add_all(logs)
            self.session.commit()
        except Exception as e:
            print(f"Failed to save batch logs: {e}")
            self.session.rollback()
    
    def flush_batch(self):
        """배치 로그 플러시"""
        if self.batch_logs:
            self.save_batch(self.batch_logs)
            self.batch_logs = []
    
    # ================= 조회 메서드 =================
    
    def get_recent_logs(self, log_type: str, limit: int = 100):
        """최근 로그 조회"""
        if log_type == "system":
            stmt = select(SystemLog).order_by(SystemLog.logged_at.desc()).limit(limit)
        elif log_type == "event":
            stmt = select(EventLog).order_by(EventLog.occurred_at.desc()).limit(limit)
        elif log_type == "api":
            stmt = select(APILog).order_by(APILog.requested_at.desc()).limit(limit)
        elif log_type == "audit":
            stmt = select(AuditLog).order_by(AuditLog.performed_at.desc()).limit(limit)
        elif log_type == "performance":
            stmt = select(PerformanceLog).order_by(PerformanceLog.measured_at.desc()).limit(limit)
        else:
            return []
        
        return self.session.exec(stmt).all()
    
    def get_error_logs(self, limit: int = 100):
        """에러 로그 조회"""
        stmt = select(SystemLog).where(
            SystemLog.level.in_([LogLevel.ERROR, LogLevel.CRITICAL])
        ).order_by(SystemLog.logged_at.desc()).limit(limit)
        
        return self.session.exec(stmt).all()


class LoggingProcessApplication(ProcessApplication[UUID]):
    """로깅 기능이 포함된 ProcessApplication"""
    
    def __init__(self, session: Session, **kwargs):
        super().__init__(**kwargs)
        self.logger = DatabaseLogger(session)
        self.event_count = 0
    
    @singledispatchmethod
    def policy(self, domain_event: DomainEventProtocol[UUID],
              processing_event: ProcessingEvent[UUID]) -> None:
        """기본 정책: 모든 이벤트 로깅"""
        start_time = time.time()
        
        try:
            # 이벤트 로깅
            self.event_count += 1
            processing_time = (time.time() - start_time) * 1000
            
            self.logger.log_event(
                event=domain_event,
                pipe_from=self.__class__.__name__,
                processing_time_ms=processing_time
            )
            
            # 시스템 로그
            self.logger.info(
                f"Event processed: {type(domain_event).__name__}",
                event_count=self.event_count,
                processing_time_ms=processing_time
            )
            
            # 100개마다 성능 로그
            if self.event_count % 100 == 0:
                self.logger.log_performance(
                    operation=f"{self.__class__.__name__}.process_events",
                    duration_ms=processing_time,
                    metrics={"event_count": self.event_count}
                )
            
        except Exception as e:
            self.logger.error(
                f"Error processing event: {type(domain_event).__name__}",
                error=e
            )


# ================= 사용 예시 =================

def example_usage():
    """로깅 시스템 사용 예시"""
    from core.database import get_session
    
    with get_session() as session:
        logger = DatabaseLogger(session)
        
        # 1. 시스템 로그
        logger.info("시스템 시작", version="1.0.0")
        logger.debug("디버그 정보", data={"key": "value"})
        logger.warning("메모리 사용량 높음", memory_usage=85.5)
        
        try:
            # 에러 시뮬레이션
            1 / 0
        except Exception as e:
            logger.error("계산 오류 발생", error=e)
        
        # 2. 이벤트 로그
        class MockEvent:
            def __init__(self):
                self.originator_id = UUID('12345678-1234-5678-1234-567812345678')
                self.customer = "김철수"
                self.amount = 50000
        
        event = MockEvent()
        logger.log_event(
            event=event,
            pipe_from="OrderService",
            pipe_to="PaymentService",
            correlation_id="CORR-001",
            processing_time_ms=15.5
        )
        
        # 3. API 로그
        logger.log_api(
            method="POST",
            path="/api/orders",
            status_code=201,
            response_time_ms=125.3,
            request_body={"product": "노트북", "quantity": 1},
            response_body={"order_id": 123, "status": "created"},
            client_ip="192.168.1.100",
            user_id=1
        )
        
        # 4. 감사 로그
        logger.log_audit(
            action="UPDATE",
            entity_type="Order",
            entity_id="123",
            user_id=1,
            user_name="관리자",
            old_value={"status": "PENDING"},
            new_value={"status": "CONFIRMED"},
            changes={"status": {"old": "PENDING", "new": "CONFIRMED"}},
            reason="고객 요청"
        )
        
        # 5. 성능 로그
        logger.log_performance(
            operation="calculate_reports",
            duration_ms=1250.5,
            cpu_usage=45.2,
            memory_usage_mb=512.3,
            query_count=15,
            query_time_ms=450.2,
            metrics={"records_processed": 10000}
        )
        
        # 최근 로그 조회
        print("\n📋 최근 시스템 로그:")
        recent_logs = logger.get_recent_logs("system", limit=5)
        for log in recent_logs:
            print(f"  [{log.level}] {log.message}")
        
        print("\n❌ 최근 에러 로그:")
        error_logs = logger.get_error_logs(limit=5)
        for log in error_logs:
            print(f"  {log.message}: {log.error_message}")
        
        print("\n✅ 로깅 완료!")


if __name__ == "__main__":
    example_usage()