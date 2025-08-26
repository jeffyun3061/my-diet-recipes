// lib/api.ts
import type { UploadedImage, RecipeRecommendation } from "@/types/image";

// 백엔드 베이스 URL (.env.local 에 NEXT_PUBLIC_API_BASE=http://localhost:8000)
const API =
  process.env.NEXT_PUBLIC_API_BASE?.trim() || "http://localhost:8000";

  // 긴 필드 정리 + steps/ingredients 3개 제한
  const normalizeRecipe = (r: any): RecipeRecommendation => ({
    id: String(r?.id ?? r?._id ?? ""),
    title: String(r?.title ?? ""),
    // summary 혹은 description 둘 중 있는 값 사용
    description: String(((r?.summary ?? r?.description ?? "") as string).replace(/\s+/g, " ")).slice(0, 90),
    ingredients: Array.isArray(r?.ingredients)
      ? r.ingredients.map((x: any) => String(x).trim()).filter(Boolean).slice(0, 3)
      : [],
    steps: Array.isArray(r?.steps)
      ? r.steps.map((s: any) => String(s).trim()).filter(Boolean).slice(0, 3)
      : [],
    imageUrl: String(r?.imageUrl ?? r?.image ?? ""),
    tags: Array.isArray(r?.tags)
      ? r.tags.map((t: any) => String(t).trim()).filter(Boolean)
      : [],
  });

  // 레시피 추천 API 호출
export const recommendRecipes = async (
  images: UploadedImage[]
): Promise<RecipeRecommendation[]> => {
  const formData = new FormData();

  // 최대 9장 + 파일만 전송
  images
    .filter((img) => !!img?.file)
    .slice(0, 9)
    .forEach((image, index) => {
      formData.append(`image_${index}`, image.file);
    });

  // // 실제 API 엔드포인트로 교체
  // const response = await fetch("/api/recipes/recommend", {
  //   method: "POST",
  //   body: formData,
  // });

  //  백엔드로 바로 호출
  const res = await fetch(`${API}/recipes/recommend`, {
    method: "POST",
    body: formData,
    credentials: "include", // anon_id 쿠키 주고받기
  });

  // 호환 이슈 대비: 실패 시 files[] 엔드포인트로 폴백
  if (!res.ok) {
    const fd = new FormData();
    images.forEach((img) => { if (img?.file) fd.append("files", img.file); });

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

    const data = await res.json()
    return Array.isArray(data) ? data.map(normalizeRecipe) : [];
};

//   if (!response.ok) {
//     throw new Error("레시피 추천 요청에 실패했습니다.");
//   }

//   return response.json();
// };
export type PreferencesIn = {
  sex: string;       // "남성" / "여성"
  age: number;
  heightCm: number;
  weightKg: number;
  diet: string;      // "저탄고지" 등 라벨
};

// 개인정보 저장
export const postPreferences = async (p: PreferencesIn) => {
  const res = await fetch(`${API}/preferences`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include", // anon_id 쿠키 주고받기
    body: JSON.stringify(p),
  });
  if (!res.ok) {
    let msg = "개인정보 저장에 실패했습니다.";
    try { msg = await res.text(); } catch {}
    throw new Error(msg);
  }
  return res.json(); // { ok:true, anonId, kcal_target, ... }
};

// 카드 목록(백엔드 flat 스키마) 불러오기
export async function fetchCardsFlat(limit = 30): Promise<RecipeRecommendation[]> {
  const res = await fetch(`${API}/recipes/cards/flat?limit=${limit}`, {
    cache: "no-store",
    credentials: "include",
  });
  if (!res.ok) {
    let msg = "카드 목록을 불러오지 못했습니다.";
    try { msg = await res.text(); } catch {}
    throw new Error(msg);
  }
  const raw = await res.json();
  return Array.isArray(raw) ? raw.map(normalizeRecipe) : [];
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
