from PIL import Image, ImageDraw
from luma.oled.device import sh1106
from luma.core.interface.serial import i2c
import time

class OLEDEmotion:
    def __init__(self, port=1, address=0x3C, rotate=2):
        self.device = None
        self.port = port
        self.address = address
        self.rotate = rotate

        self._initialize_device()

    def _initialize_device(self):
        """OLED 디바이스 초기화"""
        try:
            serial = i2c(port=self.port, address=self.address)
            self.device = sh1106(serial, rotate=self.rotate)
            print("OLED 디스플레이 초기화 완료")
        except Exception as e:
            print(f"OLED 초기화 실패: {e}")
            self.device = None

    def is_initialized(self): # 초기화했는가?
        return self.device is not None

    def clear_display(self):
        """디스플레이 화면 지우기"""
        if self.device:
            self.device.clear()

    def show_startup_sequence(self):
        """시작 화면 시퀀스 표시"""
        if not self.device:
            return
        
        try:
            self.draw_start_screen()
            time.sleep(1.5)
            self.draw_start_screen1()
            time.sleep(3)
            self.draw_start_screen2()
            time.sleep(3)
            self.draw_start_screen3()
            time.sleep(3)
            self.draw_emotion_face("neutral")
        except Exception as e:
            print(f"시작 화면 표시 중 오류: {e}")

    def draw_start_screen(self):
        """시작 화면 1"""
        image = Image.new("1", (128, 64), color=0)
        draw = ImageDraw.Draw(image)
        draw.text((30, 25), "START_ROBOT", fill=1)
        self.device.display(image)

    def draw_start_screen1(self):
        """시작 화면 2"""
        image = Image.new("1", (128, 64), color=0)
        draw = ImageDraw.Draw(image)
        draw.text((20, 25), "LLM_LeeEunseo", fill=1)
        self.device.display(image)

    def draw_start_screen2(self):
        """시작 화면 3"""
        image = Image.new("1", (128, 64), color=0)
        draw = ImageDraw.Draw(image)
        draw.text((20, 19), "FaceTracking", fill=1)
        draw.text((20, 31), "ParkMyoungWoo", fill=1)
        self.device.display(image)

    def draw_start_screen3(self):
        """시작 화면 4"""
        image = Image.new("1", (128, 64), color=0)
        draw = ImageDraw.Draw(image)
        draw.text((10, 25), "Hardware_AnJinHong", fill=1)
        self.device.display(image)

    # def get_emotion_from_text(self, text):
    #     """
    #     텍스트에서 감정 분석 (백업용 - LLM에서 감정을 못 받았을 때 사용)
        
    #     Args:
    #         text: 분석할 텍스트
            
    #     Returns:
    #         str: 감정 키워드
    #     """
    #     text = text.lower()
    #     if any(word in text for word in ["화나", "분노", "짜증", "빡쳐", "열받"]):
    #         return "angry"
    #     elif any(word in text for word in ["역겨", "구역질", "토할", "혐오"]):
    #         return "disgust"
    #     elif any(word in text for word in ["무서", "두려", "겁나", "공포", "떨려"]):
    #         return "fear"
    #     elif any(word in text for word in ["행복", "좋아", "사랑", "기뻐", "즐거워", "신나"]):
    #         return "happy"
    #     elif any(word in text for word in ["슬퍼", "눈물", "우울", "울고", "외로"]):
    #         return "sad"
    #     elif any(word in text for word in ["놀라", "헉", "어머", "세상에", "헐"]):
    #         return "surprise"
    #     else:
    #         return "neutral"
    
    def draw_emotion_face(self, emotion):
        """
        감정에 따른 표정 그리기
        
        Args:
            emotion: 감정 키워드 (angry, disgust, fear, happy, sad, surprise, neutral)
        """
        if not self.device:
            print("⚠️ OLED 디바이스가 초기화되지 않았습니다.")
            return
        
        try:
            image = Image.new("1", (128, 64), color=0)
            draw = ImageDraw.Draw(image)

            # 감정별 표정 그리기
            if emotion == "angry":
                self._draw_eyes_angry(draw)
                draw.polygon([(55, 60), (65, 50), (75, 60)], fill=1)
            elif emotion == "disgust":
                self._draw_eyes_disgust(draw)
                draw.pieslice((50, 40, 80, 60), start=180, end=0, fill=1)
                draw.rectangle((50, 50, 80, 70), outline=1)
                draw.rectangle((55, 50, 75, 70), outline=1)
                draw.rectangle((60, 50, 70, 70), outline=1)
                draw.rectangle((65, 50, 65, 70), outline=1)
            elif emotion == "fear":
                self._draw_eyes_fear(draw)
                draw.rectangle((50, 50, 80, 60), outline=1)
                draw.pieslice((50, 55, 80, 65), start=180, end=0, fill=1)
            elif emotion == "happy":
                self._draw_eyes_happy(draw)
                draw.arc((40, 40, 90, 60), 0, 180, fill=1)
            elif emotion == "sad":
                self._draw_eyes_sad(draw)
                draw.arc((45, 50, 80, 65), 180, 360, fill=1)
            elif emotion == "surprise":
                self._draw_eyes_surprise(draw)
                draw.ellipse((55, 45, 75, 60), fill=1)
            else:  # neutral
                self._draw_eyes_normal(draw)
                draw.arc((50, 45, 80, 50), 0, 180, fill=1)
            
            self.device.display(image)
            print(f"🎭 표정 표시 완료: {emotion}")
            
        except Exception as e:
            print(f"❌ 표정 그리기 중 오류: {e}")

    def _draw_eyes_normal(self, draw):
        """기본 눈"""
        draw.ellipse((10, 10, 40, 40), fill=1)
        draw.ellipse((90, 10, 120, 40), fill=1)

    def _draw_eyes_angry(self, draw):
        """화난 눈"""
        draw.polygon([(10, 10), (40, 15), (40, 25), (10, 25)], fill=1)
        draw.pieslice((10, 10, 40, 40), start=0, end=180, fill=1)
        draw.polygon([(90, 15), (120, 10), (120, 25), (90, 25)], fill=1)
        draw.pieslice((90, 10, 120, 40), start=0, end=-180, fill=1)

    def _draw_eyes_disgust(self, draw):
        """혐오하는 눈"""
        draw.pieslice((10, 10, 40, 40), start=0, end=180, fill=1)
        draw.pieslice((90, 10, 120, 40), start=0, end=-180, fill=1)

    def _draw_eyes_fear(self, draw):
        """무서워하는 눈"""
        draw.ellipse((10, 10, 40, 40), outline=1)
        draw.ellipse((90, 10, 120, 40), outline=1)
        draw.ellipse((20, 20, 30, 30), fill=1)
        draw.ellipse((100, 20, 110, 30), fill=1)
        draw.ellipse((15, 15, 35, 35), outline=1)
        draw.ellipse((95, 15, 115, 35), outline=1)
        
        # 공포 효과선들
        positions = [(25, 20, 15, 10, 5), (105, 110, 115, 120, 125)]
        for i, x_base in enumerate(positions[0]):
            draw.rectangle((x_base, 0, x_base, 5 + i*5), outline=1)
            draw.rectangle((x_base, 50 - i*5, x_base, 70), outline=1)
        
        for i, x_base in enumerate(reversed(positions[1])):
            draw.rectangle((x_base, 0, x_base, 5 + i*5), outline=1)
            draw.rectangle((x_base, 50 - i*5, x_base, 70), outline=1)

    def _draw_eyes_surprise(self, draw):
        """놀란 눈"""
        draw.ellipse((10, 10, 40, 50), fill=1)
        draw.ellipse((90, 10, 120, 50), fill=1)

    def _draw_eyes_happy(self, draw):
        """행복한 눈"""
        draw.polygon([(10, 25), (40, 25), (40, 30), (10, 25)], fill=1)
        draw.pieslice((10, 10, 40, 40), start=180, end=0, fill=1)
        draw.polygon([(90, 30), (120, 25), (120, 25), (90, 25)], fill=1)
        draw.pieslice((90, 10, 120, 40), start=180, end=-0, fill=1)

    def _draw_eyes_sad(self, draw):
        """슬픈 눈"""
        draw.polygon([(10, 25), (40, 20), (40, 30), (10, 25)], fill=1)
        draw.pieslice((10, 10, 40, 40), start=0, end=180, fill=1)
        draw.polygon([(90, 20), (120, 25), (120, 25), (90, 25)], fill=1)
        draw.pieslice((90, 10, 120, 40), start=0, end=180, fill=1)
        
        # 눈물
        draw.polygon([(110, 50), (115, 40), (120, 50)], fill=1)
        draw.ellipse((110, 45, 120, 60), fill=1)
    
    def cleanup(self):
        """리소스 정리"""
        try:
            if self.device:
                self.device.clear()
                self.device = None
            print("🧹 OLED 리소스 정리 완료")
        except Exception as e:
            print(f"⚠️ OLED 정리 중 오류: {e}")


# 테스트용 메인 함수
def main():
    """OLED 컨트롤러 테스트"""
    print("🎯 OLED 컨트롤러 테스트 시작")
    
    # 컨트롤러 초기화
    oled = OLEDEmotion()
    
    if not oled.is_initialized():
        print("❌ OLED 초기화 실패로 테스트 중단")
        return
    
    try:
        # 시작 화면 시퀀스
        print("📺 시작 화면 표시...")
        oled.show_startup_sequence()
        
        # 감정별 표정 테스트
        emotions = ["neutral", "happy", "sad", "angry", "fear", "surprise", "disgust"]
        
        print("\n🎭 감정별 표정 테스트:")
        for emotion in emotions:
            print(f"   표정: {emotion}")
            oled.draw_emotion_face(emotion)
            time.sleep(2)
        
        # 다시 중립으로
        oled.draw_emotion_face("neutral")
        print("\n✅ 테스트 완료!")
        
    except KeyboardInterrupt:
        print("\n👋 테스트 중단")
    finally:
        oled.cleanup()


if __name__ == "__main__":
    main()