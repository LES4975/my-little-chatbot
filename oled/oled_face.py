"""
구버전 파일
"""

from PIL import Image, ImageDraw
from luma.oled.device import sh1106
from luma.core.interface.serial import i2c
import time

serial = i2c(port=1, address=0x3C)
device = sh1106(serial, rotate=2)  # 2 = 180도 회전



def draw_start_screen():
    image = Image.new("1", (128, 64), color=0)
    draw = ImageDraw.Draw(image)
    draw.text((30, 25), "START_ROBOT", fill=1)
    device.display(image)


# --------------------------
# 1. 감정 분류 함수
# --------------------------
def get_emotion(text):
    text = text.lower()
    if any(word in text for word in ["화나", "분노", "짜증", "빡쳐", "열받"]):
        return "angry"
    elif any(word in text for word in ["역겨", "구역질", "토할", "혐오"]):
        return "disgust"
    elif any(word in text for word in ["무서", "두려", "겁나", "공포", "떨려"]):
        return "fear"
    elif any(word in text for word in ["행복", "좋아", "사랑", "기뻐", "즐거워", "신나"]):
        return "happy"
    elif any(word in text for word in ["슬퍼", "눈물", "우울", "울고", "외로"]):
        return "sad"
    elif any(word in text for word in ["놀라", "헉", "어머", "세상에", "헐"]):
        return "surprise"
    else:
        return "neutral"

