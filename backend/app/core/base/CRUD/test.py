"""
CRUD Service 및 Nested Handler 테스트
SQLite 인메모리 DB를 사용한 통합 테스트
이 파일은 완전히 독립적으로 CRUDService를 테스트합니다.
"""

import json
import logging
import pprint
import random
from deepdiff import DeepDiff, Delta
from deepdiff.helper import JSON
import pytest
from datetime import datetime
from typing import List, Optional, cast
from sqlmodel import SQLModel, Field, Relationship, Session, create_engine, select
from sqlalchemy import Engine

from api.user.schemas import UserOut
from core.base.CRUD.service import CRUDService
from core.base.CRUD.nested_handler import NestedRelationshipHandler
from core.base.comparator import ModelComparator
from core.base.model import Base
from models.CommonCodeModels import CommonCode
from core.internal.log_config import format_model

logger = logging.getLogger(__name__)
# Faker 로거 비활성화
logging.getLogger("faker").setLevel(logging.WARNING)
logger.setLevel(logging.DEBUG)

# ============================================================================
# 테스트용 Mock User (fixture용 - CRUDService에 전달할 사용자 객체)
# ============================================================================


# ============================================================================
# 테스트 전용 독립 모델 정의 (SQLModel 방식)
# ============================================================================


# --- Author 모델 ---
class AuthorBase(SQLModel):
    """Author 베이스 스키마"""

    name: str
    email: str


class Author(AuthorBase, Base, table=True):
    articles: List["Article"] = Relationship(back_populates="author")


class AuthorRequest(AuthorBase):
    """Author 생성/수정 요청 스키마"""

    articles: List["ArticleRequest"] = []


class AuthorResponse(AuthorBase, Base):
    """Author 응답 스키마"""

    articles: List["ArticleResponse"]


# --- Article 모델 ---
class ArticleBase(SQLModel):
    """Article 베이스 스키마"""

    title: str
    content: str


class ArticleTemplate(ArticleBase, Base):
    deleted: bool = Field(default=False)
    pass


class Article(ArticleTemplate, table=True):

    author_idx: Optional[int] = Field(
        default=None, foreign_key="author.idx", ondelete="CASCADE"
    )
    author: Author = Relationship(back_populates="articles")


class ArticleRequest(ArticleBase):
    """Article 생성/수정 요청 스키마"""


class ArticleResponse(ArticleTemplate):
    """Article 응답 스키마"""


# ============================================================================
# Pytest Fixtures
# ============================================================================

import os

db_path = os.path.join(os.path.dirname(__file__), "test.db")


@pytest.fixture
def engine():
    """SQLite 인메모리 엔진 생성 (상대경로 사용 가능)"""

    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def fake_AuthorRequest(fake_ArticleRequest):
    from faker import Faker

    fake = Faker(locale="ko_KR")
    fake_ArticleRequest = [
        ArticleRequest(
            title=fake.sentence(),
            content=fake.text(),
        )
        for i in range(3)
    ]
    return AuthorRequest(
        name=fake.name(),
        email=fake.email(),
        articles=fake_ArticleRequest,
    )


from faker import Faker


@pytest.fixture
def fake_ArticleRequest():

    fake = Faker("ko_KR")
    return ArticleRequest(
        title=fake.sentence(),
        content=fake.text(),
    )


def fakeArticleRequest_generator():
    Faker.seed(random.randint(1, 1000000))
    fake = Faker("ko_KR")

    def generator():
        while True:
            yield ArticleRequest(
                title=fake.sentence(),
                content=fake.text(max_nb_chars=20),
            )

    return next(generator())


@pytest.fixture
def session(engine):
    """테스트 세션 생성"""
    with Session(engine, autocommit=False) as session:
        try:
            yield session
            logger.warning("session commit")
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


@pytest.fixture
def mock_user() -> UserOut:
    """테스트용 Mock 사용자 (created_by, updated_by에 사용)"""
    return UserOut(
        idx=999,
        user_id="test_user",
        name="테스트사용자",
        email="test@example.com",
        register_date=datetime.now(),
        team=CommonCode(idx=1, path="USER/TEAM/ADMIN", code="ADMIN", name="ADMIN"),
        position=CommonCode(
            idx=1, path="USER/POSITION/ADMIN", code="ADMIN", name="ADMIN"
        ),
        useYN=True,
    )


