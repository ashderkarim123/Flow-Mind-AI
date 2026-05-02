import { type Metadata } from 'next'
import { Geist, Geist_Mono, Outfit, Inter } from 'next/font/google'
import { AuthProvider } from '@/lib/AuthContext'
import { BackendAuthProvider } from '@/lib/contexts/BackendAuthContext'
import { ReactQueryProvider } from '@/lib/ReactQueryProvider'
import './globals.css'

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
})

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

const outfit = Outfit({
  variable: '--font-outfit',
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700', '800'],
})

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
})

export const metadata: Metadata = {
  title: 'FlowMind AI — Intelligent Workflow Automation',
  description: 'Build, automate, and scale AI-driven workflows visually. FlowMind AI empowers teams to create intelligent automation without writing a single line of code.',
  keywords: 'AI workflow automation, drag and drop workflow builder, intelligent automation, AI agents, no-code automation',
  authors: [{ name: 'FlowMind AI Team' }],
  openGraph: {
    title: 'FlowMind AI — Intelligent Workflow Automation',
    description: 'Build AI-driven workflows visually with FlowMind AI.',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="h-full">
      <body className={`${geistSans.variable} ${geistMono.variable} ${outfit.variable} ${inter.variable} antialiased h-full`}>
        <ReactQueryProvider>
          <AuthProvider>
            <BackendAuthProvider>
              <div className="h-full">
                {children}
              </div>
            </BackendAuthProvider>
          </AuthProvider>
        </ReactQueryProvider>
      </body>
    </html>
  )
}
