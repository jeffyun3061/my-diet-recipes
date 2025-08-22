"use client";

import { Box, Paper, Typography } from "@mui/material";

export default function ChatBubble({
  role,
  text,
}: {
  role: "user" | "bot";
  text: string;
}) {
  const isUser = role === "user";
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        mb: 1.25,
      }}
    >
      <Paper
        elevation={0}
        sx={{
          px: 1.5,
          py: 1,
          maxWidth: "80%",
          bgcolor: isUser ? "primary.main" : "grey.100",
          color: isUser ? "primary.contrastText" : "text.primary",
          borderRadius: 2,
        }}
      >
        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
          {text}
        </Typography>
      </Paper>
    </Box>
  );
}
