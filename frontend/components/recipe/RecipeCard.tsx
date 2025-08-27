// components/Recipe/RecipeCard.tsx
"use client";

import React from "react";
import {
  Card,
  CardMedia,
  CardContent,
  Typography,
  Box,
  Chip,
  Stack,
} from "@mui/material";
import type { RecipeRecommendation } from "@/types/image";

interface Props {
  recipe: RecipeRecommendation;
  onClick: () => void;
}

// 리스트(그리드) 카드: 여기에서만 steps 3줄 미리보기 적용
export default function RecipeCard({ recipe, onClick }: Props) {
  // steps가 있을 때만 3줄까지 노출 (모달 상세에서는 slice 금지)
  const previewSteps =
    Array.isArray((recipe as any).steps) && (recipe as any).steps.length > 0
      ? ((recipe as any).steps as string[]).slice(0, 3)
      : [];

  // 설명 전처리: 앞 숫자목록 제거 + 줄바꿈 → 공백
  //   - "1. ..." / "1) ..." / "1 - ..." 같은 케이스도 처리
  const cleanedDesc = React.useMemo(() => {
    if (typeof (recipe as any).description !== "string") return "";
    return ((recipe as any).description as string)
      .replace(/^[\s]*\d+[.)-]?\s*/u, "") // 앞부분 숫자+구두점 제거
      .replace(/\n+/g, " ")               // 줄바꿈 → 공백
      .replace(/\s{2,}/g, " ")            // 이중 공백 정리
      .trim();
  }, [(recipe as any).description]);

  return (
    <Card
      sx={{
        width: "100%",
        height: 440, // 팀원 스타일 유지 (480 → 440)
        borderRadius: 3,
        boxShadow: "0 6px 24px rgba(0,0,0,0.12)",
        cursor: "pointer",
        transition: "all 0.2s ease",
        overflow: "hidden",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.16)",
        },
      }}
      onClick={onClick}
    >
      {/* 상단 태그 */}
      <Box sx={{ p: 1.5, pb: 0.5 }}>
        <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
          {recipe.tags?.slice(0, 3).map((tag, index) => (
            <Chip
              key={index}
              label={tag}
              size="small"
              sx={{
                height: 20,
                fontSize: "0.65rem",
                bgcolor: "primary.main",
                color: "primary.contrastText",
                fontWeight: 500,
                "& .MuiChip-label": { px: 0.8 },
              }}
            />
          ))}
        </Stack>
      </Box>

      {/* 중앙 이미지 */}
      <Box sx={{ px: 1.5, pb: 0.5 }}>
        <CardMedia
          component="img"
          image={recipe.imageUrl || "/images/recipe-placeholder.jpg"}
          alt={recipe.title}
          onError={(e) => {
            (e.target as HTMLImageElement).src = "/images/recipe-placeholder.jpg";
          }}
          sx={{
            height: 260, // 280 → 260
            objectFit: "cover",
            borderRadius: 2,
            width: "100%",
          }}
        />
      </Box>

      {/* 하단 정보 */}
      <CardContent sx={{ p: 1.5, pt: 0.5 }}>
        <Typography
          variant="h6"
          fontWeight={700}
          gutterBottom
          sx={{
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            fontSize: "1rem",
          }}
        >
          {recipe.title}
        </Typography>

        {/* 설명 2줄 컷 유지 + 전처리 텍스트 사용 */}
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            overflow: "hidden",
            textOverflow: "ellipsis",
            display: "-webkit-box",
            WebkitLineClamp: 2, // 3줄 → 2줄
            WebkitBoxOrient: "vertical",
            lineHeight: 1.3,
            fontSize: "0.8rem",
            mb: previewSteps.length ? 0.75 : 0, // steps가 있으면 살짝 간격
          }}
        >
          {cleanedDesc}
        </Typography>

        {/* 조리 단계 미리보기(최대 3줄) — 리스트 카드에서만 */}
        {previewSteps.length > 0 && (
          <Box
            component="ol"
            sx={{
              pl: 2.2,
              m: 0,
              display: "grid",
              gap: 0.25,
              fontSize: "0.78rem",
              lineHeight: 1.25,
              color: "text.secondary",
              listStyleType: "decimal",
            }}
          >
            {previewSteps.map((s, i) => (
              <li
                key={i}
                style={{
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
                title={s}
              >
                {s}
              </li>
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
