#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Text-to-Speech API 모듈
사용자가 입력한 텍스트를 음성으로 변환하여 파일로 저장하고 재생합니다.
"""

import os
import subprocess
import sys
import tempfile
from google.cloud import texttospeech
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class GoogleTTSClient:
    def __init__(self):
        """Google TTS 클라이언트 초기화"""
        # Google Cloud 인증 확인
        self._check_google_credentials()
        
        try:
            self.client = texttospeech.TextToSpeechClient()
            print("✅ Google TTS 클라이언트 초기화 완료")
        except Exception as e:
            print(f"❌ Google TTS 클라이언트 초기화 실패: {e}")
            print("📋 Google Cloud 인증이 필요합니다. 설정 방법을 확인해주세요.")
            raise
    
    def _check_google_credentials(self):
        """Google Cloud 인증 설정 확인"""
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not credentials_path:
            print("⚠️  GOOGLE_APPLICATION_CREDENTIALS 환경변수가 설정되지 않았습니다.")
            print("📁 .env 파일에 다음과 같이 추가해주세요:")
            print("   GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json")
            raise ValueError("Google Cloud 인증 정보가 없습니다.")
        
        if not os.path.exists(credentials_path):
            print(f"❌ 인증 파일을 찾을 수 없습니다: {credentials_path}")
            print("📁 파일 경로를 확인해주세요.")
            raise FileNotFoundError(f"인증 파일이 존재하지 않습니다: {credentials_path}")
        
        print(f"✅ Google Cloud 인증 파일 확인: {credentials_path}")
        return True
    
    def text_to_speech(self, text, language_code="ko-KR", voice_name="ko-KR-Wavenet-A"):
        """
        텍스트를 음성으로 변환
        
        Args:
            text (str): 변환할 텍스트
            language_code (str): 언어 코드 (기본: ko-KR)
            voice_name (str): 음성 이름 (기본: ko-KR-Wavenet-A)
        
        Returns:
            bytes: 음성 데이터 (MP3 형식)
        """
        try:
            # 텍스트 입력 설정
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # 음성 설정
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )
            
            # 오디오 설정
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            # TTS 요청
            print(f"🎤 음성 합성 중: '{text[:30]}{'...' if len(text) > 30 else ''}'")
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            print("✅ 음성 합성 완료")
            return response.audio_content
            
        except Exception as e:
            print(f"❌ 음성 합성 실패: {e}")
            return None
    
    def simple_text_to_speech(self, text, language_code="ko-KR", voice_name="ko-KR-Wavenet-A", show_progress=True):
        """
        간소화된 텍스트를 음성으로 변환 (로그 최소화)
        
        Args:
            text (str): 변환할 텍스트
            language_code (str): 언어 코드
            voice_name (str): 음성 이름
            show_progress (bool): 진행상황 출력 여부
        
        Returns:
            bytes: 음성 데이터 (MP3 형식)
        """
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            if show_progress:
                print(f"🎤 음성 합성: '{text[:30]}{'...' if len(text) > 30 else ''}'")
            
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            if show_progress:
                print("✅ 음성 합성 완료")
            
            return response.audio_content
            
        except Exception as e:
            if show_progress:
                print(f"❌ 음성 합성 실패: {e}")
            return None
    
    def save_audio(self, audio_data, filename="output.mp3"):
        """
        음성 데이터를 파일로 저장
        
        Args:
            audio_data (bytes): 저장할 음성 데이터
            filename (str): 저장할 파일 이름
        
        Returns:
            str: 저장된 파일 경로 (성공 시), None (실패 시)
        """
        try:
            # 디렉토리가 없으면 생성
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, "wb") as audio_file:
                audio_file.write(audio_data)
            print(f"💾 음성 파일 저장 완료: {filename}")
            return filename
        except Exception as e:
            print(f"❌ 파일 저장 실패: {e}")
            return None
    
    def simple_save_audio(self, audio_data, filename="output.mp3", show_progress=True):
        """
        간소화된 음성 데이터 파일 저장 (로그 최소화)
        
        Args:
            audio_data (bytes): 저장할 음성 데이터
            filename (str): 저장할 파일 이름
            show_progress (bool): 진행상황 출력 여부
        
        Returns:
            str: 저장된 파일 경로 (성공 시), None (실패 시)
        """
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, "wb") as audio_file:
                audio_file.write(audio_data)
            
            if show_progress:
                print(f"💾 파일 저장: {filename}")
            
            return filename
        except Exception as e:
            if show_progress:
                print(f"❌ 파일 저장 실패: {e}")
            return None
    
    def play_with_mpg123(self, filename):
        """
        mpg123로 MP3 파일 재생
        
        Args:
            filename (str): 재생할 파일 경로
        """
        if not os.path.exists(filename):
            print(f"❌ 파일을 찾을 수 없습니다: {filename}")
            return False
        
        # mpg123 설치 여부 확인
        if not self._check_command_exists('mpg123'):
            print("❌ mpg123이 설치되지 않았습니다.")
            print("💡 설치 명령어: sudo apt install mpg123")
            return False
        
        try:
            subprocess.run(['mpg123', filename], check=True, capture_output=True)
            print(f"🔊 mpg123로 재생 완료: {filename}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 재생 실패: {e}")
            return False
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            return False
    
    def simple_play_with_mpg123(self, filename, show_progress=True):
        """
        간소화된 mpg123 재생 (로그 최소화)
        
        Args:
            filename (str): 재생할 파일 경로
            show_progress (bool): 진행상황 출력 여부
        """
        if not os.path.exists(filename):
            if show_progress:
                print(f"❌ 파일을 찾을 수 없습니다: {filename}")
            return False
        
        if not self._check_command_exists('mpg123'):
            if show_progress:
                print("❌ mpg123이 설치되지 않았습니다.")
            return False
        
        try:
            subprocess.run(['mpg123', filename], check=True, capture_output=True)
            if show_progress:
                print("🔊 재생 완료")
            return True
        except subprocess.CalledProcessError as e:
            if show_progress:
                print(f"❌ 재생 실패: {e}")
            return False
        except Exception as e:
            if show_progress:
                print(f"❌ 재생 오류: {e}")
            return False
    
    def text_to_speech_and_play(self, text, output_file=None, voice_name="ko-KR-Wavenet-A"):
        """
        텍스트를 음성으로 변환하고 바로 재생 (main.py용 통합 메서드)
        
        Args:
            text (str): 변환할 텍스트
            output_file (str): 저장할 파일 경로 (None이면 임시 파일)
            voice_name (str): 사용할 음성
        
        Returns:
            bool: 성공 여부
        """
        try:
            # 출력 파일 설정
            if output_file is None:
                output_file = tempfile.mktemp(suffix=".mp3")
                temp_file = True
            else:
                temp_file = False
            
            # TTS 변환
            audio_data = self.text_to_speech(text, voice_name=voice_name)
            if not audio_data:
                return False
            
            # 파일 저장
            saved_file = self.save_audio(audio_data, output_file)
            if not saved_file:
                return False
            
            # 재생
            success = self.play_with_mpg123(saved_file)
            
            # 임시 파일 정리
            if temp_file and os.path.exists(output_file):
                os.remove(output_file)
            
            return success
            
        except Exception as e:
            print(f"❌ TTS 및 재생 중 오류: {e}")
            return False
    
    def simple_text_to_speech_and_play(self, text, output_file=None, voice_name="ko-KR-Wavenet-A", show_progress=True):
        """
        간소화된 텍스트 음성 변환 및 재생 (로그 최소화)
        
        Args:
            text (str): 변환할 텍스트
            output_file (str): 저장할 파일 경로
            voice_name (str): 사용할 음성
            show_progress (bool): 진행상황 출력 여부
        
        Returns:
            bool: 성공 여부
        """
        try:
            if output_file is None:
                output_file = tempfile.mktemp(suffix=".mp3")
                temp_file = True
            else:
                temp_file = False
            
            # TTS 변환
            audio_data = self.simple_text_to_speech(text, voice_name=voice_name, show_progress=show_progress)
            if not audio_data:
                return False
            
            # 파일 저장
            saved_file = self.simple_save_audio(audio_data, output_file, show_progress=show_progress)
            if not saved_file:
                return False
            
            # 재생
            success = self.simple_play_with_mpg123(saved_file, show_progress=show_progress)
            
            # 임시 파일 정리
            if temp_file and os.path.exists(output_file):
                os.remove(output_file)
            
            return success
            
        except Exception as e:
            if show_progress:
                print(f"❌ TTS 및 재생 중 오류: {e}")
            return False
    
    def _check_command_exists(self, command):
        """명령어가 시스템에 설치되어 있는지 확인"""
        try:
            subprocess.run(['which', command], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

def show_available_voices():
    """사용 가능한 한국어 음성 목록 표시"""
    print("\n📢 사용 가능한 한국어 음성:")
    voices = [
        ("ko-KR-Wavenet-A", "여성, 자연스러운 음성"),
        ("ko-KR-Wavenet-B", "여성, 밝은 톤"),
        ("ko-KR-Wavenet-C", "남성, 깊은 음성"),
        ("ko-KR-Wavenet-D", "남성, 부드러운 음성"),
        ("ko-KR-Standard-A", "여성, 기본 음성"),
        ("ko-KR-Standard-B", "여성, 기본 음성"),
        ("ko-KR-Standard-C", "남성, 기본 음성"),
        ("ko-KR-Standard-D", "남성, 기본 음성")
    ]
    
    for i, (voice_name, description) in enumerate(voices, 1):
        print(f"  {i}. {voice_name}: {description}")
    
    return [voice[0] for voice in voices]

def main():
    """메인 함수 - 테스트 실행"""
    print("🎯 Google TTS API 테스트 프로그램")
    print("="*50)
    
    try:
        # TTS 클라이언트 초기화
        tts_client = GoogleTTSClient()
        
        # 사용 가능한 음성 표시
        available_voices = show_available_voices()
        
        print(f"\n📝 현재 기본 음성: ko-KR-Wavenet-A (여성, 자연스러운 음성)")
        print("💡 다른 음성을 사용하려면 코드에서 voice_name을 변경하세요.")
        
        print("\n" + "="*50)
        print("💬 텍스트를 입력하면 음성으로 변환하여 파일로 저장하고 재생합니다.")
        print("📌 종료하려면 'quit' 또는 'exit'를 입력하세요.")
        print("="*50)
        
        while True:
            # 사용자 입력 받기
            text = input("\n🖊️  변환할 텍스트를 입력하세요: ").strip()
            
            # 종료 명령 확인
            if text.lower() in ['quit', 'exit', '종료', 'q']:
                print("👋 프로그램을 종료합니다.")
                break
            
            # 빈 입력 확인
            if not text:
                print("⚠️  텍스트를 입력해주세요.")
                continue
            
            # 텍스트 길이 확인
            if len(text) > 1000:
                print("⚠️  텍스트가 너무 깁니다. (최대 1000자)")
                continue
            
            print(f"\n📊 입력 텍스트: {len(text)}자")
            
            # TTS 변환 및 재생
            success = tts_client.text_to_speech_and_play(text, "./audio_test/output.mp3")
            
            if success:
                print("🎉 음성 변환 및 재생 완료!")
            else:
                print("😞 음성 처리 실패")
            
            print("\n" + "-"*50)
    
    except KeyboardInterrupt:
        print("\n\n👋 사용자가 프로그램을 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 프로그램 실행 중 오류 발생: {e}")
    finally:
        print("🔧 프로그램 종료")

if __name__ == "__main__":
    main()