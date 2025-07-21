#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OLED 디스플레이 제어 모듈
표정 그리기 및 화면 제어를 담당합니다.
"""

from PIL import Image, ImageDraw
from luma.oled.device import sh1106
from luma.core.interface.serial import i2c


class OLEDDisplay:
    """OLED 디스플레이 컨트롤러"""
    
    def __init__(self, i2c_port=1, i2c_address=0x3C, device_type='sh1106'):
        """
        OLED 디스플레이 초기화
        
        Args:
            i2c_port (int): I2C 포트 번호
            i2c_address (int): I2C 주소
            device_type (str): OLED 컨트롤러 타입 ('sh1106' 또는 'ssd1306')
        """
        self.serial = i2c(port=i2c_port, address=i2c_address)
        
        # 디바이스 타입에 따른 초기화
        if device_type == 'ssd1306':
            from luma.oled.device import ssd1306
            self.device = ssd1306(self.serial)
        else:  # sh1106
            self.device = sh1106(self.serial)
        
        # 화면 크기
        self.width = 128
        self.height = 64
        
        # 표정 그리기 함수들을 딕셔너리로 매핑
        self.emotion_functions = {
            "angry": self._draw_angry,
            "disgust": self._draw_disgust,
            "fear": self._draw_fear,
            "happy": self._draw_happy,
            "sad": self._draw_sad,
            "surprise": self._draw_surprise,
            "neutral": self._draw_neutral
        }
    
    def create_image(self):
        """새로운 빈 이미지 생성"""
        return Image.new("1", (self.width, self.height), color=0)
    
    def display_image(self, image):
        """이미지를 디스플레이에 출력"""
        self.device.display(image)
    
    def clear_display(self):
        """화면 지우기"""
        self.device.clear()
    
    def draw_start_screen(self):
        """시작 화면 표시"""
        image = self.create_image()
        draw = ImageDraw.Draw(image)
        draw.text((30, 25), "START_ROBOT", fill=1)
        self.display_image(image)
    
    def draw_emotion(self, emotion: str):
        """
        감정에 따른 표정 그리기
        
        Args:
            emotion (str): 감정 ("angry", "disgust", "fear", "happy", "sad", "surprise", "neutral")
        """
        if emotion in self.emotion_functions:
            self.emotion_functions[emotion]()
        else:
            # 알 수 없는 감정은 중립 표정으로
            self._draw_neutral()
    
    def _draw_eyes_normal(self, draw):
        """일반 눈 그리기"""
        draw.ellipse((10, 10, 40, 40), fill=1)
        draw.ellipse((90, 10, 120, 40), fill=1)
    
    def _draw_angry(self):
        """화난 표정"""
        image = self.create_image()
        draw = ImageDraw.Draw(image)
        
        # 화난 눈
        draw.polygon([(10, 10), (40, 15), (40, 25), (10, 25)], fill=1)
        draw.pieslice((10, 10, 40, 40), start=0, end=180, fill=1)
        draw.polygon([(90, 15), (120, 10), (120, 25), (90, 25)], fill=1)
        draw.pieslice((90, 10, 120, 40), start=0, end=-180, fill=1)
        
        # 화난 입
        draw.polygon([(55, 60), (65, 50), (75, 60)], fill=1)
        
        self.display_image(image)
    
    def _draw_disgust(self):
        """혐오 표정"""
        image = self.create_image()
        draw = ImageDraw.Draw(image)
        
        # 혐오 눈
        draw.pieslice((10, 10, 40, 40), start=0, end=180, fill=1)
        draw.pieslice((90, 10, 120, 40), start=0, end=-180, fill=1)
        
        # 혐오 입
        draw.pieslice((50, 40, 80, 60), start=180, end=0, fill=1)
        draw.rectangle((50, 50, 80, 70), outline=1)
        draw.rectangle((55, 50, 75, 70), outline=1)
        draw.rectangle((60, 50, 70, 70), outline=1)
        draw.rectangle((65, 50, 65, 70), outline=1)
        
        self.display_image(image)
    
    def _draw_fear(self):
        """두려움 표정"""
        image = self.create_image()
        draw = ImageDraw.Draw(image)
        
        # 두려움 눈
        draw.ellipse((10, 10, 40, 40), outline=1)
        draw.ellipse((90, 10, 120, 40), outline=1)
        draw.ellipse((20, 20, 30, 30), fill=1)
        draw.ellipse((100, 20, 110, 30), fill=1)
        draw.ellipse((15, 15, 35, 35), outline=1)
        draw.ellipse((95, 15, 115, 35), outline=1)
        
        # 두려움 효과선들
        lines = [
            (25, 0, 25, 5), (20, 0, 20, 10), (15, 0, 15, 15),
            (10, 0, 10, 20), (5, 0, 5, 30), (25, 50, 25, 70),
            (20, 45, 20, 70), (15, 40, 15, 70), (10, 35, 10, 70),
            (5, 15, 5, 70), (125, 0, 125, 30), (120, 0, 120, 20),
            (115, 0, 115, 15), (110, 0, 110, 10), (105, 0, 105, 5),
            (125, 15, 125, 70), (120, 35, 120, 70), (115, 40, 115, 70),
            (110, 45, 110, 70), (105, 50, 105, 70)
        ]
        for line in lines:
            draw.rectangle(line, outline=1)
        
        # 두려움 입
        draw.rectangle((50, 50, 80, 60), outline=1)
        draw.pieslice((50, 55, 80, 65), start=180, end=0, fill=1)
        
        self.display_image(image)
    
    def _draw_happy(self):
        """행복한 표정"""
        image = self.create_image()
        draw = ImageDraw.Draw(image)
        
        # 행복한 눈
        draw.polygon([(10, 25), (40, 25), (40, 30), (10, 25)], fill=1)
        draw.pieslice((10, 10, 40, 40), start=180, end=0, fill=1)
        draw.polygon([(90, 30), (120, 25), (120, 25), (90, 25)], fill=1)
        draw.pieslice((90, 10, 120, 40), start=180, end=-0, fill=1)
        
        # 웃는 입
        draw.arc((40, 40, 90, 60), 0, 180, fill=1)
        
        self.display_image(image)
    
    def _draw_sad(self):
        """슬픈 표정"""
        image = self.create_image()
        draw = ImageDraw.Draw(image)
        
        # 슬픈 눈
        draw.polygon([(10, 25), (40, 20), (40, 30), (10, 25)], fill=1)
        draw.pieslice((10, 10, 40, 40), start=0, end=180, fill=1)
        draw.polygon([(90, 20), (120, 25), (120, 25), (90, 25)], fill=1)
        draw.pieslice((90, 10, 120, 40), start=0, end=180, fill=1)
        
        # 눈물
        draw.polygon([(110, 50), (115, 40), (120, 50)], fill=1)
        draw.ellipse((110, 45, 120, 60), fill=1)
        
        # 슬픈 입
        draw.arc((45, 50, 80, 65), 180, 360, fill=1)
        
        self.display_image(image)
    
    def _draw_surprise(self):
        """놀란 표정"""
        image = self.create_image()
        draw = ImageDraw.Draw(image)
        
        # 놀란 눈
        draw.ellipse((10, 10, 40, 50), fill=1)
        draw.ellipse((90, 10, 120, 50), fill=1)
        
        # 놀란 입
        draw.ellipse((55, 45, 75, 60), fill=1)
        
        self.display_image(image)
    
    def _draw_neutral(self):
        """중립 표정"""
        image = self.create_image()
        draw = ImageDraw.Draw(image)
        
        # 일반 눈
        self._draw_eyes_normal(draw)
        
        # 무표정 입
        draw.arc((50, 45, 80, 50), 0, 180, fill=1)
        
        self.display_image(image)


# 테스트용 함수
def main():
    """OLED 디스플레이 테스트"""
    import time
    
    try:
        display = OLEDDisplay()
        
        # 시작 화면
        display.draw_start_screen()
        time.sleep(2)
        
        # 각 감정 테스트
        emotions = ["neutral", "happy", "sad", "angry", "surprise", "fear", "disgust"]
        
        for emotion in emotions:
            print(f"표정 테스트: {emotion}")
            display.draw_emotion(emotion)
            time.sleep(3)
        
        display.clear_display()
        
    except KeyboardInterrupt:
        print("테스트 종료")
    except Exception as e:
        print(f"오류 발생: {e}")


if __name__ == "__main__":
    main()