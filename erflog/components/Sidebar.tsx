"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  Target,
  Settings,
  LayoutDashboard,
  Bot,
  MessageCircle,
  Mic,
  MessageSquare,
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-[280px] border-r border-surface flex flex-col"
      style={{ backgroundColor: "#F0EFE9", borderColor: "#E5E0D8" }}
    >
      {/* Logo Area */}
      <div
        className="border-b border-surface p-6"
        style={{ borderColor: "#E5E0D8" }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ backgroundColor: "#D95D39" }}
          >
            <Bot className="w-5 h-5 text-white" />
          </div>
          <h1 className="font-serif-bold text-2xl text-ink">Erflog</h1>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-4 py-6">
        <ul className="space-y-2">
          {/* Nexus / Home */}
          <li>
            <Link
              href="/"
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                pathname === "/"
                  ? "bg-accent text-surface"
                  : "text-ink hover:bg-surface"
              }`}
              style={
                pathname === "/"
                  ? { backgroundColor: "#D95D39", color: "#FFFFFF" }
                  : { color: "#1A1A1A" }
              }
            >
              <Home size={20} />
              Nexus
            </Link>
          </li>

          {/* Dashboard */}
          <li>
            <Link
              href="/dashboard"
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                isActive("/dashboard")
                  ? "bg-accent text-surface"
                  : "text-ink hover:bg-surface"
              }`}
              style={
                isActive("/dashboard")
                  ? { backgroundColor: "#D95D39", color: "#FFFFFF" }
                  : { color: "#1A1A1A" }
              }
            >
              <LayoutDashboard size={20} />
              Dashboard
            </Link>
          </li>

          {/* Strategy Board / Jobs */}
          <li>
            <Link
              href="/jobs"
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                isActive("/jobs")
                  ? "bg-accent text-surface"
                  : "text-ink hover:bg-surface"
              }`}
              style={
                isActive("/jobs")
                  ? { backgroundColor: "#D95D39", color: "#FFFFFF" }
                  : { color: "#1A1A1A" }
              }
            >
              <Target size={20} />
              Strategy Board
            </Link>
          </li>

          {/* Interview Practice */}
          <li>
            <Link
              href="/interview"
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                pathname === "/interview"
                  ? "bg-accent text-surface"
                  : "text-ink hover:bg-surface"
              }`}
              style={
                pathname === "/interview"
                  ? { backgroundColor: "#D95D39", color: "#FFFFFF" }
                  : { color: "#1A1A1A" }
              }
            >
              <MessageCircle size={20} />
              Interview (Chat)
            </Link>
          </li>

          {/* Voice Interview */}
          <li>
            <Link
              href="/interview/voice"
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                isActive("/interview/voice")
                  ? "bg-accent text-surface"
                  : "text-ink hover:bg-surface"
              }`}
              style={
                isActive("/interview/voice")
                  ? { backgroundColor: "#D95D39", color: "#FFFFFF" }
                  : { color: "#1A1A1A" }
              }
            >
              <Mic size={20} />
              Interview (Voice)
            </Link>
          </li>

          {/* Text Interview - WebSocket Test */}
          <li>
            <Link
              href="/interview/text"
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                isActive("/interview/text")
                  ? "bg-accent text-surface"
                  : "text-ink hover:bg-surface"
              }`}
              style={
                isActive("/interview/text")
                  ? { backgroundColor: "#D95D39", color: "#FFFFFF" }
                  : { color: "#1A1A1A" }
              }
            >
              <MessageSquare size={20} />
              Interview (WS Test)
            </Link>
          </li>

          {/* Evolution / Settings */}
          <li>
            <Link
              href="/settings"
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                isActive("/settings")
                  ? "bg-accent text-surface"
                  : "text-ink hover:bg-surface"
              }`}
              style={
                isActive("/settings")
                  ? { backgroundColor: "#D95D39", color: "#FFFFFF" }
                  : { color: "#1A1A1A" }
              }
            >
              <Settings size={20} />
              Evolution
            </Link>
          </li>
        </ul>
      </nav>

      {/* User Profile Snippet - Bottom */}
      <div
        className="border-t border-surface p-4"
        style={{ borderColor: "#E5E0D8" }}
      >
        <div className="flex items-center gap-3">
          <div
            className="h-10 w-10 rounded-full"
            style={{ backgroundColor: "#E5E0D8" }}
          />
          <div className="flex-1">
            <p className="text-sm font-medium text-ink">User</p>
            <p className="text-xs text-secondary">Active</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
