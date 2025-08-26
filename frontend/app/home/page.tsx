"use client";

import { Box, Card, CardContent, Typography, Stack } from "@mui/material";
import { useRouter } from "next/navigation";
import { useUserStore } from "@/stores/userStore";

export default function HomePage() {
  const router = useRouter();
  const personalInfo = useUserStore((state) => state.personalInfo);

  const handleImageClick = () => {
    if (!personalInfo) {
      router.push("/flows/personal-details");
    } else {
      router.push("/recipes");
    }
  };

  return (
    <Box sx={{ px: 2, py: 4 }}>
      <Typography variant="h6" fontWeight={700} mb={2} textAlign="center">
        건강한 식습관, 나만의 맞춤 레시피
      </Typography>

      <Card
        variant="outlined"
        sx={
          {
            /* 카드 스타일 */
          }
        }
      >
        <CardContent sx={{ textAlign: "center", p: 2 }}>
          {/* 샐러드 볼 이미지 */}
          <Box
            component="img"
            src="/images/salad-bowl.png"
            alt="건강한 샐러드 볼"
            sx={{
              width: 160,
              height: 160,
              mt: 3,
              mb: 3,
              cursor: "pointer",
              transition: "all 0.3s cubic-bezier(.68,-0.55,.27,1.55)",
              "&:hover": { transform: "scale(1.08)" },
            }}
            onClick={handleImageClick}
          />

          {/* 안내 문구 */}
          <Stack spacing={1.5} alignItems="center">
            <Typography variant="h6" fontWeight={600}>
              나만의 건강 레시피를 찾아보세요!
            </Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{
                maxWidth: 300,
                wordBreak: "keep-all",
                overflowWrap: "break-word",
                whiteSpace: "normal",
              }}
            >
              샐러드 볼을 클릭하여 개인 정보를 입력하고, 가지고 있는 재료로
              맞춤형 건강 레시피를 추천받으세요.
            </Typography>
          </Stack>

          {/* 상태 표시 */}
          <Box
            sx={{
              mt: 3,
              px: 2,
              py: 1,
              borderRadius: 999,
              bgcolor: personalInfo ? "success.light" : "grey.100",
            }}
          >
            <Typography variant="caption" fontWeight={500}>
              {personalInfo
                ? "다이어트 정보 등록완료 ✓"
                : "다이어트 정보 입력필요"}
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
