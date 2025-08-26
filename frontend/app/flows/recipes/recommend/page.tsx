// app/flows/recipes/recommend/page.tsx
"use client";

import React, { useEffect, useState } from "react";
import { Box, Typography, Stack, Button } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import type { RecipeRecommendation } from "@/types/image";
import RecipeCarousel from "@/components/recipe/RecipeCarousel";
import RecipeDetailModal from "@/components/recipe/RecipeDetailModal";
import { fetchCardsFlat } from "@/lib/api"; // 카드 상세

export default function RecipeRecommendPage() {
  const [recommendations, setRecommendations] = useState<
    RecipeRecommendation[]
  >([]);
  const [selectedRecipe, setSelectedRecipe] =
    useState<RecipeRecommendation | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
  const stored = sessionStorage.getItem("recipeRecommendations");
  if (stored) {
    try {
      setRecommendations(JSON.parse(stored));
    } catch {
      loadFallback();
    }
  } else {
    loadFallback();
  }

  async function loadFallback() {
    try {
      const baseCards = await fetchCardsFlat(24); // /recipes/cards/flat
      setRecommendations(baseCards);
    } catch (e) {
      console.error(e);
    }
  }
}, []); // router 의존성 제거


  const handleCardClick = (recipe: RecipeRecommendation) => {
    setSelectedRecipe(recipe);
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedRecipe(null);
  };

  return (
    <Box
      sx={{
        height: "100vh", // 전체 뷰포트 높이
        display: "flex",
        flexDirection: "column",
        overflow: "hidden", // 전체 컨테이너 오버플로우 방지
      }}
    >
      {/* 상단 헤더 - 고정 */}
      {/* <Box
        sx={{
          flexShrink: 0, // 크기 고정
          p: 2,
          borderBottom: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
        }}
      >
        <Stack direction="row" alignItems="center" spacing={2}>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => router.back()}
            sx={{ minWidth: "auto", px: 1 }}
          >
            돌아가기
          </Button>
          <Typography variant="h6" fontWeight={700}>
            추천 레시피
          </Typography>
        </Stack>
      </Box> */}

      {/* 메인 콘텐츠 영역 - 스크롤 가능 */}
      <Box
        sx={{
          flex: 1, // 남은 공간 모두 사용
          overflowY: "auto", // 세로 스크롤만 허용
          overflowX: "hidden", // 가로 스크롤 방지
          pb: 2, // 하단 여백
        }}
      >
        {recommendations.length > 0 ? (
          <Box
            sx={{
              pt: 3, // 상단 여백
              px: 1, // 좌우 여백 최소화
            }}
          >
            <RecipeCarousel
              recipes={recommendations}
              onCardClick={handleCardClick}
            />
          </Box>
        ) : (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
            }}
          >
            <Typography variant="h6" color="text.secondary">
              추천 레시피를 불러오는 중...
            </Typography>
          </Box>
        )}
      </Box>

      {/* 상세 정보 모달 */}
      <RecipeDetailModal
        recipe={selectedRecipe}
        open={modalOpen}
        onClose={handleCloseModal}
      />
    </Box>
  );
}
