#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
얼굴 표정 제어 메인 모듈
감정 분석과 OLED 표시를 통합 관리합니다.
"""

import time
import threading
from typing import Optional
from emotion_analyzer import EmotionAnalyzer
from oled_display import OLEDDisplay


class FaceController:
    """로봇 얼굴 표정 통합 컨트롤러"""
    
    def __init__(self, i2c_port=1, i2c_address=0x3C, device_type='sh1106'):
        """
        얼굴 컨트롤러 초기화
        
        Args:
            i2c_port (int): I2C 포트 번호
            i2c_address (int): I2C 주소  
            device_type (str): OLED 컨트롤러 타입
        """
        self.emotion_analyzer = EmotionAnalyzer()
        self.oled_display = OLEDDisplay(i2c_port, i2c_address, device_type)
        
        self.current_emotion = "neutral"
        self.is_animating = False
        self.animation_thread = None
        
        # 표정 지속 시간 설정 (초)
        self.emotion_duration = 3.0
        self.neutral_return_timer = None
        
        print("🤖 얼굴 컨트롤러 초기화 완료")
    
    def show_start_screen(self):
        """시작 화면 표시"""
        self.oled_display.draw_start_screen()
        print("📺 시작 화면 표시")
    
    def analyze_and_show_emotion(self, text: str, duration: Optional[float] = None):
        """
        텍스트를 분석하여 감정을 파악하고 표정 표시
        
        Args:
            text (str): 분석할 텍스트
            duration (float): 표정 지속 시간 (None이면 기본값 사용)
        """
        if not text.strip():
            return
        
        # 감정 분석
        emotion = self.emotion_analyzer.get_emotion(text)
        print(f"📝 감정 분석: '{text[:30]}...' → {emotion}")
        
        # 표정 표시
        self.show_emotion(emotion, duration)
    
    def show_emotion(self, emotion: str, duration: Optional[float] = None):
        """
        지정된 감정의 표정 표시
        
        Args:
            emotion (str): 표시할 감정
            duration (float): 표정 지속 시간
        """
        self.current_emotion = emotion
        self.oled_display.draw_emotion(emotion)
        
        # 기존 타이머 취소
        if self.neutral_return_timer:
            self.neutral_return_timer.cancel()
        
        # 일정 시간 후 중립 표정으로 복귀
        if emotion != "neutral":
            timeout = duration if duration else self.emotion_duration
            self.neutral_return_timer = threading.Timer(timeout, self._return_to_neutral)
            self.neutral_return_timer.start()
            
        print(f"😊 표정 변경: {emotion}")
    
    def _return_to_neutral(self):
        """중립 표정으로 복귀"""
        if self.current_emotion != "neutral":
            self.current_emotion = "neutral"
            self.oled_display.draw_emotion("neutral")
            print("😐 중립 표정으로 복귀")
    
    def set_emotion_duration(self, duration: float):
        """
        기본 감정 지속 시간 설정
        
        Args:
            duration (float): 지속 시간 (초)
        """
        self.emotion_duration = max(0.5, duration)  # 최소 0.5초
        print(f"⏱️ 감정 지속 시간: {self.emotion_duration}초")
    
    def start_emotion_animation(self, emotions: list, interval: float = 2.0):
        """
        감정 애니메이션 시작 (순환)
        
        Args:
            emotions (list): 순환할 감정 리스트
            interval (float): 감정 전환 간격 (초)
        """
        if self.is_animating:
            self.stop_emotion_animation()
        
        self.is_animating = True
        self.animation_thread = threading.Thread(
            target=self._animation_loop, 
            args=(emotions, interval),
            daemon=True
        )
        self.animation_thread.start()
        print(f"🎭 감정 애니메이션 시작: {emotions}")
    
    def _animation_loop(self, emotions: list, interval: float):
        """애니메이션 루프"""
        emotion_index = 0
        while self.is_animating:
            emotion = emotions[emotion_index % len(emotions)]
            self.oled_display.draw_emotion(emotion)
            self.current_emotion = emotion
            
            emotion_index += 1
            time.sleep(interval)
    
    def stop_emotion_animation(self):
        """감정 애니메이션 중지"""
        if self.is_animating:
            self.is_animating = False
            if self.animation_thread and self.animation_thread.is_alive():
                self.animation_thread.join(timeout=1.0)
            print("🛑 감정 애니메이션 중지")
    
    def get_current_emotion(self) -> str:
        """현재 표시 중인 감정 반환"""
        return self.current_emotion
    
    def clear_display(self):
        """화면 지우기"""
        self.oled_display.clear_display()
        print("🧹 화면 지움")
    
    def cleanup(self):
        """리소스 정리"""
        # 애니메이션 중지
        self.stop_emotion_animation()
        
        # 타이머 취소
        if self.neutral_return_timer:
            self.neutral_return_timer.cancel()
        
        # 화면 지우기
        self.clear_display()
        
        print("🧹 얼굴 컨트롤러 정리 완료")


# main.py에서 사용할 간단한 함수들
def create_face_controller(**kwargs) -> FaceController:
    """얼굴 컨트롤러 생성"""
    return FaceController(**kwargs)


def quick_emotion_test():
    """빠른 감정 테스트"""
    controller = FaceController()
    
    try:
        controller.show_start_screen()
        time.sleep(2)
        
        test_texts = [
            "안녕하세요! 만나서 반가워요!",
            "오늘 정말 기분이 좋네요",
            "이건 너무 화가 나는 일이에요",
            "무서워서 떨리고 있어요",
            "정말 슬퍼서 눈물이 나요",
            "깜짝 놀랐어요!",
            "이건 정말 역겨워요"
        ]
        
        for text in test_texts:
            print(f"\n테스트: {text}")
            controller.analyze_and_show_emotion(text, duration=3.0)
            time.sleep(4)
        
        controller.show_emotion("neutral")
        
    except KeyboardInterrupt:
        print("\n테스트 중단")
    finally:
        controller.cleanup()


# 테스트용 메인 함수
def main():
    """얼굴 컨트롤러 테스트"""
    print("🎯 얼굴 컨트롤러 통합 테스트")
    print("=" * 50)
    
    choice = input("테스트 선택 (1: 감정 분석, 2: 애니메이션): ").strip()
    
    if choice == "2":
        # 애니메이션 테스트
        controller = FaceController()
        try:
            print("애니메이션 테스트 시작...")
            emotions = ["happy", "neutral", "surprise", "neutral"]
            controller.start_emotion_animation(emotions, interval=1.5)
            
            print("10초 후 종료됩니다...")
            time.sleep(10)
            
        except KeyboardInterrupt:
            print("\n애니메이션 테스트 중단")
        finally:
            controller.cleanup()
    
    else:
        # 감정 분석 테스트
        quick_emotion_test()


if __name__ == "__main__":
    main()