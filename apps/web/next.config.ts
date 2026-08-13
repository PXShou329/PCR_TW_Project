import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  distDir: process.env.PCR_E2E_NEXT_DIST_DIR?.trim() || ".next",
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname, "../.."),
  reactStrictMode: true,
  transpilePackages: ["@pcr-tw/api-client", "@pcr-tw/ui"],
};

export default nextConfig;
