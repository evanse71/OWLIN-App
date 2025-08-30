/** @type {import('next').NextConfig} */
const isProd = process.env.NODE_ENV === 'production';

const nextConfig = {
  // Remove experimental appDir since we're using pages directory
  reactStrictMode: true,
  swcMinify: true,
  redirects: async () => 
    isProd 
      ? [{ source: '/test-icons', destination: '/', permanent: false }] 
      : [],
}

module.exports = nextConfig 