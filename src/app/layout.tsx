import './globals.css';
import ClientBootstrap from '@/components/ClientBootstrap';
import type { Metadata, Viewport } from 'next';

export const metadata: Metadata = {
  title: 'Java 面试题库',
  description: '精选 Java 后端高频面试题，涵盖 Java 核心、并发、JVM、Spring、数据库、中间件、分布式、场景设计，含费曼快学、第一性原理、遗忘曲线智能复习。',
  manifest: '/interview-2026/manifest.json',
};

export const viewport: Viewport = {
  themeColor: '#f89820',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var s=localStorage.getItem('interview-2026');var t='light';if(s){var j=JSON.parse(s);t=j.state&&j.state.theme||t;}else if(localStorage.getItem('interview-2026.theme')){t=JSON.parse(localStorage.getItem('interview-2026.theme'));}document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`,
          }}
        />
      </head>
      <body>
        <ClientBootstrap>{children}</ClientBootstrap>
      </body>
    </html>
  );
}
