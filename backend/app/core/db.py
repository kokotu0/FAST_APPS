from sqlmodel import Session, create_engine, select

from app.core.config import settings
from app.models.UserModels import User, UserRegister

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        # 초기 슈퍼유저 생성
        user_in = UserRegister(
            user_id="admin",
            email=settings.FIRST_SUPERUSER,
            plain_password=settings.FIRST_SUPERUSER_PASSWORD,
            name="관리자",
        )
        user = User.from_register(user_in)
        user.is_superuser = True  # 슈퍼유저로 설정
        session.add(user)
        session.commit()
        session.refresh(user)
