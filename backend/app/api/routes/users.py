from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.core.config import settings
from app.models.UserModels import (
    Message,
    UpdatePassword,
    User,
    UserOut,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.utils import generate_new_account_email, send_email

router = APIRouter(prefix="/users", tags=["users"])


# ============ 회원가입 (비로그인) ============

@router.post("/signup", response_model=UserOut)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    회원가입 (로그인 불필요)
    """
    # 이메일 중복 확인
    existing_email = session.exec(
        select(User).where(User.email == user_in.email)
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="이미 등록된 이메일입니다.",
        )
    
    # user_id 중복 확인
    existing_user_id = session.exec(
        select(User).where(User.user_id == user_in.user_id)
    ).first()
    if existing_user_id:
        raise HTTPException(
            status_code=400,
            detail="이미 사용 중인 아이디입니다.",
        )

    user = User.from_register(user_in)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return user


# ============ 본인 정보 관리 ============

@router.get("/me", response_model=UserOut)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    현재 로그인한 유저 정보 조회
    """
    return current_user


@router.patch("/me", response_model=UserOut)
def update_user_me(
    *,
    session: SessionDep,
    user_in: UserUpdateMe,
    current_user: CurrentUser,
) -> Any:
    """
    본인 정보 수정
    """
    if user_in.email:
        existing_user = session.exec(
            select(User).where(User.email == user_in.email)
        ).first()
        if existing_user and existing_user.idx != current_user.idx:
            raise HTTPException(
                status_code=409,
                detail="이미 사용 중인 이메일입니다.",
            )
    
    update_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(update_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return current_user


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *,
    session: SessionDep,
    body: UpdatePassword,
    current_user: CurrentUser,
) -> Any:
    """
    본인 비밀번호 변경
    """
    if not current_user.verify_password(body.current_password):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 일치하지 않습니다.")
    
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400,
            detail="새 비밀번호는 현재 비밀번호와 달라야 합니다.",
        )
    
    current_user.set_password(body.new_password)
    session.add(current_user)
    session.commit()
    
    return Message(message="비밀번호가 변경되었습니다.")


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    본인 계정 삭제
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="관리자 계정은 본인이 삭제할 수 없습니다.",
        )
    
    session.delete(current_user)
    session.commit()
    
    return Message(message="계정이 삭제되었습니다.")


# ============ 관리자 전용 API ============

@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    유저 목록 조회 (관리자 전용)
    """
    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = select(User).offset(skip).limit(limit)
    users = list(session.exec(statement).all())

    return UsersPublic(data=users, count=count)


@router.post(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserOut,
)
def create_user(*, session: SessionDep, user_in: UserRegister) -> Any:
    """
    새 유저 생성 (관리자 전용)
    """
    # 이메일 중복 확인
    existing_email = session.exec(
        select(User).where(User.email == user_in.email)
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="이미 등록된 이메일입니다.",
        )
    
    # user_id 중복 확인
    existing_user_id = session.exec(
        select(User).where(User.user_id == user_in.user_id)
    ).first()
    if existing_user_id:
        raise HTTPException(
            status_code=400,
            detail="이미 사용 중인 아이디입니다.",
        )

    user = User.from_register(user_in)
    session.add(user)
    session.commit()
    session.refresh(user)

    # 이메일 발송
    if settings.emails_enabled:
        email_data = generate_new_account_email(
            email_to=user_in.email,
            username=user_in.user_id,
            password=user_in.plain_password,
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    
    return user


@router.get(
    "/{user_idx}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserOut,
)
def read_user_by_idx(user_idx: int, session: SessionDep) -> Any:
    """
    특정 유저 조회 (관리자 전용)
    """
    user = session.get(User, user_idx)
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")
    return user


@router.patch(
    "/{user_idx}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserOut,
)
def update_user(
    *,
    session: SessionDep,
    user_idx: int,
    user_in: UserUpdate,
) -> Any:
    """
    유저 정보 수정 (관리자 전용)
    """
    db_user = session.get(User, user_idx)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="유저를 찾을 수 없습니다.",
        )
    
    # 이메일 중복 확인
    if user_in.email:
        existing_user = session.exec(
            select(User).where(User.email == user_in.email)
        ).first()
        if existing_user and existing_user.idx != user_idx:
            raise HTTPException(
                status_code=409,
                detail="이미 사용 중인 이메일입니다.",
            )

    # 업데이트 적용
    update_data = user_in.model_dump(exclude_unset=True, exclude={"plain_password"})
    
    # 비밀번호 변경 처리
    if user_in.plain_password:
        db_user.set_password(user_in.plain_password)
    
    db_user.sqlmodel_update(update_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    return db_user


@router.delete(
    "/{user_idx}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def delete_user(
    session: SessionDep,
    current_user: CurrentUser,
    user_idx: int,
) -> Message:
    """
    유저 삭제 (관리자 전용)
    """
    user = session.get(User, user_idx)
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")
    if user.idx == current_user.idx:
        raise HTTPException(
            status_code=403,
            detail="본인 계정은 삭제할 수 없습니다.",
        )
    
    session.delete(user)
    session.commit()
    return Message(message="유저가 삭제되었습니다.")
