#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
라즈베리파이 FastAPI 서버 (GPIO 기반)
GPIO 택트 스위치로 로봇 제어 + 외부에서 API 요청도 가능
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

# GPIO 컨트롤러 import
from GPIO.gpio_recorder import get_gpio_recorder, cleanup_gpio

# .env 파일 로드
load_dotenv()


# FastAPI 앱 초기화
app = FastAPI(
    title="Robot Conversation API (GPIO)",
    description="라즈베리파이 기반 GPIO 택트 스위치 대화형 로봇 제어 API",
    version="2.0.0"
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
        self.gpio_controller = None
        self.is_busy = False
        
        # GPIO 자동 실행 설정
        self.auto_mode = True  # GPIO 버튼으로 자동 대화 시작
        self.conversation_requested = False  # 대화 요청 플래그
        self.monitor_task = None  # 모니터링 태스크
        
        # 리소스 관리
        self.conversation_count = 0  # 대화 횟수 카운터
        self.resource_cleanup_interval = 10  # 10회마다 리소스 정리
        
        print("🤖 GPIO 기반 로봇 대화 시스템 초기화 완료")
        print(f"🌐 GPU 서버: {self.gpu_server_url}")

        # API 키 설정
        self.api_key = os.getenv("GPU_SERVER_API_KEY")
    
    async def initialize_clients(self):
        """STT, TTS, GPIO 클라이언트 비동기 초기화"""
        try:
            if self.stt_client is None:
                print("🎤 STT 클라이언트 초기화 중...")
                self.stt_client = STTTester()
                print("✅ STT 클라이언트 초기화 완료")
            
            if self.tts_client is None:
                print("🔊 TTS 클라이언트 초기화 중...")
                self.tts_client = GoogleTTSClient()
                print("✅ TTS 클라이언트 초기화 완료")
            
            if self.gpio_controller is None:
                print("🎮 GPIO 컨트롤러 초기화 중...")
                self.gpio_controller = get_gpio_recorder()
                if not self.gpio_controller.button_init():
                    print("❌ GPIO 초기화 실패")
                    return False
                
                # GPIO 콜백 함수 등록
                self.gpio_controller.set_press_callback(self.on_button_press)
                self.gpio_controller.set_release_callback(self.on_button_release)
                
                # GPIO 모니터링 태스크 시작
                if self.monitor_task is None:
                    self.monitor_task = asyncio.create_task(self.gpio_monitor_loop())
                
                print("✅ GPIO 컨트롤러 초기화 완료")
            
            return True
            
        except Exception as e:
            print(f"❌ 클라이언트 초기화 실패: {e}")
            return False
    
    def on_button_press(self):
        """GPIO 버튼 눌림 콜백 - 대화 요청 플래그 설정"""
        if not self.auto_mode:
            return
        
        if self.is_busy:
            print("⚠️ 이미 대화 처리 중입니다...")
            return
        
        print("🔘 버튼 눌림 감지 - 대화 요청!")
        self.conversation_requested = True
    
    def on_button_release(self):
        """GPIO 버튼 뗌 콜백"""
        print("⭕ 버튼 뗌 감지")
    
    async def gpio_monitor_loop(self):
        """GPIO 대화 요청 모니터링 루프"""
        while True:
            try:
                if self.conversation_requested and not self.is_busy:
                    self.conversation_requested = False
                    self.is_busy = True
                    
                    print("🚀 GPIO 대화 시작!")
                    
                    # 기본 파라미터로 대화 실행
                    request_params = {
                        "user_id": "gpio_user",
                        "session_id": f"gpio_session_{int(time.time())}",
                        "max_length": 100,  # 간단한 대답
                        "temperature": 0.7
                    }
                    
                    result = await self.run_gpio_conversation(request_params)
                    
                    if result["status"] == "success":
                        print("🎉 GPIO 대화 완료!")
                    else:
                        print(f"😞 GPIO 대화 실패: {result['message']}")
                    
                    # 대화 횟수 증가 및 주기적 리소스 정리
                    self.conversation_count += 1
                    if self.conversation_count % self.resource_cleanup_interval == 0:
                        await self.periodic_resource_cleanup()
                    
                    self.is_busy = False
                
                await asyncio.sleep(0.1)  # 100ms 주기로 체크
                
            except Exception as e:
                print(f"❌ GPIO 모니터링 중 오류: {e}")
                self.is_busy = False
                await asyncio.sleep(1)
    
    async def get_user_speech_gpio(self):
        """GPIO 기반 사용자 음성 입력 받기"""
        try:
            print("🎯 GPIO 기반 음성 입력 시작")
            
            # GPIO 기반 STT 실행
            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(
                None, 
                self.stt_client.gpio_record_and_transcribe, 
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
    
    async def get_user_speech(self):
        """기존 방식 사용자 음성 입력 (API 호출용)"""
        try:
            print("🎯 음성 입력 시작")
            
            # STT 실행 (기존 방식)
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
                    headers=headers,
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
                "ko-KR-Wavenet-A",
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
    
    async def run_gpio_conversation(self, request_params: Dict):
        """GPIO 기반 대화 워크플로우 실행"""
        start_time = time.time()
        
        try:
            print("🚀 GPIO 대화 워크플로우 시작")
            
            # 클라이언트 초기화 확인
            if not await self.initialize_clients():
                return {
                    "status": "error",
                    "message": "시스템 초기화 실패",
                    "processing_time": time.time() - start_time
                }
            
            # 1단계: 사용자 음성 입력 (GPIO 기반)
            user_text = await self.get_user_speech_gpio()
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
    
    async def run_full_conversation(self, request_params: Dict):
        """API 기반 전체 대화 워크플로우 실행 (기존 방식 유지)"""
        if self.is_busy:
            return {
                "status": "error",
                "message": "로봇이 현재 다른 대화를 처리 중입니다.",
                "processing_time": 0
            }
        
        self.is_busy = True
        start_time = time.time()
        
        try:
            print("🚀 API 대화 워크플로우 시작")
            
            # 클라이언트 초기화
            if not await self.initialize_clients():
                return {
                    "status": "error",
                    "message": "시스템 초기화 실패",
                    "processing_time": time.time() - start_time
                }
            
            # 1단계: 사용자 음성 입력 (기존 방식)
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
    
    async def periodic_resource_cleanup(self):
        """주기적 리소스 정리"""
        try:
            print(f"🧹 주기적 리소스 정리 시작 (대화 {self.conversation_count}회 완료)")
            
            # STT 클라이언트 재초기화
            if self.stt_client:
                print("🔄 STT 클라이언트 재초기화...")
                old_stt_client = self.stt_client
                
                # 새 클라이언트 생성
                self.stt_client = STTTester()
                
                # 기존 클라이언트 정리
                try:
                    old_stt_client.cleanup()
                except Exception as e:
                    print(f"⚠️ 기존 STT 클라이언트 정리 중 오류: {e}")
                
                print("✅ STT 클라이언트 재초기화 완료")
            
            # TTS 클라이언트 재초기화 (필요시)
            if self.tts_client:
                print("🔄 TTS 클라이언트 상태 확인...")
                # Google TTS는 상태 유지가 좋으므로 재초기화 생략
                # 문제 발생 시에만 재초기화하도록 설정
                print("✅ TTS 클라이언트 상태 양호")
            
            # 임시 파일 정리
            await self.cleanup_temp_files()
            
            print("🎉 주기적 리소스 정리 완료")
            
        except Exception as e:
            print(f"❌ 주기적 리소스 정리 중 오류: {e}")
    
    async def cleanup_temp_files(self):
        """임시 파일 정리"""
        try:
            import glob
            import os
            
            # 임시 디렉토리의 오래된 파일들 정리
            temp_patterns = [
                "/tmp/tmp*.wav",  # 시스템 임시 파일
                "./audio_test/robot_response*.mp3",  # TTS 파일
            ]
            
            cleaned_count = 0
            for pattern in temp_patterns:
                for filepath in glob.glob(pattern):
                    try:
                        # 1시간 이상 된 파일만 정리
                        if os.path.exists(filepath):
                            file_age = time.time() - os.path.getmtime(filepath)
                            if file_age > 3600:  # 1시간 = 3600초
                                os.remove(filepath)
                                cleaned_count += 1
                    except Exception as e:
                        print(f"⚠️ 파일 정리 실패 ({filepath}): {e}")
            
            if cleaned_count > 0:
                print(f"🗑️ 임시 파일 {cleaned_count}개 정리 완료")
            
        except Exception as e:
            print(f"⚠️ 임시 파일 정리 중 오류: {e}")
    
    def set_resource_cleanup_interval(self, interval: int):
        """리소스 정리 주기 설정"""
        self.resource_cleanup_interval = max(1, interval)  # 최소 1회
        print(f"🔧 리소스 정리 주기: {self.resource_cleanup_interval}회마다")
    
    def set_auto_mode(self, enabled: bool):
        """GPIO 자동 대화 모드 설정"""
        self.auto_mode = enabled
        print(f"🎮 GPIO 자동 모드: {'활성화' if enabled else '비활성화'}")
    
    def get_conversation_stats(self):
        """대화 통계 반환"""
        return {
            "total_conversations": self.conversation_count,
            "cleanup_interval": self.resource_cleanup_interval,
            "next_cleanup_in": self.resource_cleanup_interval - (self.conversation_count % self.resource_cleanup_interval)
        }
    
    def cleanup(self):
        """리소스 정리"""
        try:
            # 모니터링 태스크 종료
            if self.monitor_task:
                self.monitor_task.cancel()
            
            if self.stt_client:
                self.stt_client.cleanup()
            
            # GPIO 정리
            cleanup_gpio()
            
            print("🧹 리소스 정리 완료")
        except Exception as e:
            print(f"⚠️ 리소스 정리 중 오류: {e}")


# API 엔드포인트 정의

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
    
    # GPIO 클라이언트 초기화 (시작 시 바로 초기화)
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

@app.get("/", response_model=StatusResponse)
async def root():
    """서버 상태 확인"""
    return StatusResponse(
        status="running",
        message="GPIO 기반 라즈베리파이 로봇 대화 시스템이 실행 중입니다.",
        system_info={
            "gpu_server_url": robot_system.gpu_server_url if robot_system else "Not initialized",
            "is_busy": robot_system.is_busy if robot_system else False,
            "auto_mode": robot_system.auto_mode if robot_system else False,
            "conversation_stats": robot_system.get_conversation_stats() if robot_system else {},
            "clients_initialized": {
                "stt": robot_system.stt_client is not None if robot_system else False,
                "tts": robot_system.tts_client is not None if robot_system else False,
                "gpio": robot_system.gpio_controller is not None if robot_system else False
            }
        }
    )

@app.post("/api/start_conversation", response_model=ConversationResponse)
async def start_conversation(request: ConversationRequest):
    """API를 통한 대화 시작 (기존 방식 유지)"""
    global robot_system
    
    if not robot_system:
        raise HTTPException(status_code=500, detail="로봇 시스템이 초기화되지 않았습니다.")
    
    print(f"📞 API 대화 요청: 사용자 {request.user_id}")
    
    # 전체 대화 워크플로우 실행 (기존 방식)
    result = await robot_system.run_full_conversation(request.dict())
    
    return ConversationResponse(**result)

@app.post("/api/gpio_mode")
async def set_gpio_mode(enabled: bool = True):
    """GPIO 자동 대화 모드 설정"""
    global robot_system
    
    if not robot_system:
        raise HTTPException(status_code=500, detail="로봇 시스템이 초기화되지 않았습니다.")
    
    robot_system.set_auto_mode(enabled)
    
    return {
        "status": "success", 
        "message": f"GPIO 자동 모드가 {'활성화' if enabled else '비활성화'}되었습니다.",
        "auto_mode": enabled
    }

@app.post("/api/cleanup_resources")
async def manual_resource_cleanup():
    """수동 리소스 정리"""
    global robot_system
    
    if not robot_system:
        raise HTTPException(status_code=500, detail="로봇 시스템이 초기화되지 않았습니다.")
    
    if robot_system.is_busy:
        raise HTTPException(status_code=409, detail="대화 진행 중에는 리소스 정리를 할 수 없습니다.")
    
    await robot_system.periodic_resource_cleanup()
    
    return {
        "status": "success",
        "message": "리소스 정리가 완료되었습니다.",
        "conversation_count": robot_system.conversation_count
    }

@app.post("/api/set_cleanup_interval")
async def set_cleanup_interval(interval: int):
    """리소스 정리 주기 설정"""
    global robot_system
    
    if not robot_system:
        raise HTTPException(status_code=500, detail="로봇 시스템이 초기화되지 않았습니다.")
    
    if interval < 1 or interval > 100:
        raise HTTPException(status_code=400, detail="주기는 1-100 사이의 값이어야 합니다.")
    
    robot_system.set_resource_cleanup_interval(interval)
    
    return {
        "status": "success",
        "message": f"리소스 정리 주기가 {interval}회로 설정되었습니다.",
        "cleanup_interval": interval
    }

@app.post("/api/emergency_stop")
async def emergency_stop():
    """비상 정지"""
    global robot_system
    
    if robot_system:
        robot_system.is_busy = False
        robot_system.set_auto_mode(False)
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
    
    return StatusResponse
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
            "auto_mode": robot_system.auto_mode,
            "conversation_stats": robot_system.get_conversation_stats(),
            "clients_initialized": {
                "stt": robot_system.stt_client is not None,
                "tts": robot_system.tts_client is not None,
                "gpio": robot_system.gpio_controller is not None
            }
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 GPIO 기반 라즈베리파이 로봇 대화 서버를 시작합니다...")
    print("⚠️  sudo 권한으로 실행해주세요: sudo python main.py")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # 모든 IP에서 접근 가능
        port=8080,       # 라즈베리파이 서버 포트
        reload=False,    # 프로덕션에서는 False
        log_level="info"
    )