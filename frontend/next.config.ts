import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    domains: [], // 외부 도메인 사용시 추가
    formats: ["image/webp", "image/avif"],
  },
  reactStrictMode: true,
  experimental: { typedRoutes: true },
  compiler: {
    emotion: true, // Emotion SSR 지원 활성화
  },
};

export default nextConfig;
