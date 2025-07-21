import RPi.GPIO as GPIO
import time
import threading
from typing import Optional, Callable

class GPIORecorder:
    def __init__(self, button_pin:int = 24): # 18번째 위치의 GPIO 24
        self.button_pin = button_pin
        self.pressed_flag = False
        self.recording_flag = False

        self.press_callback: Optional[Callable] = None # 버튼을 누를 때
        self.release_callback: Optional[Callable] = None # 버튼에서 손을 뗄 때

        self.debounce_time = 0.05 # 50ms
        self.last_event_time = 0

        self.initialized = False

    def button_init(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        GPIO.add_event_detect(self.button_pin, GPIO.BOTH,
                                callback=self._button_event_handler,
                                bouncetime=50)
        
        self.initialized = True
        print("GPIO 초기화")
        return True

    def _button_event_handler(self, channel):
        current_time = time.time()
        if current_time - self.last_event_time < self.debounce_time:
            return
        self.last_event_time = current_time

        button_state = GPIO.input(self.button_pin) == 0 # LOW

        # 버튼 눌림 이벤트
        if button_state and not self.pressed_flag:
            # HIGH 상태인데다 이전에 pressed하지 않았다면
            self.pressed_flag = True
            print("pressed")

            if self.press_callback:
                try:
                    self.press_callback()
                except Exception as e:
                    print(f"press error: {e}")
        
        if not button_state and self.pressed_flag:
            # Low 상태인데다 이전에 pressed 했었다면
            self.pressed_flag = False
            print("released")

            if self.release_callback:
                try:
                    self.release_callback()
                except Exception as e:
                    print(f"released error: {e}")

    # pressed와 released 콜백 함수 등록
    def set_press_callback(self, callback: Callable):
        self.press_callback = callback
    
    def set_release_callback(self, callback: Callable):
        self.release_callback = callback

    def get_button_state(self) -> bool:
        if not self.initialized: # 초기화되지 않았다면
            return False
        return self.pressed_flag

    def is_pressed(self) -> bool:
        return self.get_button_state()

    def wait_for_press(self, timeout: Optional[float] = None):
        start_time = time.time()

        while not self.pressed_flag:
            if timeout and (time.time() - start_time > timeout):
                return False
            time.sleep(0.01)
        return True

    def wait_for_release(self, timeout: Optional[float] = None):
        start_time = time.time()
        
        while self.pressed_flag:
            if timeout and (time.time() - start_time > timeout):
                return False
            time.sleep(0.01)
        
        return True
        
    def cleanup(self): # GPIO 리소스 정리
        try:
            if self.initialized:
                GPIO.cleanup()
                self.initialized = False
                print("🧹 GPIO 정리 완료")
        except Exception as e:
            print(f"GPIO 정리 중 오류: {e}")

# 전역 GPIO 컨트롤러 인스턴스
_gpio_recorder = None

def get_gpio_recorder(button_pin: int = 24) -> GPIORecorder:
    # 전역 컨트롤러 가져 오기
    global _gpio_recorder
    
    if _gpio_recorder is None:
        _gpio_recorder = GPIORecorder(button_pin)
    
    return _gpio_recorder

def cleanup_gpio(): # 전역 컨트롤러 정리
    global _gpio_recorder
    
    if _gpio_recorder:
        _gpio_recorder.cleanup()
        _gpio_recorder = None

# 테스트용 메인 함수
def main():
    print("GPIO 녹음 테스트")
    print("=" * 50)
    
    def on_press():
        print("recording...")
    
    def on_release():
        print("recording completed!")
    
    try:
        # GPIO 컨트롤러 생성 및 초기화
        recorder = get_gpio_recorder()
        
        if not recorder.button_init():
            print("GPIO 초기화 실패")
            return
        
        # 콜백 함수 등록
        recorder.set_press_callback(on_press)
        recorder.set_release_callback(on_release)
        print("콜백 함수 등록")
        
        print("스위치 누르기")
        print("-" * 50)
    
    except KeyboardInterrupt:
        print("종료")
    except Exception as e:
        print(f"error: {e}")
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()