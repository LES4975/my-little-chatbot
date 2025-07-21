import pyaudio
import wave
import os
import tempfile
from dotenv import load_dotenv
from openai import OpenAI
import time
import threading
import select
import sys

# GPIO 컨트롤러 import
from GPIO.gpio_recorder import get_gpio_recorder

# .env 파일 로드
load_dotenv()

class STTTester:
    def __init__(self):
        # OpenAI 클라이언트 초기화
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # 오디오 설정
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000  # Whisper 최적화 샘플링 레이트
        
        # PyAudio 초기화
        self.audio = pyaudio.PyAudio()
        
        # GPIO 컨트롤러 (녹음 제어용)
        self.gpio_recorder = None
        
        # 녹음 제어 플래그
        self.recording_active = False
        self.recording_stopped = False
    
    def initialize_gpio(self):
        """GPIO 컨트롤러 초기화 (필요시)"""
        if self.gpio_recorder is None:
            self.gpio_recorder = get_gpio_recorder()
            # 이미 초기화되어 있다면 다시 초기화하지 않음
            if not self.gpio_recorder.initialized:
                if not self.gpio_recorder.button_init():
                    print("⚠️ GPIO 초기화 실패")
                    return False
        return True
    
    def gpio_record_audio(self, filename):
        """GPIO 택트 스위치 기반 오디오 녹음 (즉시 시작)"""
        if not self.initialize_gpio():
            print("❌ GPIO 초기화 실패")
            return False
        
        print("📝 녹음 시작! (버튼을 뗄 때까지 녹음됩니다)")
        
        stream = None
        try:
            stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                input_device_index=6,  # pulse 장치 사용
                frames_per_buffer=self.CHUNK
            )
            
            frames = []
            start_time = time.time()
            
            # GPIO 버튼이 눌려있는 동안 녹음 지속
            while self.gpio_recorder.is_pressed():
                try:
                    # 비블로킹 방식으로 오디오 데이터 읽기
                    data = stream.read(self.CHUNK, exception_on_overflow=False)
                    frames.append(data)
                    
                    # 진행상황 표시 (1초마다)
                    current_time = time.time()
                    elapsed = current_time - start_time
                    if int(elapsed) % 1 == 0 and len(frames) % (self.RATE // self.CHUNK) == 0:
                        print(f"⏱️  녹음 중... ({elapsed:.1f}초)")
                    
                    # 다른 스레드 실행을 위한 최소 대기
                    time.sleep(0.001)
                    
                except Exception as e:
                    print(f"⚠️ 녹음 중 오류: {e}")
                    break
            
            print("🛑 스위치에서 손을 뗐습니다. 녹음 종료!")
            
        except Exception as e:
            print(f"❌ 오디오 스트림 생성 실패: {e}")
            return False
            
        finally:
            # 스트림 정리 (예외 발생해도 반드시 실행)
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                    print("🧹 오디오 스트림 정리 완료")
                except Exception as e:
                    print(f"⚠️ 스트림 정리 중 오류: {e}")
        
        # WAV 파일로 저장
        if frames:
            try:
                wf = wave.open(filename, 'wb')
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
                wf.setframerate(self.RATE)
                wf.writeframes(b''.join(frames))
                wf.close()
                
                # 실제 녹음 시간 계산
                actual_duration = len(frames) * self.CHUNK / self.RATE
                print(f"📊 실제 녹음 시간: {actual_duration:.1f}초")
                return True
                
            except Exception as e:
                print(f"❌ 파일 저장 실패: {e}")
                return False
        else:
            print("❌ 녹음된 데이터가 없습니다.")
            return False
    
    def transcribe_audio(self, audio_file_path):
        """OpenAI Whisper API로 STT 변환"""
        print("🤖 음성을 텍스트로 변환 중...")
        
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ko"  # 한국어 설정
                )
            
            return transcript.text
        
        except Exception as e:
            print(f"❌ STT 변환 중 오류 발생: {e}")
            return None
    

    
    def gpio_record_and_transcribe(self, show_progress=True):
        """GPIO 기반 음성 녹음 및 STT 변환 (새로운 main.py용 메서드)"""
        temp_audio_file = tempfile.mktemp(suffix=".wav")
        
        try:
            if show_progress:
                print("🎤 GPIO 기반 음성 입력을 시작합니다...")
            
            # GPIO 기반 음성 녹음
            record_success = self.gpio_record_audio(temp_audio_file)
            if not record_success:
                return None
            
            if show_progress:
                print("🤖 음성을 텍스트로 변환 중...")
            
            # STT 변환
            transcript = self.transcribe_audio(temp_audio_file)
            
            if transcript and show_progress:
                print(f"✅ 음성 인식 완료: '{transcript}'")
            
            return transcript
            
        except Exception as e:
            if show_progress:
                print(f"❌ 음성 처리 중 오류: {e}")
            return None
        finally:
            if os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
    
    def simple_record_and_transcribe(self, show_progress=True):
        """GPIO 기반 음성 녹음 및 STT 변환 (main.py용 메서드)"""
        return self.gpio_record_and_transcribe(show_progress)
    

    
    def cleanup(self):
        """PyAudio 종료 및 리소스 정리"""
        try:
            if hasattr(self, 'audio') and self.audio:
                self.audio.terminate()
                print("🧹 PyAudio 리소스 정리 완료")
        except Exception as e:
            print(f"⚠️ PyAudio 정리 중 오류: {e}")
    
    def run_test(self):
        """GPIO 기반 STT 테스트 실행"""
        # 임시 파일 생성
        temp_audio_file = tempfile.mktemp(suffix=".wav")
        
        try:
            print("=" * 50)
            print("🎯 GPIO 기반 STT 테스트 시작")
            print("=" * 50)
            
            # GPIO 기반 오디오 녹음
            record_success = self.gpio_record_audio(temp_audio_file)
            if not record_success:
                print("❌ 녹음 실패")
                return None
            
            # STT 변환
            transcript = self.transcribe_audio(temp_audio_file)
            
            # 결과 출력
            print("\n" + "=" * 50)
            if transcript:
                print("✅ STT 결과:")
                print(f"📝 \"{transcript}\"")
                print("=" * 50)
                return transcript
            else:
                print("❌ STT 변환 실패")
                return None
        
        except Exception as e:
            print(f"❌ 테스트 중 오류 발생: {e}")
            return None
        
        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
                print("🗑️  임시 파일 정리 완료")
            
            # 리소스 정리
            self.cleanup()

def main():
    """메인 실행 함수"""
    # API 키 확인
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY가 .env 파일에 설정되지 않았습니다.")
        print("💡 .env 파일에 OPENAI_API_KEY=your-api-key 를 추가해주세요.")
        return
    
    # STT 테스트 실행
    tester = STTTester()
    result = tester.run_test()
    
    if result:
        print(f"\n🎉 테스트 성공! 인식된 텍스트: '{result}'")
    else:
        print("\n😞 테스트 실패")

if __name__ == "__main__":
    main()