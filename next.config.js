/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    if (!process.env.NEXT_PUBLIC_API_BASE_URL) {
      return [{ source: "/api/:path*", destination: "http://127.0.0.1:8001/api/:path*" }];
    }
    return [];
  },
};
module.exports = nextConfig;