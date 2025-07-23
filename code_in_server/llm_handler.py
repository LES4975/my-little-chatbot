#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
이 코드는 실제로 라즈베리파이에서 동작하지 않습니다.
LLM을 가동할 수 있는 GPU가 마련된 환경에 이 파일이 있어야 합니다.
server.py와 같은 위치에 있어야 합니다.
"""
"""
Midm-2.0-Mini-Instruct 모델 로딩 및 추론 처리 모듈 (감정 분석 지원)
"""

import torch
import gc
import time
import re
from typing import Optional, Dict, List, Tuple
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig


class MidmLLMHandler:
    """Midm-2.0-Mini-Instruct 모델 핸들러 (감정 분석 지원)"""

    def __init__(self, model_name: str = "K-intelligence/Midm-2.0-Mini-Instruct"):
        """
        모델 핸들러 초기화

        Args:
            model_name: 사용할 모델 이름 (HuggingFace 모델 경로)
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.generation_config = None
        self.device = None

        # 감정 키워드 사전 (emotion_keyword.txt 기반)
        self.emotion_keywords = {
            "angry": ["화나", "분노", "짜증나", "빡쳐", "열받아", "악", "미치겠어"],
            "disgust": ["역겨워", "구역질", "토할", "혐오", "더러워", "징그러워"],
            "fear": ["무서워", "두려워", "겁나", "공포", "떨려", "불안해"],
            "happy": ["행복", "좋아", "사랑", "기뻐", "즐거워", "신나", "웃음", "감사"],
            "sad": ["슬퍼", "눈물", "우울", "울고", "외로워", "속상해", "힘들어"],
            "surprise": ["놀라워", "헉", "어머", "세상에", "헐", "와", "대박"]
        }

        # 시스템 프롬프트 (감정 키워드 지시 포함)
        emotion_list = ", ".join(self.emotion_keywords.keys())
        self.system_prompt = f"친절하고 공감해주는 태도로 대화해줘. 친구와 대화하듯 친근감있는 말투를 사용해. 대답은 반말로 해. 중요: 모든 응답은 반드시 2문장 이내로 대답하세요. 응답 마지막에 [emotion:감정키워드] 형태로 네 응답의 감정을 표시해줘. 사용 가능한 감정: {emotion_list}"

        # 모델 로드
        self._load_model()

    def _load_model(self):
        """모델 및 토크나이저 로드"""
        print(f"🔄 모델 로딩 시작: {self.model_name}")
        start_time = time.time()

        try:
            # GPU 강제 사용
            self.device = "cuda:0"
            print(f"🚀 GPU 사용: {torch.cuda.get_device_name(0)}")

            # 토크나이저 로드
            print("📚 토크나이저 로딩 중...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )

            # 모델 로드
            print("🤖 모델 로딩 중...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.bfloat16,
                trust_remote_code=True,
                device_map=self.device
            )

            # Generation Config 로드
            self.generation_config = GenerationConfig.from_pretrained(self.model_name)

            # 모델을 평가 모드로 설정
            self.model.eval()

            load_time = time.time() - start_time
            print(f"✅ 모델 로딩 완료! (소요시간: {load_time:.2f}초)")

            # GPU 메모리 사용량 출력
            self._print_gpu_memory_usage()

        except Exception as e:
            print(f"❌ 모델 로딩 실패: {e}")
            raise

    def generate_response(
            self,
            user_message: str,
            max_length: int = 100,  # 2문장은 보통 100토큰 이내
            temperature: float = 0.7,
            top_p: float = 0.9,
            do_sample: bool = True
    ) -> Tuple[str, str]:
        """
        사용자 메시지에 대한 AI 응답 생성 (감정 키워드 포함)

        Args:
            user_message: 사용자 입력 텍스트
            max_length: 최대 생성 토큰 수
            temperature: 생성 온도 (0.0 ~ 1.0)
            top_p: Top-p 샘플링 값
            do_sample: 샘플링 사용 여부

        Returns:
            Tuple[str, str]: (정리된 응답 텍스트, 감정 키워드)
        """
        if not self.model or not self.tokenizer:
            raise RuntimeError("모델이 로드되지 않았습니다.")

        try:
            # 대화 형식으로 메시지 구성
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message}
            ]

            # 토크나이저 적용
            input_ids = self.tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt"
            )

            # GPU로 이동
            input_ids = input_ids.to(self.device)

            # 생성 파라미터 설정
            generation_params = {
                "input_ids": input_ids,
                "generation_config": self.generation_config,
                "max_new_tokens": max_length,
                "temperature": temperature,
                "top_p": top_p,
                "do_sample": do_sample,
                "eos_token_id": self.tokenizer.eos_token_id,
                "pad_token_id": self.tokenizer.pad_token_id,
            }

            # GPU 메모리 효율을 위한 추론 모드
            with torch.no_grad():
                # 토큰 생성
                output_ids = self.model.generate(**generation_params)

            # 입력 부분 제거하고 응답만 추출
            response_ids = output_ids[0][input_ids.shape[1]:]
            response_text = self.tokenizer.decode(response_ids, skip_special_tokens=True)

            # 응답 정리 및 감정 추출
            cleaned_response, emotion = self._clean_response_and_extract_emotion(response_text)

            return cleaned_response, emotion

        except Exception as e:
            print(f"❌ 응답 생성 중 오류: {e}")
            raise

    def _clean_response_and_extract_emotion(self, response: str) -> Tuple[str, str]:
        """
        생성된 응답 텍스트 정리 및 감정 키워드 추출

        Args:
            response: 원본 응답 텍스트

        Returns:
            Tuple[str, str]: (정리된 응답 텍스트, 감정 키워드)
        """
        # 불필요한 공백 제거
        response = response.strip()

        # 감정 키워드 추출 (우선 처리)
        emotion = self._extract_emotion_from_response(response)

        # 감정 태그 제거 [emotion:키워드] 형태
        emotion_pattern = r'\[emotion:[a-zA-Z_]+\]'
        response = re.sub(emotion_pattern, '', response, flags=re.IGNORECASE)

        # 중복된 줄바꿈 제거
        while "\n\n\n" in response:
            response = response.replace("\n\n\n", "\n\n")

        # 특수 토큰 제거 (남아있을 경우)
        special_tokens = ["<|im_start|>", "<|im_end|>", "[/INST]", "</s>"]
        for token in special_tokens:
            response = response.replace(token, "")

        response = response.strip()

        # 2문장으로 제한 (마침표, 물음표, 느낌표 기준)
        sentences = re.split(r'[.!?]+', response)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) > 2:
            # 처음 2문장만 사용
            sentences = sentences[:2]
            # 원본에서 문장 부호 찾아서 복원
            result = ""
            for i, sentence in enumerate(sentences):
                # 원본에서 해당 문장 다음의 구두점 찾기
                match = re.search(re.escape(sentence) + r'([.!?]+)', response)
                if match:
                    result += sentence + match.group(1) + " "
                else:
                    result += sentence + ". "
            response = result.strip()

        return response, emotion

    def _extract_emotion_from_response(self, response: str) -> str:
        """
        응답에서 감정 키워드 추출

        Args:
            response: 응답 텍스트

        Returns:
            str: 감정 키워드 (기본값: "neutral")
        """
        # LLM이 지정한 감정 태그 확인 [emotion:키워드]
        emotion_match = re.search(r'\[emotion:([a-zA-Z_]+)\]', response, re.IGNORECASE)
        if emotion_match:
            specified_emotion = emotion_match.group(1).lower()
            if specified_emotion in self.emotion_keywords:
                return specified_emotion
        return "neutral"

    def generate_response_with_emotion(
            self,
            user_message: str,
            max_length: int = 100,
            temperature: float = 0.7
    ) -> Dict[str, str]:
        """
        감정 정보가 포함된 응답 생성 (API용 편의 메서드)

        Args:
            user_message: 사용자 입력 텍스트
            max_length: 최대 생성 길이
            temperature: 생성 온도

        Returns:
            Dict: {"response": 응답텍스트, "emotion": 감정키워드}
        """
        try:
            response_text, emotion = self.generate_response(
                user_message, max_length, temperature
            )
            
            return {
                "response": response_text,
                "emotion": emotion
            }
        except Exception as e:
            print(f"❌ 감정 응답 생성 중 오류: {e}")
            return {
                "response": "미안, 뭐라고 말을 해야 할지 모르겠어.",
                "emotion": "sad"
            }

    def generate_batch_responses(
            self,
            messages: List[str],
            max_length: int = 512,
            temperature: float = 0.7
    ) -> List[Dict[str, str]]:
        """
        배치 처리로 여러 메시지에 대한 응답 생성 (감정 포함)

        Args:
            messages: 사용자 메시지 리스트
            max_length: 최대 생성 길이
            temperature: 생성 온도

        Returns:
            List[Dict]: [{"response": 응답텍스트, "emotion": 감정키워드}, ...]
        """
        responses = []

        for message in messages:
            try:
                result = self.generate_response_with_emotion(message, max_length, temperature)
                responses.append(result)
            except Exception as e:
                print(f"⚠️  배치 처리 중 오류 (메시지: '{message[:30]}...'): {e}")
                responses.append({
                    "response": "미안, 뭐라고 말을 해야 할지 모르겠어.",
                    "emotion": "sad"
                })

        return responses

    def get_available_emotions(self) -> List[str]:
        """사용 가능한 감정 키워드 목록 반환"""
        return list(self.emotion_keywords.keys())

    def get_emotion_keywords(self, emotion: str) -> List[str]:
        """특정 감정의 키워드 목록 반환"""
        return self.emotion_keywords.get(emotion, [])

    def get_gpu_info(self) -> Optional[Dict]:
        """GPU 정보 반환"""
        try:
            gpu_info = {
                "device": torch.cuda.get_device_name(0),
                "total_memory_gb": torch.cuda.get_device_properties(0).total_memory / 1e9,
                "allocated_memory_gb": torch.cuda.memory_allocated(0) / 1e9,
                "reserved_memory_gb": torch.cuda.memory_reserved(0) / 1e9,
                "free_memory_gb": (torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(
                    0)) / 1e9
            }
            return gpu_info
        except Exception as e:
            return {"error": str(e)}

    def _print_gpu_memory_usage(self):
        """GPU 메모리 사용량 출력"""
        allocated = torch.cuda.memory_allocated(0) / 1e9
        reserved = torch.cuda.memory_reserved(0) / 1e9
        total = torch.cuda.get_device_properties(0).total_memory / 1e9

        print(f"📊 GPU 메모리 사용량:")
        print(f"   - 할당됨: {allocated:.2f} GB")
        print(f"   - 예약됨: {reserved:.2f} GB")
        print(f"   - 전체: {total:.2f} GB")
        print(f"   - 사용률: {(allocated / total) * 100:.1f}%")

    def clear_cache(self):
        """GPU 캐시 및 메모리 정리"""
        torch.cuda.empty_cache()
        gc.collect()
        print("🧹 GPU 캐시가 정리되었습니다.")
        self._print_gpu_memory_usage()

    def cleanup(self):
        """리소스 정리"""
        try:
            # 모델 메모리 해제
            if self.model:
                del self.model
            if self.tokenizer:
                del self.tokenizer

            # GPU 캐시 정리
            torch.cuda.empty_cache()

            gc.collect()
            print("🧹 모델 리소스가 정리되었습니다.")

        except Exception as e:
            print(f"⚠️  리소스 정리 중 오류: {e}")


