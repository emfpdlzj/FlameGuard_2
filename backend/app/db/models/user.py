import random
import string
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship
import pytz
from datetime import datetime
from app.db.database import Base

# user models/: 데이터베이스 모델을 정의합니다.

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True) # 사용자 이름
    password = Column(String) # 비밀번호
    count_login = Column(Integer, default=0) # 로그인 횟수
    validation_number = Column(String, default=lambda: ''.join(random.choices(string.digits, k=6))) # 이메일 인증 번호 랜덤한 6자리 기본값
    verified = Column(Boolean, default=False) # 이메일 인증 여부
    role = Column(String) # 권한
    plan = Column(String) # 플랜
    created_at = Column(DateTime(timezone=True), 
                       default=lambda: datetime.now(pytz.timezone('Asia/Seoul')))
    expired_at = Column(DateTime(timezone=True)) # 서비스 만료일

    # DetectionLog와의 관계 설정
    # detection_logs = relationship("DetectionLog", back_populates="user")
