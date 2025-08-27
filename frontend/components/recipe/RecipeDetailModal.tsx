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
  recipe: RecipeRecommendation | null; // 목록에서 넘어온 요약 카드
  open: boolean;
  onClose: () => void;
}

const isObjId = (v: unknown) =>
  typeof v === "string" && /^[a-f0-9]{24}$/i.test(v.trim());

export default function RecipeDetailModal({ recipe, open, onClose }: Props) {
  // /recipes/card/{id} 에서 받아오는 "풀 데이터"
  const [full, setFull] = useState<RecipeFull | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    async function load() {
      // 닫힐 때나 recipe가 없으면 초기화
      if (!open || !recipe?.id) {
        if (alive) {
          setFull(null);
          setErr(null);
        }
        return;
      }

      const rid = String(recipe.id);

      // 외부/크롤 원본 등 ObjectId가 아닌 케이스는 서버 상세 호출 생략(요약만 사용)
      if (!isObjId(rid)) {
        if (alive) {
          setFull(null);
          setErr(null);
        }
        return;
      }

      setLoading(true);
      setErr(null);
      try {
        const data = await fetchCardFull(rid);
        if (!alive) return;
        setFull(data || null);
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
    };
  }, [open, recipe?.id]);

  if (!recipe) return null;

  // 헤더: 풀데이터 우선, 없으면 목록 프리뷰 폴백
  const title = full?.title ?? recipe.title ?? "";
  const imageUrl =
    (full?.imageUrl && String(full.imageUrl)) ||
    recipe.imageUrl ||
    "/images/recipe-placeholder.jpg";
  const tags = (full?.tags?.length ? full.tags : recipe.tags) || [];

  // 본문: 풀데이터 우선, 없으면 목록 프리뷰
  const ingredients =
    (full?.ingredients_full?.length ? full.ingredients_full : recipe.ingredients) || [];
  const steps =
    (full?.steps_full?.length ? full.steps_full : recipe.steps) || [];

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

        {/* 내용 */}
        <Box sx={{ p: 3 }}>
          <Typography variant="h5" fontWeight={700} gutterBottom>
            {title}
          </Typography>

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

          {/* 에러 안내(프리뷰 폴백은 계속 동작) */}
          {err && (
            <Typography variant="body2" color="error" sx={{ mb: 2 }}>
              {err}
            </Typography>
          )}

          {/* 재료: 모달에서는 slice 제거(전체) */}
          <Typography variant="h6" fontWeight={600} gutterBottom>
            재료{full?.ingredients_full?.length ? " (전체)" : ""}
          </Typography>
          <Box mb={3}>
            {ingredients.length ? (
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

          {/* 조리 과정: 모달에서는 slice 제거(전체) */}
          <Typography variant="h6" fontWeight={600} gutterBottom>
            조리 과정{full?.steps_full?.length ? " (전체)" : ""}
          </Typography>
          <Stack spacing={2} sx={{ maxHeight: 320, overflow: "auto", pr: 1 }}>
            {steps.length ? (
              steps.map((step, index) => (
                <Box key={`${index}-${String(step).slice(0, 12)}`} sx={{ display: "flex", gap: 2 }}>
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
