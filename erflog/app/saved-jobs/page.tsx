"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import * as api from "@/lib/api";
import type { SavedJob, GlobalRoadmap } from "@/lib/api";
import {
  Bookmark,
  Trash2,
  GitMerge,
  Loader2,
  ArrowRight,
  CheckSquare,
  Square,
  MapPin,
  Clock,
  ExternalLink,
  Target,
} from "lucide-react";
import Badge from "@/components/Badge";
import Button from "@/components/Button";

export default function SavedJobsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [savedJobs, setSavedJobs] = useState<SavedJob[]>([]);
  const [globalRoadmaps, setGlobalRoadmaps] = useState<GlobalRoadmap[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());
  const [isMerging, setIsMerging] = useState(false);
  const [mergeError, setMergeError] = useState<string | null>(null);

  // Fetch saved jobs and global roadmaps
  useEffect(() => {
    const fetchData = async () => {
      if (!user?.id) return;
      
      setIsLoading(true);
      try {
        const [jobs, roadmaps] = await Promise.all([
          api.getSavedJobs(user.id),
          api.getGlobalRoadmaps(user.id),
        ]);
        setSavedJobs(jobs);
        setGlobalRoadmaps(roadmaps);
      } catch (error) {
        console.error("Failed to fetch data:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [user?.id]);

  // Toggle job selection
  const toggleJobSelection = (jobId: string) => {
    setSelectedJobs((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(jobId)) {
        newSet.delete(jobId);
      } else {
        newSet.add(jobId);
      }
      return newSet;
    });
  };

  // Handle remove saved job
  const handleRemoveJob = async (jobId: string) => {
    try {
      await api.removeSavedJob(jobId);
      setSavedJobs((prev) => prev.filter((job) => job.id !== jobId));
      setSelectedJobs((prev) => {
        const newSet = new Set(prev);
        newSet.delete(jobId);
        return newSet;
      });
    } catch (error) {
      console.error("Failed to remove job:", error);
    }
  };

  // Handle merge roadmaps
  const handleMergeRoadmaps = async () => {
    if (selectedJobs.size < 2) {
      setMergeError("Please select at least 2 jobs to merge roadmaps");
      return;
    }

    setIsMerging(true);
    setMergeError(null);

    try {
      const result = await api.mergeRoadmaps(Array.from(selectedJobs));
      setGlobalRoadmaps((prev) => [result, ...prev]);
      setSelectedJobs(new Set());
      // Navigate to the new roadmap
      router.push(`/global-roadmap/${result.id}`);
    } catch (error: any) {
      console.error("Failed to merge roadmaps:", error);
      setMergeError(error?.response?.data?.detail || "Failed to merge roadmaps");
    } finally {
      setIsMerging(false);
    }
  };

  // Handle delete global roadmap
  const handleDeleteRoadmap = async (roadmapId: string) => {
    try {
      await api.deleteGlobalRoadmap(roadmapId);
      setGlobalRoadmaps((prev) => prev.filter((r) => r.id !== roadmapId));
    } catch (error) {
      console.error("Failed to delete roadmap:", error);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex items-center gap-3 text-gray-600">
          <Loader2 className="w-6 h-6 animate-spin text-[#D95D39]" />
          <span>Loading saved jobs...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b-2 border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-[#D95D39] flex items-center justify-center shadow-lg">
                <Bookmark className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Saved Jobs</h1>
                <p className="text-sm text-gray-600 mt-0.5">
                  {savedJobs.length} jobs saved • {selectedJobs.size} selected
                </p>
              </div>
            </div>

            {/* Merge Button */}
            <button
              onClick={handleMergeRoadmaps}
              disabled={selectedJobs.size < 2 || isMerging}
              className={`flex items-center gap-2 px-5 py-3 rounded-lg font-semibold transition-all ${
                selectedJobs.size < 2 || isMerging
                  ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                  : "bg-[#D95D39] text-white hover:bg-orange-700 shadow-lg hover:shadow-xl"
              }`}
            >
              {isMerging ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Merging...
                </>
              ) : (
                <>
                  <GitMerge className="w-5 h-5" />
                  Merge Roadmaps ({selectedJobs.size})
                </>
              )}
            </button>
          </div>

          {mergeError && (
            <div className="mt-4 p-3 bg-red-50 border-2 border-red-200 rounded-lg text-red-700 text-sm font-medium">
              {mergeError}
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Global Roadmaps Section */}
        {globalRoadmaps.length > 0 && (
          <section className="mb-12">
            <h2 className="text-xl font-bold text-gray-900 mb-5 flex items-center gap-2">
              <GitMerge className="w-6 h-6 text-[#D95D39]" />
              Global Roadmaps
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {globalRoadmaps.map((roadmap) => (
                <div
                  key={roadmap.id}
                  className="bg-white rounded-xl border-2 border-gray-200 p-6 hover:shadow-xl hover:border-[#D95D39] transition-all cursor-pointer group"
                  onClick={() => router.push(`/global-roadmap/${roadmap.id}`)}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="w-12 h-12 rounded-xl bg-[#D95D39] flex items-center justify-center shadow-md">
                      <GitMerge className="w-6 h-6 text-white" />
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteRoadmap(roadmap.id);
                      }}
                      className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                  <h3 className="font-bold text-lg text-gray-900 mb-2 group-hover:text-[#D95D39] transition-colors">
                    {roadmap.name}
                  </h3>
                  <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                    {roadmap.merged_graph.description?.slice(0, 100)}...
                  </p>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-50 text-orange-700 rounded-full font-medium">
                      <Clock className="w-3.5 h-3.5" />
                      {roadmap.merged_graph.total_estimated_weeks || "?"} weeks
                    </span>
                    <span className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full font-medium">
                      {roadmap.source_job_ids.length} jobs
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Saved Jobs Section */}
        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-5 flex items-center gap-2">
            <Bookmark className="w-6 h-6 text-[#D95D39]" />
            Your Saved Jobs
          </h2>

          {savedJobs.length === 0 ? (
            <div className="bg-white rounded-xl border-2 border-gray-200 p-16 text-center">
              <div className="w-20 h-20 rounded-full bg-orange-50 flex items-center justify-center mx-auto mb-5">
                <Bookmark className="w-10 h-10 text-[#D95D39]" />
              </div>
              <h3 className="font-bold text-xl text-gray-900 mb-2">
                No saved jobs yet
              </h3>
              <p className="text-gray-600 mb-6 max-w-md mx-auto">
                Save jobs from the Jobs page to build your personalized roadmap and track your learning progress
              </p>
              <button
                onClick={() => router.push("/jobs")}
                className="px-6 py-3 bg-[#D95D39] text-white rounded-lg font-semibold hover:bg-orange-700 transition-all shadow-lg hover:shadow-xl"
              >
                Browse Jobs
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {savedJobs.map((job) => (
                <div
                  key={job.id}
                  className={`bg-white rounded-xl border-2 p-6 transition-all hover:shadow-xl ${
                    selectedJobs.has(job.id)
                      ? "border-[#D95D39] shadow-lg"
                      : "border-gray-200 hover:border-orange-300"
                  }`}
                >
                  {/* Selection Checkbox */}
                  <div className="flex items-start justify-between mb-5">
                    <button
                      onClick={() => toggleJobSelection(job.id)}
                      className="flex items-center gap-2 text-sm group"
                    >
                      {selectedJobs.has(job.id) ? (
                        <CheckSquare className="w-5 h-5 text-[#D95D39]" />
                      ) : (
                        <Square className="w-5 h-5 text-gray-400 group-hover:text-[#D95D39] transition-colors" />
                      )}
                      <span
                        className={`font-medium ${
                          selectedJobs.has(job.id)
                            ? "text-[#D95D39]"
                            : "text-gray-600 group-hover:text-[#D95D39]"
                        } transition-colors`}
                      >
                        Select for merge
                      </span>
                    </button>

                    <button
                      onClick={() => handleRemoveJob(job.id)}
                      className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>

                  {/* Job Info */}
                  <div className="flex items-start gap-3 mb-5">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 font-bold text-xl text-white bg-[#D95D39] shadow-md">
                      {job.company.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold text-gray-900 line-clamp-2 mb-1">
                        {job.title}
                      </h3>
                      <p className="text-sm text-gray-600">{job.company}</p>
                    </div>
                    {job.score && (
                      <div className="px-3 py-1.5 bg-orange-50 text-[#D95D39] rounded-lg text-sm font-bold">
                        {Math.round(job.score * 100)}%
                      </div>
                    )}
                  </div>

                  {/* Progress Bar */}
                  {job.progress && Object.keys(job.progress).length > 0 && (
                    <div className="mb-5">
                      <div className="flex items-center justify-between text-xs mb-2">
                        <span className="text-gray-600 font-medium">Learning Progress</span>
                        <span className="text-[#D95D39] font-bold">
                          {(() => {
                            const fullJobData = job.roadmap_details?.full_job_data as any;
                            const graph = job.roadmap_details?.graph || 
                              fullJobData?.roadmap?.graph;
                            const totalNodes = graph?.nodes?.length || 0;
                            const completedNodes = Object.values(job.progress).filter(
                              (p: any) => p.completed
                            ).length;
                            return totalNodes > 0 
                              ? `${Math.round((completedNodes / totalNodes) * 100)}%`
                              : "0%";
                          })()}
                        </span>
                      </div>
                      <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#D95D39] rounded-full transition-all"
                          style={{
                            width: (() => {
                              const fullJobData = job.roadmap_details?.full_job_data as any;
                              const graph = job.roadmap_details?.graph || 
                                fullJobData?.roadmap?.graph;
                              const totalNodes = graph?.nodes?.length || 0;
                              const completedNodes = Object.values(job.progress).filter(
                                (p: any) => p.completed
                              ).length;
                              return totalNodes > 0 
                                ? `${(completedNodes / totalNodes) * 100}%`
                                : "0%";
                            })(),
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Missing Skills */}
                  {job.roadmap_details?.missing_skills && (
                    <div className="mb-5">
                      <p className="text-xs text-gray-600 font-medium mb-2 flex items-center gap-1.5">
                        <Target className="w-3.5 h-3.5" />
                        Skills to Learn:
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {job.roadmap_details.missing_skills.slice(0, 4).map((skill, idx) => (
                          <span
                            key={idx}
                            className="px-2.5 py-1 bg-orange-50 text-orange-700 text-xs rounded-full font-medium border border-orange-200"
                          >
                            {skill}
                          </span>
                        ))}
                        {job.roadmap_details.missing_skills.length > 4 && (
                          <span className="px-2.5 py-1 text-xs text-gray-500 font-medium">
                            +{job.roadmap_details.missing_skills.length - 4} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => router.push(`/jobs/${job.original_job_id}`)}
                      className="flex-1 px-4 py-2.5 bg-[#D95D39] text-white rounded-lg font-semibold hover:bg-orange-700 transition-all shadow-md hover:shadow-lg"
                    >
                      View Roadmap
                    </button>
                    {job.link && (
                      <a
                        href={job.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2.5 border-2 border-gray-200 rounded-lg hover:border-[#D95D39] hover:bg-orange-50 transition-colors"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink className="w-5 h-5 text-gray-600" />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
