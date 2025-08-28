# app/services/vision_openai.py
# 사진에서 재료 추출 (OpenAI Vision)
# - Chat Completions만 사용 (Responses API 경로 제거)
# - JSON 파싱은 최대한 안전하게

from __future__ import annotations
import base64
import json
import os
import logging
from typing import List, Dict, Any

from fastapi import UploadFile

try:
    from openai import OpenAI  # v1 SDK
except Exception:
    OpenAI = None  # type: ignore

from app.core.config import settings

log = logging.getLogger(__name__)


class VisionNotReady(Exception):
    # Vision 기능 준비 미완(패키지/키 없음)
    pass


def _client() -> "OpenAI":
    if OpenAI is None:
        raise VisionNotReady("openai SDK not installed")
    api_key = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise VisionNotReady("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


# JSON 스키마(권고용 설명)
ING_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "ingredients": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "amount": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["name"],
                "additionalProperties": True,
            },
        }
    },
    "required": ["ingredients"],
    "additionalProperties": False,
}

PROMPT = (
    "사진 속 식재료를 한국어로 최대한 구체적으로 추출하세요.\n"
    "- 결과는 반드시 JSON 하나만 출력합니다.\n"
    "- 스키마: { ingredients: [{ name: string, amount?: string, confidence?: number }] }\n"
    "- 양이 보이면 amount에 적고, 불확실하면 '~1개'처럼 표기하세요.\n"
    "- name만으로도 재료를 유추할 수 있게 일반명/대표명 사용(브랜드X).\n"
    "- 감자/고구마/무/비트 등 비슷한 뿌리채소는 혼동하지 마세요. 모호하면 confidence를 낮게 두세요.\n"
)

async def extract_ingredients_from_files(files: List[UploadFile]) -> List[str]:
    # 업로드 파일(List[UploadFile]) → 바이트 읽기 → Vision → 이름 리스트(중복 제거/정렬)
    images: List[bytes] = []
    for f in files:
        if not f:
            continue
        data = await f.read()
        if data:
            images.append(data)

    if not images:
        log.info("Vision skipped (no images)")
        return []

    items = await extract_ingredients_from_images(images)

    names = [(i.get("name") or "").strip() for i in items if isinstance(i, dict)]
    names = [n for n in names if n]

    # 폴백 금지: 비어있으면 빈 리스트 그대로 반환
    if not names:
        log.info("Vision returned no ingredients (n_images=%d)", len(images))
        return []

    # 이름 원본 그대로(정규화는 라우터에서 수행)
    uniq = sorted(set(names))
    return uniq


async def extract_ingredients_from_images(images: List[bytes]) -> List[Dict[str, Any]]:
    """
    이미지 바이트 배열 → [{'name': str, 'amount': str?, 'confidence': float?}, ...]
    - OpenAI Chat Completions(gpt-4o) + data URL 만 사용
    - JSON만 수신(response_format=json_object)
    """
    client = _client()

    content: List[Dict[str, Any]] = [{"type": "text", "text": PROMPT}]
    for b in images:
        # MIME은 대부분 jpeg로 취급, png/webp도 문제 없음
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{_b64(b)}"},
        })

    try:
        chat = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.1,
            messages=[{"role": "user", "content": content}],
            # Chat Completions는 json_schema 미지원 → JSON만 받도록 강제
            response_format={"type": "json_object"},
            max_tokens=400,
        )

        text = chat.choices[0].message.content if chat and chat.choices else ""
        if not text:
            log.warning("Chat Completions returned empty text")
            return []

        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            log.warning("Chat Completions returned non-JSON content trimmed; ignoring")
            return []

        items = obj.get("ingredients", [])
        return [it for it in items if isinstance(it, dict)]

    except Exception as e:
        log.exception("Vision chat completion failed: %s", e)
        return []


def _extract_text_safe(rsp: Any) -> str | None:
    """
    (과거 Responses API 호환 유틸) — 현재는 사용하지 않음. 보존만.
    """
    try:
        return rsp.output[0].content[0].text  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        return rsp.output_text  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        d = rsp.model_dump() if hasattr(rsp, "model_dump") else rsp
        out = d.get("output") or d.get("outputs") or []
        if isinstance(out, list) and out:
            cont = out[0].get("content") or []
            if isinstance(cont, list) and cont:
                txt = cont[0].get("text")
                if isinstance(txt, str):
                    return txt
    except Exception:
        pass
    return None
