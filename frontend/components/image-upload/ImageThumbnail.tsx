// components/ImageUpload/ImageThumbnail.tsx
"use client";

import { Card, CardMedia, IconButton, Box } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import type { UploadedImage } from "@/types/image";

interface Props {
  image: UploadedImage;
  onRemove: (id: string) => void;
}

export default function ImageThumbnail({ image, onRemove }: Props) {
  return (
    <Card
      sx={{
        position: "relative",
        aspectRatio: "1/1",
        borderRadius: 2,
        overflow: "hidden",
      }}
    >
      <CardMedia
        component="img"
        image={image.url}
        alt={image.name}
        sx={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />
      <Box
        sx={{
          position: "absolute",
          top: 4,
          right: 4,
          bgcolor: "rgba(0,0,0,0.6)",
          borderRadius: "50%",
          p: 0.5,
        }}
      >
        <IconButton
          size="small"
          onClick={() => onRemove(image.id)}
          sx={{
            color: "white",
            p: 0.5,
            "&:hover": { bgcolor: "rgba(255,255,255,0.2)" },
          }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>
    </Card>
  );
}
