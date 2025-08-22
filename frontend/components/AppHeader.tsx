"use client";

import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";

export default function AppHeader() {
  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        borderBottom: "1px solid #e5e7eb",
        color: "inherit",
        bgcolor: "#fff",
      }}
    >
      <Toolbar sx={{ minHeight: 56 }}>
        <Typography variant="h6" component="div" sx={{ fontWeight: 700 }}>
          My Diet Recipes
        </Typography>
      </Toolbar>
    </AppBar>
  );
}
