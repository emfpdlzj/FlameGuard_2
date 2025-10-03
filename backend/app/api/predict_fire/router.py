# app/api/predict_fire/router.py
# ──────────────────────────────────────────────────────────────────────────────
# 이 파일은 FastAPI의 APIRouter를 사용해 /predict_fire 엔드포인트를 정의한다.
# 주요 기능:
#   1) 업로드된 이미지(카메라 프레임)를 임시 저장
#   2) YOLO 가중치(best.pt)를 로드 후 추론
#   3) 결과(불 검출 여부, 바운딩박스 등)와 시간을 JSON으로 응답
#   4) 필요 시 어노테이션 이미지를 ./log에 저장
#   5) DB에 탐지 로그를 저장
# ──────────────────────────────────────────────────────────────────────────────

import uuid
from fastapi import (
    APIRouter,
    HTTPException,
    File,
    UploadFile,
    Depends,
)  # FastAPI 라우터/의존성/예외/파일 타입
from app.api.predict_fire.schema import (
    Detection,
    PredictFireSchema,
)  # 응답/내부 사용 스키마 (Pydantic)
from sqlalchemy.orm import Session  # DB 세션 타입 힌트
from app.db.database import get_db  # FastAPI 의존성으로 주입할 DB 세션 팩토리
from datetime import datetime
from ultralytics import YOLO  # YOLO 모델 로더 (ultralytics 패키지)
from pathlib import Path
import logging  # 로그 출력
import shutil  # 파일 복사/이동 등
import os
import pytz  # 타임존 처리(Asia/Seoul)
import time
import cv2  # OpenCV (이미지 저장/그리기)

from app.api.predict_fire.crud import (
    create_detection_log,
)  # DB에 탐지 로그 저장하는 함수

# APIRouter 인스턴스 생성:
#   - prefix / tags 등은 여기서 설정 가능(지금은 main.py에서 include_router로 경로가 붙음)
router = APIRouter()

# 로깅 설정 (INFO 이상 콘솔 출력)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 허용할 파일 확장자 집합
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

# 현재 파일(=router.py) 기준 경로 계산
# __file__ → .../app/api/predict_fire/router.py
# parents[2] → .../app
APP_DIR = Path(__file__).resolve().parents[2]  # .../backend/app

# YOLO 가중치 파일 절대경로(프로젝트 내 고정 위치)
WEIGHTS = APP_DIR / "assets" / "best.pt"  # .../backend/app/assets/best.pt


