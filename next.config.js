/** @type {import('next').NextConfig} */
const nextConfig = {
  // Remove experimental appDir since we're using pages directory
  reactStrictMode: true,
  swcMinify: true,
}

module.exports = nextConfig 