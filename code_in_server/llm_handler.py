#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
이 코드는 실제로 라즈베리파이에서 동작하지 않습니다.
LLM을 가동할 수 있는 GPU가 마련된 환경에 이 파일이 있어야 합니다.
server.py와 같은 위치에 있어야 합니다.
"""

"""
Midm-2.0-Mini-Instruct 모델 로딩 및 추론 처리 모듈
"""

import torch
import gc
import time
from typing import Optional, Dict, List
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig


class MidmLLMHandler:
    """Midm-2.0-Mini-Instruct 모델 핸들러"""
    
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
        
        # 시스템 프롬프트
        self.system_prompt = "Mi:dm(믿:음)은 KT에서 개발한 AI 기반 어시스턴트입니다. 친절하고 도움이 되는 방식으로 대화합니다. 중요: 모든 응답은 반드시 2문장 이내로 간결하게 작성하세요."
        
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
    ) -> str:
        """
        사용자 메시지에 대한 AI 응답 생성
        
        Args:
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
            
            # 응답 정리
            response_text = self._clean_response(response_text)
            
            return response_text
            
        except Exception as e:
            print(f"❌ 응답 생성 중 오류: {e}")
            raise
    
    def _clean_response(self, response: str) -> str:
        """
        생성된 응답 텍스트 정리
        
        Args:
            response: 원본 응답 텍스트
        
        Returns:
            str: 정리된 응답 텍스트
        """
        # 불필요한 공백 제거
        response = response.strip()
        
        # 중복된 줄바꿈 제거
        while "\n\n\n" in response:
            response = response.replace("\n\n\n", "\n\n")
        
        # 특수 토큰 제거 (남아있을 경우)
        special_tokens = ["<|im_start|>", "<|im_end|>", "[/INST]", "</s>"]
        for token in special_tokens:
            response = response.replace(token, "")
        
        response = response.strip()
        
        # 2문장으로 제한 (마침표, 물음표, 느낌표 기준)
        import re
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
        
        return response
    
    def generate_batch_responses(
        self,
        messages: List[str],
        max_length: int = 512,
        temperature: float = 0.7
    ) -> List[str]:
        """
        배치 처리로 여러 메시지에 대한 응답 생성
        
        Args:
            messages: 사용자 메시지 리스트
            max_length: 최대 생성 길이
            temperature: 생성 온도
        
        Returns:
            List[str]: 생성된 응답 리스트
        """
        responses = []
        
        for message in messages:
            try:
                response = self.generate_response(message, max_length, temperature)
                responses.append(response)
            except Exception as e:
                print(f"⚠️  배치 처리 중 오류 (메시지: '{message[:30]}...'): {e}")
                responses.append(f"죄송합니다. 응답을 생성하는 중 오류가 발생했습니다.")
        
        return responses
    
    def get_gpu_info(self) -> Optional[Dict]:
        """GPU 정보 반환"""
        try:
            gpu_info = {
                "device": torch.cuda.get_device_name(0),
                "total_memory_gb": torch.cuda.get_device_properties(0).total_memory / 1e9,
                "allocated_memory_gb": torch.cuda.memory_allocated(0) / 1e9,
                "reserved_memory_gb": torch.cuda.memory_reserved(0) / 1e9,
                "free_memory_gb": (torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)) / 1e9
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
        print(f"   - 사용률: {(allocated/total)*100:.1f}%")
    
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
    """독립 실행 테스트"""
    print("🎯 Midm-2.0 LLM 핸들러 테스트")
    print("="*50)
    
    # 핸들러 초기화
    handler = MidmLLMHandler()
    
    # 테스트 메시지들
    test_messages = [
        "안녕하세요! 자기소개를 해주세요.",
        "오늘 날씨가 어떤가요?",
        "인공지능의 미래에 대해 어떻게 생각하시나요?",
        "KT를 공정하게 평가해주세요."
    ]
    
    print("\n🧪 응답 생성 테스트:")
    print("-"*50)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n[테스트 {i}]")
        print(f"👤 사용자: {message}")
        
        start_time = time.time()
        try:
            response = handler.generate_response(
                message,
                max_length=256,
                temperature=0.7
            )
            elapsed_time = time.time() - start_time
            
            print(f"🤖 Mi:dm: {response}")
            print(f"⏱️  처리시간: {elapsed_time:.2f}초")
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
        
        print("-"*50)
    
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