# 이미지 라벨 추출 — 시완 담당
# Google Cloud Vision API를 사용한 실제 이미지 분석

from typing import List, Dict, Any
import logging

from app.services.vision_google import analyze_image_ingredients, VisionNotReady

logger = logging.getLogger(__name__)

def analyze_labels(image_bytes: bytes) -> List[str]:
    """이미지에서 라벨 추출 (동기 버전 - 하위 호환성)"""
    try:
        # 비동기 함수를 동기적으로 호출
        import asyncio
        loop = asyncio.get_event_loop()
        ingredients = loop.run_until_complete(analyze_image_ingredients(image_bytes))
        
        # 재료명만 추출
        return [ing["name"] for ing in ingredients]
        
    except VisionNotReady as e:
        logger.warning(f"Google Cloud Vision API 사용 불가: {e}")
        # 폴백: 더미 데이터 반환
        return ["chicken-breast", "lettuce", "tomato", "olive-oil"]
    except Exception as e:
        logger.error(f"이미지 분석 실패: {e}")
        return []

async def analyze_labels_async(image_bytes: bytes) -> List[str]:
    """이미지에서 라벨 추출 (비동기 버전)"""
    try:
        ingredients = await analyze_image_ingredients(image_bytes)
        return [ing["name"] for ing in ingredients]
        
    except VisionNotReady as e:
        logger.warning(f"Google Cloud Vision API 사용 불가: {e}")
        # 폴백: 더미 데이터 반환
        return ["chicken-breast", "lettuce", "tomato", "olive-oil"]
    except Exception as e:
        logger.error(f"이미지 분석 실패: {e}")
        return []

async def analyze_image_detailed(image_bytes: bytes) -> Dict[str, Any]:
    """이미지 상세 분석 (라벨, 객체, 텍스트, 재료)"""
    try:
        from app.services.vision_google import analyze_image_comprehensive
        return await analyze_image_comprehensive(image_bytes)
        
    except VisionNotReady as e:
        logger.warning(f"Google Cloud Vision API 사용 불가: {e}")
        # 폴백: 더미 데이터 반환
        return {
            "labels": [
                {"name": "Food", "confidence": 0.9, "type": "label"},
                {"name": "Vegetable", "confidence": 0.8, "type": "label"}
            ],
            "objects": [
                {"name": "Tomato", "confidence": 0.85, "type": "object"},
                {"name": "Lettuce", "confidence": 0.75, "type": "object"}
            ],
            "texts": [],
            "ingredients": [
                {"name": "tomato", "confidence": 0.85, "source": "object_detection", "type": "ingredient"},
                {"name": "lettuce", "confidence": 0.75, "source": "object_detection", "type": "ingredient"}
            ]
        }
    except Exception as e:
        logger.error(f"이미지 상세 분석 실패: {e}")
        return {
            "labels": [],
            "objects": [],
            "texts": [],
            "ingredients": []
        }
