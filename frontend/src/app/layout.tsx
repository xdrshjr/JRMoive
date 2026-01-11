import type { Metadata } from 'next';
import '@/app/globals.css';
import '@/styles/apple-theme.css';

export const metadata: Metadata = {
  title: 'AI Movie Generator',
  description: 'Create stunning videos with AI - Apple-inspired design',
  keywords: ['AI', 'video generation', 'movie maker', 'artificial intelligence'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}

