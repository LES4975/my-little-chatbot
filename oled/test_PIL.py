from PIL import Image, ImageDraw
from luma.oled.device import sh1106
from luma.core.interface.serial import i2c
import time

serial =i2c(port=1, address=0x3C)
device = sh1106(serial)

def draw_smile_frame(step):
    image = Image.new("1", (128, 64), color=0)
    draw = ImageDraw.Draw(image)
    
    #face line ((x1:L-H, y1L-H, x2R-L, y2R-L))
    #draw.ellipse((34, 0, 94, 60), outline=1)
    
    #eye    (Left, Up, Right, Down)
    # draw.ellipse((10, 10, 40, 40), outline=1)
    # draw.ellipse((90, 10, 120, 40), fill=1)

    #mouth: 
    if step == 1:
        draw.arc((40, 40, 90, 60), 0, 180, fill=1)
        
        draw.ellipse((10, 10, 40, 40), fill=1)
        draw.ellipse((90, 10, 120, 40),  fill=1)
        
        
    elif step == 2:
        # draw.arc((48, 38, 80, 52), 0, 180, fill=1)  
        # draw.pieslice((10, 10, 40, 40), start=0, end=180, fill=1)   
        # draw.pieslice((90, 10, 120, 40), start=0, end=180, fill=1)  
        
        draw.arc((40, 40, 90, 50), 0, 180, fill=1)  
        
        draw.pieslice((10, 10, 40, 40), start=180, end=0, fill=1)   
        draw.pieslice((90, 10, 120, 40), start=180, end=-0, fill=1) 


        
        
    elif step == 3:
        draw.arc((40, 40, 90, 60), 0, 180, fill=1)
        
        draw.ellipse((10, 10, 40, 40),  fill=1)
        draw.ellipse((90, 10, 120, 40),  fill=1)
    device.display(image)
        
#animation play
while True:
    for i in [1, 2, 3, 2, 1]:
        draw_smile_frame(i)
        time.sleep(0.6)  






