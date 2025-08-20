# 시완님 구글 렌즈 API를 사용하여 이미지 분석을 수행하는 서비스
# 이미지 라벨 추출 — 시완 담당
# 지금은 더미. 나중에 Google Lens/GCV로 교체. 함수 시그니처는 유지할 것.
from typing import List

def analyze_labels(image_bytes: bytes) -> List[str]:
    # TODO: Google Lens/GCV API 호출 붙이기
    # 리턴: 정규화된 재료 토큰 리스트(소문자-하이픈)
    # 예: ["chicken-breast","lettuce","tomato","olive-oil"]
    return ["chicken-breast", "lettuce", "tomato", "olive-oil"]
