import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        poll: 1000,        // 1초마다 파일 변경 polling (WSL2 inotify 우회)
        aggregateTimeout: 300,
      };
    }
    return config;
  },
};

export default nextConfig;
