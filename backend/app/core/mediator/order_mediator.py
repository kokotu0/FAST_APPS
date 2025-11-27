"""
주문-출고 상태 중재자 (Mediator Pattern)

모든 상태 변경은 이 중재자를 통해서만 수행
- Single Source of Truth 보장
- 상태 변경 로직 중앙 집중
- 디버깅 용이
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import Session, select
from enum import Enum


class OrderFlowMediator:
    """주문 플로우 중재자 - 모든 상태 변경의 단일 진입점"""
    
    def __init__(self, session: Session):
        self.session = session
        self._listeners = []
    
    # ========================= 주문 상태 변경 =========================
    
    def confirm_order(self, order_idx: int) -> Dict[str, Any]:
        """주문 확정 - 결제 완료 후"""
        from models.SalesModels import SalesOrder, SalesOrderStatus
        from models.TransactionsModels.Item import ItemTransaction
        
        order = self.session.get(SalesOrder, order_idx)
        if not order:
            raise ValueError(f"Order {order_idx} not found")
        
        # 상태 검증
        if order.status != SalesOrderStatus.PENDING:
            raise ValueError(f"Cannot confirm order in {order.status} status")
        
        # 1. 주문 상태 변경
        order.status = SalesOrderStatus.CONFIRMED
        order.confirmed_at = datetime.now()
        
        # 2. 재고 예약
        for detail in order.details:
            self._create_inventory_transaction(
                item_idx=detail.item_idx,
                quantity=-detail.quantity,  # 예약은 음수
                transaction_type="RESERVE",
                reference_type="SalesOrder",
                reference_idx=order_idx
            )
        
        # 3. 출고 지시 생성 (자동 또는 수동)
        if order.auto_create_shipment:
            self.create_shipment_from_order(order_idx)
        
        self.session.commit()
        self._notify_listeners("ORDER_CONFIRMED", order)
        
        return {
            "success": True,
            "order_status": order.status,
            "message": "주문이 확정되었습니다"
        }
    
    def cancel_order(self, order_idx: int, reason: str = None) -> Dict[str, Any]:
        """주문 취소"""
        from models.SalesModels import SalesOrder, SalesOrderStatus
        
        order = self.session.get(SalesOrder, order_idx)
        if not order:
            raise ValueError(f"Order {order_idx} not found")
        
        # 상태 검증 - COMPLETED는 취소 불가
        if order.status == SalesOrderStatus.COMPLETED:
            raise ValueError("완료된 주문은 취소할 수 없습니다")
        
        # 1. 관련 출고 확인
        shipments = self._get_order_shipments(order_idx)
        for shipment in shipments:
            if shipment.status in ['SHIPPED', 'DELIVERED']:
                raise ValueError("이미 출고/배송된 주문은 취소할 수 없습니다")
        
        # 2. 출고 취소
        for shipment in shipments:
            self.cancel_shipment(shipment.idx, f"주문 취소: {reason}")
        
        # 3. 재고 예약 해제
        if order.status == SalesOrderStatus.CONFIRMED:
            for detail in order.details:
                self._create_inventory_transaction(
                    item_idx=detail.item_idx,
                    quantity=detail.quantity,  # 예약 해제는 양수
                    transaction_type="RESERVE_CANCEL",
                    reference_type="SalesOrder",
                    reference_idx=order_idx
                )
        
        # 4. 주문 상태 변경
        order.status = SalesOrderStatus.CANCELLED
        order.cancelled_at = datetime.now()
        order.cancel_reason = reason
        
        self.session.commit()
        self._notify_listeners("ORDER_CANCELLED", order)
        
        return {
            "success": True,
            "order_status": order.status,
            "message": "주문이 취소되었습니다"
        }
    
    # ========================= 출고 상태 변경 =========================
    
    def create_shipment_from_order(self, order_idx: int) -> Dict[str, Any]:
        """주문에서 출고 생성"""
        from models.SalesModels import SalesOrder, SalesOrderStatus
        from models.ShipmentModels import Shipment, ShipmentDetail
        
        order = self.session.get(SalesOrder, order_idx)
        if not order:
            raise ValueError(f"Order {order_idx} not found")
        
        # 상태 검증
        if order.status != SalesOrderStatus.CONFIRMED:
            raise ValueError(f"Cannot create shipment for {order.status} order")
        
        # 1. 출고 생성
        shipment = Shipment(
            shipment_no=Shipment.generate_shipment_no(self.session),
            shipment_date=datetime.now(),
            shipment_type="SALES",
            source_type="SALES_ORDER",
            source_idx=order_idx,
            from_location_idx=order.default_warehouse_idx,
            receiver_name=order.receiver,
            receiver_contact=order.primary_contact,
            delivery_address=order.address,
            delivery_memo=order.delivery_request,
            status="PENDING"
        )
        self.session.add(shipment)
        self.session.flush()  # ID 생성
        
        # 2. 출고 상세 생성
        for detail in order.details:
            shipment_detail = ShipmentDetail(
                shipment_idx=shipment.idx,
                item_idx=detail.item_idx,
                requested_quantity=detail.quantity,
                source_detail_idx=detail.idx
            )
            self.session.add(shipment_detail)
        
        # 3. 주문 상태 변경
        order.status = SalesOrderStatus.PREPARING
        
        self.session.commit()
        self._notify_listeners("SHIPMENT_CREATED", shipment)
        
        return {
            "success": True,
            "shipment_id": shipment.idx,
            "shipment_no": shipment.shipment_no,
            "message": "출고가 생성되었습니다"
        }
    
    def process_shipment(self, shipment_idx: int, action: str) -> Dict[str, Any]:
        """출고 처리"""
        from models.ShipmentModels import Shipment, ShipmentStatus
        from models.SalesModels import SalesOrder, SalesOrderStatus
        
        shipment = self.session.get(Shipment, shipment_idx)
        if not shipment:
            raise ValueError(f"Shipment {shipment_idx} not found")
        
        if action == "SHIP":
            # 1. 재고 차감
            for detail in shipment.details:
                # 예약 해제
                self._create_inventory_transaction(
                    item_idx=detail.item_idx,
                    quantity=detail.requested_quantity,
                    transaction_type="RESERVE_CANCEL",
                    reference_type="Shipment",
                    reference_idx=shipment_idx
                )
                # 실제 차감
                self._create_inventory_transaction(
                    item_idx=detail.item_idx,
                    quantity=-detail.shipped_quantity or -detail.requested_quantity,
                    transaction_type="SHIP",
                    reference_type="Shipment", 
                    reference_idx=shipment_idx
                )
            
            # 2. 출고 상태 변경
            shipment.status = ShipmentStatus.SHIPPED
            shipment.shipped_at = datetime.now()
            
            # 3. 주문 상태 변경 (source가 주문인 경우)
            if shipment.source_type == "SALES_ORDER":
                order = self.session.get(SalesOrder, shipment.source_idx)
                if order:
                    order.status = SalesOrderStatus.SHIPPED
            
        elif action == "DELIVER":
            # 1. 출고 상태 변경
            shipment.status = ShipmentStatus.DELIVERED
            shipment.delivered_at = datetime.now()
            
            # 2. 주문 상태 변경 (source가 주문인 경우)
            if shipment.source_type == "SALES_ORDER":
                order = self.session.get(SalesOrder, shipment.source_idx)
                if order:
                    # 모든 출고가 배송 완료인지 확인
                    all_delivered = all(
                        s.status == ShipmentStatus.DELIVERED 
                        for s in self._get_order_shipments(order.idx)
                    )
                    if all_delivered:
                        order.status = SalesOrderStatus.DELIVERED
        
        self.session.commit()
        self._notify_listeners(f"SHIPMENT_{action}", shipment)
        
        return {
            "success": True,
            "shipment_status": shipment.status,
            "message": f"출고가 {action} 처리되었습니다"
        }
    
    def cancel_shipment(self, shipment_idx: int, reason: str = None) -> Dict[str, Any]:
        """출고 취소"""
        from models.ShipmentModels import Shipment, ShipmentStatus
        
        shipment = self.session.get(Shipment, shipment_idx)
        if not shipment:
            raise ValueError(f"Shipment {shipment_idx} not found")
        
        # 상태 검증
        if shipment.status in [ShipmentStatus.SHIPPED, ShipmentStatus.DELIVERED]:
            raise ValueError(f"Cannot cancel {shipment.status} shipment")
        
        # 1. 출고 상태 변경
        shipment.status = ShipmentStatus.CANCELLED
        shipment.cancelled_at = datetime.now()
        shipment.cancel_reason = reason
        
        self.session.commit()
        self._notify_listeners("SHIPMENT_CANCELLED", shipment)
        
        return {
            "success": True,
            "shipment_status": shipment.status,
            "message": "출고가 취소되었습니다"
        }
    
    # ========================= 헬퍼 메서드 =========================
    
    def _create_inventory_transaction(self, item_idx: int, quantity: float, 
                                     transaction_type: str, reference_type: str, 
                                     reference_idx: int):
        """재고 트랜잭션 생성"""
        from models.TransactionsModels.Item import ItemTransaction
        
        # 실제 구현은 TransactionModels 구조에 맞춰 조정
        transaction = ItemTransaction(
            item_idx=item_idx,
            quantity=quantity,
            status="COMPLETED",
            # transaction_type, reference 등 추가
        )
        self.session.add(transaction)
    
    def _get_order_shipments(self, order_idx: int):
        """주문의 출고 목록 조회"""
        from models.ShipmentModels import Shipment
        
        stmt = select(Shipment).where(
            Shipment.source_type == "SALES_ORDER",
            Shipment.source_idx == order_idx
        )
        return self.session.exec(stmt).all()
    
    def _notify_listeners(self, event: str, entity: Any):
        """리스너에게 이벤트 알림"""
        for listener in self._listeners:
            listener.on_event(event, entity)
    
    def register_listener(self, listener):
        """리스너 등록"""
        self._listeners.append(listener)
    
    # ========================= 조회 메서드 =========================
    
    def get_order_full_status(self, order_idx: int) -> Dict[str, Any]:
        """주문의 전체 상태 조회"""
        from models.SalesModels import SalesOrder
        
        order = self.session.get(SalesOrder, order_idx)
        if not order:
            return None
        
        shipments = self._get_order_shipments(order_idx)
        
        return {
            "order": {
                "idx": order.idx,
                "status": order.status,
                "order_number": order.order_number
            },
            "shipments": [
                {
                    "idx": s.idx,
                    "status": s.status,
                    "shipment_no": s.shipment_no,
                    "tracking_no": s.tracking_no
                }
                for s in shipments
            ],
            "display_status": self._calculate_display_status(order, shipments),
            "available_actions": self._get_available_actions(order, shipments)
        }
    
    def _calculate_display_status(self, order, shipments) -> str:
        """고객 화면용 통합 상태 계산"""
        if order.status == "CANCELLED":
            return "주문취소"
        elif not shipments:
            if order.status == "CONFIRMED":
                return "결제완료"
            else:
                return "주문접수"
        elif all(s.status == "DELIVERED" for s in shipments):
            return "배송완료"
        elif any(s.status == "SHIPPED" for s in shipments):
            return "배송중"
        elif any(s.status == "PREPARING" for s in shipments):
            return "상품준비중"
        else:
            return "출고대기"
    
    def _get_available_actions(self, order, shipments) -> List[str]:
        """현재 상태에서 가능한 액션"""
        actions = []
        
        if order.status == "PENDING":
            actions.extend(["confirm", "cancel"])
        elif order.status == "CONFIRMED":
            actions.extend(["create_shipment", "cancel"])
        elif order.status == "DELIVERED":
            actions.extend(["complete", "return"])
        
        return actions