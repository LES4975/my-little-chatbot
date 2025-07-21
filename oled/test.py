from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont
import time

serial = i2c(port=1, address=0x3c)
device = sh1106(serial)



with canvas(device) as draw:
    draw.text((10, 20), "Hello, SH1106!", fill="blue")
    
    
time.sleep(10)