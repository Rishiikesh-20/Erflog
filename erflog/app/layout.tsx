import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Sidebar from "@/components/Sidebar";
import { SessionProvider } from "@/lib/SessionContext";
import { AuthProvider } from "@/lib/AuthContext";
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
  title: "Erflog | Career Intelligence Platform",
  description: "Initialize your career protocol with AI-powered job matching",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        style={{ backgroundColor: "#F7F5F0" }}
      >
        <AuthProvider>
          <SessionProvider>
            <Sidebar />
            {/* Main content area with left margin for sidebar */}
            <main className="ml-[280px] min-h-screen w-[calc(100%-280px)]">
              {children}
            </main>
          </SessionProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
