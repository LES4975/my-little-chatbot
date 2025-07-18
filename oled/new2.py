from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from PIL import Image
import time

serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

expressions = ["neutral", "happy", "angry", "sad", "curious"]

while True:
    for expr in expressions:
        img = Image.open(f"faces/{expr}.png").convert("1")
        device.display(img)
        time.sleep(1)
