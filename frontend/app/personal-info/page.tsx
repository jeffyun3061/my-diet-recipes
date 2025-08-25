"use client";

import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Stack,
  Divider,
  Chip,
} from "@mui/material";
import PlayCircleOutlineIcon from "@mui/icons-material/PlayCircleOutline";
import PersonIcon from "@mui/icons-material/Person";
import CakeIcon from "@mui/icons-material/Cake";
import HeightIcon from "@mui/icons-material/Height";
import FitnessIcon from "@mui/icons-material/FitnessCenter";
import RestaurantIcon from "@mui/icons-material/Restaurant";
import RefreshIcon from "@mui/icons-material/Refresh";
import { useRouter } from "next/navigation";
import { useUserStore } from "@/stores/userStore";

export default function PersonalInfoPage() {
  const router = useRouter();
  const personalInfo = useUserStore((state) => state.personalInfo);
  const clearPersonalInfo = useUserStore((state) => state.clearPersonalInfo);

  // personalInfo가 없으면 기존 입력 화면 표시
  if (!personalInfo) {
    return (
      <Box>
        <Card variant="outlined" sx={{ borderRadius: 2 }}>
          <CardContent>
            <Typography variant="h6" fontWeight={700}>
              내 정보
            </Typography>
            <Typography variant="body2" color="text.secondary" mt={1}>
              건강 목표를 위해 기본 정보를 입력해 주세요.
            </Typography>

            <Stack alignItems="center" mt={3}>
              <Button
                size="large"
                variant="contained"
                startIcon={<PlayCircleOutlineIcon />}
                onClick={() => router.push("/flows/personal-details")}
                sx={{ borderRadius: 999, px: 3 }}
              >
                시작하기
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Box>
    );
  }

  // personalInfo가 있으면 정보 표시 화면
  const handleReset = () => {
    if (
      window.confirm("개인정보를 초기화하시겠습니까? 다시 입력해야 합니다.")
    ) {
      clearPersonalInfo();
    }
  };

  return (
    <Box>
      <Card variant="outlined" sx={{ borderRadius: 2 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={700} mb={1}>
            내 개인 정보
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={2}>
            현재 등록된 정보입니다.
          </Typography>

          <Stack spacing={1.5}>
            {/* 성별 */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <PersonIcon color="primary" sx={{ fontSize: 20 }} />
                <Typography variant="body2" color="text.secondary">
                  성별
                </Typography>
              </Box>
              <Typography variant="body1" fontWeight={600}>
                {personalInfo.sex}
              </Typography>
            </Box>

            <Divider />

            {/* 나이 */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <CakeIcon color="primary" sx={{ fontSize: 20 }} />
                <Typography variant="body2" color="text.secondary">
                  나이
                </Typography>
              </Box>
              <Typography variant="body1" fontWeight={600}>
                {personalInfo.age}세
              </Typography>
            </Box>

            <Divider />

            {/* 키 */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <HeightIcon color="primary" sx={{ fontSize: 20 }} />
                <Typography variant="body2" color="text.secondary">
                  키
                </Typography>
              </Box>
              <Typography variant="body1" fontWeight={600}>
                {personalInfo.heightCm}cm
              </Typography>
            </Box>

            <Divider />

            {/* 몸무게 */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <FitnessIcon color="primary" sx={{ fontSize: 20 }} />
                <Typography variant="body2" color="text.secondary">
                  몸무게
                </Typography>
              </Box>
              <Typography variant="body1" fontWeight={600}>
                {personalInfo.weightKg}kg
              </Typography>
            </Box>

            <Divider />

            {/* 다이어트 방식 */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <RestaurantIcon color="primary" sx={{ fontSize: 20 }} />
                <Typography variant="body2" color="text.secondary">
                  다이어트 방식
                </Typography>
              </Box>
              <Chip
                label={personalInfo.diet}
                variant="outlined"
                color="primary"
                size="small"
                sx={{ fontWeight: 600 }}
              />
            </Box>
          </Stack>

          {/* BMI 정보 */}
          <Box
            sx={{
              mt: 3,
              p: 2,
              bgcolor: "primary.light",
              borderRadius: 2,
              textAlign: "center",
            }}
          >
            <Typography
              variant="body2"
              color="primary.contrastText"
              gutterBottom
            >
              BMI 지수
            </Typography>
            <Typography
              variant="h5"
              color="primary.contrastText"
              fontWeight={700}
            >
              {(
                personalInfo.weightKg / Math.pow(personalInfo.heightCm / 100, 2)
              ).toFixed(1)}
            </Typography>
          </Box>

          {/* 초기화 버튼 */}
          <Stack alignItems="center" mt={3}>
            <Button
              variant="outlined"
              color="error"
              startIcon={<RefreshIcon />}
              onClick={handleReset}
              sx={{ borderRadius: 999, px: 3 }}
            >
              초기화 및 다시 입력
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