@pytest.fixture
def author_service():
    """Author CRUD 서비스 (관계별 키 필드 설정 포함)"""
    return CRUDService[Author, AuthorRequest, AuthorResponse](
        Author,
        AuthorRequest,
        AuthorResponse,
        # articles 관계에 대한 키 필드 및 제외 필드 설정
        relationship_key_fields={"articles": {"title"}},
    )


@pytest.fixture
def article_service():
    """Article CRUD 서비스"""
    return CRUDService[Article, ArticleRequest, ArticleResponse](
        Article,
        ArticleRequest,
        ArticleResponse,  # is_soft_delete=True
    )


@pytest.fixture
def test_author_idx(
    session: Session,
    author_service: CRUDService[Author, AuthorRequest, AuthorResponse],
    mock_user: UserOut,
) -> int:
    return 1


@pytest.fixture
def test_author_idx_get(
    session: Session,
    author_service: CRUDService[Author, AuthorRequest, AuthorResponse],
    mock_user: UserOut,
) -> AuthorResponse:
    author = author_service.get_by_idx(session, mock_user, 1)
    return author


# ============================================================================
# 테스트 클래스
# ============================================================================


class TestCrud:
    def test_crud_service_settings(
        self,
        session: Session,
        author_service: CRUDService[Author, AuthorRequest, AuthorResponse],
        mock_user: UserOut,
    ):
        author_service = CRUDService[Author, AuthorRequest, AuthorResponse](
            Author,
            AuthorRequest,
            AuthorResponse,
            relationship_key_fields={"articles": {"title"}},
            relationship_deleted_columns={"articles": "deleted"},
        )
        assert author_service.is_soft_delete == True
        logger.debug(
            f"author_service.relationship_deleted_columns: {author_service.relationship_deleted_columns}"
        )

    def test_create_nested(
        self,
        session: Session,
        author_service: CRUDService[Author, AuthorRequest, AuthorResponse],
        mock_user: UserOut,
        fake_AuthorRequest: AuthorRequest,
    ):
        author_request = fake_AuthorRequest
        logger.debug(f"author_request: {author_request}")
        author_response = author_service.post(session, author_request, mock_user)
        assert author_response.idx is not None
        return author_response

    @pytest.mark.skip(reason="get_nested ->  정상작동확인.")
    def test_get_nested(
        self,
        session: Session,
        author_service: CRUDService[Author, AuthorRequest, AuthorResponse],
        mock_user: UserOut,
    ):
        author = author_service.get_by_idx(session, mock_user, 1)
        logger.debug(f"author: {author}")
        assert author.idx is not None
        return author

    def test_update_not_changed(
        self,
        session: Session,
        author_service: CRUDService[Author, AuthorRequest, AuthorResponse],
        mock_user: UserOut,
        test_author_idx_get: AuthorResponse,
    ):
        """중첩 관계 업데이트 테스트: Article 추가"""

        # 1. 기존 Author 조회
        created_author = test_author_idx_get

        assert created_author.idx is not None

        Not_Changed_Author_Request = AuthorRequest(
            name=created_author.name,
            email=created_author.email,
            articles=[
                ArticleRequest(title=article.title, content=article.content)
                for article in created_author.articles
                if not article.deleted
            ],
        )
        logger.debug(f"Not_Changed_Author_Request: {Not_Changed_Author_Request}")
        from core.base.comparator.compartor import ModelComparator

        origin_articles = [
            ArticleRequest(title=article.title, content=article.content)
            for article in created_author.articles
            if not article.deleted
        ]
        comparator = ModelComparator[ArticleRequest](
            origin_articles,
            Not_Changed_Author_Request.articles,
        )
        logger.debug(f"comparator: {comparator.result}")
        assert comparator.has_changes == False
        assert comparator.unchanged.__len__() == 3

        updated_author = author_service.put(
            session, created_author.idx, Not_Changed_Author_Request, mock_user
        )

    def test_update_nested_add(
        self,
        session: Session,
        author_service: CRUDService[Author, AuthorRequest, AuthorResponse],
        mock_user: UserOut,
        test_author_idx: int,
        test_author_idx_get: AuthorResponse,
        fake_ArticleRequest: ArticleRequest,
    ):
        """중첩 관계 업데이트 테스트: Article 추가"""
        original_author = test_author_idx_get
        original_articles = [
            ArticleRequest(title=article.title, content=article.content)
            for article in original_author.articles
            if not article.deleted
        ]
        logger.debug(original_articles)
        new_articles = [
            *original_articles,
            fakeArticleRequest_generator(),
        ]
        logger.debug(new_articles)
        AuthorRequest_Add = AuthorRequest(
            name=original_author.name,
            email=original_author.email,
            articles=[
                *new_articles,
            ],
        )
        updated_author = author_service.put(
            session, test_author_idx, AuthorRequest_Add, mock_user
        )
        logger.debug(f"updated_author: {format_model(updated_author)}")

    def test_update_nested_remove(
        self,
        session: Session,
        author_service: CRUDService[Author, AuthorRequest, AuthorResponse],
        mock_user: UserOut,
        test_author_idx: int,
    ):
        """중첩 관계 업데이트 테스트: Article 제거"""

        # 1. 기존 Author 조회

        original_author = author_service.get_by_idx(session, mock_user, test_author_idx)
        original_articles = [
            ArticleRequest(title=article.title, content=article.content)
            for article in original_author.articles
            if not article.deleted
        ]
        AuthorRequest_Remove = AuthorRequest(
            name=original_author.name,
            email=original_author.email,
            articles=[
                *original_articles[:-1],
            ],
        )
        updated_author = author_service.put(
            session, test_author_idx, AuthorRequest_Remove, mock_user
        )

        comparator = ModelComparator[ArticleRequest](
            original_articles,
            AuthorRequest_Remove.articles,
        )
        logger.debug(f"comparator: {comparator.pretty()}")
        assert len(comparator.modified) == 0
        # logger.debug(f"updated_author: {format_model(updated_author)}")

        # session.rollback()

    def test_update_nested_modify(
        self,
        session: Session,
        author_service: CRUDService[Author, AuthorRequest, AuthorResponse],
        mock_user: UserOut,
        test_author_idx: int,
        test_author_idx_get: AuthorResponse,
    ):
        """중첩 관계 업데이트 테스트: Article 내용 변경"""

        # 1. 기존 Author 조회
        original_author = test_author_idx_get

        # 2. Article 내용 변경 (개수는 동일하지만 content 수정)
        logger.info("=== Article 내용 변경 테스트 ===")
        original_articles = [
            ArticleRequest(title=article.title, content=article.content)
            for article in original_author.articles
            if not article.deleted
        ]
        modified_article = ArticleRequest(
            title=original_author.articles[-1].title,
            content=fakeArticleRequest_generator().content,
        )
        original_articles.pop(-1)
        update_request = AuthorRequest(
            name=original_author.name,
            email=original_author.email,
            articles=[
                *original_articles,
                modified_article,
            ],
        )

        updated_author = author_service.put(
            session, test_author_idx, update_request, mock_user
        )

        # 검증: 여전히 3개이지만 내용이 변경되어야 함
    def test_update_nested_multiple(
        self,
        session: Session,
        author_service: CRUDService[Author, AuthorRequest, AuthorResponse],
        mock_user: UserOut,
        test_author_idx: int,
        test_author_idx_get: AuthorResponse,
    ):
        """중첩 관계 업데이트 테스트: Article  추가, 삭제, 수정"""
        original_author = test_author_idx_get
        original_articles = [
            ArticleRequest(title=article.title, content=article.content)
            for article in original_author.articles
            if not article.deleted
        ]
        new_articles = [
            fakeArticleRequest_generator(),
        ]
        modified_article = [ArticleRequest(
            title=original_author.articles[-1].title,
            content=fakeArticleRequest_generator().content,
        )]
        
        update_request = AuthorRequest(
            name=original_author.name,
            email=original_author.email,
            articles=[
                *new_articles,
                *modified_article,
            ],
        )
        updated_author = author_service.put(
            session, test_author_idx, update_request, mock_user
        )
        logger.debug(f"updated_author: {format_model(updated_author)}")
    @pytest.mark.skip(reason="미구현.")
    def test_delete_nested(
        self,
        session: Session,
        author_service: CRUDService[Author, AuthorRequest, AuthorResponse],
        mock_user: UserOut,
        fake_AuthorRequest: AuthorRequest,
    ):
        author_request = fake_AuthorRequest
        logger.debug(f"author_request: {author_request}")


# ============================================================================
# 테스트 실행
# ============================================================================

if __name__ == "__main__":
    import os

    os.system(f"python -m pytest {__file__} -v -s")
