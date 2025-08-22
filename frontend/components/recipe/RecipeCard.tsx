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

// components/Recipe/RecipeCard.tsx에서 카드 높이를 줄임
export default function RecipeCard({ recipe, onClick }: Props) {
  return (
    <Card
      sx={{
        width: "100%",
        height: 440, // 480에서 440으로 줄임
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
      {/* 상단 태그들 */}
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
                "& .MuiChip-label": {
                  px: 0.8,
                },
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
            (e.target as HTMLImageElement).src =
              "/images/recipe-placeholder.jpg";
          }}
          sx={{
            height: 260, // 280에서 260으로 줄임
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
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            overflow: "hidden",
            textOverflow: "ellipsis",
            display: "-webkit-box",
            WebkitLineClamp: 2, // 3줄에서 2줄로 줄임
            WebkitBoxOrient: "vertical",
            lineHeight: 1.3,
            fontSize: "0.8rem",
          }}
        >
          {recipe.description}
        </Typography>
      </CardContent>
    </Card>
  );
}
