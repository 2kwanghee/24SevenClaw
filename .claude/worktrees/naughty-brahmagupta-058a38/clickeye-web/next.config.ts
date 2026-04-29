import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  allowedDevOrigins: ["172.22.118.30", "10.60.1.15"],
};

export default nextConfig;
