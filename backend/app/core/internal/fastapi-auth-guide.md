# FastAPI 인증 및 권한 관리 가이드

## 개요

이 문서는 FastAPI에서 JWT를 사용한 인증 및 권한 관리 시스템에 대한 가이드입니다. 사용자 인증, 토큰 생성/검증, 권한 확인 등의 기능을 포함합니다.

## 기본 구성 요소

### 암호화 설정
```python
from passlib.context import CryptContext

# bcrypt 알고리즘을 사용한 비밀번호 암호화
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

### JWT 설정
```python
SECRET_KEY = 'ha2n'  # 실제 서비스에서는 환경 변수로 관리 권장
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 7200  # 2시간
```

## 주요 기능

### 1. 토큰 생성

```python
def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    """
    액세스 토큰을 생성합니다.
    
    Args:
        data: 토큰에 인코딩할 데이터
        expires_delta: 토큰 만료 시간(분)
        
    Returns:
        str: JWT 토큰
    """
    to_encode = jsonable_encoder(data)  # datetime 등을 JSON 직렬화 가능한 형태로 변환
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### 2. 토큰 디코딩 유틸리티

```python
def DecodeHashed(Hashed: str) -> dict:
    """JWT 토큰을 디코딩하여 데이터를 반환합니다."""
    return jwt.decode(Hashed, key=SECRET_KEY, algorithms=ALGORITHM)

def EncodeDict(Dictionary: dict) -> str:
    """딕셔너리를 JWT 토큰으로 인코딩합니다."""
    return jwt.encode(Dictionary, key=SECRET_KEY, algorithm=ALGORITHM)
```

### 3. 토큰 검증

```python
async def verify_token(token: str = Depends(security.OAuth2PasswordBearer(tokenUrl="login"))):
    """
    JWT 토큰을 검증하고 페이로드를 반환합니다.
    유효하지 않은 토큰은 401 Unauthorized 예외를 발생시킵니다.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401)
        return payload
    except JWTError:
        raise HTTPException(status_code=401)
```

### 4. 현재 사용자 확인

```python
oauth2_scheme = security.OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(session: SessionDep, token: str = Depends(oauth2_scheme)) -> User:
    """
    현재 인증된 사용자 정보를 데이터베이스에서 조회하여 반환합니다.
    
    이 함수는 다음을 수행합니다:
    1. JWT 토큰 디코딩 및 검증
    2. 토큰 타입 확인 (액세스 토큰만 허용)
    3. 사용자 idx 추출 및 데이터베이스 조회
    4. 사용자 객체 반환
    
    인증 실패 시 적절한 HTTP 예외를 발생시킵니다.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 토큰 타입 검증 (리프레시 토큰 방지)
        token_type = payload.get("token_type")
        if token_type == "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="리프레시 토큰으로 인증할 수 없습니다. 액세스 토큰을 사용하세요.",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰에 사용자 ID가 없습니다",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 데이터베이스에서 사용자 조회
    user = session.exec(
        select(User).where(User.idx == int(user_id))
    ).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
        
    return user
```

### 5. 권한 확인

```python
async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    사용자가 활성 상태인지 확인합니다.
    비활성화된 사용자는 403 Forbidden 예외를 발생시킵니다.
    """
    if not current_user.useYN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="비활성화된 사용자입니다"
        )
    return current_user

async def get_current_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    사용자가 관리자 권한을 가지고 있는지 확인합니다.
    관리자가 아닌 사용자는 403 Forbidden 예외를 발생시킵니다.
    """
    if not current_user.position == 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )
    return current_user
```

## 사용 방법

### 엔드포인트에 인증 적용

```python
@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """인증된 사용자의 정보를 반환합니다."""
    return current_user

@app.get("/admin/users")
async def get_all_users(current_user: User = Depends(get_current_admin)):
    """관리자만 접근 가능한 엔드포인트"""
    # 사용자 목록 조회 로직
    return {"message": "관리자 권한으로 모든 사용자 조회"}
```

### 라우터 단위로 인증 적용

```python
admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin)]  # 이 라우터의 모든 엔드포인트는 관리자 권한 필요
)

@admin_router.get("/stats")
async def get_stats():
    """관리자 전용 통계 페이지"""
    return {"message": "관리자 통계 페이지"}
```

## 사용자 설정 확장 방법

현재 구현에서는 사용자의 기본 정보만 처리하고 있지만, 아래와 같이 사용자별 설정 정보를 함께 처리하도록 확장할 수 있습니다:

### 사용자 설정을 위한 모델 정의 (예시)

```python
class UserSettings(SQLModel, table=True):
    """사용자별 설정 정보를 저장하는 모델"""
    idx: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.idx")
    settings_data: str = Field(default="{}")  # JSON 문자열로 저장
    
    user: User = Relationship(back_populates="settings")
```

### 사용자 설정 조회 함수

```python
async def get_user_with_settings(
    current_user: User = Depends(get_current_active_user),
    session: SessionDep = None
) -> dict:
    """사용자 정보와 함께 설정 정보를 반환합니다."""
    
    # 사용자 설정 조회
    settings = session.exec(
        select(UserSettings).where(UserSettings.user_id == current_user.idx)
    ).first()
    
    # 설정이 없으면 기본값 생성
    if settings is None:
        settings = UserSettings(user_id=current_user.idx)
        session.add(settings)
        session.commit()
        session.refresh(settings)
    
    # 사용자 정보와 설정을 함께 반환
    user_data = {
        "idx": current_user.idx,
        "name": current_user.name,
        "email": current_user.email,
        "team": current_user.team,
        "position": current_user.position,
        "settings": json.loads(settings.settings_data)
    }
    
    return user_data
```

### 토큰에 일부 설정 포함하기

```python
async def login_for_access_token(
    session: SessionDep,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    # 사용자 인증 로직...
    
    # 기본 설정 조회
    settings = session.exec(
        select(UserSettings).where(UserSettings.user_id == user.idx)
    ).first()
    
    # 중요 사용자 설정 (자주 사용되는)
    user_preferences = {}
    if settings:
        all_settings = json.loads(settings.settings_data)
        # 토큰에는 중요하고 자주 사용되는 설정만 포함
        user_preferences = {
            "theme": all_settings.get("theme", "light"),
            "language": all_settings.get("language", "ko"),
            "notifications": all_settings.get("notifications", True)
        }
    
    # 토큰 생성
    access_token_data = {
        "sub": str(user.idx),
        "name": user.name,
        "token_type": "access",
        "preferences": user_preferences  # 일부 설정만 토큰에 포함
    }
    
    access_token = create_access_token(access_token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
```

## 주의사항

1. **보안**: 실제 서비스에서는 SECRET_KEY를 환경 변수로 관리하고, 충분히 복잡한 값을 사용해야 합니다.

2. **토큰 크기**: JWT 토큰에 많은 데이터를 넣으면 토큰 크기가 커지므로, 필수적인 정보만 포함하는 것이 좋습니다.

3. **리프레시 토큰**: 장기간 사용을 위해 리프레시 토큰 구현을 고려하세요.

4. **오류 처리**: 프론트엔드에서 토큰 만료 시 자동으로 리프레시하는 로직을 구현하는 것이 좋습니다.

## 결론

이 시스템은 JWT를 사용해 사용자 인증과 권한 관리를 효과적으로 구현하고 있습니다. 사용자 설정과 같은 추가 기능을 통해 확장 가능하며, 보안과 성능의 균형을 고려하여 필요에 맞게 조정할 수 있습니다.
