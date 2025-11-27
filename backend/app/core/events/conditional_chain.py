"""
조건부 이벤트 체이닝 - 상황에 따른 선택적 체이닝 처리

SalesOrder → Transaction (항상)
SalesOrder → Shipment (조건부: 실물 배송이 필요한 경우만)
"""

from typing import Optional, Dict, Any, Callable
from enum import Enum
import logging

from core.events.event_manager import EventMixin, event_subscriber
from api.sales.schemas import SalesOrderResponse
from api.sales.publish_events import SalesOrderEvents
from core.events.event_types import ReferenceType

logger = logging.getLogger(__name__)


class ChainCondition(str, Enum):
    """체이닝 조건"""
    ALWAYS = "항상"           # Transaction처럼 항상 생성
    PHYSICAL_ONLY = "실물만"   # 실물 배송이 필요한 경우만 Shipment 생성
    MANUAL_ONLY = "수동만"     # 수동으로만 생성
    CONDITIONAL = "조건부"     # 복잡한 조건 확인 후 생성


class ConditionalChainProcessor(EventMixin):
    """
    조건부 체이닝 처리기
    
    이벤트 발생 시 조건을 확인하고 필요한 경우에만 하위 체인 실행
    """
    
    def __init__(self, session, current_user):
        super().__init__(session, current_user)
        
        # 조건 확인 함수들 등록
        self.condition_checkers: Dict[str, Callable] = {
            "needs_shipment": self._needs_shipment,
            "needs_qm": self._needs_quality_management,
            "needs_import_manage": self._needs_import_management,
        }
    
    @event_subscriber(SalesOrderEvents.CREATED)
    def handle_sales_order_created_conditional(
        self, 
        prev_result: SalesOrderResponse, 
        **kwargs
    ) -> None:
        """
        SalesOrder 생성 시 조건부 하위 서비스 체이닝
        
        - Transaction: 항상 생성 (재무/회계 기록)
        - Shipment: 실물 배송이 필요한 경우만 생성
        - QM: 품질관리가 필요한 제품인 경우만 생성
        """
        if not prev_result.idx:
            return
            
        sales_order_id = prev_result.idx
        logger.info(f"🔄 Conditional chain processing for SalesOrder #{sales_order_id}")
        
        # 1. Transaction은 항상 생성 (이미 Pipeline에서 처리됨)
        # 별도 처리 불필요
        
        # 2. Shipment 조건부 생성
        if self._needs_shipment(prev_result):
            logger.info(f"📦 Creating Shipment for SalesOrder #{sales_order_id}")
            self._create_shipment_request(prev_result)
        else:
            logger.info(f"⏭️ Skipping Shipment for SalesOrder #{sales_order_id} (디지털 상품)")
        
        # 3. QualityManagement 조건부 생성
        if self._needs_quality_management(prev_result):
            logger.info(f"🔬 Creating QM for SalesOrder #{sales_order_id}")
            self._create_qm_request(prev_result)
        else:
            logger.info(f"⏭️ Skipping QM for SalesOrder #{sales_order_id}")
    
    @event_subscriber(SalesOrderEvents.UPDATED)
    def handle_sales_order_updated_conditional(
        self, 
        prev_result: SalesOrderResponse, 
        **kwargs
    ) -> None:
        """
        SalesOrder 업데이트 시 조건부 하위 서비스 동기화
        
        기존 하위 서비스가 있으면 업데이트, 없으면 조건 확인 후 생성
        """
        if not prev_result.idx:
            return
            
        sales_order_id = prev_result.idx
        logger.info(f"🔄 Conditional update processing for SalesOrder #{sales_order_id}")
        
        # 기존 Shipment 존재 여부 확인
        existing_shipment = self._get_existing_shipment(sales_order_id)
        
        if existing_shipment:
            # 기존 Shipment가 있으면 상태에 따라 처리
            self._handle_existing_shipment_update(prev_result, existing_shipment)
        else:
            # Shipment가 없으면 조건 확인 후 생성
            if self._needs_shipment(prev_result):
                logger.info(f"📦 Creating new Shipment for updated SalesOrder #{sales_order_id}")
                self._create_shipment_request(prev_result)
    
    def _needs_shipment(self, sales_order: SalesOrderResponse) -> bool:
        """실물 배송이 필요한지 확인"""
        # 비즈니스 로직 예시:
        # - 디지털 상품은 배송 불필요
        # - 현장 픽업 주문은 배송 불필요
        # - 일반 상품은 배송 필요
        
        # TODO: 실제 비즈니스 로직 구현
        # 예: sales_order.delivery_type이 "PHYSICAL"인 경우만 True
        return True  # 임시로 항상 True
    
    def _needs_quality_management(self, sales_order: SalesOrderResponse) -> bool:
        """품질관리가 필요한지 확인"""
        # 비즈니스 로직 예시:
        # - 식품/의료기기는 품질관리 필요
        # - 일반 상품은 품질관리 불필요
        # - 고가 상품은 품질관리 필요
        
        return False  # 임시로 항상 False
    
    def _needs_import_management(self, sales_order: SalesOrderResponse) -> bool:
        """수입관리가 필요한지 확인"""
        # 비즈니스 로직 예시:
        # - 해외 주문은 수입관리 필요
        # - 국내 주문은 수입관리 불필요
        
        return False  # 임시로 항상 False
    
    def _get_existing_shipment(self, sales_order_id: int) -> Optional[Dict[str, Any]]:
        """기존 Shipment 조회"""
        try:
            # ShipmentApp에서 조회
            shipment_app = self.mediator.get_app("ShipmentApp")
            shipment = shipment_app.get_shipment(
                ReferenceType.SALES_ORDER, 
                sales_order_id
            )
            return {
                "id": shipment.id,
                "status": shipment.status,
                "reference_idx": shipment.reference_idx,
            }
        except Exception as e:
            logger.debug(f"Shipment not found for SalesOrder #{sales_order_id}: {e}")
            return None
    
    def _handle_existing_shipment_update(
        self, 
        sales_order: SalesOrderResponse, 
        existing_shipment: Dict[str, Any]
    ) -> None:
        """기존 Shipment 업데이트 처리"""
        shipment_status = existing_shipment.get("status")
        
        if shipment_status in ["대기중", "준비중"]:
            # 아직 출하 전이면 자동 업데이트
            logger.info(f"📦 Auto-updating Shipment for SalesOrder #{sales_order.idx}")
            self._update_shipment_request(sales_order)
        
        elif shipment_status in ["출하됨", "포장됨"]:
            # 이미 출하되었으면 알림만 생성
            logger.info(f"⚠️ SalesOrder #{sales_order.idx} updated after shipment - creating notification")
            self._create_change_notification(sales_order, existing_shipment)
        
        else:
            # 완료/취소 상태면 처리하지 않음
            logger.info(f"⏭️ Skipping update for completed/cancelled Shipment")
    
    def _create_shipment_request(self, sales_order: SalesOrderResponse) -> None:
        """Shipment 생성 요청"""
        # ShipmentApp으로 생성 이벤트 발행
        self.mediator.publish(
            "shipment_create_requested",
            reference=ReferenceType.SALES_ORDER,
            reference_idx=sales_order.idx,
            sales_order_data=sales_order
        )
    
    def _update_shipment_request(self, sales_order: SalesOrderResponse) -> None:
        """Shipment 업데이트 요청"""
        # ShipmentApp으로 업데이트 이벤트 발행
        self.mediator.publish(
            "shipment_update_requested",
            reference=ReferenceType.SALES_ORDER,
            reference_idx=sales_order.idx,
            sales_order_data=sales_order
        )
    
    def _create_qm_request(self, sales_order: SalesOrderResponse) -> None:
        """QualityManagement 생성 요청"""
        # QMApp으로 생성 이벤트 발행
        self.mediator.publish(
            "qm_create_requested",
            reference=ReferenceType.SALES_ORDER,
            reference_idx=sales_order.idx,
            sales_order_data=sales_order
        )
    
    def _create_change_notification(
        self, 
        sales_order: SalesOrderResponse, 
        existing_shipment: Dict[str, Any]
    ) -> None:
        """변경 알림 생성"""
        # NotificationApp으로 알림 이벤트 발행
        self.mediator.publish(
            "notification_order_changed_after_shipment",
            sales_order=sales_order,
            shipment=existing_shipment,
            message=f"출하 후 주문 정보가 변경되었습니다. 검토가 필요합니다."
        )