def allowed_file(filename: str) -> bool:
    """
    파일명에서 확장자를 뽑아 허용 목록에 있는지 점검.
    - 보안/유효성 검사의 최소 단계. (MIME 타입 검증은 추가 고려 여지)
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_random_file_name(filename: str) -> str:
    """
    원래 확장자를 유지하면서 UUID로 랜덤 파일명을 생성.
    - 임시/로그 파일 충돌 방지.
    """
    _, file_extension = os.path.splitext(filename)
    random_file_name = f"{uuid.uuid4()}{file_extension}"
    return random_file_name


@router.post("/predict_fire", response_model=PredictFireSchema)
async def predict_fire(
    file: UploadFile = File(...),  # multipart/form-data 필드명 'file'로 업로드
    db: Session = Depends(get_db),  # DB 세션을 FastAPI 의존성으로 주입
    # current_user=Depends(get_current_user),  # 인증/인가가 필요한 경우 사용
):
    """
    업로드된 이미지를 받아 YOLO로 불 탐지 → 결과/로그 저장 후 JSON 반환.
    응답 형식은 PredictFireSchema로 검증된다.
    """
    logger.info("--------------------------------")
    logger.info(f"Received file: {file.filename}")

    # 1) 파일 확장자 유효성 검증 (간단한 1차 필터)
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=422,
            detail="unsupported file format. only jpg, jpeg or png are allowed.",
        )

    # 2) 임시 저장 경로 준비 (상대경로 'temp' → 실행 위치에 의존)
    #    - 실행 디렉터리가 바뀌면 경로가 바뀔 수 있음(절대경로 사용 권장)
    new_file_name = generate_random_file_name(file.filename)
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, new_file_name)

    # 3) 업로드 파일을 디스크로 저장
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(
                file.file, buffer
            )  # 스트림을 직접 복사 (대용량에서도 효율적)
    except IOError as e:
        logger.error(f"error occurred while saving file: {str(e)}")
        raise HTTPException(status_code=500, detail="failed to save file.")

    # 4) 모델 로드
    #    - 현재는 요청마다 로드 → 느릴 수 있음.
    #    - 개선: 모듈 전역에서 한 번만 로드하고 여기선 재사용 권장.
    try:
        model = YOLO(str(WEIGHTS))  # 절대 경로로 지정해 실행 위치에 상관없이 동작
        logger.info("model loaded successfully.")
    except Exception as e:
        logger.error(f"error occurred while loading model: {str(e)}")
        raise HTTPException(status_code=500, detail="failed to load model.")

    try:
        # 5) 추론 수행
        #    - model() 호출은 이미지 경로/배열을 받아 결과 리스트 반환
        results = model(temp_file_path)

        # 6) 1장 처리 가정 (YOLO 결과는 리스트 형태)
        result = results[0]
        boxes = result.boxes  # 탐지된 박스/클래스/점수 등이 들어있는 컨테이너

        # 7) 어노테이션 이미지 생성 (바운딩박스/라벨 그려진 프레임)
        annotated_img = result.plot()  # ndarray(BGR) 반환. (result.render()도 유사)

        # 8) 응답 페이로드 초기화
        processed_result = {"file_name": file.filename, "detections": []}
        fire_detected = False  # 불 검출 여부 플래그

        # 9) 탐지 결과 순회: 클래스/점수/좌표 추출 → Detection 스키마로 래핑
        for box in boxes:
            class_name = model.names[int(box.cls)]  # 클래스 인덱스 → 이름 맵핑
            detection = Detection(
                class_name=class_name,
                confidence=float(box.conf),  # tensor → float
                bbox=box.xyxy[0].tolist(),  # [x1,y1,x2,y2] 리스트로 변환
            )
            processed_result["detections"].append(detection)

            if class_name == "fire":
                fire_detected = True

        # 10) 시간: UTC → Asia/Seoul 로 변환 후 문자열 포맷
        utc_now = datetime.now(pytz.UTC)
        korea_timezone = pytz.timezone("Asia/Seoul")
        current_time = utc_now.astimezone(korea_timezone).strftime("%Y-%m-%d %H:%M:%S")

        # 11) 로그 디렉터리 준비 (현재는 상대경로 'log')
        #     - ./app/log로 고정하려면 APP_DIR / "log" 절대경로를 사용하는 게 안전
        #       e.g., log_dir = str(APP_DIR / "log")
        log_dir = "log"
        os.makedirs(log_dir, exist_ok=True)

        if fire_detected:
            # 12) 불이 검출된 경우: 어노테이션 이미지를 로그에 저장
            log_file_path = os.path.join(log_dir, new_file_name)
            cv2.imwrite(log_file_path, annotated_img)  # BGR ndarray를 파일로 저장

            # 13) (향후) S3 등 외부 저장소에 업로드 후 키를 사용
            #     현재는 파일명만 키처럼 사용
            result_file_key = new_file_name

            resResult = {
                "message": "fire detected",
                "file_name": file.filename,
                "detections": processed_result[
                    "detections"
                ],  # Detection[] (Pydantic이 직렬화)
                "result_image": result_file_key,  # 저장 파일명 or S3 키
                "date": current_time,
            }

            # (선택) 결과 파일 즉시 삭제 로직은 주석 처리됨
        else:
            # 14) 불이 없으면 안전 메시지/이미지 없음
            resResult = {
                "message": "safe",
                "file_name": None,
                "detections": processed_result["detections"],
                "result_image": None,
                "date": current_time,
            }

        # 15) DB에 탐지 로그 저장
        #     - create_detection_log는 스키마 dict를 받아 세션으로 저장하는 함수로 가정
        create_detection_log(db=db, detection_data=resResult)

        logger.info(f"Response result: {resResult}")
        return resResult  # FastAPI가 PredictFireSchema에 맞춰 검증/직렬화

    except Exception as e:
        # 추론/후처리 단계에서 발생한 모든 예외를 500으로 변환
        logger.error(f"error occurred while processing image: {str(e)}")
        raise HTTPException(status_code=500, detail="failed to process image.")

    finally:
        # 16) 리소스 정리 단계 (현재는 로그만)
        logger.info("Cleaning up temporary files.")
        # 주석 해제 시 임시 파일 삭제 가능
        # if os.path.exists(temp_file_path):
        #     try:
        #         os.remove(temp_file_path)
        #         logger.info(f"Successfully deleted temp file: {temp_file_path}")
        #     except Exception as e:
        #         logger.error(f"Failed to delete temp file: {str(e)}")
