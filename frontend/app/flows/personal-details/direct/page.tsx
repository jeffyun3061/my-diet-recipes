"use client";

import {
  Box,
  Card,
  CardContent,
  TextField,
  MenuItem,
  Button,
  Stack,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
} from "@mui/material";
import { DIET_OPTIONS } from "@/data/dietOptions";
import { useState } from "react";
import { useRouter } from "next/navigation";           // 추가
import { postPreferences } from "@/lib/api";           // 추가 

export default function DirectInputPage() {
  const [gender, setGender] = useState<string>("");
  const [age, setAge] = useState("25");
  const [height, setHeight] = useState("160");
  const [weight, setWeight] = useState("50");
  const [diet, setDiet] = useState("");
  const [submitting, setSubmitting] = useState(false);  // 추가
  const router = useRouter();                           // 추가

  const handleGenderChange = (
    event: React.MouseEvent<HTMLElement>,
    newGender: string | null
  ) => {
    if (newGender !== null) {
      setGender(newGender);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {   //async 로 변경
  e.preventDefault();

  if (!gender) {
    alert("성별을 선택해주세요.");
    return;
  }
  if (!diet) {
    alert("다이어트 방식을 선택해주세요.");
    return;
  }

  // 프론트 값 → 백엔드 기대 라벨로 매핑
  const sexLabel = gender === "male" ? "남성" : "여성";
  const dietLabel = DIET_OPTIONS.find((o) => o.value === diet)?.label ?? diet;

  try {
    setSubmitting(true);

    await postPreferences({
      sex: sexLabel,
      age: Number(age),
      heightCm: Number(height),
      weightKg: Number(weight),
      diet: dietLabel, // 예: "저탄고지"
    });

    // 저장 성공 → 업로드 페이지로 이동
    router.push("/recipes");
  } catch (err) {
    alert(err instanceof Error ? err.message : "개인정보 저장 중 오류가 발생했습니다.");
  } finally {
    setSubmitting(false);
  }
};


  return (
    <Box component="form" onSubmit={handleSubmit}>
      <Card variant="outlined" sx={{ borderRadius: 2 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={700} mb={2}>
            바로 입력
          </Typography>

          <Stack spacing={2}>
            {/* 성별 선택 */}
            <Box>
              <Typography variant="body2" color="text.secondary" mb={1}>
                성별 *
              </Typography>
              <ToggleButtonGroup
                value={gender}
                exclusive
                onChange={handleGenderChange}
                aria-label="성별 선택"
                fullWidth
                sx={{
                  "& .MuiToggleButton-root": {
                    borderRadius: 1,
                    py: 1.5,
                    fontWeight: 600,
                    "&.Mui-selected": {
                      bgcolor: "primary.main",
                      color: "primary.contrastText",
                      "&:hover": {
                        bgcolor: "primary.dark",
                      },
                    },
                  },
                }}
              >
                <ToggleButton value="male" aria-label="남성">
                  남성
                </ToggleButton>
                <ToggleButton value="female" aria-label="여성">
                  여성
                </ToggleButton>
              </ToggleButtonGroup>
            </Box>

            {/* 나이 */}
            <TextField
              label="나이"
              type="number"
              inputProps={{ inputMode: "numeric", min: 1, max: 120, step: "1" }}
              value={age}
              onChange={(e) => setAge(e.target.value)}
              required
              fullWidth
            />

            {/* 키 */}
            <TextField
              label="키(cm)"
              type="number"
              inputProps={{
                inputMode: "numeric",
                min: 100,
                max: 250,
                step: "1",
              }}
              value={height}
              onChange={(e) => setHeight(e.target.value)}
              required
              fullWidth
            />

            {/* 몸무게 */}
            <TextField
              label="몸무게(kg)"
              type="number"
              inputProps={{
                inputMode: "numeric",
                min: 20,
                max: 300,
                step: "0.5",
              }}
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
              required
              fullWidth
            />

            {/* 다이어트 방식 */}
            <TextField
              select
              label="다이어트 방식"
              value={diet}
              onChange={(e) => setDiet(e.target.value)}
              required
              fullWidth
            >
              {DIET_OPTIONS.map((opt) => (
                <MenuItem key={opt.value} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </TextField>

            <Button type="submit" variant="contained" size="large">
              입력 완료
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
