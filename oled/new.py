from PIL import Image, ImageDraw
import os

# 폴더 생성
os.makedirs("faces", exist_ok=True)

def create_face(expression, filename):
    image = Image.new("1", (128, 64), color=0)  # 1비트 흑백 이미지
    draw = ImageDraw.Draw(image)

    # 눈 (동그랗게)
    draw.ellipse((40, 20, 46, 26), fill=1)  # 왼쪽 눈
    draw.ellipse((80, 20, 86, 26), fill=1)  # 오른쪽 눈

    # 표정별 입 모양
    if expression == "neutral":  # 무표정
        draw.line((50, 44, 78, 44), fill=1, width=2)

    elif expression == "happy":  # 즐거움
        draw.arc((50, 38, 78, 50), start=0, end=180, fill=1)

    elif expression == "angry":  # 화남
        draw.line((50, 44, 78, 44), fill=1, width=2)
        # 눈썹
        draw.line((38, 18, 46, 16), fill=1, width=2)
        draw.line((80, 16, 88, 18), fill=1, width=2)

    elif expression == "sad":  # 슬픔
        draw.arc((50, 44, 78, 54), start=180, end=360, fill=1)

    elif expression == "curious":  # 궁금
        draw.arc((50, 40, 78, 50), start=0, end=180, fill=1)
        draw.ellipse((85, 35, 90, 40), outline=1)  # 작은 땀방울

    # 파일 저장
    image.save(filename)
    print(f"생성 완료: {filename}")

# 표정 리스트
expressions = ["neutral", "happy", "angry", "sad", "curious"]

# PNG 생성
for expr in expressions:
    create_face(expr, f"faces/{expr}.png")
