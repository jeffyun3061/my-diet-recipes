# backend/app/startup/indexes.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple

# Motor(비동기) 기준. (동기 PyMongo라면 아래 Sync 버전 참고)

async def ensure_indexes(db) -> None:
    """
    recipe_cards 컬렉션 인덱스를 안전하게 보장한다.
    - 이미 있으면 재생성하지 않음
    - 스펙(예: unique/sparse)이 다르면 드롭 후 재생성
    """
    coll = db.recipe_cards

    # Motor는 index_information() 가 async
    existing: Dict[str, Dict[str, Any]] = await coll.index_information()

    async def ensure(name: str, keys: List[Tuple[str, int]], **options: Any) -> None:
        if name in existing:
            idx = existing[name]  # 예: {'v':2,'key':[('id',1)],'unique':True,'sparse':True}
            # 필요한 옵션만 비교 (unique/sparse 정도면 충분)
            need_unique = bool(options.get("unique", False))
            need_sparse = options.get("sparse", None)

            unique_ok = (not need_unique) or bool(idx.get("unique", False))
            sparse_ok = (need_sparse is None) or (bool(idx.get("sparse", False)) == bool(need_sparse))

            if unique_ok and sparse_ok:
                return  # 이미 원하는 스펙
            # 스펙이 다르면 재생성
            await coll.drop_index(name)
        # 없거나 스펙이 달라 드롭했으면 생성
        await coll.create_index(keys, name=name, **options)

    # 충돌나던 id_1은 반드시 sparse + unique 로
    await ensure("id_1", [("id", 1)], unique=True, sparse=True)

    # 검색/필터용 인덱스들 (있으면 skip)
    await ensure("tags_1", [("tags", 1)])
    await ensure("key_ingredients_1", [("key_ingredients", 1)])
    await ensure("ingredients_1", [("ingredients", 1)])
    await ensure("ingredients_full_1", [("ingredients_full", 1)])
