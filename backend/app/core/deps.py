# 공용 의존성/헬퍼 (익명 사용자 쿠키 발급 등)
import uuid
from fastapi import Request, Response

COOKIE = "anon_id"
MAX_AGE = 60 * 60 * 24 * 365 * 2  # 2년

def get_or_set_anon_id(request: Request, response: Response) -> str:
    # 쿠키 없으면 발급, 있으면 그대로 사용
    v = request.cookies.get(COOKIE)
    if not v:
        v = uuid.uuid4().hex
        response.set_cookie(COOKIE, v, max_age=MAX_AGE, httponly=True, samesite="lax")
    return v