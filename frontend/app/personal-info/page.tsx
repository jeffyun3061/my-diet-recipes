"use client";

import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Stack,
} from "@mui/material";
import PlayCircleOutlineIcon from "@mui/icons-material/PlayCircleOutline";
import { useRouter } from "next/navigation";

export default function PersonalInfoPage() {
  const router = useRouter();

  return (
    <Box>
      <Card variant="outlined" sx={{ borderRadius: 2 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={700}>
            개인 정보
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
