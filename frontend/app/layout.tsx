// app/layout.tsx
import type { Metadata, Viewport } from "next";
import "./globals.css";
import { ReactNode } from "react";
import { CssBaseline } from "@mui/material";
import ThemeRegistry from "@/components/ThemeRegistry";
import AppHeader from "@/components/AppHeader";
import BottomNav from "@/components/BottomNav";
import { Box } from "@mui/material";
import BackgroundVideoWithControls from "@/components/BackgroundVideoWithControls";

export const metadata: Metadata = {
  title: "My Mobile Web",
  description: "Mobile-like web with Next.js + MUI",
  icons: { icon: "/favicon.ico" },
};

// ✅ viewport는 별도 export
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  maximumScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <ThemeRegistry>
          <CssBaseline />
          <BackgroundVideoWithControls />

          {/* 메인 컨테이너 - 중앙 정렬 */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              width: "100%",
              bgcolor: "#f5f6f8",
              minHeight: "100vh",
            }}
          >
            {/* 모바일 캔버스 */}
            <Box
              sx={{
                width: "100%",
                maxWidth: 420,
                minHeight: "100dvh",
                bgcolor: "background.paper",
                display: "flex",
                flexDirection: "column",
                borderLeft: "1px solid",
                borderRight: "1px solid",
                borderColor: "divider",
                position: "relative",
              }}
            >
              <AppHeader />

              {/* 메인 콘텐츠 영역 */}
              <Box
                component="main"
                sx={{
                  flex: 1,
                  px: 2,
                  py: 1,
                  pb: 8,
                  overflowY: "auto",
                }}
              >
                {children}
              </Box>

              {/* 하단 네비게이션 - 고정 위치 */}
              <Box
                sx={{
                  position: "fixed",
                  bottom: 0,
                  left: "50%",
                  transform: "translateX(-50%)",
                  width: "100%",
                  maxWidth: 420,
                  zIndex: 1000,
                }}
              >
                <BottomNav />
              </Box>
            </Box>
          </Box>
        </ThemeRegistry>
      </body>
    </html>
  );
}
