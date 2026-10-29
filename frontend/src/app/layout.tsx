import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { PrototypeBanner } from "@/components/PrototypeBanner";
import { AppFooter } from "@/components/ui/AppFooter";
import { AppHeader } from "@/components/ui/AppHeader";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Trade Surveillance Agent",
  description:
    "An insider-trading investigation agent whose findings are checked against the evidence, and whose process is audited, before you see them.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body suppressHydrationWarning className="flex min-h-full flex-col font-sans">
        <AppHeader />
        <PrototypeBanner />
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 sm:py-10">{children}</main>
        <AppFooter />
      </body>
    </html>
  );
}
