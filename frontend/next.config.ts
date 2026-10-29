import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Only the Docker build needs the self-contained server; `next start` rejects it.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
};

export default nextConfig;
