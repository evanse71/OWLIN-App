// next.config.js
module.exports = {
  // Enable static export for GitHub Pages
  trailingSlash: false,
  assetPrefix: process.env.NODE_ENV === 'production' ? '/OWLIN-App' : '',
  
  // Configure webpack with better module resolution
  webpack: (config, { dev, isServer }) => {
    // Fix module resolution issues
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
      net: false,
      tls: false,
    };
    
    // Better error handling
    config.infrastructureLogging = {
      level: 'error',
    };
    
    if (dev && !isServer) {
      config.watchOptions = {
        ignored: ['**/node_modules/**', '**/.next/**', '**/data/uploads/**', '**/venv/**'],
      };
    }
    
    return config;
  },
  
  // Environment variables
  env: {
            NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8002',
    NEXT_PUBLIC_HOST: process.env.NEXT_PUBLIC_HOST || 'localhost',
    NEXT_PUBLIC_PORT: process.env.NEXT_PUBLIC_PORT || '3000',
  },
  
  // Server configuration for development
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_BASE ? `${process.env.NEXT_PUBLIC_API_BASE}/api/:path*` : 'http://localhost:8002/api/:path*',
      },
    ];
  },

  // Experimental features
  experimental: {
    // Remove deprecated appDir option
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