# 하위 호환성을 위해 app.core.model에서 재export
from app.core.model import Base

__all__ = ["Base"]