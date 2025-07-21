import time
import threading
from typing import Optional, Callable
from gpiozero import Button

class GPIORecorder:
    def __init__(self, button_pin: int = 24):
        self.button_pin = button_pin
        self.pressed_flag = False
        self.recording_flag = False

        self.press_callback: Optional[Callable] = None # 버튼을 누를 때
        self.release_callback: Optional[Callable] = None # 버튼에서 손을 뗄 때

        self.debounce_time = 0.05 # 50ms
        self.last_event_time = 0

        self.initialized = False
        self.button = None

    def button_init(self):
        try:
            # gpiozero Button 객체 생성 (pull_up=True로 내부 풀업 저항 활성화)
            self.button = Button(self.button_pin, pull_up=True, bounce_time=0.05)
            
            # 콜백 함수 등록
            self.button.when_pressed = self._button_pressed_handler
            self.button.when_released = self._button_released_handler
            
            self.initialized = True
            print("✅ GPIO 초기화 성공")
            return True
            
        except Exception as e:
            print(f"❌ GPIO 초기화 실패: {e}")
            self.initialized = False
            return False

    def _button_pressed_handler(self):
        """버튼 눌림 이벤트 핸들러"""
        current_time = time.time()
        if current_time - self.last_event_time < self.debounce_time:
            return
        self.last_event_time = current_time

        if not self.pressed_flag:
            self.pressed_flag = True
            print("pressed")

            if self.press_callback:
                try:
                    self.press_callback()
                except Exception as e:
                    print(f"press error: {e}")

    def _button_released_handler(self):
        """버튼 뗌 이벤트 핸들러"""
        current_time = time.time()
        if current_time - self.last_event_time < self.debounce_time:
            return
        self.last_event_time = current_time

        if self.pressed_flag:
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
        """현재 버튼이 눌려있는지 확인 (gpiozero의 실시간 상태 + 내부 플래그)"""
        if not self.initialized:
            return False
        
        # gpiozero의 실시간 상태와 내부 플래그 모두 확인
        gpio_pressed = self.button.is_pressed if self.button else False
        return gpio_pressed or self.pressed_flag

    def wait_for_press(self, timeout: Optional[float] = None):
        """버튼이 눌릴 때까지 대기"""
        if not self.initialized:
            return False
            
        if self.button:
            # gpiozero의 내장 wait_for_press 사용
            return self.button.wait_for_press(timeout)
        
        # 백업 방식 (기존 로직)
        start_time = time.time()
        while not self.pressed_flag:
            if timeout and (time.time() - start_time > timeout):
                return False
            time.sleep(0.01)
        return True

    def wait_for_release(self, timeout: Optional[float] = None):
        """버튼이 뗄 때까지 대기"""
        if not self.initialized:
            return False
            
        if self.button:
            # gpiozero의 내장 wait_for_release 사용
            return self.button.wait_for_release(timeout)
        
        # 백업 방식 (기존 로직)
        start_time = time.time()
        while self.pressed_flag:
            if timeout and (time.time() - start_time > timeout):
                return False
            time.sleep(0.01)
        return True
        
    def cleanup(self):
        """GPIO 리소스 정리"""
        try:
            if self.initialized and self.button:
                self.button.close()  # gpiozero 리소스 정리
                self.button = None
                self.initialized = False
                print("🧹 GPIO 정리 완료")
        except Exception as e:
            print(f"GPIO 정리 중 오류: {e}")

# 전역 GPIO 컨트롤러 인스턴스
_gpio_recorder = None

def get_gpio_recorder(button_pin: int = 24) -> GPIORecorder:
    """전역 GPIO 컨트롤러 가져오기"""
    global _gpio_recorder
    
    if _gpio_recorder is None:
        _gpio_recorder = GPIORecorder(button_pin)
    
    return _gpio_recorder

def cleanup_gpio():
    """전역 GPIO 컨트롤러 정리"""
    global _gpio_recorder
    
    if _gpio_recorder:
        _gpio_recorder.cleanup()
        _gpio_recorder = None

# 테스트용 메인 함수
def main():
    print("GPIO 녹음 테스트 (gpiozero 버전)")
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
        print("콜백 함수 등록 완료")
        
        print("버튼을 눌러보세요...")
        print("Ctrl+C로 종료")
        print("-" * 50)
        
        # 무한 대기 (인터럽트 테스트)
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n프로그램 종료")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()