import asyncio
from typing import List
from app.db.init import get_db
from app.models.tags import CANON, is_valid

def _problems(card: dict) -> List[str]:
    probs: List[str] = []
    tags = card.get("tags") or []
    if not tags:
        probs.append("no-tags")
    if len(tags) > 4:
        probs.append(f"too-many-tags({len(tags)})")
    for t in tags:
        if not is_valid(t):
            probs.append(f"non-canon:{t}")
    # variants 내부도 점검(요약/단계 비었는지)
    vs = card.get("variants") or []
    if not vs:
        probs.append("no-variants")
    else:
        v0 = vs[0]
        if not v0.get("steps_compact"):
            probs.append("no-steps")
        if not v0.get("summary"):
            probs.append("no-summary")
    return probs

async def main(limit: int = 50):
    db = get_db()
    docs = await db["recipe_cards"].find({"source.site":"만개의레시피"}, {"_id":0}).limit(limit).to_list(length=limit)
    bad = []
    for d in docs:
        p = _problems(d)
        if p:
            bad.append((d.get("id"), d.get("title"), p, d.get("tags")))
    print(f"checked: {len(docs)}, issues: {len(bad)}")
    for bid, title, probs, tags in bad[:20]:
        print("-", bid, "/", title, "=>", probs, "| tags:", tags)

if __name__ == "__main__":
    asyncio.run(main())
