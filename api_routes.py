#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 라우트 및 엔드포인트 정의
"""

from fastapi import FastAPI, HTTPException
from api_models import ConversationRequest, ConversationResponse, StatusResponse, SimpleResponse


def setup_routes(app: FastAPI, robot_system):
    """라우트 설정"""
    
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
        """API를 통한 대화 시작"""
        if not robot_system:
            raise HTTPException(status_code=500, detail="로봇 시스템이 초기화되지 않았습니다.")
        
        print(f"📞 API 대화 요청: 사용자 {request.user_id}")
        
        result = await robot_system.run_full_conversation(request.dict())
        return ConversationResponse(**result)

    @app.post("/api/gpio_mode", response_model=SimpleResponse)
    async def set_gpio_mode(enabled: bool = True):
        """GPIO 자동 대화 모드 설정"""
        if not robot_system:
            raise HTTPException(status_code=500, detail="로봇 시스템이 초기화되지 않았습니다.")
        
        robot_system.set_auto_mode(enabled)
        
        return SimpleResponse(
            status="success", 
            message=f"GPIO 자동 모드가 {'활성화' if enabled else '비활성화'}되었습니다.",
            data={"auto_mode": enabled}
        )

    @app.post("/api/cleanup_resources", response_model=SimpleResponse)
    async def manual_resource_cleanup():
        """수동 리소스 정리"""
        if not robot_system:
            raise HTTPException(status_code=500, detail="로봇 시스템이 초기화되지 않았습니다.")
        
        if robot_system.is_busy:
            raise HTTPException(status_code=409, detail="대화 진행 중에는 리소스 정리를 할 수 없습니다.")
        
        await robot_system.periodic_resource_cleanup()
        
        return SimpleResponse(
            status="success",
            message="리소스 정리가 완료되었습니다.",
            data={"conversation_count": robot_system.conversation_count}
        )

    @app.post("/api/set_cleanup_interval", response_model=SimpleResponse)
    async def set_cleanup_interval(interval: int):
        """리소스 정리 주기 설정"""
        if not robot_system:
            raise HTTPException(status_code=500, detail="로봇 시스템이 초기화되지 않았습니다.")
        
        if interval < 1 or interval > 100:
            raise HTTPException(status_code=400, detail="주기는 1-100 사이의 값이어야 합니다.")
        
        robot_system.set_resource_cleanup_interval(interval)
        
        return SimpleResponse(
            status="success",
            message=f"리소스 정리 주기가 {interval}회로 설정되었습니다.",
            data={"cleanup_interval": interval}
        )

    @app.post("/api/emergency_stop", response_model=SimpleResponse)
    async def emergency_stop():
        """비상 정지"""
        if robot_system:
            robot_system.is_busy = False
            robot_system.set_auto_mode(False)
            print("🛑 비상 정지 실행")
            return SimpleResponse(
                status="success", 
                message="비상 정지가 실행되었습니다."
            )
        else:
            raise HTTPException(status_code=500, detail="로봇 시스템이 초기화되지 않았습니다.")

    @app.get("/api/status", response_model=StatusResponse)
    async def get_status():
        """상세 시스템 상태 조회"""
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