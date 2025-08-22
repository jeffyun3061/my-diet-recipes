# app/services/vision_openai.py
# 사진에서 재료 추출 (OpenAI) — 환각 방지 위해 JSON 스키마 강제

from __future__ import annotations
import base64, json
from typing import List, Dict, Any
from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

ING_SCHEMA = {
    "type": "object",
    "properties": {
        "ingredients": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "amount": {"type": "string"},
                    "confidence": {"type": "number"}
                },
                "required": ["name"]
            }
        }
    },
    "required": ["ingredients"]
}

def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")

async def extract_ingredients_from_images(images: List[bytes]) -> List[Dict[str, Any]]:
    parts = []
    for b in images:
        parts.append({
            "type": "input_image",
            "image_data": {"data": _b64(b), "mime_type": "image/jpeg"}
        })
    prompt = ("사진 속 식재료를 한국어로 추출하세요. 양이 보이면 amount에, 불확실하면 '~1개'처럼 적으세요. "
              "반드시 JSON으로, 아래 스키마를 따르세요.")

    rsp = client.responses.create(
        model="gpt-4o-mini",
        temperature=0.1,
        input=[{"role":"user","content":[{"type":"text","text":prompt}, *parts]}],
        response_format={"type":"json_schema","json_schema":{"name":"ingredients","schema":ING_SCHEMA}},
        max_output_tokens=400
    )
    try:
        obj = json.loads(rsp.output[0].content[0].text)
        return obj.get("ingredients", [])
    except Exception:
        return []
