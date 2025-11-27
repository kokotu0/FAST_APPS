from typing import List, Optional
from pydantic import EmailStr
from sqlmodel import Field, SQLModel
from datetime import datetime
from passlib.context import CryptContext

from app.core.model import Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============ 요청 스키마 ============

class UserRegister(SQLModel):
    """회원가입 요청"""
    user_id: str = Field(min_length=4, max_length=50)
    plain_password: str = Field(min_length=8, max_length=40)
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)


class UserUpdate(SQLModel):
    """유저 정보 수정 요청 (관리자용)"""
    email: EmailStr | None = None
    name: str | None = Field(default=None, max_length=100)
    useYN: bool | None = None
    plain_password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    """본인 정보 수정 요청"""
    email: EmailStr | None = None
    name: str | None = Field(default=None, max_length=100)


class UpdatePassword(SQLModel):
    """비밀번호 변경 요청"""
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# ============ DB 모델 ============

class UserBase(SQLModel):
    user_id: str = Field(unique=True, index=True)
    hashed_password: str
    email: EmailStr = Field(unique=True, index=True)
    name: str
    register_date: datetime = Field(default_factory=datetime.utcnow)
    useYN: bool = Field(default=True)
    is_superuser: bool = Field(default=False)


class User(UserBase, Base, table=True):
    
    @classmethod
    def from_register(cls, register: UserRegister):
        """UserRegister로부터 User 생성"""
        user_data = register.model_dump(exclude={"plain_password"})
        user_data["hashed_password"] = pwd_context.hash(register.plain_password)
        return cls(**user_data)
    
    # def verify_password(self, plain_password: str) -> bool:
    #     """비밀번호 검증"""
    #     return pwd_context.verify(plain_password, self.hashed_password)
    
    # def set_password(self, plain_password: str) -> None:
    #     """비밀번호 설정"""
    #     self.hashed_password = pwd_context.hash(plain_password)


# ============ 응답 스키마 ============

class UserOut(SQLModel):
    """유저 공개 정보 응답"""
    idx: int
    user_id: str
    email: EmailStr
    name: str
    register_date: datetime
    useYN: bool
    is_superuser: bool


class UsersPublic(SQLModel):
    """유저 목록 응답"""
    data: list["User"]  # User -> UserOut 자동 변환
    count: int


# ============ 공통 ============

class Message(SQLModel):
    """일반 메시지 응답"""
    message: str
