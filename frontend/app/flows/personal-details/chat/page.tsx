// components path: frontend/app/flows/personal-details/chat/page.tsx
"use client";

import {
  Box,
  Card,
  CardContent,
  Typography,
  Stack,
  TextField,
  IconButton,
  InputAdornment,
  Button,
  Chip,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import ChatBubble from "@/components/ChatBubble";
import { DIET_OPTIONS, type DietOption } from "@/data/dietOptions";
import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { postPreferences } from "@/lib/api";
import { useUserStore } from "@/stores/userStore";

type Message = { role: "user" | "bot"; text: string };
type Step =
  | "gender"
  | "age"
  | "height"
  | "weight"
  | "diet"
  | "summary"
  | "confirm";
type UserData = {
  gender: string;
  age: number | null;
  height: number | null;
  weight: number | null;
  diet: string;
};

const GENDER_OPTIONS = [
  { value: "male", label: "남성" },
  { value: "female", label: "여성" },
];

const CONFIRM_OPTIONS = [
  { value: "yes", label: "네, 맞습니다", icon: <CheckIcon /> },
  { value: "no", label: "아니오, 다시 입력", icon: <CloseIcon /> },
];

export default function ChatInputPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [step, setStep] = useState<Step>("gender");
  const [input, setInput] = useState("");
  const [userData, setUserData] = useState<UserData>({
    gender: "",
    age: null,
    height: null,
    weight: null,
    diet: "",
  });
  const [initialized, setInitialized] = useState(false);
  const [submitting, setSubmitting] = useState(false); // ★ 추가
  const listRef = useRef<HTMLDivElement>(null);

  const router = useRouter(); // ★ 추가
  const setPersonalInfo = useUserStore((s) => s.setPersonalInfo); // ★ 추가 (전역 상태)

  // 메시지 추가
  const addMessage = useCallback((role: "user" | "bot", text: string) => {
    setMessages((prev) => [...prev, { role, text }]);
  }, []);

  // 초기 안내 메시지
  useEffect(() => {
    if (!initialized) {
      addMessage(
        "bot",
        "안녕하세요! 친근한 건강 코치예요 🙂\n먼저 성별을 선택해주세요!"
      );
      setInitialized(true);
    }
  }, [initialized, addMessage]);

  // 스크롤 하단 고정
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  // 성별 선택
  const handleGenderSelect = useCallback(
    (gender: { value: string; label: string }) => {
      addMessage("user", gender.label);
      setUserData((prev) => ({ ...prev, gender: gender.value }));
      setTimeout(
        () =>
          addMessage(
            "bot",
            "좋아요! 이제 나이를 알려주세요. 숫자로만 입력해주세요!"
          ),
        150
      );
      setStep("age");
    },
    [addMessage]
  );

  // 확인 선택
  const handleConfirmSelect = useCallback(
    (confirm: { value: string; label: string }) => {
      addMessage("user", confirm.label);

      if (confirm.value === "yes") {
        setTimeout(
          () =>
            addMessage(
              "bot",
              "완료되었습니다! 🎉 입력해주신 정보로 맞춤 건강 관리를 도와드릴게요!"
            ),
          150
        );
        setStep("summary");
      } else {
        setTimeout(
          () =>
            addMessage(
              "bot",
              "알겠습니다! 처음부터 다시 입력받겠습니다. 성별부터 다시 선택해주세요!"
            ),
          150
        );
        setStep("gender");
        setUserData({
          gender: "",
          age: null,
          height: null,
          weight: null,
          diet: "",
        });
      }
    },
    [addMessage]
  );

  // 단계별 입력 처리
  const processInput = useCallback(
    (text: string) => {
      if (step === "gender" || step === "confirm") {
        setTimeout(
          () => addMessage("bot", "위의 버튼 중에서 선택해주세요! 👆"),
          150
        );
        return;
      }

      const stepConfig = {
        age: {
          validate: (val: number) => val > 0 && val <= 120,
          errorMsg: "올바른 나이를 숫자로 입력해주세요! (1-120세)",
          successMsg: "좋아요! 이번엔 키(cm)를 알려주세요!",
          nextStep: "height" as Step,
          updateData: (val: number) =>
            setUserData((prev) => ({ ...prev, age: val })),
        },
        height: {
          validate: (val: number) => val >= 100 && val <= 250,
          errorMsg: "올바른 키를 숫자로 입력해주세요! (100-250cm)",
          successMsg: "훌륭해요! 이제 몸무게(kg)를 알려주세요!",
          nextStep: "weight" as Step,
          updateData: (val: number) =>
            setUserData((prev) => ({ ...prev, height: val })),
        },
        weight: {
          validate: (val: number) => val >= 20 && val <= 300,
          errorMsg: "올바른 몸무게를 숫자로 입력해주세요! (20-300kg)",
          successMsg:
            "마지막이에요! 선호하는 다이어트 방식을 골라주세요.\n아래 버튼 중 하나를 눌러도 좋고, 직접 입력해도 됩니다! 🙂",
          nextStep: "diet" as Step,
          updateData: (val: number) =>
            setUserData((prev) => ({ ...prev, weight: val })),
        },
      };

      if (step === "diet") {
        const found = DIET_OPTIONS.find(
          (d) =>
            d.value === text.trim().toLowerCase() ||
            d.label === text.trim() ||
            d.label.replace(/\s/g, "") === text.replace(/\s/g, "")
        );

        if (!found) {
          setTimeout(
            () =>
              addMessage(
                "bot",
                "목록 중에서 선택해 주세요: 균형식, 저탄고지, 키토, 고단백, 간헐적 단식"
              ),
            150
          );
          return;
        }

        setUserData((prev) => ({ ...prev, diet: found.value }));
        setStep("summary");
        setTimeout(
          () => addMessage("bot", "좋아요! 입력해주신 정보를 정리해볼게요."),
          150
        );
        setTimeout(() => {
          const genderLabel =
            GENDER_OPTIONS.find((g) => g.value === userData.gender)?.label ||
            "미입력";
          addMessage(
            "bot",
            `📋 입력 정보 확인\n\n성별: ${genderLabel}\n나이: ${
              userData.age ?? "-"
            }세\n키: ${userData.height ?? "-"}cm\n몸무게: ${
              userData.weight ?? "-"
            }kg\n다이어트: ${found.label}\n\n모든 정보가 정확한가요?`
          );
        }, 800);
        setStep("confirm");
        return;
      }

      const config = stepConfig[step as keyof typeof stepConfig];
      if (!config) return;

      const num = Number(text);
      if (!Number.isFinite(num) || isNaN(num) || !config.validate(num)) {
        setTimeout(() => addMessage("bot", config.errorMsg), 150);
        return;
      }

      config.updateData(num);
      setTimeout(() => addMessage("bot", config.successMsg), 150);
      setStep(config.nextStep);
    },
    [step, userData, addMessage]
  );

  const handleSubmit = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed) return;

    addMessage("user", trimmed);
    setInput("");
    processInput(trimmed);
  }, [input, addMessage, processInput]);

  const handleChipClick = useCallback(
    (option: DietOption) => {
      addMessage("user", option.label);
      setUserData((prev) => ({ ...prev, diet: option.value }));
      setStep("summary");
      setTimeout(
        () => addMessage("bot", "좋아요! 입력해주신 정보를 정리해볼게요."),
        150
      );
      setTimeout(() => {
        const genderLabel =
          GENDER_OPTIONS.find((g) => g.value === userData.gender)?.label ||
          "미입력";
        addMessage(
          "bot",
          `📋 입력 정보 확인\n\n성별: ${genderLabel}\n나이: ${
            userData.age ?? "-"
          }세\n키: ${userData.height ?? "-"}cm\n몸무게: ${
            userData.weight ?? "-"
          }kg\n다이어트: ${option.label}\n\n모든 정보가 정확한가요?`
        );
      }, 800);
      setStep("confirm");
    },
    [userData, addMessage]
  );

  const reset = useCallback(() => {
    setMessages([]);
    setStep("gender");
    setInput("");
    setUserData({
      gender: "",
      age: null,
      height: null,
      weight: null,
      diet: "",
    });
    setInitialized(false);
  }, []);

  // 성별 버튼
  const genderButtons = useMemo(
    () =>
      step === "gender"
        ? GENDER_OPTIONS.map((gender) => (
            <Button
              key={gender.value}
              variant="contained"
              onClick={() => handleGenderSelect(gender)}
              sx={{
                borderRadius: 999,
                px: 3,
                py: 1,
                mr: 1,
                mb: 1,
              }}
            >
              {gender.label}
            </Button>
          ))
        : [],
    [step, handleGenderSelect]
  );

  // 확인 버튼
  const confirmButtons = useMemo(
    () =>
      step === "confirm"
        ? CONFIRM_OPTIONS.map((confirm) => (
            <Button
              key={confirm.value}
              variant={confirm.value === "yes" ? "contained" : "outlined"}
              color={confirm.value === "yes" ? "primary" : "secondary"}
              startIcon={confirm.icon}
              onClick={() => handleConfirmSelect(confirm)}
              sx={{
                borderRadius: 999,
                px: 2,
                py: 1,
                mr: 1,
                mb: 1,
                minWidth: 140,
              }}
            >
              {confirm.label}
            </Button>
          ))
        : [],
    [step, handleConfirmSelect]
  );

  // 다이어트 칩
  const dietChips = useMemo(
    () =>
      step === "diet"
        ? DIET_OPTIONS.map((opt) => (
            <Chip
              key={opt.value}
              label={opt.label}
              onClick={() => handleChipClick(opt)}
              sx={{ borderRadius: 999 }}
            />
          ))
        : [],
    [step, handleChipClick]
  );

  const placeholderText = {
    gender: "위의 버튼을 선택해주세요",
    age: "나이를 입력하세요 (예: 29)",
    height: "키를 입력하세요 (예: 170)",
    weight: "몸무게를 입력하세요 (예: 65.5)",
    diet: "다이어트 방식을 입력하거나 위 버튼을 선택하세요",
    summary: "",
    confirm: "위의 버튼을 선택해주세요",
  }[step];

  const canInput =
    step !== "summary" && step !== "gender" && step !== "confirm";

  // ★ 핵심: 개인정보 저장 + 다음 화면 이동
  const handleNextStep = useCallback(async () => {
    if (submitting) return;
    const { gender, age, height, weight, diet } = userData;
    if (!gender || age == null || height == null || weight == null || !diet) {
      alert("입력 정보가 부족합니다. 성별/나이/키/몸무게/다이어트를 모두 입력해주세요.");
      return;
    }

    try {
      setSubmitting(true);

      const sexLabel =
        GENDER_OPTIONS.find((g) => g.value === gender)?.label ?? "남성";
      const dietLabel =
        DIET_OPTIONS.find((d) => d.value === diet)?.label ?? diet;

      // 1) 서버 저장
      await postPreferences({
        sex: sexLabel,
        age: Number(age),
        heightCm: Number(height),
        weightKg: Number(weight),
        diet: dietLabel,
      });

      // 2) 전역 상태 보관 (카메라/추천 페이지에서 사용)
      setPersonalInfo({
        sex: sexLabel,
        age: Number(age),
        heightCm: Number(height),
        weightKg: Number(weight),
        diet: dietLabel,
      });

      // 3) 다음 단계로
      router.push("/recipes");
    } catch (e) {
      const msg =
        e instanceof Error ? e.message : "개인정보 저장 중 오류가 발생했습니다.";
      alert(msg);
    } finally {
      setSubmitting(false);
    }
  }, [userData, submitting, setPersonalInfo, router]);

  return (
    <Box sx={{ pb: 2 }}>
      <Card variant="outlined" sx={{ borderRadius: 2 }}>
        <CardContent sx={{ p: 2 }}>
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
          >
            <Typography variant="h6" fontWeight={700}>
              챗봇 입력
            </Typography>
            <IconButton size="small" onClick={reset} aria-label="대화 초기화">
              <RestartAltIcon fontSize="small" />
            </IconButton>
          </Stack>

          <Box
            ref={listRef}
            sx={{
              height: "calc(100vh - 250px)",
              maxHeight: "calc(100vh - 250px)",
              overflowY: "auto",
              border: 1,
              borderColor: "grey.200",
              borderRadius: 1.5,
              p: 1,
              mb: 1,
              bgcolor: "grey.50",
            }}
          >
            {messages.map((m, i) => (
              <ChatBubble key={i} role={m.role} text={m.text} />
            ))}

            {/* 성별 선택 버튼들 */}
            {genderButtons.length > 0 && (
              <Box sx={{ mt: 1, mb: 1 }}>{genderButtons}</Box>
            )}

            {/* 확인 버튼들 */}
            {confirmButtons.length > 0 && (
              <Box sx={{ mt: 1, mb: 1 }}>{confirmButtons}</Box>
            )}

            {/* 다이어트 칩들 */}
            {dietChips.length > 0 && (
              <Stack
                direction="row"
                spacing={1}
                flexWrap="wrap"
                useFlexGap
                sx={{ mt: 1 }}
              >
                {dietChips}
              </Stack>
            )}
          </Box>

          {canInput ? (
            <TextField
              placeholder={placeholderText}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              fullWidth
              size="small"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton size="small" onClick={handleSubmit}>
                      <SendIcon fontSize="small" />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
          ) : step === "gender" || step === "confirm" ? (
            <Box sx={{ textAlign: "center", py: 1 }}>
              <Typography variant="body2" color="text.secondary">
                위의 버튼 중 하나를 선택해주세요
              </Typography>
            </Box>
          ) : (
            <Stack alignItems="center">
              <Button
                variant="contained"
                size="small"
                onClick={handleNextStep}
                disabled={submitting}
              >
                {submitting ? "저장 중..." : "다음 단계 진행"}
              </Button>
            </Stack>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
