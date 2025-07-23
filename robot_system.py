#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로봇 대화 시스템 핵심 클래스
GPIO 제어, 음성 처리, GPU 서버 통신을 담당
"""

import os
import asyncio
import requests
import time
import glob
import tempfile
from typing import Dict, Optional
from dotenv import load_dotenv

# conversation 모듈에서 import
from conversation.stt import STTTester
from conversation.tts import GoogleTTSClient
from GPIO.gpio_recorder import get_gpio_recorder, cleanup_gpio
from oled.show_emotion import OLEDEmotion

# .env 파일 로드
load_dotenv()


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

        # OLED 초기화
        self.oled_emotion = OLEDEmotion()
        
        # GPIO 자동 실행 설정
        self.auto_mode = True
        self.conversation_requested = False
        self.monitor_task = None
        
        # 리소스 관리
        self.conversation_count = 0
        self.resource_cleanup_interval = 10
        
        # API 키 설정
        self.api_key = os.getenv("GPU_SERVER_API_KEY")

        # 시작 화면 표시
        if self.oled_emotion.is_initialized():
            self.oled_emotion.show_startup_sequence()
        
        print("🤖 GPIO 기반 로봇 대화 시스템 초기화 완료")
        print(f"🌐 GPU 서버: {self.gpu_server_url}")
    
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
        """GPIO 버튼 눌림 콜백"""
        if not self.auto_mode or self.is_busy:
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
                    
                    request_params = {
                        "user_id": "gpio_user",
                        "session_id": f"gpio_session_{int(time.time())}",
                        "max_length": 100,
                        "temperature": 0.7
                    }
                    
                    result = await self.run_gpio_conversation(request_params)
                    
                    if result["status"] == "success":
                        print("🎉 GPIO 대화 완료!")
                    else:
                        print(f"😞 GPIO 대화 실패: {result['message']}")
                    
                    self.conversation_count += 1
                    if self.conversation_count % self.resource_cleanup_interval == 0:
                        await self.periodic_resource_cleanup()
                    
                    self.is_busy = False
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"❌ GPIO 모니터링 중 오류: {e}")
                self.is_busy = False
                await asyncio.sleep(1)
    
    async def get_user_speech_gpio(self):
        """GPIO 기반 사용자 음성 입력"""
        try:
            print("🎯 GPIO 기반 음성 입력 시작")
            
            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(
                None, 
                self.stt_client.gpio_record_and_transcribe, 
                False
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
            
            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(
                None, 
                self.stt_client.simple_record_and_transcribe, 
                False
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
            
            request_data = {
                "message": user_text,
                "user_id": request_params.get("user_id", "raspberry_pi_user"),
                "session_id": request_params.get("session_id", f"session_{int(time.time())}"),
                "max_length": request_params.get("max_length", 512),
                "temperature": request_params.get("temperature", 0.7)
            }
            
            print(f"📤 GPU 서버로 전송: '{user_text[:50]}{'...' if len(user_text) > 50 else ''}'")
            
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
            
            if response.status_code == 200:
                response_data = response.json()
                
                if response_data.get('status') == 'success':
                    llm_response = response_data.get('response', '')
                    emotion = response_data.get('emotion', 'neutral')
                    processing_time = response_data.get('processing_time', 0)
                    
                    print(f"✅ GPU 서버 응답 수신 완료 (처리시간: {processing_time:.2f}초)")
                    return llm_response, emotion, processing_time
                else:
                    print(f"❌ GPU 서버 처리 오류: {response_data.get('message', 'Unknown error')}")
                    return None, 'neutral', 0
            else:
                print(f"❌ HTTP 요청 실패: {response.status_code}")
                return None, 'neutral', 0
                
        except requests.exceptions.Timeout:
            print("❌ GPU 서버 응답 시간 초과 (30초)")
            return None, 'neutral', 0
        except Exception as e:
            print(f"❌ GPU 서버 통신 중 오류: {e}")
            return None, 'neutral', 0
    
    async def speak_response(self, response_text: str):
        """응답 텍스트를 음성으로 변환하여 재생"""
        try:
            print("🔊 음성 응답 생성 및 재생 시작")
            
            output_file = "./audio_test/robot_response.mp3"
            loop = asyncio.get_event_loop()
            
            success = await loop.run_in_executor(
                None,
                self.tts_client.simple_text_to_speech_and_play,
                response_text,
                output_file,
                "ko-KR-Wavenet-A",
                False
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
            llm_response, emotion, llm_processing_time = await self.send_to_gpu_server(user_text, request_params)
            if not llm_response:
                return {
                    "status": "error",
                    "message": "GPU 서버 통신 실패",
                    "user_text": user_text,
                    "processing_time": time.time() - start_time
                }
            
            # 3단계: 표정 표시 후 음성 응답 재생
            await self.change_oled_expression(emotion)
            speech_success = await self.speak_response(llm_response)
            

            total_time = time.time() - start_time
            
            return {
                "status": "success" if speech_success else "partial_success",
                "message": "대화가 성공적으로 완료되었습니다." if speech_success else "LLM 응답은 받았지만 음성 재생에 실패했습니다.",
                "user_text": user_text,
                "llm_response": llm_response,
                "emotion": emotion,
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
        """API 기반 전체 대화 워크플로우 실행"""
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
            llm_response, emotion, llm_processing_time = await self.send_to_gpu_server(user_text, request_params)
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
            
            return {
                "status": "success" if speech_success else "partial_success",
                "message": "대화가 성공적으로 완료되었습니다." if speech_success else "LLM 응답은 받았지만 음성 재생에 실패했습니다.",
                "user_text": user_text,
                "llm_response": llm_response,
                "emotion": emotion,
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

    async def change_oled_expression(self, emotion:str):
        if self.oled_emotion and self.oled_emotion.is_initialized():
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.oled_emotion.draw_emotion_face, emotion)
        else:
            print("⚠️ OLED 컨트롤러가 초기화되지 않았습니다.")


    async def periodic_resource_cleanup(self):
        """주기적 리소스 정리"""
        try:
            print(f"🧹 주기적 리소스 정리 시작 (대화 {self.conversation_count}회 완료)")
            
            # STT 클라이언트 재초기화
            if self.stt_client:
                print("🔄 STT 클라이언트 재초기화...")
                old_stt_client = self.stt_client
                self.stt_client = STTTester()
                
                try:
                    old_stt_client.cleanup()
                except Exception as e:
                    print(f"⚠️ 기존 STT 클라이언트 정리 중 오류: {e}")
                
                print("✅ STT 클라이언트 재초기화 완료")
            
            # 임시 파일 정리
            await self.cleanup_temp_files()
            
            print("🎉 주기적 리소스 정리 완료")
            
        except Exception as e:
            print(f"❌ 주기적 리소스 정리 중 오류: {e}")
    
    async def cleanup_temp_files(self):
        """임시 파일 정리"""
        try:
            temp_patterns = [
                "/tmp/tmp*.wav",
                "./audio_test/robot_response*.mp3",
            ]
            
            cleaned_count = 0
            for pattern in temp_patterns:
                for filepath in glob.glob(pattern):
                    try:
                        if os.path.exists(filepath):
                            file_age = time.time() - os.path.getmtime(filepath)
                            if file_age > 3600:  # 1시간
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
        self.resource_cleanup_interval = max(1, interval)
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

            if self.oled_emotion:
                self.oled_emotion.cleanup()
            
            # GPIO 정리
            cleanup_gpio()
            
            print("🧹 리소스 정리 완료")
        except Exception as e:
            print(f"⚠️ 리소스 정리 중 오류: {e}")