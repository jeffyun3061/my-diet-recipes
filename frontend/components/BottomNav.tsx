// components/BottomNav.tsx
"use client";

import React from "react";
import type { Route } from "next";
import { usePathname, useRouter } from "next/navigation";
import { BottomNavigation, BottomNavigationAction, Box } from "@mui/material";
import HomeIcon from "@mui/icons-material/Home";
import FoodBankIcon from "@mui/icons-material/FoodBank";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import InfoIcon from "@mui/icons-material/Info";
import ContactPageIcon from "@mui/icons-material/ContactPage";
import Face2Icon from "@mui/icons-material/Face2";
import FaceRetouchingNaturalIcon from "@mui/icons-material/FaceRetouchingNatural";

const NAV_ITEMS = [
  { label: "홈", path: "/", icon: <FoodBankIcon /> },
  { label: "레시피", path: "/recipes", icon: <MenuBookIcon /> },
  {
    label: "내정보",
    path: "/personal-info",
    icon: <FaceRetouchingNaturalIcon />,
  },
];

export default function BottomNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [value, setValue] = React.useState(pathname);

  React.useEffect(() => {
    setValue(pathname);
  }, [pathname]);

  const handleChange = (_: React.SyntheticEvent, newValue: string) => {
    setValue(newValue);
    if (newValue !== pathname) {
      router.push(newValue as Route);
    }
  };

  return (
    <Box
      sx={{
        position: "absolute", // sticky에서 absolute로 변경
        bottom: 0,
        left: 5,
        right: 5,
        borderTop: 1,
        borderColor: "divider",
        bgcolor: "background.paper",
        pb: `env(safe-area-inset-bottom)`,
        zIndex: 1000, // 다른 콘텐츠 위에 표시
      }}
    >
      <BottomNavigation
        value={value}
        onChange={handleChange}
        showLabels
        sx={{ bgcolor: "transparent" }}
      >
        {NAV_ITEMS.map((item) => (
          <BottomNavigationAction
            key={item.path}
            value={item.path}
            icon={item.icon}
            label={item.label}
          />
        ))}
      </BottomNavigation>
    </Box>
  );
}
