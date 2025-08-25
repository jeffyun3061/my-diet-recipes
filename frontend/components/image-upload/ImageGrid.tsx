// components/ImageUpload/ImageGrid.tsx
"use client";

import { Box, Typography, Stack } from "@mui/material";
import ImageIcon from "@mui/icons-material/Image";
import ImageThumbnail from "./ImageThumbnail";
import type { UploadedImage } from "@/types/image";
import EggIcon from "@mui/icons-material/Egg";
import EggAltIcon from "@mui/icons-material/EggAlt";
import LocalDiningIcon from "@mui/icons-material/LocalDining";

interface Props {
  images: UploadedImage[];
  onRemoveImage: (id: string) => void;
}

export default function ImageGrid({ images, onRemoveImage }: Props) {
  if (images.length === 0) {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: 300,
          color: "text.secondary",
        }}
      >
        {/* <ImageIcon sx={{ fontSize: 64, mb: 2, opacity: 0.5 }} /> */}
        <EggIcon sx={{ fontSize: 96, mb: 2, opacity: 0.5 }} />
        <Typography variant="h6" gutterBottom>
          재료의 사진을 보여주세요
        </Typography>
        <Typography variant="body2" textAlign="center">
          음식 사진을 올리면 AI로 맞춤 레시피를 추천해드려요
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle2" color="text.secondary" mb={2}>
        업로드된 사진 ({images.length}개)
      </Typography>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 1,
        }}
      >
        {images.map((image) => (
          <ImageThumbnail
            key={image.id}
            image={image}
            onRemove={onRemoveImage}
          />
        ))}
      </Box>
    </Box>
  );
}
