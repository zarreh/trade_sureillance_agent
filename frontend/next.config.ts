import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Only the Docker build needs the self-contained server; `next start` rejects it.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  async redirects() {
    // Run links used to live on the home page; the live runner is now /investigate.
    return [
      {
        source: "/",
        has: [{ type: "query", key: "run", value: "(?<run>.+)" }],
        destination: "/investigate?run=:run",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
