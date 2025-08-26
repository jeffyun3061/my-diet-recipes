// components/Recipe/RecipeDetailModal.tsx
"use client";

import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  Typography,
  Box,
  Chip,
  Stack,
  IconButton,
  CardMedia,
  LinearProgress,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import type { RecipeRecommendation } from "@/types/image";
import { fetchCardFull } from "@/lib/api";

interface Props {
  recipe: RecipeRecommendation | null;
  open: boolean;
  onClose: () => void;
}

export default function RecipeDetailModal({ recipe, open, onClose }: Props) {
    // 추가: 풀 조리과정/재료 로딩 상태
  const [full, setFull] = useState<null | {
    ingredients_full: string[];
    steps_full: string[];
  }>(null);
  const [loading, setLoading] = useState(false);

  // 추가: 모달 열렸고 id 있으면 상세 호출
  useEffect(() => {
    let alive = true;
    async function load() {
      if (!open || !recipe?.id) {
        setFull(null);
        return;
      }
      setLoading(true);
      try {
        const f = await fetchCardFull(recipe.id);
        if (alive) {
          setFull({
            ingredients_full: f.ingredients_full || [],
            steps_full: f.steps_full || [],
          });
        }
      } catch {
        if (alive) setFull(null);
      } finally {
        if (alive) setLoading(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, [open, recipe?.id]);

  if (!recipe) return null;
  
   // 표시 우선순위: full 있으면 full → 없으면 썸네일 3줄
  const stepsToRender =
    full?.steps_full?.length ? full.steps_full : recipe.steps || [];
  const ingredientsToRender =
    full?.ingredients_full?.length
      ? full.ingredients_full
      : recipe.ingredients || [];

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 3, maxHeight: "90vh" },
      }}
    >
      <DialogContent sx={{ p: 0 }}>
        {/* 헤더 */}
        <Box sx={{ position: "relative", p: 2, pb: 0 }}>
          <IconButton
            onClick={onClose}
            sx={{
              position: "absolute",
              right: 8,
              top: 8,
              bgcolor: "background.paper",
              boxShadow: 2,
            }}
          >
            <CloseIcon />
          </IconButton>
        </Box>

        {/* 이미지 */}
        <CardMedia
          component="img"
          image={recipe.imageUrl || "/images/recipe-placeholder.jpg"}
          alt={recipe.title}
          sx={{
            height: 250,
            objectFit: "cover",
            mx: 2,
            borderRadius: 2,
          }}
        />

        {/* 로딩바 (full 로딩 중일 때만) */}
        {loading && (
          <Box sx={{ px: 3, pt: 1 }}>
            <LinearProgress />
          </Box>
        )}

        {/* 내용 */}
        <Box sx={{ p: 3 }}>
          <Typography variant="h5" fontWeight={700} gutterBottom>
            {recipe.title}
          </Typography>

          <Typography variant="body1" color="text.secondary" mb={3}>
            {recipe.description}
          </Typography>

          {/* 태그들 */}
          {recipe.tags && (
            <Box mb={3}>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {recipe.tags.map((tag, index) => (
                  <Chip
                    key={index}
                    label={tag}
                    size="small"
                    sx={{
                      bgcolor: "primary.light",
                      color: "primary.contrastText",
                    }}
                  />
                ))}
              </Stack>
            </Box>
          )}

          {/* 재료 */}
          <Typography variant="h6" fontWeight={600} gutterBottom>
            재료{full?.ingredients_full?.length ? " (전체)" : ""}
          </Typography>
          <Box mb={3}>
            {ingredientsToRender.map((ingredient, index) => (
              <Chip
                key={index}
                label={ingredient}
                size="small"
                variant="outlined"
                sx={{ mr: 1, mb: 1 }}
              />
            ))}
            {!ingredientsToRender.length && 
              <Typography variant="body2" color="text.secondary">
                제공된 재료 정보가 없습니다.
              </Typography>  
            } 
          </Box>

          {/* 조리 과정 */}
<Typography variant="h6" fontWeight={600} gutterBottom>
  조리 과정{full?.steps_full?.length ? " (전체)" : ""}
</Typography>

<Stack spacing={2} sx={{ maxHeight: 320, overflow: "auto", pr: 1 }}>
  {stepsToRender.length === 0 ? (
    <Typography variant="body2" color="text.secondary">
      조리 과정 정보가 없습니다.
    </Typography>
  ) : (
    stepsToRender.map((step, index) => (
      <Box key={index} sx={{ display: "flex", gap: 2 }}>
        <Box
          sx={{
            minWidth: 28,
            height: 28,
            borderRadius: "50%",
            bgcolor: "primary.main",
            color: "white",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "0.875rem",
            fontWeight: 600,
            mt: 0.25,
          }}
        >
          {index + 1}
        </Box>
        <Typography variant="body2" sx={{ flex: 1, pt: 0.5 }}>
          {step}
        </Typography>
      </Box>
    ))
  )}
</Stack>

        </Box>
      </DialogContent>
    </Dialog>
  );
}
