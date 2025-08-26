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
import type { RecipeFull } from "@/lib/api";

interface Props {
  recipe: RecipeRecommendation | null;
  open: boolean;
  onClose: () => void;
}

export default function RecipeDetailModal({ recipe, open, onClose }: Props) {
  // /full 결과만 사용
  const [full, setFull] = useState<RecipeFull | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // 모달 열릴 때마다 /full 호출 (프리뷰는 모달에서 사용 안 함)
  useEffect(() => {
    let alive = true;
    const ac = new AbortController();

    async function load() {
      if (!open || !recipe?.id) {
        setFull(null);
        setErr(null);
        return;
      }
      setLoading(true);
      setErr(null);
      try {
        const data = await fetchCardFull(recipe.id);
        if (!alive) return;
        setFull(data);
      } catch (e: any) {
        if (!alive) return;
        setErr(e?.message || "상세 불러오기 실패");
      } finally {
        if (alive) setLoading(false);
      }
    }

    load();
    return () => {
      alive = false;
      ac.abort();
    };
  }, [open, recipe?.id]);

  if (!recipe) return null;

  // 제목/이미지/태그는 풀 응답 우선, 없으면 목록 값 사용
  const title = full?.title ?? recipe.title ?? "";
  const imageUrl =
    (full?.imageUrl && String(full.imageUrl)) ||
    recipe.imageUrl ||
    "/images/recipe-placeholder.jpg";
  const tags = (full?.tags?.length ? full.tags : recipe.tags) || [];

  // 핵심: 모달에서는 풀데이터만 사용 (프리뷰 3줄로 대체하지 않음)
  const ingredients = full?.ingredients_full || [];
  const steps = full?.steps_full || [];

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{ sx: { borderRadius: 3, maxHeight: "90vh" } }}
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
            aria-label="close"
          >
            <CloseIcon />
          </IconButton>
        </Box>

        {/* 이미지 */}
        <CardMedia
          component="img"
          image={imageUrl}
          alt={title}
          sx={{ height: 250, objectFit: "cover", mx: 2, borderRadius: 2 }}
        />

        {/* 로딩바 */}
        {loading && (
          <Box sx={{ px: 3, pt: 1 }}>
            <LinearProgress />
          </Box>
        )}

        <Box sx={{ p: 3 }}>
          <Typography variant="h5" fontWeight={700} gutterBottom>
            {title}
          </Typography>

          {/* (설명은 /full 스키마에 없으니 목록의 description만 보조로) */}
          {recipe.description ? (
            <Typography variant="body1" color="text.secondary" mb={3}>
              {recipe.description}
            </Typography>
          ) : null}

          {/* 태그 */}
          {!!tags.length && (
            <Box mb={3}>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {tags.map((tag, i) => (
                  <Chip
                    key={`${tag}-${i}`}
                    label={tag}
                    size="small"
                    sx={{ bgcolor: "primary.light", color: "primary.contrastText" }}
                  />
                ))}
              </Stack>
            </Box>
          )}

          {/* 에러 메시지 */}
          {err && (
            <Typography variant="body2" color="error" sx={{ mb: 2 }}>
              {err}
            </Typography>
          )}

          {/* 재료: 풀데이터만 표시. 로딩 중/없음 처리 분리 */}
          <Typography variant="h6" fontWeight={600} gutterBottom>
            재료{ingredients.length ? " (전체)" : ""}
          </Typography>
          <Box mb={3}>
            {loading ? (
              <Typography variant="body2" color="text.secondary">
                재료 불러오는 중…
              </Typography>
            ) : ingredients.length ? (
              ingredients.map((ingredient, index) => (
                <Chip
                  key={`${ingredient}-${index}`}
                  label={ingredient}
                  size="small"
                  variant="outlined"
                  sx={{ mr: 1, mb: 1 }}
                />
              ))
            ) : (
              <Typography variant="body2" color="text.secondary">
                제공된 재료 정보가 없습니다.
              </Typography>
            )}
          </Box>

          {/* 조리 과정: 풀데이터만 표시. 프리뷰 3줄로 대체하지 않음 */}
          <Typography variant="h6" fontWeight={600} gutterBottom>
            조리 과정{steps.length ? " (전체)" : ""}
          </Typography>
          <Stack spacing={2} sx={{ maxHeight: 320, overflow: "auto", pr: 1 }}>
            {loading ? (
              <Typography variant="body2" color="text.secondary">
                조리 과정 불러오는 중…
              </Typography>
            ) : steps.length ? (
              steps.map((step, index) => (
                <Box key={`${index}-${step.slice(0, 12)}`} sx={{ display: "flex", gap: 2 }}>
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
            ) : (
              <Typography variant="body2" color="text.secondary">
                조리 과정 정보가 없습니다.
              </Typography>
            )}
          </Stack>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
