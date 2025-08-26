"use client";

import { Box, IconButton, Typography } from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PauseIcon from "@mui/icons-material/Pause";
import VolumeOffIcon from "@mui/icons-material/VolumeOff";
import VolumeUpIcon from "@mui/icons-material/VolumeUp";
import { useRef, useState, useEffect } from "react";
import { green, orange } from "@mui/material/colors";
import { Gaegu } from "next/font/google";

const gamjaFlower = Gaegu({
  weight: "400",
  subsets: ["latin"],
});

export default function BackgroundVideoWithControls() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(true);
  const [muted, setMuted] = useState(true);
  const [mounted, setMounted] = useState(false);
  const [hasError, setHasError] = useState(false);

  const BG_PLACEHOLDER = "/images/bg-placeholder.jpg";
  const VIDEO_SRC_LIST = [
    "/videos/bg-saja.mp4",
    "/videos/bg-mv.mp4",
    "/videos/bg-buddha.mp4",
    "/videos/bg-nature.mp4",
  ];
  const [currentVideoIndex, setCurrentVideoIndex] = useState(0);
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

  useEffect(() => {
    if (!videoRef.current) return;

    if (leftAreaWidth < 230) {
      // 너비가 230 미만이면 영상 멈춤 + 사진 보여주기
      videoRef.current.pause();
      setPlaying(false);
    }
  }, [leftAreaWidth]);

  const handlePlayPause = () => {
    if (!videoRef.current || hasError) return;

    if (playing) {
      videoRef.current.pause();
      setPlaying(false);
    } else {
      setMuted(false);
      videoRef.current.muted = false;
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

  const handleSelectVideo = (index: number) => {
    if (index === currentVideoIndex) return;

    setCurrentVideoIndex(index);
    setPlaying(true);
    setHasError(false);

    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.src = VIDEO_SRC_LIST[index];
      videoRef.current.muted = muted;

      const handleLoadedData = () => {
        videoRef.current
          ?.play()
          .catch((err) => console.error("비디오 재생 오류:", err));
        videoRef.current?.removeEventListener("loadeddata", handleLoadedData);
      };

      videoRef.current.addEventListener("loadeddata", handleLoadedData);
      videoRef.current.load();
    }
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
          src={VIDEO_SRC_LIST[currentVideoIndex]}
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
      <Box
        sx={{
          // 1. 바깥쪽 Box: 위치와 정렬을 담당하는 컨테이너
          display:
            !playing || hasError
              ? leftAreaWidth >= 330
                ? "flex"
                : "none"
              : "none",
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
            bgcolor: "rgba(255,255,255,0.2)",
            paddingX: 3, // 좌우 패딩
            paddingY: 1.5, // 상하 패딩
            borderRadius: 2,
            color: "#fff",
            textAlign: "center",
          }}
        >
          <Typography
            variant="h2"
            component="div"
            sx={{
              fontWeight: 700,
              fontFamily: `${gamjaFlower.style.fontFamily} !important`,
            }}
          >
            MY DIET RECIPES
          </Typography>
          <Typography
            variant="h3"
            component="div"
            sx={{
              fontWeight: 700,
              fontFamily: `${gamjaFlower.style.fontFamily} !important`,
            }}
          >
            나의{" "}
            <Box component="span" sx={{ color: green[300] }}>
              다
            </Box>
            이어트 레
            <Box component="span" sx={{ color: green[300] }}>
              시피
            </Box>
          </Typography>
          <br />
          <br />
          <Typography
            variant="h4"
            component="div"
            sx={{
              fontWeight: 700,
              textAlign: "left",
              fontFamily: `${gamjaFlower.style.fontFamily} !important`,
            }}
          >
            모두가 알 다시피
          </Typography>
          <br />
          <br />
          <Typography
            variant="h2"
            component="div"
            sx={{
              fontWeight: 700,
              whiteSpace: "nowrap",
              marginRight: 5,
              fontFamily: `${gamjaFlower.style.fontFamily} !important`,
            }}
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
        {/* 재생/일시정지 버튼 */}
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

        {/* 음소거 버튼 */}
        {playing && !hasError && (
          <IconButton size="small" onClick={handleMute} sx={{ color: "#fff" }}>
            {muted ? (
              <VolumeOffIcon fontSize="small" />
            ) : (
              <VolumeUpIcon fontSize="small" />
            )}
          </IconButton>
        )}

        {/* 점 UI */}
        {playing && !hasError && VIDEO_SRC_LIST.length > 1 && (
          <Box sx={{ display: "flex", gap: 0.5, ml: 1 }}>
            {VIDEO_SRC_LIST.map((_, idx) => (
              <Box
                key={idx}
                onClick={() => handleSelectVideo(idx)}
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  bgcolor: idx === currentVideoIndex ? "#fff" : "#888",
                  cursor: "pointer",
                }}
              />
            ))}
          </Box>
        )}
      </Box>
    </>
  );
}
