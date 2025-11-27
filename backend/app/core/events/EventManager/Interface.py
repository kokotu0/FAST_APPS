"""
EventManager 인터페이스 정의

EventSubscriber: 이벤트 구독자 프로토콜
event_publisher: 이벤트 발행 데코레이터
event_subscriber: 이벤트 구독 데코레이터
"""

from typing import Any, Callable, Protocol, Union
from functools import wraps
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EventSubscriber(Protocol):
    """이벤트 구독자 메서드 - 반드시 prev_result 필요"""
    def __call__(self, __self: Any, prev_result: Any, **kwargs: Any) -> None:
        ...


def event_publisher(event_name: Union[str, Enum]):
    """
    메서드 실행 후 이벤트를 자동으로 발행하는 데코레이터
    
    Args:
        event_name: 이벤트 이름 (str 또는 EventName Enum)
    
    사용법:
        # 문자열 사용
        class MyApp(EventMixin):
            @event_publisher("order_created")
            def create_order(self, data) -> OrderModel:
                return order
        
        # Enum 사용 (권장 - 타입 안정성)
        class MyApp(EventMixin):
            @event_publisher(EventName.ORDER_CREATED)
            def create_order(self, data) -> OrderModel:
                return order  # 반환 타입이 보존됨!
    """
    # Enum이면 value 추출
    event_name_str = event_name.value if isinstance(event_name, Enum) else event_name
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 원래 메서드 실행
            result = func(self, *args, **kwargs)
            
            # Mediator가 있으면 이벤트 발행
            if hasattr(self, 'mediator') and self.mediator:
                # 발행자 App 이름 전달 (역전파 방지용)
                source_app_name = self.__class__.__name__
                self.mediator.publish(
                    event_name_str, 
                    source_app_name=source_app_name,
                    prev_result=result
                )
            
            return result
        
        # 메타데이터 추가 (동적 속성 - 타입 체커 무시)
        wrapper._is_event_publisher = True  # type: ignore
        wrapper._event_name = event_name_str  # type: ignore
        
        return wrapper
    return decorator


def event_subscriber(*event_names: Union[str, Enum]) -> Callable[[EventSubscriber], EventSubscriber]:
    """
    이벤트를 구독하는 데코레이터
    
    Args:
        event_names: 이벤트 이름들 (str 또는 EventName Enum)
    
    중요: 이 데코레이터가 붙은 함수는 반드시 prev_result 매개변수를 받아야 합니다!
    
    사용법:
        @event_subscriber(SalesEvents.CREATED)
        def on_order_created(self, prev_result: SalesResponse, **kwargs):
            # prev_result는 이전 단계의 결과를 담고 있음
            print(f"주문 생성됨: {prev_result.id}")
            pass
    """
    # Enum이면 value 추출
    event_names_str = tuple(
        name.value if isinstance(name, Enum) else name 
        for name in event_names
    )
    
    def decorator(func: EventSubscriber) -> EventSubscriber:
        func._event_subscriptions = event_names_str  # type: ignore
        return func
    return decorator
