"use client";

import React, { useRef, useState, useEffect } from "react";
import {
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Button,
  Stack,
  Box,
  CircularProgress,
} from "@mui/material";
import CameraAltIcon from "@mui/icons-material/CameraAlt";
import PhotoCameraIcon from "@mui/icons-material/PhotoCamera";
import PhotoLibraryIcon from "@mui/icons-material/PhotoLibrary";
import RestaurantIcon from "@mui/icons-material/Restaurant";
import { ACCEPTED_IMAGE_TYPES } from "@/data/imageUtils";
import { useUserStore } from "@/stores/userStore";
import { useRouter } from "next/navigation";
import type { Route } from "next";

interface Props {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

export default function CameraButton({ onFilesSelected, disabled }: Props) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [personalInfoDialogOpen, setPersonalInfoDialogOpen] = useState(false);
  const [countdown, setCountdown] = useState(5);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const personalInfo = useUserStore((state) => state.personalInfo);
  const router = useRouter();

  // 카운트다운 효과
  useEffect(() => {
    let timer: NodeJS.Timeout;

    if (personalInfoDialogOpen && countdown > 0) {
      timer = setTimeout(() => {
        setCountdown(countdown - 1);
      }, 1000);
    } else if (personalInfoDialogOpen && countdown === 0) {
      handleNavigateToPersonalInfo();
    }

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [personalInfoDialogOpen, countdown]);

  const handleNavigateToPersonalInfo = () => {
    setPersonalInfoDialogOpen(false);
    setCountdown(5); // 초기화
    router.push("/flows/personal-details" as Route);
  };

  const handleCameraClick = () => {
    // 개인정보가 없으면 개인정보 입력 안내 다이얼로그 표시
    if (!personalInfo) {
      setPersonalInfoDialogOpen(true);
      setCountdown(5);
      return;
    }

    // 개인정보가 있으면 일반 파일 선택 다이얼로그 표시
    setDialogOpen(true);
  };

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
        onClick={handleCameraClick}
        disabled={disabled}
      >
        <CameraAltIcon />
      </Fab>

      {/* 개인정보 입력 안내 다이얼로그 - 수정된 부분 */}
      <Dialog
        open={personalInfoDialogOpen}
        onClose={() => setPersonalInfoDialogOpen(false)}
        maxWidth="xs"
        fullWidth
        PaperProps={{
          sx: { borderRadius: 3 },
        }}
      >
        {/* DialogTitle에는 텍스트만 넣기 */}
        <DialogTitle sx={{ textAlign: "center", pb: 1 }}>
          맞춤 레시피 추천
        </DialogTitle>

        <DialogContent sx={{ textAlign: "center", pb: 4 }}>
          <Stack spacing={3} alignItems="center">
            {/* 아이콘을 여기로 이동 */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 1,
              }}
            >
              <RestaurantIcon color="primary" fontSize="large" />
            </Box>

            <Typography variant="h6" fontWeight={700} color="text.primary">
              원하는 다이어트 방식을 알려주시겠어요? 🥗
            </Typography>

            <Typography variant="body2" color="text.secondary">
              더 정확한 맞춤 레시피 추천을 위해 간단한 정보가 필요해요
            </Typography>

            {/* 카운트다운 원형 진행바 */}
            <Box sx={{ position: "relative", display: "inline-flex" }}>
              <CircularProgress
                variant="determinate"
                value={(5 - countdown) * 20}
                size={80}
                thickness={4}
                sx={{
                  color: "primary.main",
                  "& .MuiCircularProgress-circle": {
                    strokeLinecap: "round",
                  },
                }}
              />
              <Box
                sx={{
                  top: 0,
                  left: 0,
                  bottom: 0,
                  right: 0,
                  position: "absolute",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Typography variant="h4" fontWeight={700} color="primary">
                  {countdown}
                </Typography>
              </Box>
            </Box>

            <Typography variant="body2" color="text.secondary">
              {countdown}초 후 자동으로 이동합니다
            </Typography>

            {/* 바로 이동 버튼 */}
            <Button
              variant="contained"
              onClick={handleNavigateToPersonalInfo}
              sx={{
                borderRadius: 999,
                px: 4,
                py: 1.5,
                fontWeight: 600,
              }}
            >
              지금 바로 입력하기
            </Button>
          </Stack>
        </DialogContent>
      </Dialog>

      {/* 기존 사진 업로드 방법 선택 다이얼로그 */}
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
