import uuid
from fastapi import APIRouter, HTTPException, File, UploadFile, Depends
from app.api.predict_fire.schema import Detection, PredictFireSchema
from sqlalchemy.orm import Session
from app.db.database import get_db
from datetime import datetime
from ultralytics import YOLO #yolo
import logging # 로그기록 
import shutil
import os
import pytz  # new import #time
import time 
import cv2 #image

from app.api.predict_fire.crud import create_detection_log


router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


def allowed_file(filename: str) -> bool:
    """
    confirm file extension is in ALLOWED_EXTENSIONS
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_random_file_name(filename: str) -> str:
    """
    keep file extension and generate random file name
    """
    _, file_extension = os.path.splitext(filename)
    random_file_name = f"{uuid.uuid4()}{file_extension}"
    return random_file_name


@router.post("/predict_fire", response_model=PredictFireSchema)
async def predict_fire(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    # current_user=Depends(get_current_user),  # get current user info
):
    logger.info("--------------------------------")
    logger.info(f"Received file: {file.filename}")

    # check file extension
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=422,
            detail="unsupported file format. only jpg, jpeg or png are allowed.",
        )

    # generate random file name and set temp directory
    new_file_name = generate_random_file_name(file.filename)
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, new_file_name)

    # save temp file
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except IOError as e:
        logger.error(f"error occurred while saving file: {str(e)}")
        raise HTTPException(status_code=500, detail="failed to save file.")

    # load model
    try:
        model = YOLO("assets/best.pt")  # relative path
        logger.info("model loaded successfully.")
    except Exception as e:
        logger.error(f"error occurred while loading model: {str(e)}")
        raise HTTPException(status_code=500, detail="failed to load model.")

    try:
        # run model
        results = model(temp_file_path)

        result = results[0]
        boxes = result.boxes

        # create annotated image (bounding box)
        annotated_img = result.plot()  # or result.render()

        processed_result = {"file_name": file.filename, "detections": []}
        fire_detected = False  # track fire detection

        # process results: extract class name, confidence, and coordinates for each box
        for box in boxes:
            class_name = model.names[int(box.cls)]
            detection = Detection(
                class_name=class_name,
                confidence=float(box.conf),
                bbox=box.xyxy[0].tolist(),
            )
            processed_result["detections"].append(detection)

            if class_name == "fire":
                fire_detected = True

        # set current time (UTC -> Asia/Seoul)
        utc_now = datetime.now(pytz.UTC)
        korea_timezone = pytz.timezone("Asia/Seoul")
        current_time = utc_now.astimezone(korea_timezone).strftime("%Y-%m-%d %H:%M:%S")

        # create log directory
        log_dir = "log"
        os.makedirs(log_dir, exist_ok=True)

        if fire_detected:
            # save result image when fire is detected
            log_file_path = os.path.join(log_dir, new_file_name)
            cv2.imwrite(log_file_path, annotated_img)

            # upload to S3 or other external storage and get file key (later)
            # result_file_key = uploadImageToAWS.usingFilePath(log_file_path)
            result_file_key = new_file_name  # temporary value

            resResult = {
                "message": "fire detected",
                "file_name": file.filename,
                "detections": processed_result["detections"],
                "result_image": result_file_key,  # S3 파일 키로 변경
                "date": current_time,
            }

            # delete result image (later)
            # if os.path.exists(log_file_path):
            #     try:
            #         os.remove(log_file_path)
            #         logger.info(f"Successfully deleted result file: {log_file_path}")
            #     except Exception as e:
            #         logger.error(f"Failed to delete result file: {str(e)}")
        else:
            resResult = {
                "message": "safe",
                "file_name": None,
                "detections": processed_result["detections"],
                "result_image": None,
                "date": current_time,
            }

        # save detection log
        create_detection_log(db=db, detection_data=resResult)

        logger.info(f"Response result: {resResult}")
        return resResult

    except Exception as e:
        logger.error(f"error occurred while processing image: {str(e)}")
        raise HTTPException(status_code=500, detail="failed to process image.")

    finally:
        logger.info("Cleaning up temporary files.")
        # delete temp file (later)
        # if os.path.exists(temp_file_path):
        #     try:
        #         os.remove(temp_file_path)
        #         logger.info(f"Successfully deleted temp file: {temp_file_path}")
        #     except Exception as e:
        #         logger.error(f"Failed to delete temp file: {str(e)}")
