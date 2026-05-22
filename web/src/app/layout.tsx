import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "recording-to-video",
  description: "Turn any screen recording into a polished demo",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen bg-[#0f0f0f] text-white`}>
        {/* Header */}
        <header className="border-b border-zinc-800/60">
          <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
            <div>
              <span className="text-sm font-semibold tracking-tight text-zinc-100">
                recording-to-video
              </span>
              <span className="ml-3 hidden text-xs text-zinc-500 sm:inline">
                Screen recording → polished demo
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              <span className="text-xs text-zinc-500">AI-powered</span>
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="mx-auto max-w-4xl px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
