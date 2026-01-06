"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAuth } from "@/lib/AuthContext";
import * as api from "@/lib/api";
import type { TodayDataItem } from "@/lib/api";
import {
  Trophy,
  Calendar,
  ExternalLink,
  DollarSign,
  MapPin,
  Loader2,
  Search,
  RefreshCw,
  ArrowLeft,
} from "lucide-react";

export default function HackathonsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [hackathons, setHackathons] = useState<TodayDataItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Fetch hackathons on mount
  useEffect(() => {
    const fetchHackathons = async () => {
      if (!isAuthenticated) return;

      try {
        setIsLoading(true);
        const data = await api.getTodayHackathons();
        setHackathons(data.hackathons || []);
      } catch (err) {
        console.error("Failed to fetch hackathons:", err);
        setError("Failed to load hackathons. Please try again.");
      } finally {
        setIsLoading(false);
      }
    };

    if (!authLoading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else {
        fetchHackathons();
      }
    }
  }, [isAuthenticated, authLoading, router]);

  // Filter hackathons based on search
  const filteredHackathons = hackathons.filter((h) =>
    h.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    h.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
    h.summary.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      await api.refreshTodayData();
      const data = await api.getTodayHackathons();
      setHackathons(data.hackathons || []);
    } catch (err) {
      console.error("Refresh failed:", err);
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F7F5F0]">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-[#D95D39] mx-auto mb-4" />
          <p className="text-gray-600">Loading hackathons...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F7F5F0] py-8 px-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push("/dashboard")}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                <Trophy className="w-8 h-8 text-[#D95D39]" />
                Hackathons
              </h1>
              <p className="text-gray-600 mt-1">
                AI-matched hackathons based on your profile
              </p>
            </div>
          </div>
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {/* Search */}
        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search hackathons..."
              className="w-full pl-12 pr-4 py-3 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#D95D39] focus:border-transparent"
            />
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-red-700">
            {error}
          </div>
        )}

        {/* Hackathon Cards - Responsive Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {filteredHackathons.length > 0 ? (
            filteredHackathons.map((hackathon, index) => (
              <motion.div
                key={hackathon.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="bg-white rounded-2xl border overflow-hidden transition-all duration-300 hover:shadow-xl hover:scale-[1.02] group"
                style={{ 
                  borderColor: "#E5E0D8",
                  background: "linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(249,247,243,0.95) 100%)"
                }}
              >
                {/* Card Header */}
                <div className="p-6 border-b" style={{ borderColor: "#E5E0D8" }}>
                  <div className="flex items-start justify-between gap-4 mb-4">
                    <div className="flex items-start gap-4 flex-1 min-w-0">
                      {/* Trophy Icon */}
                      <div
                        className="h-14 w-14 rounded-xl flex-shrink-0 flex items-center justify-center shadow-lg"
                        style={{ 
                          background: "linear-gradient(135deg, #a855f7 0%, #ec4899 100%)"
                        }}
                      >
                        <Trophy className="w-7 h-7 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-bold text-lg text-gray-900 mb-1 line-clamp-2 group-hover:text-[#D95D39] transition-colors">
                          {hackathon.title}
                        </h3>
                        <p className="text-gray-600 text-sm font-medium">{hackathon.company}</p>
                      </div>
                    </div>
                    {/* Match Score Badge */}
                    <div className="flex-shrink-0">
                      <div
                        className="px-4 py-2 rounded-xl text-center shadow-md"
                        style={{ 
                          background: Math.round(hackathon.score * 100) >= 80 
                            ? "linear-gradient(135deg, #22c55e 0%, #16a34a 100%)"
                            : Math.round(hackathon.score * 100) >= 60
                            ? "linear-gradient(135deg, #D95D39 0%, #c54d2d 100%)"
                            : "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)"
                        }}
                      >
                        <div className="text-2xl font-bold text-white">
                          {Math.round(hackathon.score * 100)}%
                        </div>
                        <div className="text-xs text-white/90 font-medium">Match</div>
                      </div>
                    </div>
                  </div>

                  {/* Platform & Source Badges */}
                  <div className="flex gap-2 flex-wrap">
                    {hackathon.platform && (
                      <span className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-md font-medium">
                        {hackathon.platform}
                      </span>
                    )}
                    {hackathon.source && (
                      <span className="px-2 py-1 bg-purple-50 text-purple-700 text-xs rounded-md font-medium">
                        {hackathon.source}
                      </span>
                    )}
                  </div>
                </div>

                {/* Description */}
                <div className="p-6 border-b" style={{ borderColor: "#E5E0D8" }}>
                  <h4 className="font-semibold text-sm text-gray-900 mb-2 uppercase tracking-wide">
                    About
                  </h4>
                  <p className="text-gray-600 text-sm leading-relaxed line-clamp-3">
                    {hackathon.summary || "No description available"}
                  </p>
                </div>

                {/* Metadata */}
                {hackathon.location && (
                  <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-slate-50 border-b" style={{ borderColor: "#E5E0D8" }}>
                    <div className="flex items-center gap-2 text-sm">
                      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gray-400 to-slate-500 flex items-center justify-center flex-shrink-0">
                        <MapPin className="w-4 h-4 text-white" />
                      </div>
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900">{hackathon.location}</p>
                        <p className="text-xs text-gray-600">Location</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Action Button */}
                <div className="p-6 bg-gray-50">
                  {hackathon.link ? (
                    <a
                      href={hackathon.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full py-3 px-4 rounded-xl font-semibold text-sm text-white transition-all hover:shadow-lg hover:scale-105 flex items-center justify-center gap-2"
                      style={{ background: "linear-gradient(135deg, #a855f7 0%, #ec4899 100%)" }}
                    >
                      View Details
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  ) : (
                    <button
                      disabled
                      className="w-full py-3 px-4 rounded-xl font-semibold text-sm bg-gray-300 text-gray-500 cursor-not-allowed"
                    >
                      No Link Available
                    </button>
                  )}
                </div>
              </motion.div>
            ))
          ) : (
            <div className="col-span-full text-center py-16 bg-white rounded-xl border border-gray-200">
              <Trophy className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 mb-2">No hackathons found</p>
              <p className="text-sm text-gray-400">
                {searchQuery
                  ? "Try a different search term"
                  : "Check back later for new hackathon opportunities"}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
