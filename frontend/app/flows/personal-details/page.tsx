"use client";

import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Typography,
  Stack,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import ChatIcon from "@mui/icons-material/Chat";
import { useRouter } from "next/navigation";
import type { Route } from "next";

export default function StartFlowPage() {
  const router = useRouter();

  return (
    <Box>
      <Typography variant="h6" fontWeight={700} mb={2}>
        입력 방식을 선택하세요
      </Typography>

      <Stack spacing={2}>
        <Card variant="outlined" sx={{ borderRadius: 2 }}>
          <CardActionArea
            onClick={() =>
              router.push("/flows/personal-details/direct" as Route)
            }
          >
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <EditIcon color="primary" />
                <Box>
                  <Typography fontWeight={700}>바로 입력</Typography>
                  <Typography variant="body2" color="text.secondary">
                    키·몸무게·다이어트 방식을 한 번에 입력합니다.
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </CardActionArea>
        </Card>

        <Card variant="outlined" sx={{ borderRadius: 2 }}>
          <CardActionArea
            onClick={() => router.push("/flows/personal-details/chat" as Route)}
          >
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <ChatIcon color="secondary" />
                <Box>
                  <Typography fontWeight={700}>챗봇 입력</Typography>
                  <Typography variant="body2" color="text.secondary">
                    대화하듯 하나씩 물어보고 입력을 도와드려요.
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </CardActionArea>
        </Card>
      </Stack>
    </Box>
  );
}
