// components/ImageUpload/CameraButton.tsx
"use client";

import React, { useRef } from "react";
import {
  Fab,
  Dialog,
  DialogTitle,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
} from "@mui/material";
import CameraAltIcon from "@mui/icons-material/CameraAlt";
import PhotoCameraIcon from "@mui/icons-material/PhotoCamera";
import PhotoLibraryIcon from "@mui/icons-material/PhotoLibrary";
import { ACCEPTED_IMAGE_TYPES } from "@/data/imageUtils";

interface Props {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

export default function CameraButton({ onFilesSelected, disabled }: Props) {
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    if (files.length > 0) {
      onFilesSelected(files);
    }
    setDialogOpen(false);
    if (event.target) event.target.value = "";
  };

  const acceptedTypes = Object.keys(ACCEPTED_IMAGE_TYPES).join(",");

  return (
    <>
      <Fab
        color="primary"
        size="medium"
        onClick={() => setDialogOpen(true)}
        disabled={disabled}
      >
        <CameraAltIcon />
      </Fab>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>사진 업로드 방법 선택</DialogTitle>
        <List sx={{ minWidth: 250 }}>
          <ListItem disablePadding>
            <ListItemButton onClick={() => cameraInputRef.current?.click()}>
              <ListItemIcon>
                <PhotoCameraIcon />
              </ListItemIcon>
              <ListItemText primary="카메라로 촬영" />
            </ListItemButton>
          </ListItem>
          <ListItem disablePadding>
            <ListItemButton onClick={() => fileInputRef.current?.click()}>
              <ListItemIcon>
                <PhotoLibraryIcon />
              </ListItemIcon>
              <ListItemText primary="갤러리에서 선택" />
            </ListItemButton>
          </ListItem>
        </List>
      </Dialog>

      {/* 카메라 입력 */}
      <input
        ref={cameraInputRef}
        type="file"
        accept={acceptedTypes}
        capture="environment"
        multiple
        style={{ display: "none" }}
        onChange={handleFileSelect}
      />

      {/* 파일 입력 */}
      <input
        ref={fileInputRef}
        type="file"
        accept={acceptedTypes}
        multiple
        style={{ display: "none" }}
        onChange={handleFileSelect}
      />
    </>
  );
}
