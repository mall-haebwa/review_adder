#!/usr/bin/env python3
"""리뷰 추가기 서버 실행"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=7000,
        reload=True
    )
