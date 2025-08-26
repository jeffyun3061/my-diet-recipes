# app/services/vision_google.py
# Google Cloud Vision API를 사용한 이미지 분석 — 시완 담당

from __future__ import annotations
from typing import List, Dict, Any, Optional
import base64
import logging
import os

try:
    from google.cloud import vision
    from google.cloud.vision_v1 import types
    from google.cloud import aiplatform
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False
    logging.warning("Google Cloud Vision not available. Install with: pip install google-cloud-vision")

logger = logging.getLogger(__name__)

class VisionNotReady(Exception):
    """Vision API가 준비되지 않았을 때 발생하는 예외"""
    pass

def _get_vision_client():
    """Google Cloud Vision 클라이언트 생성"""
    if not GOOGLE_VISION_AVAILABLE:
        raise VisionNotReady("Google Cloud Vision API가 설치되지 않았습니다")
    
    try:
        # 환경변수에서 인증 정보 확인
        if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            raise VisionNotReady("GOOGLE_APPLICATION_CREDENTIALS 환경변수가 설정되지 않았습니다")
        
        return vision.ImageAnnotatorClient()
    except Exception as e:
        raise VisionNotReady(f"Google Cloud Vision 클라이언트 생성 실패: {e}")

def _encode_image(image_bytes: bytes) -> types.Image:
    """이미지 바이트를 Google Vision API 형식으로 인코딩"""
    image = types.Image()
    image.content = image_bytes
    return image

async def analyze_image_labels(image_bytes: bytes) -> List[Dict[str, Any]]:
    """이미지에서 라벨(객체) 추출"""
    try:
        client = _get_vision_client()
        image = _encode_image(image_bytes)
        
        # 라벨 감지 요청
        response = client.label_detection(image=image)
        labels = response.label_annotations
        
        results = []
        for label in labels:
            results.append({
                "name": label.description,
                "confidence": label.score,
                "mid": label.mid,
                "type": "label"
            })
        
        return results
        
    except VisionNotReady:
        raise
    except Exception as e:
        logger.error(f"라벨 분석 실패: {e}")
        return []

async def analyze_image_objects(image_bytes: bytes) -> List[Dict[str, Any]]:
    """이미지에서 객체 감지"""
    try:
        client = _get_vision_client()
        image = _encode_image(image_bytes)
        
        # 객체 감지 요청
        response = client.object_localization(image=image)
        objects = response.localized_object_annotations
        
        results = []
        for obj in objects:
            results.append({
                "name": obj.name,
                "confidence": obj.score,
                "mid": obj.mid,
                "type": "object"
            })
        
        return results
        
    except VisionNotReady:
        raise
    except Exception as e:
        logger.error(f"객체 감지 실패: {e}")
        return []

async def analyze_image_text(image_bytes: bytes) -> List[Dict[str, Any]]:
    """이미지에서 텍스트 추출 (OCR)"""
    try:
        client = _get_vision_client()
        image = _encode_image(image_bytes)
        
        # 텍스트 감지 요청
        response = client.text_detection(image=image)
        texts = response.text_annotations
        
        results = []
        for text in texts:
            results.append({
                "text": text.description,
                "confidence": getattr(text, 'confidence', 0.0),
                "type": "text"
            })
        
        return results
        
    except VisionNotReady:
        raise
    except Exception as e:
        logger.error(f"텍스트 추출 실패: {e}")
        return []

async def analyze_image_ingredients(image_bytes: bytes) -> List[Dict[str, Any]]:
    """이미지에서 식재료 추출 (전문 분석)"""
    try:
        client = _get_vision_client()
        image = _encode_image(image_bytes)
        
        # 라벨 감지
        label_response = client.label_detection(image=image)
        labels = label_response.label_annotations
        
        # 객체 감지
        object_response = client.object_localization(image=image)
        objects = object_response.localized_object_annotations
        
        # 텍스트 감지
        text_response = client.text_detection(image=image)
        texts = text_response.text_annotations
        
        # 식재료 관련 키워드 필터링
        food_keywords = {
            "vegetable", "fruit", "meat", "fish", "chicken", "beef", "pork", "lamb",
            "tomato", "onion", "garlic", "potato", "carrot", "lettuce", "cabbage",
            "rice", "noodle", "bread", "egg", "milk", "cheese", "butter", "oil",
            "salt", "sugar", "pepper", "sauce", "spice", "herb", "grain", "bean",
            "감자", "양파", "마늘", "당근", "상추", "배추", "토마토", "고추",
            "쌀", "면", "빵", "계란", "우유", "치즈", "버터", "기름",
            "소금", "설탕", "후추", "소스", "향신료", "허브", "곡물", "콩"
        }
        
        ingredients = []
        
        # 라벨에서 식재료 찾기
        for label in labels:
            if label.description.lower() in food_keywords:
                ingredients.append({
                    "name": label.description,
                    "confidence": label.score,
                    "source": "label_detection",
                    "type": "ingredient"
                })
        
        # 객체에서 식재료 찾기
        for obj in objects:
            if obj.name.lower() in food_keywords:
                ingredients.append({
                    "name": obj.name,
                    "confidence": obj.score,
                    "source": "object_detection",
                    "type": "ingredient"
                })
        
        # 텍스트에서 식재료 찾기
        for text in texts:
            text_lower = text.description.lower()
            for keyword in food_keywords:
                if keyword in text_lower:
                    ingredients.append({
                        "name": text.description,
                        "confidence": getattr(text, 'confidence', 0.8),
                        "source": "text_detection",
                        "type": "ingredient"
                    })
                    break
        
        # 중복 제거 및 신뢰도 순 정렬
        unique_ingredients = {}
        for ing in ingredients:
            name = ing["name"].lower()
            if name not in unique_ingredients or ing["confidence"] > unique_ingredients[name]["confidence"]:
                unique_ingredients[name] = ing
        
        return sorted(unique_ingredients.values(), key=lambda x: x["confidence"], reverse=True)
        
    except VisionNotReady:
        raise
    except Exception as e:
        logger.error(f"식재료 분석 실패: {e}")
        return []

async def analyze_image_comprehensive(image_bytes: bytes) -> Dict[str, Any]:
    """이미지 종합 분석"""
    try:
        results = {
            "labels": await analyze_image_labels(image_bytes),
            "objects": await analyze_image_objects(image_bytes),
            "texts": await analyze_image_text(image_bytes),
            "ingredients": await analyze_image_ingredients(image_bytes)
        }
        
        return results
        
    except VisionNotReady:
        raise
    except Exception as e:
        logger.error(f"종합 분석 실패: {e}")
        return {
            "labels": [],
            "objects": [],
            "texts": [],
            "ingredients": []
        }
