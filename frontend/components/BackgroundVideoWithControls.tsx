"use client";

import { Box, IconButton, Typography } from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PauseIcon from "@mui/icons-material/Pause";
import VolumeOffIcon from "@mui/icons-material/VolumeOff";
import VolumeUpIcon from "@mui/icons-material/VolumeUp";
import { useRef, useState, useEffect } from "react";

export default function BackgroundVideoWithControls() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(true);
  const [muted, setMuted] = useState(true);
  const [mounted, setMounted] = useState(false);
  const [hasError, setHasError] = useState(false);

  const BG_PLACEHOLDER = "/images/bg-placeholder.jpg";
  const VIDEO_SRC = "/videos/bg-saja.mp4";

  const MOBILE_WIDTH = 420;
  const [windowWidth, setWindowWidth] = useState(0);

  useEffect(() => {
    // 컴포넌트가 마운트된 후에 window 객체에 접근
    setWindowWidth(window.innerWidth);

    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener("resize", handleResize);

    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // 왼쪽 여백 공간의 너비 계산
  const leftAreaWidth = (windowWidth - MOBILE_WIDTH) / 2;

  useEffect(() => {
    setMounted(true);
  }, []);

  const handlePlayPause = () => {
    if (!videoRef.current || hasError) return;

    if (playing) {
      videoRef.current.pause();
      setPlaying(false);
    } else {
      videoRef.current.muted = muted;
      videoRef.current
        .play()
        .then(() => setPlaying(true))
        .catch((error) => {
          console.error("비디오 재생 오류:", error);
          setHasError(true);
        });
    }
  };

  const handleMute = () => {
    if (!videoRef.current || hasError) return;

    const newMutedState = !muted;
    setMuted(newMutedState);
    videoRef.current.muted = newMutedState;
  };

  const handleVideoError = (e: any) => {
    console.error("비디오 로드 실패:", e);
    setHasError(true);
    setPlaying(false);
  };

  const handleImageError = (e: any) => {
    console.error("이미지 로드 실패:", e);
  };

  if (!mounted) return null;

  return (
    <>
      {/* 배경 비디오/이미지 */}
      <Box
        sx={{
          position: "fixed",
          top: 0,
          left: 0,
          width: "100vw",
          height: "100vh",
          zIndex: 0,
          overflow: "hidden",
          bgcolor: "#f0f0f0",
        }}
      >
        {/* 비디오 */}
        <video
          ref={videoRef}
          src={VIDEO_SRC}
          autoPlay
          loop
          muted={muted}
          playsInline
          onError={handleVideoError}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: "brightness(0.78)",
            display: playing && !hasError ? "block" : "none",
          }}
        />

        {/* 이미지 */}
        <Box
          component="img"
          src={BG_PLACEHOLDER}
          alt="Video Paused Background"
          onError={handleImageError}
          sx={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: "brightness(0.78)",
            display: !playing || hasError ? "block" : "none",
          }}
        />
      </Box>

      {/* 왼쪽 텍스트 */}
      {/* <Box
        sx={{
          // 배경 이미지가 보일 때만 flex로 표시, 아닐 때는 none
          display: !playing || hasError ? "flex" : "none",
          // flex 아이템(텍스트)을 수평/수직 중앙 정렬
          alignItems: "center",
          justifyContent: "center",
          position: "fixed",
          top: "10%",
          left: 0,
          // 계산된 왼쪽 영역의 너비를 적용 (음수 방지)
          width: leftAreaWidth > 0 ? leftAreaWidth : 0,
          transform: "translateY(-50%)",
          color: "#fff",
          zIndex: 1000,
          // 텍스트 자체에 대한 스타일 (필요시 수정)
          bgcolor: "rgba(255,255,255,0.3)",
          padding: 2,
          borderRadius: 2,
        }}
      >
        <Typography variant="h6" component="div" sx={{ fontWeight: 700 }}>
          MY DIET RECIPES
        </Typography>
        <Typography variant="h6" component="div" sx={{ fontWeight: 700 }}>
          나의 다이어트 레시피
        </Typography>
        <Typography variant="h6" component="div" sx={{ fontWeight: 700 }}>
          모두가 알 ✨다시피
        </Typography>
      </Box> */}
      <Box
        sx={{
          // 1. 바깥쪽 Box: 위치와 정렬을 담당하는 컨테이너
          display: !playing || hasError ? "flex" : "none", // 보일 때 flex로 설정
          alignItems: "center", // 자식(안쪽 Box)을 수직 중앙 정렬
          justifyContent: "center", // 자식(안쪽 Box)을 수평 중앙 정렬
          position: "fixed",
          top: "40%",
          left: 0,
          width: leftAreaWidth > 0 ? leftAreaWidth : 0, // 왼쪽 영역 전체 너비 차지
          transform: "translateY(-50%)",
          zIndex: 1000,
        }}
      >
        {/* 2. 안쪽 Box: 실제 스타일(배경, 패딩 등)을 담당 */}
        <Box
          sx={{
            bgcolor: "rgba(255,255,255,0.3)",
            paddingX: 3, // 좌우 패딩
            paddingY: 1.5, // 상하 패딩
            borderRadius: 2,
            color: "#fff",
            textAlign: "center",
          }}
        >
          <Typography variant="h3" component="div" sx={{ fontWeight: 700 }}>
            MY DIET RECIPES
          </Typography>
          <Typography variant="h4" component="div" sx={{ fontWeight: 700 }}>
            나의 다이어트 레시피
          </Typography>
          <br />
          <br />
          <Typography
            variant="h5"
            component="div"
            sx={{ fontWeight: 700, textAlign: "left" }}
          >
            모두가 알 다시피
          </Typography>
          <br />
          <br />
          <Typography
            variant="h3"
            component="div"
            sx={{ fontWeight: 700, whiteSpace: "nowrap", marginRight: 5 }}
          >
            ✨다시피
          </Typography>
          <br />
        </Box>
      </Box>

      {/* 컨트롤 버튼 */}
      <Box
        sx={{
          position: "fixed",
          right: 40,
          bottom: 16,
          display: "flex",
          gap: 1,
          zIndex: 1001,
          opacity: 0.7,
          bgcolor: "rgba(34, 34, 34, 0.8)",
          borderRadius: 6,
          px: 1,
          py: 0.5,
          boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
          alignItems: "center",
          transition: "opacity 0.2s ease",
          "&:hover": {
            opacity: 0.9,
          },
        }}
      >
        <IconButton
          size="small"
          onClick={handlePlayPause}
          disabled={hasError}
          sx={{
            color: "#fff",
            "&:disabled": {
              color: "#666",
            },
          }}
        >
          {playing && !hasError ? (
            <PauseIcon fontSize="small" />
          ) : (
            <PlayArrowIcon fontSize="small" />
          )}
        </IconButton>

        {playing && !hasError && (
          <IconButton size="small" onClick={handleMute} sx={{ color: "#fff" }}>
            {muted ? (
              <VolumeOffIcon fontSize="small" />
            ) : (
              <VolumeUpIcon fontSize="small" />
            )}
          </IconButton>
        )}
      </Box>
    </>
  );
}
