"""
EventManager - 중재자 패턴 기반 이벤트 시스템

모든 서비스 간 통신을 중재하는 EventMediator 시스템
- 요청 스코프별 관리
- 간단한 데코레이터만으로 이벤트 발행/구독
- Pipeline 역전파 방지

사용법:
    from core.events.EventManager import EventMediator, Pipes, Pipeline, EventMixin
    from core.events.EventManager import event_publisher, event_subscriber
"""

# 인터페이스와 데코레이터
from .Interface import EventSubscriber, event_publisher, event_subscriber

# Pipeline 시스템
from .Pipe import Pipeline, Pipes, EventMixin

# 핵심 EventMediator
from .Mediator import EventMediator, SimpleEventBus

# 컨텍스트 변수 (필요한 경우)
from contextvars import ContextVar
from typing import List, Tuple

# 현재 이벤트 전파 체인 추적 (스레드별 컨텍스트)
_event_propagation_chain: ContextVar[List[Tuple[str, str]]] = ContextVar(
    '_event_propagation_chain', 
    default=[]
)

# 모든 public 클래스/함수 export
__all__ = [
    # 핵심 클래스
    'EventMediator',
    'SimpleEventBus',  # 하위 호환성
    
    # Pipeline 시스템
    'Pipeline',
    'Pipes', 
    'EventMixin',
    
    # 데코레이터
    'event_publisher',
    'event_subscriber',
    
    # 프로토콜
    'EventSubscriber',
    
    # 컨텍스트 변수
    '_event_propagation_chain',
]
