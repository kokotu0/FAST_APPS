"""
EventManager Pipeline 시스템

Pipeline: 명시적 이벤트 파이프라인 정의
Pipes: 여러 Pipeline 관리
EventMixin: 모든 App의 기본 클래스
"""

from typing import Any, List, Type, Optional, TYPE_CHECKING
from sqlmodel import Session
import logging

from api.user.schemas import UserOut

if TYPE_CHECKING:
    from .Mediator import EventMediator

logger = logging.getLogger(__name__)


class Pipeline:
    """
    명시적 이벤트 파이프라인 정의
    
    App들의 체이닝을 명시적으로 선언
    
    사용법:
        Pipeline([ManufactureApp, TransactionApp, SalesApp])
        # ManufactureApp → TransactionApp → SalesApp
    """
    
    def __init__(self, app_classes: List[Type]):
        """
        Pipeline 초기화
        
        Args:
            app_classes: App 클래스 리스트 (순서대로 체이닝)
        """
        self.app_classes = app_classes
        self.app_instances: List[Any] = []
    
    def instantiate(self, session: Session, current_user: UserOut) -> List[Any]:
        """
        Pipeline의 모든 App 인스턴스 생성
        
        Returns:
            생성된 App 인스턴스 리스트
        """
        self.app_instances = []
        for app_class in self.app_classes:
            app_instance = app_class(session, current_user)
            self.app_instances.append(app_instance)
            logger.debug(f"   Instantiated: {app_class.__name__}")
        return self.app_instances
    
    def __repr__(self):
        app_names = " → ".join([cls.__name__ for cls in self.app_classes])
        return f"Pipeline({app_names})"


class Pipes:
    """
    여러 Pipeline 관리
    
    동일 시작점에서 여러 Pipeline으로 분기 가능
    
    사용법:
        Pipes([
            Pipeline([CustomerServiceApp, TransactionRecordApp]),
            Pipeline([CustomerServiceApp, ShipmentApp]),
            Pipeline([CustomerServiceApp, ImportManageApp]),
        ])
    """
    
    def __init__(self, pipelines: List[Pipeline]):
        """
        Pipes 초기화
        
        Args:
            pipelines: Pipeline 리스트
        """
        self.pipelines = pipelines
    
    def instantiate_all(self, session: Session, current_user: UserOut) -> List[Any]:
        """
        모든 Pipeline의 App 인스턴스 생성
        
        Returns:
            생성된 모든 App 인스턴스 리스트 (중복 제거)
        """
        all_apps = []
        app_classes_seen = set()
        
        logger.debug("Instantiating Pipes:")
        for i, pipeline in enumerate(self.pipelines, 1):
            logger.debug(f"  Pipeline {i}: {pipeline}")
            apps = pipeline.instantiate(session, current_user)
            
            # 중복 제거 (같은 클래스의 App은 한 번만 인스턴스화)
            for app in apps:
                app_class = app.__class__
                if app_class not in app_classes_seen:
                    all_apps.append(app)
                    app_classes_seen.add(app_class)
        
        logger.debug(f"Total {len(all_apps)} unique App(s) instantiated")
        return all_apps
    
    def __repr__(self):
        return f"Pipes({len(self.pipelines)} pipeline(s))"


class EventMixin:
    """
    모든 App의 기본 클래스
    
    EventMediator와 통신하기 위한 인터페이스 제공
    
    사용법:
        class BuyApp(EventMixin):
            def __init__(self, session, current_user):
                super().__init__(session, current_user)
                # 비즈니스 로직...
                
            @event_publisher("buy_created")
            def create_buy(self, item):
                # 구매 생성 로직
                return buy
    """
    
    def __init__(self, session: Session, current_user: UserOut):
        self.session = session
        self.current_user = current_user
        self.mediator: Optional['EventMediator'] = None
    
    def publish_event(self, event_name: str, **data):
        """수동으로 이벤트 발행"""
        if self.mediator:
            source_app_name = self.__class__.__name__
            self.mediator.publish(event_name, source_app_name=source_app_name, **data)
        else:
            logger.warning(f"Mediator not set, event '{event_name}' not published")
