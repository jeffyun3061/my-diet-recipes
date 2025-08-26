// lib/api.ts
import type { UploadedImage, RecipeRecommendation } from "@/types/image";

/** --------------------------
 *  백엔드 베이스 URL
 *  (.env.local → NEXT_PUBLIC_API_BASE=http://localhost:8000)
 * -------------------------- */
const API = process.env.NEXT_PUBLIC_API_BASE?.trim() || "http://localhost:8000";

/** Blob -> File 강제 변환 (파일명이 없으면 생성) */
const toFile = (blob: Blob, fallbackName: string): File => {
  if (blob instanceof File) return blob;
  const type = blob.type || "image/jpeg";
  return new File([blob], fallbackName, { type });
};

/* --------------------------
   공통 유틸
-------------------------- */
const _toArr = (v: any): string[] =>
  Array.isArray(v)
    ? v.map((x) => String(x).trim()).filter(Boolean)
    : typeof v === "string"
    ? String(v)
        .split(/[#,;|\s]+/)
        .map((x) => x.trim())
        .filter(Boolean)
    : [];

const _uniq = (arr: string[]) => Array.from(new Set(arr));

const _isObjId = (v: unknown) =>
  typeof v === "string" && /^[a-f0-9]{24}$/i.test(v);

/** recipe_cards._id 우선 추출 (팀원 케이스 포함) */
const _pickCardId = (r: any): string | null => {
  if (_isObjId(r?.id)) return String(r.id); // 우리 백엔드: id = recipe_cards._id
  const cand =
    r?.cardId ??
    r?.card_id ??
    r?.card?._id ??
    r?.card?.id ??
    r?._id ??
    null;
  return _isObjId(cand) ? String(cand) : null;
};

/** variant 선택 (단일 variant 또는 variants[0]) */
const pickVariant = (r: any) =>
  r?.variant ?? (Array.isArray(r?.variants) ? r.variants[0] : null);

/** --------------------------
 *  팀원 타입에 맞춘 프리뷰 정규화
 *  - 카드 리스트 전용(ingredients/steps 3개 프리뷰)
 *  - 상세 모달은 /full API로 전체 사용
 * -------------------------- */
const normalizeRecipe = (r: any): RecipeRecommendation => {
  const v = pickVariant(r);

  const description = String(
    (
      (r?.summary ??
        r?.description ??
        r?.subtitle ??
        v?.summary ??
        "") as string
    ).replace(/\s+/g, " ")
  ).slice(0, 90);

  const ingredients = Array.isArray(r?.ingredients)
    ? r.ingredients.map((x: any) => String(x).trim()).filter(Boolean).slice(0, 3)
    : Array.isArray(v?.key_ingredients)
    ? v.key_ingredients.map((x: any) => String(x).trim()).filter(Boolean).slice(0, 3)
    : [];

  const steps = Array.isArray(r?.steps)
    ? r.steps.map((s: any) => String(s).trim()).filter(Boolean).slice(0, 3)
    : Array.isArray(v?.steps)
    ? v.steps.map((s: any) => String(s).trim()).filter(Boolean).slice(0, 3)
    : Array.isArray(v?.steps_compact)
    ? v.steps_compact.map((s: any) => String(s).trim()).filter(Boolean).slice(0, 3)
    : [];

  // 태그: 여러 키(tags/hashtags/chips/labels/categories 등)에서 모아 고유화
  const rawTags = _uniq([
    ..._toArr(r?.tags),
    ..._toArr(r?.hashTags),
    ..._toArr(r?.hashtags),
    ..._toArr(r?.chips),
    ..._toArr(r?.labels),
    ..._toArr(r?.tagList),
    ..._toArr(r?.categories),
    ..._toArr(r?.category),
    // variant 쪽에 태그류가 있을 수도 있으니 흡수
    ..._toArr(v?.tags),
    ..._toArr(v?.labels),
  ]);

  return {
    id: String(_pickCardId(r) ?? ""),
    title: String(r?.title ?? ""),
    description,
    ingredients,
    steps,
    imageUrl: String(r?.imageUrl ?? r?.image ?? ""),
    tags: rawTags,
  };
};

/* --------------------------
   레시피 추천 (이미지 업로드)
-------------------------- */
export const recommendRecipes = async (
  images: UploadedImage[]
): Promise<RecipeRecommendation[]> => {
  const formData = new FormData();

  // ✅ filename 반드시 전달 (없으면 임의 이름 생성)
  images
    .filter((img) => !!img?.file)
    .slice(0, 9)
    .forEach((image, index) => {
      const src = image.file as Blob; // Blob | File
      const ext =
        (src as any)?.type?.split?.("/")?.[1]?.trim() ||
        ((src as any as File)?.name?.split?.(".")?.pop()?.trim() || "jpg");
      const name =
        ((src as any as File)?.name?.trim?.() as string) ||
        `image_${index}.${ext || "jpg"}`;
      const file = toFile(src, name); // ✅ 항상 File 보장
      formData.append(`image_${index}`, file, file.name); // ✅ filename 포함
    });

  // 절대 headers에 multipart 직접 지정하지 말 것 (브라우저가 boundary 붙여야 함)
  const res = await fetch(`${API}/recipes/recommend`, {
    method: "POST",
    body: formData,
    credentials: "include", // anon_id 쿠키
  });

  // 실패 시 에러 본문 로그 + files[] 폴백 (동일하게 filename 포함)
  if (!res.ok) {
    try {
      console.warn("recommend error 1st:", await res.text());
    } catch {}

    const fd = new FormData();
    images.forEach((img, i) => {
      if (!img?.file) return;
      const src = img.file as Blob;
      const ext =
        (src as any)?.type?.split?.("/")?.[1]?.trim() ||
        ((src as any as File)?.name?.split?.(".")?.pop()?.trim() || "jpg");
      const name =
        ((src as any as File)?.name?.trim?.() as string) ||
        `file_${i}.${ext || "jpg"}`;
      const file = toFile(src, name);
      fd.append("files", file, file.name);
    });

    const res2 = await fetch(`${API}/recipes/recommend/files`, {
      method: "POST",
      body: fd,
      credentials: "include",
    });
    if (!res2.ok) {
      let msg = "레시피 추천 요청에 실패했습니다.";
      try {
        msg = await res2.text();
      } catch {}
      throw new Error(msg);
    }
    const data2 = await res2.json();
    return Array.isArray(data2) ? data2.map(normalizeRecipe) : [];
  }

  const data = await res.json();
  return Array.isArray(data) ? data.map(normalizeRecipe) : [];
};

/* --------------------------
   개인정보 저장
-------------------------- */
export type PreferencesIn = {
  sex: string; // "남성" / "여성"
  age: number;
  heightCm: number;
  weightKg: number;
  diet: string; // "저탄고지" 등 라벨
};

export const postPreferences = async (p: PreferencesIn) => {
  const res = await fetch(`${API}/preferences`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(p),
  });
  if (!res.ok) {
    let msg = "개인정보 저장에 실패했습니다.";
    try {
      msg = await res.text();
    } catch {}
    throw new Error(msg);
  }
  return res.json(); // { ok:true, anonId, kcal_target, ... }
};

/* --------------------------
   카드 목록(flat)
-------------------------- */
export async function fetchCardsFlat(
  limit = 30
): Promise<RecipeRecommendation[]> {
  const res = await fetch(`${API}/recipes/cards/flat?limit=${limit}`, {
    cache: "no-store",
    credentials: "include",
  });
  if (!res.ok) {
    let msg = "카드 목록을 불러오지 못했습니다.";
    try {
      msg = await res.text();
    } catch {}
    throw new Error(msg);
  }
  const raw = await res.json();
  return Array.isArray(raw) ? raw.map(normalizeRecipe) : [];
}

/* --------------------------
   상세 카드(full steps)
-------------------------- */
export type RecipeFull = {
  id: string;
  title: string;
  imageUrl?: string;
  tags: string[];
  ingredients_full: string[];
  steps_full: string[];
  source?: any;
  [k: string]: any;
};

export async function fetchCardFull(id: string): Promise<RecipeFull> {
  const url = `${API}/recipes/cards/${encodeURIComponent(id)}/full`;
  let res: Response;
  try {
    res = await fetch(url, { cache: "no-store" });
  } catch (e: any) {
    throw new Error(`상세 요청 실패(Fetch): ${e?.message || e}`);
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`상세 요청 ${res.status}: ${body || res.statusText}`);
  }
  return res.json();
}

