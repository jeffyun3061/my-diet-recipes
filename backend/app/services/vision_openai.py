# app/services/vision_openai.py
# 사진에서 재료 추출 (OpenAI Vision)
# - Responses API(신) 우선 사용, 미지원/버전 차이 시 Chat Completions(구)로 폴백
# - JSON 파싱은 최대한 안전하게

from __future__ import annotations
import base64
import json
import os
from typing import List, Dict, Any

from fastapi import UploadFile

try:
    from openai import OpenAI  # v1 SDK
except Exception:
    OpenAI = None  # type: ignore

from app.core.config import settings


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


# JSON 스키마(권고)
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
        return []
    items = await extract_ingredients_from_images(images)
    names = [(i.get("name") or "").strip() for i in items if isinstance(i, dict)]
    names = [n for n in names if n]
    # 이름 원본 그대로(정규화는 라우터에서 수행)
    uniq = sorted(set(names))
    return uniq


async def extract_ingredients_from_images(images: List[bytes]) -> List[Dict[str, Any]]:
    
    # 이미지 바이트 배열 → [{'name': str, 'amount': str?, 'confidence': float?}, ...]
    # Responses API(신) + json_schema 사용 시도
    # 미지원/오류면 Chat Completions로 폴백
    
    client = _client()

    # 1) Responses API 시도
    try:
        # content 파트 구성: input_text + input_image
        parts: List[Dict[str, Any]] = [{"type": "input_text", "text": PROMPT}]
        for b in images:
            parts.append({
                "type": "input_image",
                "image_data": {"data": _b64(b), "mime_type": "image/jpeg"},
            })

        kwargs: Dict[str, Any] = dict(
            model="gpt-4o-mini",
            input=[{"role": "user", "content": parts}],
            max_output_tokens=400,
            temperature=0.1,
        )

        # 일부 구버전 SDK는 response_format 미지원 → 넣고 실패 시 빼고 재시도
        try:
            rsp = client.responses.create(
                **kwargs,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "ingredients", "schema": ING_SCHEMA},
                },
            )
        except TypeError:
            # response_format 인자를 모르는 버전 → 없이 한 번 더
            rsp = client.responses.create(**kwargs)

        text = _extract_text_safe(rsp)
        obj = json.loads(text or "{}")
        items = obj.get("ingredients", [])
        return [it for it in items if isinstance(it, dict)]
    except Exception:
        # 2) Chat Completions로 폴백
        try:
            content = [{"type": "text", "text": PROMPT}]
            for b in images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{_b64(b)}"},
                })
            chat = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.1,
                messages=[{"role": "user", "content": content}],
                # chat.completions는 json_schema 미지원 → 강한 지시어로 대체
                response_format={"type": "json_object"},  # 가능하면 JSON만 받도록
            )
            text = chat.choices[0].message.content if chat and chat.choices else ""
            obj = json.loads(text or "{}")
            items = obj.get("ingredients", [])
            return [it for it in items if isinstance(it, dict)]
        except Exception:
            return []


def _extract_text_safe(rsp: Any) -> str | None:
    
    # OpenAI Responses SDK의 리턴 구조가 버전에 따라 달라서 가능한 경로를 순서대로 시도.

    # 1) 직렬화된 필드
    try:
        return rsp.output[0].content[0].text  # type: ignore[attr-defined]
    except Exception:
        pass
    # 2) helper
    try:
        return rsp.output_text  # type: ignore[attr-defined]
    except Exception:
        pass
    # 3) dict로 풀어서
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
