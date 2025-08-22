# app/services/vision_openai.py
# 사진에서 재료 추출 (OpenAI) — 환각 방지 위해 JSON 스키마 강제
# 업로드 파일(List[UploadFile]) → 바이트 → Responses/Chat API 호출 → JSON 파싱
# SDK/키 미설치 시 앱이 죽지 않도록 VisionNotReady 예외를 던지고, 라우터에서 503 처리

from __future__ import annotations
import base64, json, os
from typing import List, Dict, Any
from fastapi import UploadFile

# OpenAI SDK가 없더라도 앱 기동은 살려야 함
try:
    from openai import OpenAI  # v1 SDK
except Exception:
    OpenAI = None  # type: ignore

from app.core.config import settings


# 예외/유틸
class VisionNotReady(Exception):
    """Vision 기능 준비 미완(패키지/키 없음)"""
    pass


def _client() -> "OpenAI":
    """OpenAI 클라이언트 생성 (없으면 명확한 예외)"""
    if OpenAI is None:
        raise VisionNotReady("openai SDK not installed")
    api_key = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise VisionNotReady("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


# 스키마/프롬프트
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
    "사진 속 식재료를 한국어로 추출하세요. "
    "양이 보이면 amount에, 불확실하면 '~1개'처럼 적으세요. "
    "반드시 JSON으로만 출력하고(설명 금지), 아래 스키마를 따르세요."
)

# 파일 엔트리(라우터에서 호출) — 업로드 파일 → 이름 리스트
async def extract_ingredients_from_files(files: List[UploadFile]) -> List[str]:
    """업로드 파일 리스트를 받아 재료 이름 배열만 반환."""
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
    return sorted(set(names))

# 핵심 호출 — byte 이미지 → JSON [{name, amount?, confidence?}, ...]
async def extract_ingredients_from_images(images: List[bytes]) -> List[Dict[str, Any]]:
    client = _client()  # SDK/키 준비 확인

    # Responses API 입력 파트 (base64 직접 전달)
    parts: List[Dict[str, Any]] = []
    for b in images:
        parts.append({
            "type": "input_image",
            "image_data": {"data": _b64(b), "mime_type": "image/jpeg"},
        })

    # 1) 최신 Responses API (json_schema 강제) 시도 — input_text / input_image
    payload = {
        "model": "gpt-4o-mini",
        "temperature": 0.1,
        "input": [{
            "role": "user",
            "content": [{"type": "input_text", "text": PROMPT}, *parts],
        }],
        "response_format": {"type": "json_schema", "json_schema": {"name": "ingredients", "schema": ING_SCHEMA}},
        "max_output_tokens": 400,
    }
    try:
        rsp = client.responses.create(**payload)
        text = _extract_text_safe(rsp)
        if text:
            obj = json.loads(text)
            items = obj.get("ingredients", [])
            return [it for it in items if isinstance(it, dict)]
    except TypeError as te:

        # 일부 구버전에서 response_format 미지원 → 폴백
        if "response_format" not in str(te):
            # 다른 타입오류는 상위에서 503으로 래핑될 수 있게 그대로 전달
            raise

        # 2) Responses API (스키마 없이 텍스트 JSON 유도)
        pf = dict(payload)
        pf.pop("response_format", None)
        try:
            rsp = client.responses.create(**pf)
            text = _extract_text_safe(rsp)
            if text:
                try:
                    obj = json.loads(text)
                    items = obj.get("ingredients", [])
                    return [it for it in items if isinstance(it, dict)]
                except Exception:
                    pass  # 아래 Chat API 폴백으로 진행
        except Exception:
            # 여기서도 실패하면 Chat 폴백으로
            pass

    # 3) Chat Completions 폴백 (data URL로 전달)
    try:
        data_parts = [
            {"type": "text", "text": PROMPT},
            *[
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{_b64(b)}"}}
                for b in images
            ],
        ]

        # json_object 강제(지원 안 하면 TypeError)
        try:
            rsp = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.1,
                messages=[{"role": "user", "content": data_parts}],
                response_format={"type": "json_object"},
            )
            text = rsp.choices[0].message.content  # type: ignore
        except TypeError:
            # response_format 미지원 → 일반 텍스트로 받고 JSON 파싱 시도
            rsp = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.1,
                messages=[{"role": "user", "content": data_parts}],
            )
            text = rsp.choices[0].message.content  # type: ignore

        if text:
            obj = json.loads(text)
            items = obj.get("ingredients", [])
            return [it for it in items if isinstance(it, dict)]
    except Exception as e:
        # 라우터에서 503로 래핑하므로 여기선 조용히 실패 전달
        raise e

    # 모든 경로가 실패한 경우
    return []


# SDK 버전별 안전 텍스트 추출
def _extract_text_safe(rsp: Any) -> str | None:
    # 1) 예전 경로
    try:
        return rsp.output[0].content[0].text  # type: ignore[attr-defined]
    except Exception:
        pass
    # 2) 최신 속성
    try:
        return rsp.output_text  # type: ignore[attr-defined]
    except Exception:
        pass
    # 3) dict로 변환해 탐색
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
