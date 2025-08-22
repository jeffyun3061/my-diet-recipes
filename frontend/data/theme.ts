// utils/theme.ts
"use client";

import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#111827" }, // slate-900
    secondary: { main: "#2563eb" }, // blue-600
    background: {
      default: "#ffffff",
      paper: "#ffffff",
    },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiBottomNavigation: {
      styleOverrides: {
        root: {
          borderTop: "1px solid #e5e7eb",
          backgroundColor: "#fff",
        },
      },
    },
  },
});

export default theme;