// // 테스트용 Mock API - 업로드된 이미지를 사용한 다양한 레시피
// export const mockRecommendRecipes = async (
//   images: UploadedImage[]
// ): Promise<RecipeRecommendation[]> => {
//   await new Promise((resolve) => setTimeout(resolve, 2000));

//   return [
    
//     {
//       id: "1",
//       title: "아보카도 포케 볼",
//       description: "신선한 연어와 아보카도가 들어간 건강한 하와이안 포케 볼",
//       ingredients: [
//         "연어회 200g",
//         "아보카도 1개",
//         "현미밥 1공기",
//         "오이 1/2개",
//         "무순 적당량",
//         "참깨 1큰술",
//         "간장 2큰술",
//         "참기름 1큰술",
//         "고춧가루 1/2큰술",
//       ],
//       steps: [
//         "연어회를 한입 크기로 썰어 양념에 재워둡니다",
//         "아보카도를 슬라이스로 썰어 준비합니다",
//         "오이를 얇게 채 썰어 찬물에 담가둡니다",
//         "현미밥을 볼에 담고 연어, 아보카도, 오이를 올립니다",
//         "무순과 참깨를 뿌려 완성합니다",
//       ],
//       imageUrl: "/images/test.jpg", // 첫 번째 이미지 사용
//       tags: ["건강식", "포케볼", "다이어트", "하와이안"],
//     },
//     {
//       id: "2",
//       title: "그린 샐러드 볼",
//       description: "각종 채소와 견과류가 어우러진 영양 만점 샐러드",
//       ingredients: [
//         "로메인 상추 3잎",
//         "적양배추 50g",
//         "방울토마토 5개",
//         "아보카도 1/2개",
//         "호두 30g",
//         "올리브오일 2큰술",
//         "레몬즙 1큰술",
//         "발사믹식초 1큰술",
//         "소금, 후추 약간",
//       ],
//       steps: [
//         "모든 채소를 깨끗이 씻어 물기를 제거합니다",
//         "상추와 양배추를 한입 크기로 뜯어둡니다",
//         "방울토마토를 반으로 자르고 아보카도는 슬라이스합니다",
//         "드레싱 재료를 섞어 소스를 만듭니다",
//         "모든 재료를 볼에 담고 드레싱을 뿌려 완성합니다",
//       ],
//       imageUrl: "/images/test_copy.jpg", // 두 번째 이미지 사용
//       tags: ["샐러드", "채식", "다이어트", "건강식"],
//     },
//     {
//       id: "3",
//       title: "컬러풀 부처 볼",
//       description: "다양한 색깔의 채소와 곡물로 만든 영양 균형 완벽 한 그릇",
//       ingredients: [
//         "퀴노아 80g",
//         "적무 50g",
//         "당근 1/3개",
//         "브로콜리 100g",
//         "병아리콩 50g",
//         "아보카도 1/2개",
//         "올리브오일 3큰술",
//         "타히니 2큰술",
//         "레몬즙 1큰술",
//         "마늘 1쪽",
//       ],
//       steps: [
//         "퀴노아를 깨끗이 씻어 삶아줍니다",
//         "브로콜리는 데치고 당근은 채 썰어 둡니다",
//         "적무는 얇게 슬라이스하고 소금에 절여둡니다",
//         "타히니 드레싱을 만들어 둡니다",
//         "모든 재료를 예쁘게 담고 드레싱을 뿌려 완성합니다",
//       ],
//       imageUrl: "/images/test_copy_2.jpg", // 세 번째 이미지 사용
//       tags: ["부처볼", "퀴노아", "건강식", "완전식품"],
//     },
//     {
//       id: "4",
//       title: "레인보우 누들 볼",
//       description: "컬러풀한 채소와 면이 조화를 이룬 아시안 스타일 누들 볼",
//       ingredients: [
//         "소바면 100g",
//         "적양배추 80g",
//         "당근 1/2개",
//         "오이 1/2개",
//         "콩나물 100g",
//         "계란 1개",
//         "참기름 1큰술",
//         "간장 2큰술",
//         "식초 1큰술",
//         "설탕 1/2큰술",
//       ],
//       steps: [
//         "소바면을 삶아 찬물에 헹구어 둡니다",
//         "채소들을 곱게 채 썰어 준비합니다",
//         "계란을 얇게 부쳐 채 썰어 둡니다",
//         "양념장을 만들어 면과 함께 버무립니다",
//         "볼에 면을 담고 채소들을 색깔별로 올려 완성합니다",
//       ],
//       imageUrl: "/images/test_copy_3.jpg", // 네 번째 이미지 사용
//       tags: ["누들볼", "소바", "아시안", "채소"],
//     },
//     {
//       id: "5",
//       title: "프로틴 파워 볼",
//       description: "단백질이 풍부한 재료들로 구성된 운동 후 완벽한 한 그릇",
//       ingredients: [
//         "닭가슴살 150g",
//         "현미밥 1공기",
//         "삶은 계란 1개",
//         "아보카도 1/2개",
//         "체리토마토 5개",
//         "브로콜리 100g",
//         "올리브오일 2큰술",
//         "발사믹 글레이즈 1큰술",
//         "소금, 후추 약간",
//       ],
//       steps: [
//         "닭가슴살을 소금, 후추로 간해 구워줍니다",
//         "브로콜리는 살짝 데쳐 둡니다",
//         "계란을 삶아 반으로 자르고 아보카도는 슬라이스합니다",
//         "현미밥을 볼에 담고 모든 재료를 올립니다",
//         "발사믹 글레이즈를 뿌려 마무리합니다",
//       ],
//       imageUrl: "/images/test.jpg", // 첫 번째 이미지 재사용
//       tags: ["프로틴", "닭가슴살", "운동식", "고단백"],
//     },
//     {
//       id: "6",
//       title: "비건 파워 볼",
//       description: "식물성 재료만으로 만든 영양 가득한 완전 채식 한 그릇",
//       ingredients: [
//         "템페 100g",
//         "현미 80g",
//         "케일 50g",
//         "적무 30g",
//         "당근 1/4개",
//         "호박씨 20g",
//         "타히니 2큰술",
//         "간장 1큰술",
//         "메이플시럽 1큰술",
//         "라임즙 1큰술",
//       ],
//       steps: [
//         "현미를 삶아 식혀둡니다",
//         "템페를 구워 한입 크기로 썰어둡니다",
//         "케일은 마사지해서 부드럽게 만듭니다",
//         "모든 채소를 예쁘게 썰어 준비합니다",
//         "타히니 드레싱을 만들어 뿌리고 완성합니다",
//       ],
//       imageUrl: "/test_copy_2.jpg", // 세 번째 이미지 재사용
//       tags: ["비건", "채식", "템페", "완전식품"],
//     },
//   ];
// };
