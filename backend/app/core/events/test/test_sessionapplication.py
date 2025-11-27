from core.events.app import SessionApplication
from core.events.custom_recorder import ManagedSessionRecorder
from sqlmodel import Session
from core.database import engine


def test_sessionapplication():
    """SessionApplication이 외부 session을 올바르게 사용하는지 테스트"""
    session = Session(bind=engine)
    app = SessionApplication(session=session)

    # Recorder 타입 확인
    assert isinstance(app.recorder, ManagedSessionRecorder), \
        f"Expected ManagedSessionRecorder, got {type(app.recorder)}"
    
    # Session ID 일치 확인
    assert id(session) == id(app.session), \
        f"Session ID mismatch: original={id(session)}, app={id(app.session)}"
    
    # 동일 객체 확인
    assert session is app.session, \
        "Session objects are not the same instance"
    
    # Datastore에 scoped_session이 설정되어 있는지 확인
    assert app.recorder.datastore.scoped_session is not None, \
        "Datastore scoped_session is None"
    
    print("✅ All tests passed!")
    print(f"  - Recorder type: {type(app.recorder).__name__}")
    print(f"  - Session ID: {id(session)}")
    print(f"  - Same object: {session is app.session}")
    print(f"  - Scoped session: {type(app.recorder.datastore.scoped_session).__name__}")


if __name__ == "__main__":
    test_sessionapplication()