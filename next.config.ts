import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'export',
  basePath: process.env.NODE_ENV === 'production' ? '/interview-2026' : '',
  assetPrefix: process.env.NODE_ENV === 'production' ? '/interview-2026/' : undefined,
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
