import type { VercelConfig } from '@vercel/config/v1';

// Publish the recorded evidence. Native C++ execution stays in local/CI tests.
export const config: VercelConfig = {
  framework: null,
  buildCommand: 'npm run build',
  outputDirectory: 'dist',
};
