from PIL import Image, ImageDraw
from luma.oled.device import sh1106
from luma.core.interface.serial import i2c
import time

serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

# --------------------------
# 1. Emotion Detection (Keyword-based)
# --------------------------
def get_emotion(text):
    text = text.lower()
    if any(word in text for word in ["angry", "mad", "furious", "rage", "annoyed"]):
        return "angry"
    elif any(word in text for word in ["disgust", "gross", "nasty", "yuck", "ew"]):
        return "disgust"
    elif any(word in text for word in ["fear", "scared", "afraid", "terrified", "nervous"]):
        return "fear"
    elif any(word in text for word in ["happy", "love", "great", "good", "joy", "fun", "smile"]):
        return "happy"
    elif any(word in text for word in ["sad", "cry", "tears", "unhappy", "depressed"]):
        return "sad"
    elif any(word in text for word in ["surprise", "wow", "omg", "shocked", "amazing"]):
        return "surprise"
    else:
        return "neutral"

# --------------------------
# 2. Face Drawing by Emotion
# --------------------------
def draw_emotion_face(emotion):
    image = Image.new("1", (128, 64), color=0)
    draw = ImageDraw.Draw(image)

    # Common eye styles
    def draw_eyes_normal():
        draw.ellipse((10, 10, 40, 40), fill=1)
        draw.ellipse((90, 10, 120, 40), fill=1)

    def draw_eyes_angry():
        draw.polygon([(10, 10), (40, 15), (40, 25), (10, 20)], fill=1)
        draw.polygon([(90, 15), (120, 10), (120, 20), (90, 25)], fill=1)

    def draw_eyes_disgust():
        draw.rectangle((10, 20, 40, 30), fill=1)
        draw.rectangle((90, 20, 120, 30), fill=1)

    def draw_eyes_fear():
        draw.ellipse((10, 10, 40, 40), outline=1)
        draw.ellipse((90, 10, 120, 40), outline=1)

    def draw_eyes_surprise():
        draw.ellipse((15, 15, 35, 35), outline=1)
        draw.ellipse((95, 15, 115, 35), outline=1)

    # Draw face based on emotion
    if emotion == "angry":
        draw_eyes_angry()
        draw.arc((40, 50, 90, 70), 180, 360, fill=1)  # mouth down
    elif emotion == "disgust":
        draw_eyes_disgust()
        draw.line((40, 55, 90, 55), fill=1, width=3)  # flat mouth
    elif emotion == "fear":
        draw_eyes_fear()
        draw.ellipse((50, 45, 80, 60), outline=1)  # open mouth
    elif emotion == "happy":
        draw_eyes_normal()
        draw.arc((40, 40, 90, 60), 0, 180, fill=1)  # smile
    elif emotion == "sad":
        draw_eyes_normal()
        draw.arc((40, 50, 90, 70), 180, 360, fill=1)  # sad mouth
    elif emotion == "surprise":
        draw_eyes_surprise()
        draw.ellipse((55, 45, 75, 60), outline=1)  # surprised mouth
    else:  # neutral
        draw_eyes_normal()
        draw.line((40, 55, 90, 55), fill=1)  # straight mouth

    device.display(image)

# --------------------------
# 3. Main Loop
# --------------------------
if __name__ == "__main__":
    try:
        while True:
            user_input = input("Enter text: ")  # In real use, replace with STT result
            emotion = get_emotion(user_input)
            print(f"[Emotion Detection] {user_input} -> {emotion}")
            draw_emotion_face(emotion)
    except KeyboardInterrupt:
        device.clear()
        print("Program stopped")
