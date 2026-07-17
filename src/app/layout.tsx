import './globals.css';
import ClientBootstrap from '@/components/ClientBootstrap';
import type { Metadata, Viewport } from 'next';

export const metadata: Metadata = {
  title: '面试题库 2026',
  description: '2734 道精选面试题，合并 AI / Java / 大厂 JD 三大方向，含费曼快学、第一性原理、结构化回答、视频脚本、苏格拉底式追问、遗忘曲线智能复习。',
  manifest: '/interview-2026/manifest.json',
};

export const viewport: Viewport = {
  themeColor: '#0071e3',
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
