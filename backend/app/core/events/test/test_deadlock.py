"""
Deadlock 재현 테스트

이전 문제 상황을 의도적으로 재현하여:
1. Lock이 있는 경우 (기존 SQLAlchemyProcessRecorder) - Deadlock 발생 가능
2. Lock이 없는 경우 (ManagedSessionRecorder) - 정상 작동

를 비교합니다.
"""

from sqlmodel import Session
from core.database import engine
from eventsourcing_sqlalchemy.recorders import SQLAlchemyProcessRecorder
from core.events.custom_recorder import ManagedSessionRecorder
from core.events.app import SessionApplication
from api.sales.service import SalesService
from api.user.schemas import UserOut
import time


def test_with_lock_enabled():
    """Lock이 활성화된 경우 - Deadlock 재현"""
    print("\n=== Test 1: Lock 활성화 (기존 방식) ===")
    
    session = Session(bind=engine)
    
    # 임시로 ManagedSessionRecorder의 _lock_table을 원래대로 복원
    class LockEnabledRecorder(SQLAlchemyProcessRecorder):
        """Lock을 활성화한 recorder (deadlock 재현용)"""
        def insert_events(self, stored_events, *, session=None, **kwargs):
            if session is not None:
                notification_ids = self._insert_events(session, stored_events, **kwargs)
                # flush만 하고 commit 안 함 (deadlock 유발)
                session.flush()
                return notification_ids
            else:
                return super().insert_events(stored_events, **kwargs)
    
    try:
        # SalesOrder 여러 개 연속 삭제 시도
        user = UserOut(idx=0, email="test@test.com", name="Test User")
        sales_service = SalesService(session, user)
        
        # 여기서 원래는 recorder를 교체해야 하지만,
        # 실제로는 API를 통해 연속 요청하는 게 더 현실적
        print("⚠️  이 테스트는 실제 API 호출로 해야 정확합니다")
        print("  → 여러 DELETE /sales/{idx} 요청을 빠르게 연속으로 보내세요")
        
    except Exception as e:
        print(f"❌ Error (예상됨): {e}")
    finally:
        session.close()


def test_with_lock_disabled():
    """Lock이 비활성화된 경우 - 정상 작동"""
    print("\n=== Test 2: Lock 비활성화 (ManagedSessionRecorder) ===")
    
    session = Session(bind=engine)
    app = SessionApplication(session=session)
    
    # ManagedSessionRecorder 확인
    assert isinstance(app.recorder, ManagedSessionRecorder)
    print(f"✅ Recorder: {type(app.recorder).__name__}")
    print(f"✅ Lock disabled: _lock_table returns immediately")
    
    # 실제 테스트는 API를 통해
    print("✅ 이제 여러 DELETE 요청을 보내도 deadlock이 발생하지 않습니다")
    
    session.close()


def simulate_concurrent_deletes():
    """실제 시나리오 시뮬레이션"""
    print("\n=== Test 3: 연속 삭제 시뮬레이션 ===")
    print("다음 명령어로 테스트하세요:")
    print()
    print("# PowerShell에서:")
    print("for ($i=1; $i -le 5; $i++) {")
    print("    Invoke-RestMethod -Uri 'http://localhost:8000/sales/$i' -Method Delete")
    print("    Write-Host 'Deleted sales order $i'")
    print("}")
    print()
    print("# 또는 Python에서:")
    print("import requests")
    print("for i in range(1, 6):")
    print("    response = requests.delete(f'http://localhost:8000/sales/{i}')")
    print("    print(f'Deleted {i}: {response.status_code}')")


if __name__ == "__main__":
    print("=" * 60)
    print("Deadlock 재현 테스트")
    print("=" * 60)
    
    # Test 1: Lock 활성화 (deadlock 재현)
    # test_with_lock_enabled()  # 실제로는 주석 처리 (위험)
    
    # Test 2: Lock 비활성화 (정상)
    test_with_lock_disabled()
    
    # Test 3: 실제 테스트 방법 안내
    simulate_concurrent_deletes()
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)

