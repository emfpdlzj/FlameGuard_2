# main.py
# ──────────────────────────────────────────────────────────────────────────────
# 이 파일은 FastAPI 앱의 엔트리포인트.
# - DB 초기화(Base.metadata.create_all)
# - CORS 설정
# - api/ 하위 라우터를 자동으로 스캔해서 include
# - ./app/log 폴더를 정적 파일로 서빙(/log 경로)
# - lifespan 훅(서버 시작/종료 시점)에서 준비 작업 수행
# ──────────────────────────────────────────────────────────────────────────────

from typing import Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import importlib
import pkgutil  # (현재는 사용 안 하지만, 폴더 내 모듈 탐색 시에 유용)
import sys
import os

# ── [임시 경로 해킹] 부모(backend)를 sys.path에 추가
#   - 'from app.***' 절대 임포트를 가능하게 함
#   - 프로덕션/테스트에선 가급적 PYTHONPATH/패키지 설정으로 대체 권장
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 라우터(직접 임포트한 두 개: 샘플/확인용)
from app.api.create_user.router import router as create_user_router  # (아래 auto include가 이미 포함하므로 필수는 아님)
from app.api.get_test.router import router as get_test_router       # (동일)

# ── DB 연결/모델 메타
from app.db.database import engine, Base
from app.db.models import (
    user as user_model,             # 모델을 임포트해야 metadata에 등록됨
    session as session_model,       # (create_all 전에 반드시 임포트)
    detection_log as detection_log_model,
)

from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager


# ──────────────────────────────────────────────────────────────────────────────
# DB 초기화: 모든 모델의 테이블 생성
#   - Alembic 사용 전 초기 개발 단계에서만 create_all을 사용
#   - 운영 단계에서는 스키마 변경 추적을 위해 Alembic 마이그레이션 권장
# ──────────────────────────────────────────────────────────────────────────────
def init_db():
    Base.metadata.create_all(bind=engine)


# ──────────────────────────────────────────────────────────────────────────────
# lifespan 훅: 앱 시작/종료 시 실행되는 컨텍스트
#   - 여기서는 앱 시작 시점에 DB 초기화만 수행
#   - (필요 시) 모델/캐시/외부 리소스 초기화, 종료 시 정리 코드 추가 가능
# ──────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()        # 앱 시작 시 테이블 생성
    yield            # 여기까지가 "startup", 아래부터가 "shutdown"
    # 종료 시 정리(cleanup) 작업이 필요하면 여기서 수행
    # e.g., close db pools, flush logs, etc.


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI 앱 인스턴스
#   - lifespan으로 startup/shutdown 정의 연결
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(lifespan=lifespan)


# ──────────────────────────────────────────────────────────────────────────────
# CORS 설정
#   - 프런트엔드(예: http://localhost:3000)에서 API 호출을 허용
#   - 개발 초반엔 와일드카드(*)를 쓰되, 운영에선 특정 도메인으로 제한 권장
# ──────────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 예: ["http://localhost:3000"] 로 좁히는 것을 권장
    allow_credentials=True,
    allow_methods=["*"],        # 모든 HTTP 메서드 허용
    allow_headers=["*"],        # 모든 헤더 허용
)


# ──────────────────────────────────────────────────────────────────────────────
# api 폴더 스캔 및 라우터 자동 등록
#   - 디렉터리(app/api/XXX)에 router.py가 있고 내부에 'router' 객체가 있으면 include
#   - 새 엔드포인트 폴더를 만들고 router.py만 두면 자동으로 인식됨
# ──────────────────────────────────────────────────────────────────────────────
api_dir = Path(__file__).parent / "api"  # app/api

for api in api_dir.iterdir():
    if api.is_dir():  # 각 하위 폴더가 하나의 엔드포인트 묶음
        router_module = f"app.api.{api.name}.router"  # 예: app.api.predict_fire.router
        try:
            module = importlib.import_module(router_module)
            if hasattr(module, "router"):
                app.include_router(module.router)
                print(f"✅ router added: {router_module}")  # 디버그 로그
        except ModuleNotFoundError:
            # __pycache__/__init__ 등 라우터가 없는 폴더는 건너뛰기
            if api.name in {"__pycache__", "__init__"}:
                continue
            print(f"⚠️ {router_module} not found (router.py is missing)")


# ──────────────────────────────────────────────────────────────────────────────
# 정적 파일 서빙: ./app/log 폴더를 /log 경로로 제공
#   - 예: http://127.0.0.1:8000/log/파일명.jpg
#   - 라우터에서 결과 이미지를 app/log에 저장하면 프런트에서 접근 가능
# ──────────────────────────────────────────────────────────────────────────────
# 현재 파일(app/main.py) 기준 ./app/log 절대경로 구성
log_directory = os.path.join(os.path.dirname(__file__), "log")

# log 폴더가 없으면 생성
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# /log 경로로 mount: 정적 파일 서버 연결
app.mount("/log", StaticFiles(directory=log_directory), name="log")


# ──────────────────────────────────────────────────────────────────────────────
# (선택) 헬스체크 엔드포인트: 배포/모니터링 용이
#   - 서버/DB 상태 간단 확인용으로 유용
# ──────────────────────────────────────────────────────────────────────────────
# from fastapi import Depends
# from sqlalchemy import text
# from app.db.database import SessionLocal
#
# @app.get("/health")
# def health():
#     try:
#         # 간단한 응답만으로도 충분. 필요하면 DB 핑 추가 가능
#         return {"ok": True}
#     except Exception:
#         return {"ok": False}
