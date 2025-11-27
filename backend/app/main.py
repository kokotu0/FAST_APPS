import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
import uvicorn
from app.core.internal.utils.utils import regist_all_routers


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    swagger_ui_parameters={
        "docExpansion": "none",  # 모든 엔드포인트를 접힌 상태로 표시
        "defaultModelsExpandDepth": -1,  # 모델 스키마를 접힌 상태로 표시
        "filter": True,  # 검색 필터 활성화
        "persistAuthorization": True,  # 인증 정보 유지
    },
)

app.add_middleware(
CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.0\.129):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # 응답 헤더도 노출
)
# Set all CORS enabled origins
# if settings.all_cors_origins:
#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=settings.all_cors_origins,
#         allow_credentials=True,
#         allow_methods=["*"],
#         allow_headers=["*"],
#     )

app.include_router(api_router, prefix=settings.API_V1_STR)
regist_all_routers(app,base_dir="app/api",pattern=r"routes\.py$")
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
