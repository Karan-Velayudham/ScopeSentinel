import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { AppSidebar } from "@/components/app-sidebar";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

import { HitlBanner } from "@/components/hitl-banner";

export const metadata: Metadata = {
  title: "ScopeSentinel",
  description: "Web UI Monitoring Dashboard for ScopeSentinel",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} min-h-screen font-sans antialiased`}>
        <Providers attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          {children}
        </Providers>
      </body>
    </html>
  );
}
