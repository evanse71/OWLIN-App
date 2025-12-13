/** @type {import('next').NextConfig} */
const isProd = process.env.NODE_ENV === 'production';

const nextConfig = {
  reactStrictMode: false,
  swcMinify: true,
  // allow dev even if types are broken short-term
  typescript: { ignoreBuildErrors: true },
  eslint: { ignoreDuringBuilds: true },
  // IMPORTANT: do NOT set output:"export" in dev
  ...(isProd && { output: 'export' }),
  trailingSlash: true,
  images: {
    unoptimized: true
  },
  redirects: async () => 
    isProd 
      ? [{ source: '/test-icons', destination: '/', permanent: false }] 
      : [],
}

module.exports = nextConfig 