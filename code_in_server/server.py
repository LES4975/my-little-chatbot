#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU 서버 FastAPI 메인 실행 코드
라즈베리파이로부터 텍스트를 받아 Midm-2.0-Mini-Instruct 모델로 응답 생성
"""

import os
import time
import asyncio
from typing import Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# LLM 핸들러 임포트 (다음에 작성할 파일)
from llm_handler import MidmLLMHandler


# 요청/응답 모델 정의
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "raspberry_pi_user"
    session_id: Optional[str] = None
    max_length: Optional[int] = 100  # 2문장용 기본값
    temperature: Optional[float] = 0.7

class ChatResponse(BaseModel):
    status: str
    response: str
    processing_time: float
    session_id: str
    emotion: str # OLED로 표현할 표정
    model_info: Optional[Dict] = None

class StatusResponse(BaseModel):
    status: str
    message: str
    model_info: Dict
    gpu_info: Optional[Dict] = None


# 전역 변수
llm_handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작/종료 시 실행되는 라이프사이클 관리"""
    global llm_handler
    
    # 서버 시작 시
    print("🚀 GPU 서버 시작 중...")
    print("🤖 LLM 모델 로딩 중... (첫 실행 시 시간이 걸릴 수 있습니다)")
    
    try:
        # LLM 핸들러 초기화
        llm_handler = MidmLLMHandler()
        print("✅ 모델 로딩 완료!")
        print(f"📍 서버가 준비되었습니다.")
        
    except Exception as e:
        print(f"❌ 모델 로딩 실패: {e}")
        raise
    
    yield  # 서버 실행
    
    # 서버 종료 시
    print("👋 GPU 서버 종료 중...")
    if llm_handler:
        llm_handler.cleanup()
    print("🛑 서버가 종료되었습니다.")


# FastAPI 앱 초기화
app = FastAPI(
    title="Midm-2.0 LLM Server",
    description="GPU 기반 한국어 LLM 추론 서버",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정 (라즈베리파이에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 IP만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=StatusResponse)
async def root():
    """서버 상태 확인"""
    global llm_handler
    
    model_info = {
        "model_name": "Midm-2.0-Mini-Instruct",
        "model_loaded": llm_handler is not None,
        "device": llm_handler.device if llm_handler else "N/A"
    }
    
    # GPU 정보 가져오기 (옵션)
    gpu_info = None
    if llm_handler and hasattr(llm_handler, 'get_gpu_info'):
        gpu_info = llm_handler.get_gpu_info()
    
    return StatusResponse(
        status="running",
        message="GPU LLM 서버가 실행 중입니다.",
        model_info=model_info,
        gpu_info=gpu_info
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    텍스트 입력을 받아 LLM 응답 생성
    
    Args:
        request: ChatRequest 모델
            - message: 사용자 입력 텍스트
            - user_id: 사용자 식별자
            - session_id: 세션 식별자
            - max_length: 최대 생성 길이
            - temperature: 생성 온도 (0.0 ~ 1.0)
    
    Returns:
        ChatResponse: LLM 응답 및 메타데이터
    """
    global llm_handler
    
    if not llm_handler:
        raise HTTPException(status_code=503, detail="모델이 로드되지 않았습니다.")
    
    # 입력 검증
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어있습니다.")
    
    if len(request.message) > 2000:
        raise HTTPException(status_code=400, detail="메시지가 너무 깁니다. (최대 2000자)")
    
    # 세션 ID 생성 (없는 경우)
    if not request.session_id:
        request.session_id = f"session_{int(time.time() * 1000)}"
    
    print(f"\n📨 새로운 요청 수신:")
    print(f"   사용자: {request.user_id}")
    print(f"   세션: {request.session_id}")
    print(f"   메시지: '{request.message[:50]}{'...' if len(request.message) > 50 else ''}'")
    
    start_time = time.time()
    
    try:
        # 비동기로 LLM 추론 실행
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            llm_handler.generate_response_with_emotion,
            request.message,
            request.max_length,
            request.temperature
        )
        response_text = result["response"]
        emotion = result["emotion"]
        processing_time = time.time() - start_time
        
        # 개선: 2단계 처리 과정 반영
        print(f"   2단계 응답 생성 완료 (처리시간: {processing_time:.2f}초)")
        print(f"   1단계: 대화 응답 생성")
        print(f"   2단계: 감정 분석 완료")
        print(f"   응답: '{response_text[:50]}{'...' if len(response_text) > 50 else ''}'")
        print(f"   감정: {emotion}")

        # 토큰 수 계산 (옵션)
        tokens_used = len(request.message.split()) + len(response_text.split())
        
        return ChatResponse(
            status="success",
            response=response_text,
            processing_time=processing_time,
            session_id=request.session_id,
            emotion=emotion, # OLED 표정
            model_info={
                "model": "Midm-2.0-Mini-Instruct",
                "tokens_used": tokens_used,
                "temperature": request.temperature,
                "max_length": request.max_length
            }
        )
        
    except Exception as e:
        print(f"❌ 추론 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"추론 중 오류가 발생했습니다: {str(e)}")


@app.get("/api/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    global llm_handler
    
    health_status = {
        "status": "healthy" if llm_handler else "unhealthy",
        "timestamp": time.time(),
        "model_loaded": llm_handler is not None
    }
    
    if llm_handler:
        # 간단한 추론 테스트
        try:
            test_result= llm_handler.generate_response_with_emotion("안녕", max_length=10)
            health_status["test_inference"] = "success"
        except:
            health_status["test_inference"] = "failed"
            health_status["status"] = "unhealthy"
    
    return health_status


@app.post("/api/clear_cache")
async def clear_cache():
    """모델 캐시 정리 (메모리 관리용)"""
    global llm_handler
    
    if not llm_handler:
        raise HTTPException(status_code=503, detail="모델이 로드되지 않았습니다.")
    
    try:
        if hasattr(llm_handler, 'clear_cache'):
            llm_handler.clear_cache()
            return {"status": "success", "message": "캐시가 정리되었습니다."}
        else:
            return {"status": "info", "message": "캐시 정리 기능이 구현되지 않았습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 정리 중 오류: {str(e)}")


# 에러 핸들러
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """일반 예외 처리"""
    print(f"❌ 처리되지 않은 오류: {exc}")
    return {
        "status": "error",
        "error_code": "INTERNAL_ERROR",
        "message": "서버 내부 오류가 발생했습니다.",
        "details": str(exc) if os.getenv("DEBUG") == "true" else None
    }


def main():
    """메인 실행 함수"""
    # 환경 변수 설정
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8002"))
    reload = os.getenv("SERVER_RELOAD", "false").lower() == "true"
    
    print("🚀 Midm-2.0 LLM 서버를 시작합니다...")
    print(f"📍 주소: http://{host}:{port}")
    print(f"📄 API 문서: http://{host}:{port}/docs")
    print("="*50)
    
    # 서버 실행
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()