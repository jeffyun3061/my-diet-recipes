// components/Recipe/RecipeCarousel.tsx
"use client";

import React, { useState, useRef, useCallback } from "react";
import { Box, IconButton, Stack, Typography } from "@mui/material";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import RecipeCard from "./RecipeCard";
import type { RecipeRecommendation } from "@/types/image";

interface Props {
  recipes: RecipeRecommendation[];
  onCardClick: (recipe: RecipeRecommendation) => void;
}

export default function RecipeCarousel({ recipes, onCardClick }: Props) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [dragOffset, setDragOffset] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);
  const startX = useRef(0);
  const startTime = useRef(0);

  const currentRecipe = recipes[currentIndex];
  const canGoPrev = currentIndex > 0;
  const canGoNext = currentIndex < recipes.length - 1;

  const handlePrev = useCallback(() => {
    if (canGoPrev && !isTransitioning) {
      setIsTransitioning(true);
      setCurrentIndex((prev) => prev - 1);
      setTimeout(() => setIsTransitioning(false), 300);
    }
  }, [canGoPrev, isTransitioning]);

  const handleNext = useCallback(() => {
    if (canGoNext && !isTransitioning) {
      setIsTransitioning(true);
      setCurrentIndex((prev) => prev + 1);
      setTimeout(() => setIsTransitioning(false), 300);
    }
  }, [canGoNext, isTransitioning]);

  const handleStart = useCallback(
    (clientX: number) => {
      if (isTransitioning) return;

      isDragging.current = true;
      startX.current = clientX;
      startTime.current = Date.now();
      setDragOffset(0);
    },
    [isTransitioning]
  );

  const handleMove = useCallback(
    (clientX: number) => {
      if (!isDragging.current || isTransitioning) return;

      const deltaX = clientX - startX.current;
      const maxOffset = 80;
      const constrainedOffset = Math.max(
        -maxOffset,
        Math.min(maxOffset, deltaX)
      );
      setDragOffset(constrainedOffset);
    },
    [isTransitioning]
  );

  const handleEnd = useCallback(() => {
    if (!isDragging.current) return;

    const deltaX = dragOffset;
    const deltaTime = Date.now() - startTime.current;
    const velocity = Math.abs(deltaX) / deltaTime;

    const shouldSwipe = Math.abs(deltaX) > 30 || velocity > 0.3;

    if (shouldSwipe) {
      if (deltaX < 0 && canGoNext) {
        handleNext();
      } else if (deltaX > 0 && canGoPrev) {
        handlePrev();
      }
    }

    isDragging.current = false;
    setDragOffset(0);
  }, [dragOffset, canGoNext, canGoPrev, handleNext, handlePrev]);

  // 이벤트 핸들러들 (동일)
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    handleStart(e.clientX);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    handleMove(e.clientX);
  };

  const handleMouseUp = () => {
    handleEnd();
  };

  const handleMouseLeave = () => {
    handleEnd();
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    handleStart(e.touches[0].clientX);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    e.preventDefault();
    handleMove(e.touches[0].clientX);
  };

  const handleTouchEnd = () => {
    handleEnd();
  };

  if (!currentRecipe) {
    return (
      <Box sx={{ textAlign: "center", py: 8 }}>
        <Typography variant="h6" color="text.secondary">
          추천 레시피가 없습니다.
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        width: "100%",
        maxWidth: 380, // 조금 더 넓게
        mx: "auto",
        position: "relative",
        // 높이를 고정하지 않고 콘텐츠에 맞게 조정
      }}
    >
      {/* 카드 컨테이너 */}
      <Box
        ref={containerRef}
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: "calc(100vh - 180px)", // 뷰포트에서 헤더, 네비 등 제외
          position: "relative",
          cursor: isDragging.current ? "grabbing" : "grab",
          userSelect: "none",
          px: 2,
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* 현재 카드 */}
        <Box
          sx={{
            transform: `translateX(${dragOffset}px) rotate(${
              dragOffset * 0.05
            }deg)`,
            transition: isDragging.current
              ? "none"
              : isTransitioning
              ? "all 0.3s ease-out"
              : "transform 0.2s ease-out",
            width: "100%",
            maxWidth: 320,
            zIndex: 2,
          }}
        >
          <RecipeCard
            recipe={currentRecipe}
            onClick={() => !isDragging.current && onCardClick(currentRecipe)}
          />
        </Box>

        {/* 미리보기 카드들 */}
        {canGoNext && (
          <Box
            sx={{
              position: "absolute",
              right: -15,
              transform: "scale(0.85)",
              opacity: 0.3,
              zIndex: 1,
              width: "100%",
              maxWidth: 320,
              pointerEvents: "none",
            }}
          >
            <RecipeCard recipe={recipes[currentIndex + 1]} onClick={() => {}} />
          </Box>
        )}

        {canGoPrev && (
          <Box
            sx={{
              position: "absolute",
              left: -15,
              transform: "scale(0.85)",
              opacity: 0.3,
              zIndex: 1,
              width: "100%",
              maxWidth: 320,
              pointerEvents: "none",
            }}
          >
            <RecipeCard recipe={recipes[currentIndex - 1]} onClick={() => {}} />
          </Box>
        )}
      </Box>

      {/* 화살표 버튼 */}
      {canGoPrev && (
        <IconButton
          onClick={handlePrev}
          sx={{
            position: "absolute",
            left: 4,
            top: "50%",
            transform: "translateY(-50%)",
            bgcolor: "rgba(255, 255, 255, 0.9)",
            boxShadow: 2,
            zIndex: 10,
            width: 36,
            height: 36,
          }}
        >
          <ChevronLeftIcon sx={{ fontSize: 20 }} />
        </IconButton>
      )}

      {canGoNext && (
        <IconButton
          onClick={handleNext}
          sx={{
            position: "absolute",
            right: 4,
            top: "50%",
            transform: "translateY(-50%)",
            bgcolor: "rgba(255, 255, 255, 0.9)",
            boxShadow: 2,
            zIndex: 10,
            width: 36,
            height: 36,
          }}
        >
          <ChevronRightIcon sx={{ fontSize: 20 }} />
        </IconButton>
      )}

      {/* 인디케이터 */}
      <Stack
        direction="row"
        spacing={1}
        justifyContent="center"
        sx={{ mt: 2, mb: 1 }}
      >
        {recipes.map((_, index) => (
          <Box
            key={index}
            sx={{
              width: index === currentIndex ? 20 : 6,
              height: 6,
              borderRadius: 3,
              bgcolor: index === currentIndex ? "primary.main" : "grey.300",
              cursor: "pointer",
              transition: "all 0.3s ease",
            }}
            onClick={() => {
              if (!isTransitioning) {
                setIsTransitioning(true);
                setCurrentIndex(index);
                setTimeout(() => setIsTransitioning(false), 300);
              }
            }}
          />
        ))}
      </Stack>

      {/* 카드 정보 표시 */}
      <Box sx={{ textAlign: "center", px: 2 }}>
        <Typography variant="body2" color="text.secondary" fontSize="0.75rem">
          {currentIndex + 1} / {recipes.length}
        </Typography>
        <Typography
          variant="body2"
          color="text.secondary"
          fontSize="0.7rem"
          sx={{ mt: 0.5 }}
        >
          좌우로 스와이프하거나 화살표를 클릭하세요
        </Typography>
      </Box>
    </Box>
  );
}
