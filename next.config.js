// next.config.js
module.exports = {
  // Enable static export for GitHub Pages
  trailingSlash: true,
  assetPrefix: process.env.NODE_ENV === 'production' ? '/OWLIN-App' : '',
  
  // Configure webpack
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      config.watchOptions = {
        ignored: ['**/node_modules/**', '**/.next/**', '**/data/uploads/**', '**/venv/**'],
      };
    }
    return config;
  },
  
  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
    NEXT_PUBLIC_HOST: process.env.NEXT_PUBLIC_HOST || 'localhost',
    NEXT_PUBLIC_PORT: process.env.NEXT_PUBLIC_PORT || '3000',
  },
  
  // Server configuration for development
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'}/:path*`,
      },
    ];
  },

  // Experimental features
  experimental: {
    appDir: false, // Disable app directory for now
  },

  // TypeScript configuration
  typescript: {
    ignoreBuildErrors: false,
  },

  // ESLint configuration
  eslint: {
    ignoreDuringBuilds: false,
  },
}; 