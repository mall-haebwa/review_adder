"""
리뷰 추가기 API 서버
FastAPI 기반 백엔드
"""

import uuid
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

import boto3
from botocore.config import Config
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB 설정
MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "ecommerce")
REVIEWS_COL = "reviews"

# AWS S3 설정
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_REGION = os.getenv("AWS_S3_REGION", "ap-northeast-2")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")

# S3 클라이언트
s3_client = None
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_S3_REGION,
        config=Config(signature_version="s3v4")
    )

# 전역 DB 클라이언트
db_client: Optional[AsyncIOMotorClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_client
    db_client = AsyncIOMotorClient(MONGO_URL)
    yield
    db_client.close()


app = FastAPI(
    title="리뷰 추가기 API",
    description="리뷰 등록을 위한 API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic 모델
class ReviewCreate(BaseModel):
    product_id: str = Field(..., alias="productId", min_length=1)
    rating: float = Field(..., ge=0.5, le=5)
    user_name: str = Field(..., alias="userName", min_length=1)
    content: Optional[str] = Field(default="", max_length=2000)
    images: Optional[list[str]] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        # 0.5 단위로 반올림
        return round(v * 2) / 2


class ReviewResponse(BaseModel):
    success: bool
    review_id: Optional[str] = Field(None, alias="reviewId")
    message: str

    model_config = {"populate_by_name": True}


class ImageUploadResponse(BaseModel):
    success: bool
    url: Optional[str] = None
    message: str


def get_db():
    return db_client[DB_NAME]


@app.post("/api/upload/image", response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...), product_id: str = ""):
    """이미지 S3 업로드"""
    if not s3_client:
        raise HTTPException(status_code=500, detail="S3 설정이 되어있지 않습니다")

    if not product_id:
        return ImageUploadResponse(success=False, message="상품 ID가 필요합니다")

    # 파일 확장자 검증
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        return ImageUploadResponse(
            success=False,
            message=f"허용되지 않는 파일 형식입니다. ({', '.join(allowed_extensions)})"
        )

    # 파일 크기 제한 (10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        return ImageUploadResponse(success=False, message="파일 크기는 10MB 이하여야 합니다")

    # S3 경로 생성
    file_name = f"{uuid.uuid4()}{file_ext}"
    s3_key = f"reviews/{product_id}/{file_name}" if product_id else f"reviews/{file_name}"

    try:
        # S3 업로드
        content_type = file.content_type or "image/jpeg"
        s3_client.put_object(
            Bucket=AWS_S3_BUCKET_NAME,
            Key=s3_key,
            Body=contents,
            ContentType=content_type
        )

        # URL 생성
        url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_S3_REGION}.amazonaws.com/{s3_key}"

        return ImageUploadResponse(success=True, url=url, message="업로드 완료")

    except Exception as e:
        return ImageUploadResponse(success=False, message=f"업로드 실패: {str(e)}")


@app.post("/api/reviews", response_model=ReviewResponse)
async def create_review(review: ReviewCreate):
    """리뷰 등록"""
    db = get_db()

    review_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"

    new_review = {
        "reviewId": review_id,
        "productId": review.product_id,
        "userId": None,
        "userName": review.user_name,
        "rating": review.rating,
        "content": review.content or "",
        "images": review.images or [],
        "createdAt": now,
        "updatedAt": now,
        "helpful": 0,
        "helpfulUsers": [],
        "status": "active"
    }

    result = await db[REVIEWS_COL].insert_one(new_review)

    if result.inserted_id:
        return ReviewResponse(
            success=True,
            review_id=review_id,
            message="리뷰가 등록되었습니다"
        )

    return ReviewResponse(success=False, message="리뷰 저장에 실패했습니다")


# 정적 파일 서빙 (프론트엔드)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)
