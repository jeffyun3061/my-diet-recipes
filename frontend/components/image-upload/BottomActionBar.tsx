"use client";

import React from "react";
import { Box, Button, CircularProgress } from "@mui/material";
import RestaurantIcon from "@mui/icons-material/Restaurant";
import CameraButton from "./CameraButton";

interface Props {
  hasImages: boolean;
  loading: boolean;
  maxImagesReached: boolean;
  onFilesSelected: (files: File[]) => void;
  onRecommendRecipes: () => void;
}

export default function BottomActionBar({
  hasImages,
  loading,
  maxImagesReached,
  onFilesSelected,
  onRecommendRecipes,
}: Props) {
  return (
    <Box
      sx={{
        position: "fixed",
        bottom: 80, // BottomNav 위에 위치
        left: "50%",
        transform: "translateX(-50%)",
        width: "100%",
        maxWidth: 380, // 모바일 캔버스보다 조금 작게
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        px: 3,
        zIndex: 1000,
      }}
    >
      {/* 왼쪽 여백 */}
      <Box sx={{ width: 56 }} /> {/* Fab 크기만큼 여백 확보 */}
      {/* 중앙 레시피 추천 버튼 */}
      {hasImages && (
        <Button
          variant="contained"
          size="large"
          startIcon={
            loading ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              <RestaurantIcon />
            )
          }
          onClick={onRecommendRecipes}
          disabled={loading}
          sx={{
            borderRadius: 999,
            px: 3,
            minWidth: 140, // 최소 너비 보장
          }}
        >
          {loading ? "분석 중..." : "레시피 추천"}
        </Button>
      )}
      {/* 우측 카메라 버튼 */}
      <CameraButton
        onFilesSelected={onFilesSelected}
        disabled={maxImagesReached}
      />
    </Box>
  );
}
