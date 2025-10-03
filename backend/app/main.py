# backend/app/main.py
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.create_user.router import router as create_user_router
from app.api.get_test.router import router as get_test_router

from app.db.database import engine, Base

# 테이블 생성 시 메타데이터에 모델이 등록되도록 import
# 1) models/__init__.py 안에서 user, session, detection_log를 import하는 방식이면:
# from app.db import models  # noqa: F401

# 2) 아니면 명시적으로 각각 임포트:
from app.db.models import (
    user as user_model,
    session as session_model,
    detection_log as detection_log_model,
)
from fastapi.staticfiles import StaticFiles


def init_db():
    Base.metadata.create_all(bind=engine)


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}
