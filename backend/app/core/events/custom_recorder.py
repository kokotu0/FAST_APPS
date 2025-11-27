"""
Custom SQLAlchemy Recorder for SessionApplication

SessionApplication 전용 recorder로, 외부 session을 명시적으로 관리합니다:
- 항상 외부에서 전달받은 session 사용
- insert_events 후 명시적으로 flush() 호출
- LOCK TABLE 비활성화 (notification ordering 불필요)
"""

from typing import Any, Optional, Sequence
from sqlalchemy.orm import Session
from eventsourcing.persistence import StoredEvent
from eventsourcing_sqlalchemy.recorders import SQLAlchemyProcessRecorder


class ManagedSessionRecorder(SQLAlchemyProcessRecorder):
    """
    SessionApplication 전용 recorder
    
    특징:
    - 외부 session을 명시적으로 관리
    - insert_events 후 flush()로 변경사항 즉시 반영
    - LOCK TABLE 비활성화 (EventMediator가 in-memory로 즉시 전파)
    """
    
    def insert_events(  # pyright: ignore[reportIncompatibleMethodOverride] : overide 과정에서 insert_events의 구현부가 다르기 때문에.
        self,
        stored_events: Sequence[StoredEvent],
        *,
        session: Optional[Session] = None,  # Optional로 변경
        **kwargs: Any,
    ) -> Optional[Sequence[int]]:
        """
        외부 session을 받아서 이벤트 저장 후 명시적으로 flush
        
        Args:
            stored_events: 저장할 이벤트들
            session: 외부에서 관리하는 session (필수, 하지만 시그니처 호환성을 위해 Optional)
            **kwargs: 추가 인자 (tracking 등)
            
        Returns:
            notification IDs (있는 경우)
        """
        if session is None:
            raise ValueError(
                "ManagedSessionRecorder requires 'session' argument. "
                "This recorder is designed for SessionApplication only."
            )
        
        notification_ids = self._insert_events(session, stored_events, **kwargs)
        
        # ✅ 명시적으로 flush
        # - DB에 변경사항 반영
        # - LOCK 해제 (lock이 있었다면)
        # - 다음 이벤트 핸들러가 깨끗한 상태에서 시작
        session.flush()
        
        return notification_ids
    
    def _lock_table(self, session: Session) -> None:
        """
        LOCK TABLE 비활성화
        
        이유:
        - notification ID 순서 보장이 필요 없음
        - EventMediator가 같은 request 내에서 in-memory로 즉시 전파
        - Process 간 notification polling 사용 안 함
        - Lock으로 인한 deadlock 방지
        """
        # Lock 비활성화 - pass만 하면 됨
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"_lock_table called for {self.events_table_name} - SKIPPED (lock disabled)")
        pass

