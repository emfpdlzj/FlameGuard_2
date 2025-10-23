# FlameGuard_2

웹캠/영상 스트림을 이용해 **실시간 화재(불꽃/연기) 감지**를 수행하는 토이 프로젝트입니다.  
YOLOv11 기반 추론(FastAPI) + Next.js 프런트엔드로 구성되며, 감지 로그를 저장/조회할 수 있습니다.

## 주요 기능

* 🔥 YOLOv11로 불꽃/연기 객체 감지 (신뢰도 임계값 설정 가능)
* 🎥 웹캠/비디오 스트림 실시간 처리
* 🗂 감지 결과(시간/신뢰도/스냅샷) 저장 및 로그 페이지 제공

---

## 기술 스택

* **AI/추론**: YOLOv11 (Ultralytics), Roboflow 데이터/모델 관리

  * Ultralytics 문서: [https://docs.ultralytics.com/usage/python](https://docs.ultralytics.com/usage/python)
* **백엔드**: FastAPI, SQLite(+ SQLAlchemy), Pydantic, Argon2
* **프런트엔드**: Next.js, TanStack Query, pnpm
* **환경**: Conda

---

## 프로젝트 구조

```
FlameGuard_2/
├─ backend/
│  ├─ app/
│  │  ├─ main.py             # FastAPI 엔트리포인트
│  │  ├─ routers/            # 엔드포인트 라우터
│  │  ├─ schemas/            # Pydantic 모델 (입출력/검증)
│  │  ├─ crud/               # DB CRUD 로직
│  │  ├─ models.py           # SQLAlchemy 모델
│  │  ├─ deps.py             # DI, 공통 의존성
│  │  └─ services/           # YOLO 추론, 보안(Argon2) 등
│  └─ db.sqlite3
└─ frontend/
   ├─ (Next.js 프로젝트 파일들)
   └─ public/
```

## Conda / 유틸 메모

```bash
# conda
conda env list
conda info --envs
conda remove --name flameguard --all

# yolo 환경 전환
conda activate flameguard
conda deactivate

# fastapi
fastapi dev app/main.py
```

--

## Reference

* 원 프로젝트(아이디어/구조): [https://github.com/nohsangwoo/FlameGuard](https://github.com/nohsangwoo/FlameGuard)

---

## 향후 개선 / TODO

1. 화재 감지 **로그 페이지 → Home 이동 버튼** 추가
2. **감지 민감도 설정** 개선: **0.7 이하 무시**(백엔드/프런트 동시 반영)
3. **CSS 스타일 개선**(다크/라이트 테마, 버튼/테이블 폴리시 정리)
