#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
라즈베리파이 FastAPI 서버
외부에서 로봇 제어 요청을 받아 STT → GPU 서버 통신 → TTS 워크플로우 실행
"""

import os
import asyncio
import requests
import json
import time
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv
from stt import STTTester
from tts import GoogleTTSClient

# .env 파일 로드
load_dotenv()


# FastAPI 앱 초기화
app = FastAPI(
    title="Robot Conversation API",
    description="라즈베리파이 기반 대화형 로봇 제어 API",
    version="1.0.0"
)

# 요청/응답 모델 정의
class ConversationRequest(BaseModel):
    user_id: Optional[str] = "anonymous"
    session_id: Optional[str] = None
    max_length: Optional[int] = 512
    temperature: Optional[float] = 0.7

class ConversationResponse(BaseModel):
    status: str
    message: str
    user_text: Optional[str] = None
    llm_response: Optional[str] = None
    processing_time: Optional[float] = None
    session_id: Optional[str] = None

class StatusResponse(BaseModel):
    status: str
    message: str
    system_info: Dict

# 전역 변수
robot_system = None

class RobotConversationSystem:
    def __init__(self):
        """로봇 대화 시스템 초기화"""
        # GPU 서버 설정
        self.gpu_server_url = os.getenv('GPU_SERVER_URL', 'http://localhost:8000')
        self.gpu_server_endpoint = f"{self.gpu_server_url}/api/chat"
        
        # 클라이언트 초기화
        self.stt_client = None
        self.tts_client = None
        self.is_busy = False
        
        print("🤖 로봇 대화 시스템 초기화 완료")
        print(f"🌐 GPU 서버: {self.gpu_server_url}")

        # API 키 설정
        self.api_key = os.getenv("GPU_SERVER_API_KEY")
    
    async def initialize_clients(self):
        """STT, TTS 클라이언트 비동기 초기화"""
        try:
            if self.stt_client is None:
                print("🎤 STT 클라이언트 초기화 중...")
                self.stt_client = STTTester()
                print("✅ STT 클라이언트 초기화 완료")
            
            if self.tts_client is None:
                print("🔊 TTS 클라이언트 초기화 중...")
                self.tts_client = GoogleTTSClient()
                print("✅ TTS 클라이언트 초기화 완료")
            
            return True
            
        except Exception as e:
            print(f"❌ 클라이언트 초기화 실패: {e}")
            return False
    
    async def get_user_speech(self):
        """사용자 음성 입력 받기"""
        try:
            print("🎯 음성 입력 시작")
            
            # STT 실행 (간소화된 방법 사용)
            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(
                None, 
                self.stt_client.simple_record_and_transcribe, 
                False  # show_progress=False
            )
            
            if transcript:
                print(f"✅ 음성 인식 완료: '{transcript}'")
                return transcript
            else:
                print("❌ 음성 인식 실패")
                return None
                
        except Exception as e:
            print(f"❌ 음성 입력 처리 중 오류: {e}")
            return None
    
    async def send_to_gpu_server(self, user_text: str, request_params: Dict):
        """GPU 서버로 텍스트 전송 및 응답 받기"""
        try:
            print("🌐 GPU 서버 통신 시작")
            
            # 요청 데이터 구성
            request_data = {
                "message": user_text,
                "user_id": request_params.get("user_id", "raspberry_pi_user"),
                "session_id": request_params.get("session_id", f"session_{int(time.time())}"),
                "max_length": request_params.get("max_length", 512),
                "temperature": request_params.get("temperature", 0.7)
            }
            
            print(f"📤 GPU 서버로 전송: '{user_text[:50]}{'...' if len(user_text) > 50 else ''}'")
            
            # 비동기 HTTP 요청
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            } 

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    self.gpu_server_endpoint,
                    json=request_data,
                    headers=headers, # 추가
                    timeout=30
                )
            )
            
            # 응답 처리
            if response.status_code == 200:
                response_data = response.json()
                
                if response_data.get('status') == 'success':
                    llm_response = response_data.get('response', '')
                    processing_time = response_data.get('processing_time', 0)
                    
                    print(f"✅ GPU 서버 응답 수신 완료 (처리시간: {processing_time:.2f}초)")
                    return llm_response, processing_time
                else:
                    print(f"❌ GPU 서버 처리 오류: {response_data.get('message', 'Unknown error')}")
                    return None, 0
            else:
                print(f"❌ HTTP 요청 실패: {response.status_code}")
                return None, 0
                
        except requests.exceptions.Timeout:
            print("❌ GPU 서버 응답 시간 초과 (30초)")
            return None, 0
        except Exception as e:
            print(f"❌ GPU 서버 통신 중 오류: {e}")
            return None, 0
    
    async def speak_response(self, response_text: str):
        """응답 텍스트를 음성으로 변환하여 재생"""
        try:
            print("🔊 음성 응답 생성 및 재생 시작")
            
            # TTS 변환 및 재생 (간소화된 방법 사용)
            output_file = "./audio_test/robot_response.mp3"
            loop = asyncio.get_event_loop()
            
            success = await loop.run_in_executor(
                None,
                self.tts_client.simple_text_to_speech_and_play,
                response_text,
                output_file,
                False  # show_progress=False
            )
            
            if success:
                print("✅ 음성 재생 완료")
                return True
            else:
                print("❌ 음성 재생 실패")
                return False
                
        except Exception as e:
            print(f"❌ 음성 응답 처리 중 오류: {e}")
            return False
    
    async def run_full_conversation(self, request_params: Dict):
        """전체 대화 워크플로우 실행"""
        if self.is_busy:
            return {
                "status": "error",
                "message": "로봇이 현재 다른 대화를 처리 중입니다.",
                "processing_time": 0
            }
        
        self.is_busy = True
        start_time = time.time()
        
        try:
            print("🚀 대화 워크플로우 시작")
            
            # 클라이언트 초기화
            if not await self.initialize_clients():
                return {
                    "status": "error",
                    "message": "시스템 초기화 실패",
                    "processing_time": time.time() - start_time
                }
            
            # 1단계: 사용자 음성 입력
            user_text = await self.get_user_speech()
            if not user_text:
                return {
                    "status": "error",
                    "message": "음성 입력 실패",
                    "processing_time": time.time() - start_time
                }
            
            # 2단계: GPU 서버 통신
            llm_response, llm_processing_time = await self.send_to_gpu_server(user_text, request_params)
            if not llm_response:
                return {
                    "status": "error",
                    "message": "GPU 서버 통신 실패",
                    "user_text": user_text,
                    "processing_time": time.time() - start_time
                }
            
            # 3단계: 음성 응답 재생
            speech_success = await self.speak_response(llm_response)
            
            total_time = time.time() - start_time
            
            if speech_success:
                print("🎉 대화 완료!")
                return {
                    "status": "success",
                    "message": "대화가 성공적으로 완료되었습니다.",
                    "user_text": user_text,
                    "llm_response": llm_response,
                    "processing_time": total_time,
                    "session_id": request_params.get("session_id")
                }
            else:
                return {
                    "status": "partial_success",
                    "message": "LLM 응답은 받았지만 음성 재생에 실패했습니다.",
                    "user_text": user_text,
                    "llm_response": llm_response,
                    "processing_time": total_time,
                    "session_id": request_params.get("session_id")
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"예상치 못한 오류: {str(e)}",
                "processing_time": time.time() - start_time
            }
        finally:
            self.is_busy = False
    
    def cleanup(self):
        """리소스 정리"""
        try:
            if self.stt_client:
                self.stt_client.cleanup()
            print("🧹 리소스 정리 완료")
        except Exception as e:
            print(f"⚠️ 리소스 정리 중 오류: {e}")


# API 엔드포인트 정의

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 초기화"""
    global robot_system
    
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
    print("🎊 서버가 성공적으로 시작되었습니다!")

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 정리"""
    global robot_system
    if robot_system:
        robot_system.cleanup()
    print("👋 서버가 종료되었습니다.")

@app.get("/", response_model=StatusResponse)
async def root():
    """서버 상태 확인"""
    return StatusResponse(
        status="running",
        message="라즈베리파이 로봇 대화 시스템이 실행 중입니다.",
        system_info={
            "gpu_server_url": robot_system.gpu_server_url if robot_system else "Not initialized",
            "is_busy": robot_system.is_busy if robot_system else False,
            "clients_initialized": {
                "stt": robot_system.stt_client is not None if robot_system else False,
                "tts": robot_system.tts_client is not None if robot_system else False
            }
        }
    )

@app.post("/api/start_conversation", response_model=ConversationResponse)
async def start_conversation(request: ConversationRequest):
    """대화 시작 (전체 워크플로우 실행)"""
    global robot_system
    
    if not robot_system:
        raise HTTPException(status_code=500, detail="로봇 시스템이 초기화되지 않았습니다.")
    
    print(f"📞 새로운 대화 요청: 사용자 {request.user_id}")
    
    # 전체 대화 워크플로우 실행
    result = await robot_system.run_full_conversation(request.dict())
    
    return ConversationResponse(**result)

@app.post("/api/emergency_stop")
async def emergency_stop():
    """비상 정지"""
    global robot_system
    
    if robot_system:
        robot_system.is_busy = False
        print("🛑 비상 정지 실행")
        return {"status": "success", "message": "비상 정지가 실행되었습니다."}
    else:
        raise HTTPException(status_code=500, detail="로봇 시스템이 초기화되지 않았습니다.")

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """상세 시스템 상태 조회"""
    global robot_system
    
    if not robot_system:
        raise HTTPException(status_code=500, detail="로봇 시스템이 초기화되지 않았습니다.")
    
    return StatusResponse(
        status="running",
        message="시스템이 정상 작동 중입니다.",
        system_info={
            "gpu_server_url": robot_system.gpu_server_url,
            "is_busy": robot_system.is_busy,
            "clients_initialized": {
                "stt": robot_system.stt_client is not None,
                "tts": robot_system.tts_client is not None
            }
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 라즈베리파이 로봇 대화 서버를 시작합니다...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # 모든 IP에서 접근 가능
        port=8080,       # 라즈베리파이 서버 포트
        reload=False,    # 프로덕션에서는 False
        log_level="info"
    )