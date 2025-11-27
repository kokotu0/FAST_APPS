#나중에 user/service에 통합할 것. authenticate.py랑 user랑 관심사가 겹치는 경우가 많네.

from typing import cast
from fastapi import Depends, HTTPException, security, Response
from passlib.context import CryptContext
from sqlmodel import select

from core.database import SessionDep
from models.UserModels import User
from api.user.schemas import UserOut
from api.user.schemas import UserOut
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

import jwt
from datetime import datetime, timedelta
import os
from fastapi.encoders import jsonable_encoder
# 환경 변수로 관리하는 것이 좋습니다
# SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
SECRET_KEY = 'ha2n'
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 7200

oauth2_scheme = security.OAuth2PasswordBearer(tokenUrl="user/swagger-login",)


def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = jsonable_encoder(data)
    current = datetime.utcnow()
    expire = current + timedelta(minutes=expires_delta)
    
    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(current.timestamp()),
        "type": "access"
    })
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def DecodeHashed(Hashed:str) ->dict:
    return jwt.decode(Hashed, key=SECRET_KEY, algorithms=[ALGORITHM])


def EncodeDict(Dictionary:dict) ->str:
    return jwt.encode(Dictionary, key=SECRET_KEY, algorithm=ALGORITHM)

async def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401)
        return payload
    except JWTError:
        raise HTTPException(status_code=401)


# 의존성 함수

async def auth_get_current_user(
    session:SessionDep,
    token: str = Depends(oauth2_scheme),
) -> UserOut:
    if os.getenv('ENVIRONMENT') == 'development':
        user = session.exec(select(User)).first()
        if not user:
            raise HTTPException(status_code=401, detail="존재하지 않는 사용자입니다")
        return UserOut(
            idx=cast(int,user.idx),
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            register_date=user.register_date,
            team=user.team,
            position=user.position,
            useYN=user.useYN
        )
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        token_type = payload.get("type")
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
        try:
            old_payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            new_token_data = {k: v for k, v in old_payload.items() if k not in ['exp', 'iat', 'type']}
            new_token = create_access_token(new_token_data)
            return await auth_get_current_user(session, new_token)
        except Exception as e:
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
        
    return UserOut(
        idx=cast(int,user.idx),
        email=user.email,
        name=user.name,
        position=user.position,
        useYN=user.useYN,
        register_date=user.register_date,
        team=user.team,
        user_id=user.user_id,
    )


# 권한 확인을 위한 추가 의존성
async def get_current_active_user(
    current_user: User = Depends(auth_get_current_user)
) -> User:
    """활성 사용자 확인"""
    if not current_user.useYN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="비활성화된 사용자입니다"
        )
    return current_user

async def get_current_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """관리자 권한 확인"""
    if not current_user.position=='관리자':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )
    return current_user