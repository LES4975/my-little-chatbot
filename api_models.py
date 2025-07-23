#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 요청/응답 모델 정의
"""

from typing import Dict, Optional
from pydantic import BaseModel


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
    emotion: Optional[str] = None
    processing_time: Optional[float] = None
    session_id: Optional[str] = None


class StatusResponse(BaseModel):
    status: str
    message: str
    system_info: Dict


class SimpleResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict] = None