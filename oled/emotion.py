#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
감정 분석 모듈 (초안)
텍스트에서 감정을 분석하여 반환합니다.
초안이라서 나중에 수정해야 해요!
"""

class EmotionAnalyzer:
    """텍스트 기반 감정 분석기"""
    
    def __init__(self):
        """감정 분석기 초기화"""
        # 감정별 키워드 사전 (초안 - 추후 개선 필요)
        self.emotion_keywords = {
            "angry": ["화나", "분노", "짜증", "빡쳐", "열받", "악", "미쳐"],
            "disgust": ["역겨", "구역질", "토할", "혐오", "더럽", "징그"],
            "fear": ["무서", "두려", "겁나", "공포", "떨려", "불안"],
            "happy": ["행복", "좋아", "사랑", "기뻐", "즐거워", "신나", "웃", "감사"],
            "sad": ["슬퍼", "눈물", "우울", "울고", "외로", "속상", "힘들"],
            "surprise": ["놀라", "헉", "어머", "세상에", "헐", "와", "대박"]
        }
    
    def analyze_emotion_basic(self, text: str) -> str:
        """
        기본 키워드 기반 감정 분석
        
        Args:
            text (str): 분석할 텍스트
            
        Returns:
            str: 감정 ("angry", "disgust", "fear", "happy", "sad", "surprise", "neutral")
        """
        if not text:
            return "neutral"
        
        text = text.lower()
        
        # 각 감정별 키워드 매칭 점수 계산
        emotion_scores = {}
        for emotion, keywords in self.emotion_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                emotion_scores[emotion] = score
        
        # 가장 높은 점수의 감정 반환
        if emotion_scores:
            return max(emotion_scores, key=emotion_scores.get)
        
        return "neutral"
    
    def analyze_emotion_advanced(self, text: str) -> str:
        """
        고급 감정 분석 (추후 구현 예정)
        - 자연어 처리 모델 활용
        - 문맥 고려
        - 감정 강도 측정
        
        Args:
            text (str): 분석할 텍스트
            
        Returns:
            str: 감정
        """
        # TODO: 향후 구현
        # - BERT, KoBERT 등 사전 훈련된 모델 활용
        # - 감정 분류 모델 fine-tuning
        # - 실시간 처리 최적화
        
        # 현재는 기본 분석기 사용
        return self.analyze_emotion_basic(text)
    
    def get_emotion(self, text: str, method: str = "basic") -> str:
        """
        감정 분석 메인 메서드
        
        Args:
            text (str): 분석할 텍스트
            method (str): 분석 방법 ("basic" 또는 "advanced")
            
        Returns:
            str: 감정
        """
        if method == "advanced":
            return self.analyze_emotion_advanced(text)
        else:
            return self.analyze_emotion_basic(text)


# 테스트용 함수
def main():
    """감정 분석 테스트"""
    analyzer = EmotionAnalyzer()
    
    test_texts = [
        "정말 행복해요!",
        "너무 화가 나네요",
        "슬퍼서 눈물이 나요",
        "깜짝 놀랐어요!",
        "정말 역겨워요",
        "무서워서 떨려요",
        "오늘 날씨가 좋네요"
    ]
    
    print("감정 분석 테스트:")
    print("-" * 30)
    
    for text in test_texts:
        emotion = analyzer.get_emotion(text)
        print(f"'{text}' → {emotion}")


if __name__ == "__main__":
    main()