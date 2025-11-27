"""
실제 서비스에서 ManagedSessionRecorder가 사용되는지 확인
"""

from core.database import engine
from sqlmodel import Session
from api.user.schemas import UserOut
from api.sales.service import SalesService

def test_recorder_in_service():
    """실제 service에서 사용되는 recorder 확인"""
    session = Session(bind=engine)
    user = UserOut(idx=0, email="test@test.com", name="Test")
    
    sales_service = SalesService(session, user)
    
    # ShipmentApp과 TransactionApp 확인
    shipment_app = sales_service.mediator.get_app("ShipmentApp")
    transaction_app = sales_service.mediator.get_app("TransactionApp")
    
    print(f"ShipmentApp recorder: {type(shipment_app.recorder)}")
    print(f"TransactionApp recorder: {type(transaction_app.recorder)}")
    
    # _lock_table 메서드 확인
    print(f"\nShipmentApp._lock_table code:")
    import inspect
    print(inspect.getsource(shipment_app.recorder._lock_table))
    
    session.close()

if __name__ == "__main__":
    test_recorder_in_service()

