import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // Local dev: proxy /api/v1/* to the FastAPI backend on the same host.
    // Production (Railway, etc.): the frontend reads NEXT_PUBLIC_API_URL at build
    // time and calls the backend directly, so we don't add a rewrite.
    if (process.env.NEXT_PUBLIC_API_URL) return [];
    return [
      {
        source: "/api/v1/:path*",
        destination: `http://localhost:${process.env.BACKEND_PORT || "8000"}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
