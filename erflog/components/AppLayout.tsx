"use client";

import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // Pages where sidebar should be hidden
  const hideSidebar = pathname === "/" || pathname.startsWith("/onboarding") || pathname.startsWith("/login");

  if (hideSidebar) {
    return <>{children}</>;
  }

  return (
    <>
      <Sidebar />
      {/* Main content area with left margin for sidebar */}
      <main className="ml-[280px] min-h-screen w-[calc(100%-280px)]">
        {children}
      </main>
    </>
  );
}
