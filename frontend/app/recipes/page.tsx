// app/recipes/page.tsx
"use client";

import React, { useState } from "react";
import { Box, Typography, Alert } from "@mui/material";
import { useRouter } from "next/navigation";
import type { Route } from "next";

import ImageGrid from "@/components/image-upload/ImageGrid";
import BottomActionBar from "@/components/image-upload/BottomActionBar";
import type { UploadedImage } from "@/types/image";
import {
  validateImageFile,
  createImageId,
  MAX_IMAGES,
} from "@/data/imageUtils";
// import { mockRecommendRecipes } from "@/lib/api";  // 실제 API 호출로 교체
import { recommendRecipes } from "@/lib/api";

export default function RecipesPage() {
  const [images, setImages] = useState<UploadedImage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const router = useRouter();

  const handleFilesSelected = (files: File[]) => {
    setError("");

    const remainingSlots = MAX_IMAGES - images.length;
    const filesToAdd = files.slice(0, remainingSlots);

    const validImages: UploadedImage[] = [];
    const errors: string[] = [];

    filesToAdd.forEach((file) => {
      const validation = validateImageFile(file);
      if (validation) {
        errors.push(`${file.name}: ${validation}`);
      } else {
        validImages.push({
          id: createImageId(),
          file,
          url: URL.createObjectURL(file),
          name: file.name,
          size: file.size,
        });
      }
    });

    if (errors.length > 0) {
      setError(errors.join("\n"));
    }

    if (validImages.length > 0) {
      setImages((prev) => [...prev, ...validImages]);
    }

    if (files.length > remainingSlots) {
      setError(
        (prev) => prev + `\n최대 ${MAX_IMAGES}개까지만 업로드할 수 있습니다.`
      );
    }
  };

  const handleRemoveImage = (id: string) => {
    setImages((prev) => {
      const updated = prev.filter((img) => img.id !== id);
      const toRemove = prev.find((img) => img.id === id);
      if (toRemove) URL.revokeObjectURL(toRemove.url);
      return updated;
    });
  };

  const handleRecommendRecipes = async () => {
    if (images.length === 0) return;

    setLoading(true);
    setError("");

    try {
      // const recommendations = await mockRecommendRecipes(images);
      const recommendations = await recommendRecipes(images);
      sessionStorage.setItem(
        "recipeRecommendations",
        JSON.stringify(recommendations)
      );
      router.push("/flows/recipes/recommend" as Route);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "레시피 추천 중 오류가 발생했습니다."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ pb: 16 }}>
      {" "}
      {/* 하단 액션바 공간 확보 */}
      <Box sx={{ mb: 3 }}>
        <Typography
          variant="h6"
          fontWeight={700}
          mt={4}
          mb={2}
          textAlign="center"
        >
          레시피 추천
        </Typography>
        {/* <Typography variant="body2" color="text.secondary">
          음식 사진을 업로드하면 AI가 맞춤 레시피를 추천해드려요
        </Typography> */}
      </Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}
      <ImageGrid images={images} onRemoveImage={handleRemoveImage} />
      <BottomActionBar
        hasImages={images.length > 0}
        loading={loading}
        maxImagesReached={images.length >= MAX_IMAGES}
        onFilesSelected={handleFilesSelected}
        onRecommendRecipes={handleRecommendRecipes}
      />
    </Box>
  );
}
