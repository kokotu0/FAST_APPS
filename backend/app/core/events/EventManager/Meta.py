"""
EventMediator 메타클래스와 레지스트리 관리

### 역할 구분 ###
1. EventMediatorRegistry: 
   - EventMediator를 상속받는 **Service 클래스**들을 전역 레지스트리에 등록
   - 예: SalesService, BuyService, ShipmentService
   - 용도: 디버깅, 시스템 모니터링

2. EventMediator._apps:
   - EventMixin을 상속받는 **App 인스턴스**들을 요청별로 관리
   - 예: SalesOrderApp, BuyApp, ShipmentApp
   - 용도: 실제 이벤트 발행/구독, 비즈니스 로직

EventMediatorMeta: EventMediator를 상속받는 Service 클래스 자동 등록을 위한 메타클래스
"""

from typing import Dict, Type, TYPE_CHECKING, cast
from threading import Lock
import logging

from api.user.routes import get_current_user
from api.user.service import temp_user
from core.database import get_session
from api.user.schemas import UserOut

if TYPE_CHECKING:
    from .Mediator import EventMediator

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class EventMediatorRegistry:
    """EventMediator 클래스들의 전역 레지스트리"""
    _mediators: Dict[str, Type['EventMediator']] = {}
    _lock: Lock = Lock()
    
    @classmethod
    def get_mediator(cls, name: str) -> Type['EventMediator']:
        with cls._lock:
            return cls._mediators[name]
    
    @classmethod
    def register_mediator(cls, name: str, mediator: Type['EventMediator']):
        with cls._lock:
            cls._mediators[name] = mediator
    
    @classmethod
    def cleanup_mediator(cls, name: str):
        with cls._lock:
            if name in cls._mediators:
                del cls._mediators[name]
                logger.debug(f"Cleaned up EventMediator for request {name}")
    
    @classmethod    
    def get_all_mediators(cls) -> Dict[str, Type['EventMediator']]:
        with cls._lock:
            return dict[str, type['EventMediator']](cls._mediators)
    @classmethod
    def get_all_mediator_names(cls) -> list[str]:
        with cls._lock:
            return list[str](cls._mediators.keys())
    
    # Pipeline 템플릿 관리 추가
    _pipeline_templates: Dict[str, Dict] = {}  # 클래스별 Pipeline 템플릿 정보
    
    @classmethod
    def register_pipeline_template(cls, class_name: str, pipeline_info: Dict):
        """클래스별 Pipeline 템플릿 정보 등록"""
        with cls._lock:
            cls._pipeline_templates[class_name] = pipeline_info
            logger.debug(f"Registered pipeline template for {class_name}")
    
    @classmethod
    def get_all_pipeline_templates(cls) -> Dict[str, Dict]:
        """모든 클래스별 Pipeline 템플릿 정보 반환"""
        with cls._lock:
            return dict(cls._pipeline_templates)
    
    @classmethod
    def get_pipeline_template(cls, class_name: str) -> Dict:
        """특정 클래스의 Pipeline 템플릿 정보 반환"""
        with cls._lock:
            return cls._pipeline_templates.get(class_name, {})

class EventMediatorMeta(type):
    """
    EventMediator 자동 등록을 위한 메타클래스
    
    ### 작동 방식 ###
    1. EventMediator를 **직접** 상속받는 Service 클래스가 정의될 때 자동 실행
    2. 해당 클래스를 EventMediatorRegistry에 등록
    3. 등록된 클래스 정보는 디버깅/모니터링 용도로 사용
    
    ### 주의사항 ###
    - EventMixin을 상속받는 App 클래스들은 여기서 등록되지 않음
    - App 인스턴스는 EventMediator.__init__에서 Pipes를 통해 등록됨
    
    ### 등록되는 클래스 예시 ###
    - [O] SalesService(EventMediator) -> Registry에 등록됨
    - [O] BuyService(EventMediator) -> Registry에 등록됨
    - [X] SalesOrderApp(EventMixin) -> Registry에 등록 안 됨 (정상)
    - [X] BuyApp(EventMixin) -> Registry에 등록 안 됨 (정상)
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        mcs.logger.debug(f"EventMediatorMeta __new__: {name} bases={[b.__name__ for b in bases]}")
        
        # EventMediator를 **직접** 상속받는 Service 클래스만 등록
        if bases and any(base.__name__ == 'EventMediator' for base in bases):
            EventMediatorRegistry.register_mediator(name, cast(Type['EventMediator'], cls))
            mcs.logger.debug(f"Registered Service class to Registry: {name}")
        else:
            mcs.logger.debug(f"Skipped (not direct EventMediator child): {name}")
        
        return cls
