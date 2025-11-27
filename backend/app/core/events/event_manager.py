"""
Event Mediator - 중재자 패턴 기반 이벤트 시스템

모든 서비스 간 통신을 중재하는 단일 EventMediator
- 전역 인스턴스로 관리
- 자동 서비스 등록
- 간단한 데코레이터만으로 이벤트 발행/구독
- Pipeline 역전파 방지

이 파일은 하위 호환성을 위해 유지되며, 
실제 구현은 EventManager 모듈로 분리되었습니다.
"""

# 하위 호환성을 위해 모든 클래스를 재export
from .EventManager import *

# 명시적으로 주요 클래스들 재export (IDE 자동완성 지원)
from .EventManager import (
    EventMediator,
    SimpleEventBus,
    Pipeline,
    Pipes,
    EventMixin,
    event_publisher,
    event_subscriber,
    EventSubscriber,
    _event_propagation_chain,
)