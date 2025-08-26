"use client";

import { Box, IconButton } from "@mui/material";
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

  useEffect(() => {
    setMounted(true);
  }, []);

  const handlePlayPause = () => {
    if (!videoRef.current || hasError) return;

    if (playing) {
      videoRef.current.pause();
      setPlaying(false);
    } else {
      // 사용자가 클릭했으므로 autoplay 제한 해제됨
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
          bgcolor: "#f0f0f0", // 폴백 배경색
        }}
      >
        {/* 비디오: 항상 DOM 안에 유지 */}
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

        {/* 이미지: 비디오 안 보일 때만 표시 */}
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

      {/* 컨트롤 버튼 */}
      <Box
        sx={{
          position: "fixed",
          left: 46,
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