# 테스트용 메인 함수
def main():
    """독립 실행 테스트 (감정 분석 포함)"""
    print("🎯 Midm-2.0 LLM 핸들러 테스트 (감정 분석)")
    print("="*50)

    # 핸들러 초기화
    handler = MidmLLMHandler()

    # 테스트 메시지들 (다양한 감정)
    test_messages = [
        "안녕하세요! 자기소개를 해주세요.",
        "오늘 너무 기분이 좋아요!",
        "시험에서 떨어져서 너무 슬퍼요...",
        "갑자기 무서운 일이 생겼어요.",
        "화가 너무 나서 미치겠어요!"
    ]

    print("\n🧪 감정 분석 응답 생성 테스트:")
    print("-" * 50)

    for i, message in enumerate(test_messages, 1):
        print(f"\n[테스트 {i}]")
        print(f"👤 사용자: {message}")

        start_time = time.time()
        try:
            result = handler.generate_response_with_emotion(
                message,
                max_length=100,
                temperature=0.7
            )
            elapsed_time = time.time() - start_time

            print(f"🤖 응답: {result['response']}")
            print(f"😊 감정: {result['emotion']}")
            print(f"⏱️  처리시간: {elapsed_time:.2f}초")

        except Exception as e:
            print(f"❌ 오류 발생: {e}")

        print("-" * 50)

    # 사용 가능한 감정 목록 출력
    print(f"\n📋 사용 가능한 감정: {handler.get_available_emotions()}")

    # GPU 정보 출력
    print("\n📊 최종 GPU 상태:")
    gpu_info = handler.get_gpu_info()
    for key, value in gpu_info.items():
        if isinstance(value, float):
            print(f"   - {key}: {value:.2f}")
        else:
            print(f"   - {key}: {value}")

    # 정리
    handler.cleanup()
    print("\n✅ 테스트 완료!")


if __name__ == "__main__":
    main()