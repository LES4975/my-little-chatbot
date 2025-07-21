#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
라즈베리파이 FastAPI 서버 메인 실행 파일
GPIO 기반 로봇 대화 시스템
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from robot_system import RobotConversationSystem
from api_routes import setup_routes


# FastAPI 앱 초기화
app = FastAPI(
    title="Robot Conversation API (GPIO)",
    description="라즈베리파이 기반 GPIO 택트 스위치 대화형 로봇 제어 API",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수
robot_system = None


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 초기화"""
    global robot_system
    
    print("🚀 GPIO 기반 로봇 서버 시작...")
    print("⚠️  이 서버는 sudo 권한이 필요합니다!")
    
    # 필수 환경 변수 확인
    required_vars = ['OPENAI_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ 필수 환경 변수가 설정되지 않았습니다:")
        for var in missing_vars:
            print(f"   - {var}")
        raise RuntimeError("환경 변수 설정이 필요합니다.")
    
    # 오디오 출력 디렉토리 생성
    os.makedirs("./audio_test", exist_ok=True)
    
    # 로봇 시스템 초기화
    robot_system = RobotConversationSystem()
    
    # GPIO 클라이언트 초기화
    init_success = await robot_system.initialize_clients()
    if init_success:
        print("🎊 GPIO 기반 서버가 성공적으로 시작되었습니다!")
        print("🔘 택트 스위치를 눌러서 대화를 시작할 수 있습니다!")
    else:
        print("⚠️ GPIO 초기화에 실패했지만 API는 사용 가능합니다.")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 정리"""
    global robot_system
    if robot_system:
        robot_system.cleanup()
    print("👋 서버가 종료되었습니다.")


# 라우트 설정
setup_routes(app, robot_system)


if __name__ == "__main__":
    print("🚀 GPIO 기반 라즈베리파이 로봇 대화 서버를 시작합니다...")
    print("⚠️  sudo 권한으로 실행해주세요: sudo python main.py")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # 모든 IP에서 접근 가능
        port=8080,       # 라즈베리파이 서버 포트
        reload=False,    # 프로덕션에서는 False
        log_level="info"
    )