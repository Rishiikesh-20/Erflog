"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import Image from "next/image";
import {
  Target,
  Settings,
  LayoutDashboard,
  Bot,
  MessageCircle,
  Mic,
  MessageSquare,
  Trophy,
  User,
  Code,
  Bookmark,
} from "lucide-react";
import { useAuth } from "@/lib/AuthContext";

export default function Sidebar() {
  const pathname = usePathname();
  const { userMetadata, isAuthenticated } = useAuth();

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
          {/* Dashboard */}
          <li>
            <Link
              href="/dashboard"
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${isActive("/dashboard")
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
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${isActive("/jobs")
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
              My Jobs
            </Link>
          </li>

          {/* Hackathons */}
          <li>
            <Link
              href="/hackathons"
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                isActive("/hackathons")
                  ? "bg-accent text-surface"
                  : "text-ink hover:bg-surface"
                }`}
              style={
                isActive("/hackathons")
                  ? { backgroundColor: "#D95D39", color: "#FFFFFF" }
                  : { color: "#1A1A1A" }
              }
            >
              <Trophy size={20} />
              Hackathons
            </Link>
          </li>

          {/* Saved Jobs */}
          <li>
            <Link
              href="/saved-jobs"
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                isActive("/saved-jobs") || isActive("/global-roadmap")
                  ? "bg-accent text-surface"
                  : "text-ink hover:bg-surface"
              }`}
              style={
                isActive("/saved-jobs") || isActive("/global-roadmap")
                  ? { backgroundColor: "#D95D39", color: "#FFFFFF" }
                  : { color: "#1A1A1A" }
              }
            >
              <Bookmark size={20} />
              Saved Jobs
            </Link>
          </li>

          {/* Interview Practice */}
          <li>
            <Link
              href="/problem-solving"
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${isActive("/problem-solving")
                  ? "bg-accent text-surface"
                  : "text-ink hover:bg-surface"
                }`}
              style={
                isActive("/problem-solving")
                  ? { backgroundColor: "#D95D39", color: "#FFFFFF" }
                  : { color: "#1A1A1A" }
              }
            >
              <Code size={20} />
              Problem Solving
            </Link>
          </li>

          {/* Evolution / Settings */}
          <li>
            <Link
              href="/settings"
              className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${isActive("/settings")
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
          {userMetadata.avatarUrl ? (
            <Image
              src={userMetadata.avatarUrl}
              alt={userMetadata.fullName || "User"}
              width={40}
              height={40}
              className="rounded-full object-cover"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div
              className="h-10 w-10 rounded-full flex items-center justify-center"
              style={{ backgroundColor: "#E5E0D8" }}
            >
              <User size={20} className="text-gray-500" />
            </div>
          )}
          <div className="flex-1 overflow-hidden">
            <p className="text-sm font-medium text-ink truncate">
              {userMetadata.fullName || "User"}
            </p>
            <p className="text-xs text-secondary truncate">
              {isAuthenticated
                ? userMetadata.email || "Active"
                : "Not signed in"}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
