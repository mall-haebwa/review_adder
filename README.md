# 리뷰 추가기

상품 리뷰를 등록하는 웹 도구입니다.

## 기능

- 상품 ID 기반 리뷰 등록
- 평점 0.5 ~ 5점 (0.5 단위)
- 이미지 업로드 (S3, 최대 5장)
- 이미지 붙여넣기 업로드 (Ctrl+V)
- 랜덤 이름 생성기 (토글 모드)
- 최근 등록 리뷰 확인

## 설치

```bash
# 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 수정
```

## 환경 변수

```
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=ecommerce_ai

AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_S3_REGION=ap-northeast-2
AWS_S3_BUCKET_NAME=your_bucket_name
```

## 실행

```bash
python run.py
```

http://localhost:7000 에서 접속

## API

### POST /api/reviews
리뷰 등록

```json
{
  "productId": "상품ID",
  "rating": 5,
  "userName": "작성자",
  "content": "리뷰 내용 (선택)",
  "images": ["이미지URL"]
}
```

### POST /api/upload/image
이미지 S3 업로드

- `file`: 이미지 파일
- `product_id`: 상품 ID (query parameter)
