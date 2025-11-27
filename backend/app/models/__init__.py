from os.path import dirname, basename, isfile, join
import glob

# 현재 디렉토리의 모든 .py 파일을 가져옴
modules = glob.glob(join(dirname(__file__), "*.py"))

# __init__.py를 제외한 모든 .py 파일들
__all__ = [
    basename(f)[:-3] for f in modules
    if isfile(f) and not f.endswith('__init__.py')
]

from .FormModels import *
from .UserModels import *





# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)
