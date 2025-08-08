#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Midm-2.0-Mini-Instruct 모델 로딩 및 추론 처리 모듈 (2단계 감정 분석)
"""

import torch
import gc
import time
import re
from typing import Optional, Dict, List, Tuple
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig


class MidmLLMHandler:
    """Midm-2.0-Mini-Instruct 모델 핸들러 (2단계 감정 분석)"""

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

        # 감정 키워드 목록
        self.emotion_keywords = ["happy", "sad", "angry", "fear", "surprise", "disgust", "neutral"]

        # 1단계: 대화 응답 생성용 시스템 프롬프트
        self.conversation_prompt = (
            "공감해주는 태도로 대화해줘. 정보를 전달하기보다는 사용자의 마음을 감정적으로 공감하는 것이 우선이야. 네가 겪었던 일을 대답에 사용하면 안 돼."
            "사용자가 걱정을 하면 달래주는 게  좋겠어."
            "친구와 대화하듯 친근감있는 말투를 사용해."
            "네 MBTI는 ISFP야."
            "대답은 반말로 해."
            "중요: 모든 응답은 반드시 2문장 이내로 대답해."
        )

        # 2단계: 감정 분석용 시스템 프롬프트
        emotion_list = ", ".join(self.emotion_keywords)
        self.emotion_analysis_prompt = (
            f"다음 사용자 메시지의 감정을 분석해서 가장 유사한 감정 키워드 하나만 답해줘."
            f"사용 가능한 감정: {emotion_list}. "
            f"기본적으로 neutral한 감정을 선택하면 되지만, 감정적인 메시지에 대해서는 neutral 이외의 감정으로 제시하는 게 좋아."
            f"감정 키워드 하나만 정확히 답해."
        )

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

    def _generate_llm_response(
            self,
            system_prompt: str,
            user_message: str,
            max_length: int = 100,
            temperature: float = 0.3,
            top_p: float = 0.9,
            do_sample: bool = True
    ) -> str:
        """
        LLM 응답 생성 (내부 공통 메서드)

        Args:
            system_prompt: 시스템 프롬프트
            user_message: 사용자 입력 텍스트
            max_length: 최대 생성 토큰 수
            temperature: 생성 온도 (0.0 ~ 1.0)
            top_p: Top-p 샘플링 값
            do_sample: 샘플링 사용 여부

        Returns:
            str: 생성된 응답 텍스트
        """
        if not self.model or not self.tokenizer:
            raise RuntimeError("모델이 로드되지 않았습니다.")

        try:
            # 대화 형식으로 메시지 구성
            messages = [
                {"role": "system", "content": system_prompt},
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

            return response_text.strip()

        except Exception as e:
            print(f"❌ LLM 응답 생성 중 오류: {e}")
            raise

    def generate_conversation_response(
            self,
            user_message: str,
            max_length: int = 100,
            temperature: float = 0.7
    ) -> str:
        """
        1단계: 순수한 대화 응답 생성

        Args:
            user_message: 사용자 입력 텍스트
            max_length: 최대 생성 토큰 수
            temperature: 생성 온도

        Returns:
            str: 대화 응답 텍스트
        """
        try:
            response = self._generate_llm_response(
                system_prompt=self.conversation_prompt,
                user_message=user_message,
                max_length=max_length,
                temperature=temperature
            )

            # 응답 정리 (2문장 제한)
            cleaned_response = self._clean_conversation_response(response)
            return cleaned_response

        except Exception as e:
            print(f"❌ 대화 응답 생성 중 오류: {e}")
            return "미안, 뭐라고 말을 해야 할지 모르겠어."

    def analyze_emotion(self, user_message: str) -> str:
        """
        2단계: 생성된 응답의 감정 분석

        Args:
            user_message: 분석할 응답 텍스트

        Returns:
            str: 감정 키워드 (happy, sad, angry, fear, surprise, disgust, neutral)
        """
        try:
            # 감정 분석 요청 메시지 구성
            analysis_request = f"분석할 텍스트: \"{user_message}\""

            emotion_response = self._generate_llm_response(
                system_prompt=self.emotion_analysis_prompt,
                user_message=analysis_request,
                max_length=10,  # 감정 키워드만 반환하므로 짧게
                temperature=0.3,  # 일관성을 위해 낮은 온도
                do_sample=False   # 일관성을 위해 샘플링 비활성화
            )

            # 응답에서 감정 키워드 추출
            detected_emotion = self._extract_emotion_keyword(emotion_response)
            return detected_emotion

        except Exception as e:
            print(f"❌ 감정 분석 중 오류: {e}")
            return "neutral"

    def _clean_conversation_response(self, response: str) -> str:
        """
        대화 응답 텍스트 정리

        Args:
            response: 원본 응답 텍스트

        Returns:
            str: 정리된 응답 텍스트
        """
        # 불필요한 공백 및 특수 토큰 제거
        response = response.strip()

        # 중복된 줄바꿈 제거
        while "\n\n\n" in response:
            response = response.replace("\n\n\n", "\n\n")

        # 특수 토큰 제거
        special_tokens = ["<|im_start|>", "<|im_end|>", "[/INST]", "</s>"]
        for token in special_tokens:
            response = response.replace(token, "")

        response = response.strip()

        # 2문장으로 제한 (마침표, 물음표, 느낌표 기준)
        sentences = re.split(r'[.!?]+', response)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) > 2:
            sentences = sentences[:2]
            # 원본에서 문장 부호 찾아서 복원
            result = ""
            for sentence in sentences:
                match = re.search(re.escape(sentence) + r'([.!?]+)', response)
                if match:
                    result += sentence + match.group(1) + " "
                else:
                    result += sentence + ". "
            response = result.strip()

        return response

    def _extract_emotion_keyword(self, emotion_response: str) -> str:
        """
        LLM 감정 분석 응답에서 키워드 추출

        Args:
            emotion_response: LLM의 감정 분석 응답

        Returns:
            str: 유효한 감정 키워드
        """
        # 응답 정리
        emotion_response = emotion_response.strip().lower()

        # 유효한 감정 키워드 찾기
        for emotion in self.emotion_keywords:
            if emotion in emotion_response:
                return emotion

        # 키워드를 찾지 못한 경우 기본값
        print(f"⚠️ 감정 키워드를 찾을 수 없음: '{emotion_response}' -> 'neutral'로 설정")
        return "neutral"

    def generate_response_with_emotion(
            self,
            user_message: str,
            max_length: int = 100,
            temperature: float = 0.7
    ) -> Dict[str, str]:
        """
        2단계 프로세스로 응답 생성 및 감정 분석

        Args:
            user_message: 사용자 입력 텍스트
            max_length: 최대 생성 길이
            temperature: 생성 온도

        Returns:
            Dict: {"response": 응답텍스트, "emotion": 감정키워드}
        """
        try:
            print(f"🎯 1단계: 대화 응답 생성...")
            # 1단계: 대화 응답 생성
            response_text = self.generate_conversation_response(
                user_message, max_length, temperature
            )

            print(f"🎯 2단계: 감정 분석...")
            # 2단계: 생성된 응답의 감정 분석
            emotion = self.analyze_emotion(user_message)

            print(f"✅ 완료 - 응답: '{response_text[:30]}...', 감정: {emotion}")
            
            return {
                "response": response_text,
                "emotion": emotion
            }

        except Exception as e:
            print(f"❌ 2단계 응답 생성 중 오류: {e}")
            return {
                "response": "미안, 뭐라고 말을 해야 할지 모르겠어.",
                "emotion": "sad"
            }

    def generate_response(
            self,
            user_message: str,
            max_length: int = 100,
            temperature: float = 0.7,
            top_p: float = 0.9,
            do_sample: bool = True
    ) -> Tuple[str, str]:
        """
        기존 인터페이스 호환성을 위한 메서드

        Returns:
            Tuple[str, str]: (응답 텍스트, 감정 키워드)
        """
        result = self.generate_response_with_emotion(user_message, max_length, temperature)
        return result["response"], result["emotion"]

    def generate_batch_responses(
            self,
            messages: List[str],
            max_length: int = 100,
            temperature: float = 0.7
    ) -> List[Dict[str, str]]:
        """
        배치 처리로 여러 메시지에 대한 응답 생성

        Args:
            messages: 사용자 메시지 리스트
            max_length: 최대 생성 길이
            temperature: 생성 온도

        Returns:
            List[Dict]: [{"response": 응답텍스트, "emotion": 감정키워드}, ...]
        """
        responses = []

        for i, message in enumerate(messages, 1):
            try:
                print(f"📝 배치 처리 {i}/{len(messages)}: '{message[:30]}...'")
                result = self.generate_response_with_emotion(message, max_length, temperature)
                responses.append(result)
            except Exception as e:
                print(f"⚠️ 배치 처리 중 오류 (메시지 {i}): {e}")
                responses.append({
                    "response": "미안, 뭐라고 말을 해야 할지 모르겠어.",
                    "emotion": "sad"
                })

        return responses

    def get_available_emotions(self) -> List[str]:
        """사용 가능한 감정 키워드 목록 반환"""
        return self.emotion_keywords.copy()

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
            print(f"⚠️ 리소스 정리 중 오류: {e}")


# 테스트용 메인 함수
def main():
    """독립 실행 테스트 (2단계 감정 분석)"""
    print("🎯 Midm-2.0 LLM 핸들러 테스트 (2단계 감정 분석)")
    print("="*50)

    # 핸들러 초기화
    handler = MidmLLMHandler()

    # 테스트 메시지들
    test_messages = [
        # "안녕하세요! 오늘 기분이 어떠세요?",
        # "시험에 합격했어요! 너무 기뻐요!",
        # "친구가 약속을 갑자기 취소해서 속상해요...",
        # "밤에 혼자 집에 있는데 무서운 소리가 나요",
        # "버스에서 누가 새치기해서 정말 화가 나요!",
        # # "이 바보야! 정말 실망이다.",
        # "저녁 메뉴 추천해줘.",
        # "버스를 탔는데, 옆사람한테서 땀냄새가 너무 많이 났어.",
        # "난 지금 아무 생각이 없어.",
        # "어두운 곳에 혼자 있었는데, 뒤돌아보기 무서웠어.",
        # "공용화장실에서 변기 뚜껑을 열어봤더니 똥이 있었어.",
        # # "네 뒤에 팔척귀신이 있어.",
        # "몸이 움직여지지 않아. 어떻게 해야 할지 모르겠어.",
        # "내가 이렇게 맨날 우울한 소리만 해도 괜찮아?",
        # "무서워",
        "나 오늘 기분이 안 좋아. 내 말 좀 들어 줄래?",
        "내일 중요한 발표가 있는데 실수할까봐 불안해.",
        "심지어 팀원들이 발표 자료를 제대로 준비 안 해왔어. 나에게 전부 떠넘기는 것 같던데? 너무 화가 나더라고.",
        "저녁밥이나 맛있게 먹고 기분 풀어야겠다. 저녁 메뉴 추천해 줄래?"
    ]

    print("\n🧪 2단계 감정 분석 테스트:")
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
            print(f"⏱️ 총 처리시간: {elapsed_time:.2f}초")

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