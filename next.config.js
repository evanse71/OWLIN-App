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
  },
}; 