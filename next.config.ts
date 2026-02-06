import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  rewrites: async () => {
    return [
      {
        source: "/api/:path*",
        destination: "/api/main.py", // Directs all /api traffic to your FastAPI bridge
      },
    ];
  },
};

export default nextConfig;
