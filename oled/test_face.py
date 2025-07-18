from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from PIL import Image
import time
import glob

# I2C 
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

#image file loading
frames = sorted(glob.glob("faces/image.png")) #faces 

while True:
    for frame in frames:
        image = Image.open(frame).convert("1").resize((128, 64))
        device.display(image)
        time.sleep(10)
        
        



