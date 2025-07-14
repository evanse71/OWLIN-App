// next.config.js
module.exports = {
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      config.watchOptions = {
        ignored: ['**/node_modules/**', '**/.next/**', '**/data/uploads/**', '**/venv/**'],
      };
    }
    return config;
  },
}; 