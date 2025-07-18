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
        self.RECORD_SECONDS = 10
        
        # PyAudio 초기화
        self.audio = pyaudio.PyAudio()
    
    def record_audio(self, filename):
        """최대 10초간 오디오 녹음 (Enter 키로 조기 종료 가능)"""
        print("🎤 최대 10초간 음성을 녹음합니다...")
        print("💡 Enter 키를 누르면 언제든 녹음을 종료할 수 있습니다.")
        print("3... 2... 1... 시작!")
        
        stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        frames = []
        stop_recording = False
        
        def check_keyboard_input():
            """키보드 입력 감지 (별도 스레드)"""
            nonlocal stop_recording
            try:
                input()  # Enter 키 대기
                stop_recording = True
            except:
                pass
        
        # 키보드 입력 감지 스레드 시작
        keyboard_thread = threading.Thread(target=check_keyboard_input, daemon=True)
        keyboard_thread.start()
        
        total_frames = int(self.RATE / self.CHUNK * self.RECORD_SECONDS)
        
        # 녹음 루프
        for i in range(total_frames):
            if stop_recording:
                print("⏹️  사용자가 녹음을 중단했습니다.")
                break
                
            try:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                frames.append(data)
                
                # 진행상황 표시 (2초마다)
                if i % (int(self.RATE / self.CHUNK * 2)) == 0:
                    elapsed = int(i / (self.RATE / self.CHUNK))
                    remaining = self.RECORD_SECONDS - elapsed
                    print(f"⏱️  {remaining}초 남음... (Enter로 종료)")
            
            except Exception as e:
                print(f"⚠️ 녹음 중 오류: {e}")
                break
        
        if not stop_recording:
            print("⏰ 최대 녹음 시간(10초) 완료!")
        
        print("✅ 녹음 완료!")
        
        stream.stop_stream()
        stream.close()
        
        # WAV 파일로 저장
        if frames:  # 녹음된 데이터가 있을 때만 저장
            wf = wave.open(filename, 'wb')
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            # 실제 녹음 시간 계산
            actual_duration = len(frames) * self.CHUNK / self.RATE
            print(f"📊 실제 녹음 시간: {actual_duration:.1f}초")
        else:
            print("❌ 녹음된 데이터가 없습니다.")
    
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
    
    def cleanup(self):
        """PyAudio 종료"""
        self.audio.terminate()
    
    def run_test(self):
        """STT 테스트 실행"""
        # 임시 파일 생성
        temp_audio_file = tempfile.mktemp(suffix=".wav")
        
        try:
            print("=" * 50)
            print("🎯 STT 테스트 시작")
            print("=" * 50)
            
            # 오디오 녹음
            self.record_audio(temp_audio_file)
            
            # STT 변환
            transcript = self.transcribe_audio(temp_audio_file)
            
            # 결과 출력
            print("\n" + "=" * 50)
            if transcript:
                print("✅ STT 결과:")
                print(f"📝 \"{transcript}\"")
                print("=" * 50)
                
                # GPU 서버 전송 준비 (나중에 구현)
                print("💡 다음 단계: GPU 서버로 텍스트 전송")
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