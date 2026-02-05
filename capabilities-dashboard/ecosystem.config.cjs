module.exports = {
  apps: [
    {
      name: 'dashboard-server',
      cwd: '/Users/mmirvois/projects/capabilities-dashboard',
      script: 'npx',
      args: 'tsx server/index.ts',
      watch: false,
      env: {
        NODE_ENV: 'development',
        PORT: 3001
      }
    },
    {
      name: 'dashboard-client',
      cwd: '/Users/mmirvois/projects/capabilities-dashboard',
      script: 'npx',
      args: 'vite',
      watch: false,
      env: {
        NODE_ENV: 'development'
      }
    }
  ]
};
