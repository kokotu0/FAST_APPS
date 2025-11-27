import subprocess

from core.events.app import SessionApplication
from core.internal.utils import get_file_hash
import models as M
from core.internal.ts_generator import Generate_TsFile, Generate_specific_TsFile
import os
import asyncio

# async def setup_state(app):
#     with Session(engine) as session:  # 직접 세션 생성
#         result = session.execute(select(M.ProductCategory))
#         app.state.categories = result.scalars().all()
result = subprocess.run(
    [".venv/Scripts/python", "script.py"],
    capture_output=True,
    text=True,
    cwd=".",  # 작업 디렉토리
)

import logging
logger = logging.getLogger(__name__)
async def startup_event(app):
    # await setup_state(app)
    ts_path = "../new-front/src/api"
    if not os.path.exists("models/EventModels.py"):
        SessionApplication.write_event_model()
    if get_file_hash(SessionApplication.event_model_definition()) != get_file_hash(
        open("models/EventModels.py", "r").read()
    ):
        SessionApplication.write_event_model()
    Generate_TsFile(ts_path)
    Generate_specific_TsFile(ts_path=ts_path)
    logger.info("TsFile Generated")
    with open("requirements.txt", "r") as f:
        requirements = f.read()
        result = subprocess.run(
            ["pip", "freeze"], capture_output=True, text=True, cwd="."  # 작업 디렉토리
        )
        if requirements != result.stdout:
            with open("requirements.txt", "w") as f:
                logger.info(f"requirements.txt updated")
                f.write(result.stdout)


if __name__ == "__main__":
    asyncio.run(startup_event(None))