# --------------------------
# 2. 얼굴 표정 함수
# --------------------------
def draw_emotion_face(emotion):
    image = Image.new("1", (128, 64), color=0)
    draw = ImageDraw.Draw(image)

    # 공통 눈 기본형
    def draw_eyes_normal():
        draw.ellipse((10, 10, 40, 40), fill=1)
        draw.ellipse((90, 10, 120, 40), fill=1)

    # def draw_eyes_angry():
    #     draw.polygon([(10, 10), (40, 15), (40, 25), (10, 20)], fill=1)
    #     draw.polygon([(90, 15), (120, 10), (120, 20), (90, 25)], fill=1)

    def draw_eyes_angry():

        # 왼쪽 눈: 윗부분은 사선, 아래는 호(arc)
        draw.polygon([(10, 10), (40, 15), (40, 25), (10, 25)], fill=1)  # 윗부분 사선
        draw.pieslice((10, 10, 40, 40), start=0, end=180, fill=1)           # 아랫부분 곡선
        
        # 오른쪽 눈: 윗부분은 사선, 아래는 호(arc)
        draw.polygon([(90, 15), (120, 10), (120, 25), (90, 25)], fill=1)
        draw.pieslice((90, 10, 120, 40), start=0, end=-180, fill=1) 
        
    
    def draw_eyes_disgust():
        # draw.rectangle((10, 20, 50, 25), fill=1)
        # draw.rectangle((25, 25, 35, 30), fill=1)
        
        # draw.rectangle((80, 20, 120, 25), fill=1)
        # draw.rectangle((95, 25, 105, 30), fill=1)
        
        # 왼쪽 눈
        draw.pieslice((10, 10, 40, 40), start=0, end=180, fill=1)           
        
        # 오른쪽 눈
        draw.pieslice((90, 10, 120, 40), start=0, end=-180, fill=1) 


    def draw_eyes_fear():
        draw.ellipse((10, 10, 40, 40), outline=1)
        draw.ellipse((90, 10, 120, 40), outline=1)
        
        draw.ellipse((20, 20, 30, 30), fill=1)
        draw.ellipse((100, 20, 110, 30), fill=1)
        
        draw.ellipse((15, 15, 35, 35), outline=1)
        draw.ellipse((95, 15, 115, 35), outline=1)
        
        
        draw.rectangle((25, 0, 25, 5), outline=1)
        draw.rectangle((20, 0, 20, 10), outline=1)
        draw.rectangle((15, 0, 15, 15), outline=1)
        draw.rectangle((10, 0, 10, 20), outline=1)
        draw.rectangle((5, 0, 5, 30), outline=1)
        
        draw.rectangle((25, 50, 25, 70), outline=1)
        draw.rectangle((20, 45, 20, 70), outline=1)
        draw.rectangle((15, 40, 15, 70), outline=1)
        draw.rectangle((10, 35, 10, 70), outline=1)
        draw.rectangle((5, 15, 5, 70), outline=1)
        
        draw.rectangle((125, 0, 125, 30), outline=1)
        draw.rectangle((120, 0, 120, 20), outline=1)
        draw.rectangle((115, 0, 115, 15), outline=1)
        draw.rectangle((110, 0, 110, 10), outline=1)
        draw.rectangle((105, 0, 105, 5), outline=1)
        
        draw.rectangle((125, 15, 125, 70), outline=1)
        draw.rectangle((120, 35, 120, 70), outline=1)
        draw.rectangle((115, 40, 115, 70), outline=1)
        draw.rectangle((110, 45, 110, 70), outline=1)
        draw.rectangle((105, 50, 105, 70), outline=1)


    def draw_eyes_surprise():
        #draw.ellipse((15, 15, 35, 35), outline=1)
        #draw.ellipse((95, 15, 115, 35), outline=1)
        draw.ellipse((10, 10, 40, 50), fill=1)
        draw.ellipse((90, 10, 120, 50), fill=1)
        
        #draw.rectangle((55, 50, 75, 60), outline=1)

    def draw_eyes_happy():
        # 왼쪽 눈: 윗부분은 사선, 아래는 호(arc)
        draw.polygon([(10, 25), (40, 25), (40, 30), (10, 25)], fill=1)  # 윗부분 사선
        draw.pieslice((10, 10, 40, 40), start=180, end=0, fill=1)           # 아랫부분 곡선
        
        # 오른쪽 눈: 윗부분은 사선, 아래는 호(arc)
        draw.polygon([(90, 30), (120, 25), (120, 25), (90, 25)], fill=1)
        draw.pieslice((90, 10, 120, 40), start=180, end=-0, fill=1)


    def draw_eyes_sad():
        draw.polygon([(10, 25), (40, 20), (40, 30), (10, 25)], fill=1)  # 윗부분 사선
        draw.pieslice((10, 10, 40, 40), start=0, end=180, fill=1)           # 아랫부분 곡선
        
        # 오른쪽 눈: 윗부분은 사선, 아래는 호(arc)
        draw.polygon([(90, 20), (120, 25), (120, 25), (90, 25)], fill=1)
        draw.pieslice((90, 10, 120, 40), start=0, end=180, fill=1)
        
        
        #눈물
        draw.polygon([(110, 50), (115, 40), (120, 50)], fill=1)
        draw.ellipse((110, 45, 120, 60), fill=1)

    # 감정별 표정
    if emotion == "angry":
        draw_eyes_angry()
        # draw.arc((40, 50, 90, 70), 180, 360, fill=1)  # 입이 아래로
        draw.polygon([(55, 60), (65, 50), (75, 60)], fill=1)
    elif emotion == "disgust":
        draw_eyes_disgust()
        # draw.line((40, 55, 90, 55), fill=1, width=3)  # 직선 입
        draw.pieslice((50, 40, 80, 60), start=180, end=0, fill=1)
        draw.rectangle((50, 50, 80, 70), outline=1)
        draw.rectangle((55, 50, 75, 70), outline=1)
        draw.rectangle((60, 50, 70, 70), outline=1)
        draw.rectangle((65, 50, 65, 70), outline=1)
        
    elif emotion == "fear":
        draw_eyes_fear()
        #draw.ellipse((55, 45, 70, 60), outline=1)  # 둥근 입
        draw.rectangle((50, 50, 80, 60), outline=1)
        draw.pieslice((50, 55, 80, 65), start=180, end=0, fill=1) 
        
    elif emotion == "happy":
        draw_eyes_happy()
        draw.arc((40, 40, 90, 60), 0, 180, fill=1)  # 웃는 입
        
    elif emotion == "sad":
        draw_eyes_sad()
        # draw.arc((40, 50, 90, 70), 180, 360, fill=1)  # 입 아래로
        draw.arc((45, 50, 80, 65), 180, 360, fill=1)
        
    elif emotion == "surprise":
        draw_eyes_surprise()
        draw.ellipse((55, 45, 75, 60), fill=1)  # 놀란 입
    else:  # neutral
        draw_eyes_normal()
        # draw.line((40, 55, 90, 55), fill=1)  # 무표정
        draw.arc((50, 45, 80, 50), 0, 180, fill=1)
           
    device.display(image)

# --------------------------
# 3. 실행 루프
# --------------------------
if __name__ == "__main__":
    try:
        draw_start_screen()
        
        time.sleep(3)
        draw_emotion_face("neutral")
        
        while True:
            user_input = input("대화 입력: ")  # 실제 환경에서는 STT 결과가 여기에 들어옴
            emotion = get_emotion(user_input)
            print(f"[감정 분석] {user_input} -> {emotion}")
            draw_emotion_face(emotion)
    except KeyboardInterrupt:
        device.clear()
        print("프로그램 종료")
