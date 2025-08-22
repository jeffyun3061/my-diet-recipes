// components/Recipe/RecipeDetailModal.tsx
"use client";

import React from "react";
import {
  Dialog,
  DialogContent,
  Typography,
  Box,
  Chip,
  Stack,
  IconButton,
  CardMedia,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import type { RecipeRecommendation } from "@/types/image";

interface Props {
  recipe: RecipeRecommendation | null;
  open: boolean;
  onClose: () => void;
}

export default function RecipeDetailModal({ recipe, open, onClose }: Props) {
  if (!recipe) return null;

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
            재료
          </Typography>
          <Box mb={3}>
            {recipe.ingredients.map((ingredient, index) => (
              <Chip
                key={index}
                label={ingredient}
                size="small"
                variant="outlined"
                sx={{ mr: 1, mb: 1 }}
              />
            ))}
          </Box>

          {/* 조리 과정 */}
          <Typography variant="h6" fontWeight={600} gutterBottom>
            조리 과정
          </Typography>
          <Stack spacing={2}>
            {recipe.steps.map((step, index) => (
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
                  }}
                >
                  {index + 1}
                </Box>
                <Typography variant="body2" sx={{ flex: 1, pt: 0.5 }}>
                  {step}
                </Typography>
              </Box>
            ))}
          </Stack>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
