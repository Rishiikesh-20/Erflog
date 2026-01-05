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
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <div className="flex items-center gap-3 text-secondary">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Loading saved jobs...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-cream">
      {/* Header */}
      <header className="bg-white border-b border-surface sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center"
                style={{ backgroundColor: "#D95D39" }}
              >
                <Bookmark className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="font-serif-bold text-2xl text-ink">Saved Jobs</h1>
                <p className="text-sm text-secondary">
                  {savedJobs.length} jobs saved • {selectedJobs.size} selected
                </p>
              </div>
            </div>

            {/* Merge Button */}
            <Button
              variant="black"
              size="lg"
              onClick={handleMergeRoadmaps}
              disabled={selectedJobs.size < 2 || isMerging}
              className="flex items-center gap-2"
            >
              {isMerging ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Merging...
                </>
              ) : (
                <>
                  <GitMerge className="w-4 h-4" />
                  Merge Roadmaps ({selectedJobs.size})
                </>
              )}
            </Button>
          </div>

          {mergeError && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
              {mergeError}
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Global Roadmaps Section */}
        {globalRoadmaps.length > 0 && (
          <section className="mb-12">
            <h2 className="font-serif-bold text-xl text-ink mb-4 flex items-center gap-2">
              <GitMerge className="w-5 h-5" style={{ color: "#D95D39" }} />
              Global Roadmaps
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {globalRoadmaps.map((roadmap) => (
                <div
                  key={roadmap.id}
                  className="bg-white rounded-xl border border-surface p-5 hover:shadow-md transition-all cursor-pointer"
                  onClick={() => router.push(`/global-roadmap/${roadmap.id}`)}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center"
                      style={{ backgroundColor: "#D95D39" }}
                    >
                      <GitMerge className="w-5 h-5 text-white" />
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteRoadmap(roadmap.id);
                      }}
                      className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <h3 className="font-serif-bold text-lg text-ink mb-1">
                    {roadmap.name}
                  </h3>
                  <p className="text-sm text-secondary mb-3">
                    {roadmap.merged_graph.description?.slice(0, 100)}...
                  </p>
                  <div className="flex items-center gap-4 text-xs text-secondary">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {roadmap.merged_graph.total_estimated_weeks || "?"} weeks
                    </span>
                    <span>
                      {roadmap.source_job_ids.length} jobs merged
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Saved Jobs Section */}
        <section>
          <h2 className="font-serif-bold text-xl text-ink mb-4 flex items-center gap-2">
            <Bookmark className="w-5 h-5" style={{ color: "#D95D39" }} />
            Your Saved Jobs
          </h2>

          {savedJobs.length === 0 ? (
            <div className="bg-white rounded-xl border border-surface p-12 text-center">
              <Bookmark className="w-12 h-12 mx-auto text-gray-300 mb-4" />
              <h3 className="font-serif-bold text-lg text-ink mb-2">
                No saved jobs yet
              </h3>
              <p className="text-secondary mb-6">
                Save jobs from the Jobs page to build your personalized roadmap
              </p>
              <Button
                variant="black"
                onClick={() => router.push("/jobs")}
              >
                Browse Jobs
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {savedJobs.map((job) => (
                <div
                  key={job.id}
                  className={`bg-white rounded-xl border-2 p-5 transition-all ${
                    selectedJobs.has(job.id)
                      ? "border-[#D95D39] shadow-md"
                      : "border-surface hover:shadow-md"
                  }`}
                >
                  {/* Selection Checkbox */}
                  <div className="flex items-start justify-between mb-4">
                    <button
                      onClick={() => toggleJobSelection(job.id)}
                      className="flex items-center gap-2 text-sm"
                    >
                      {selectedJobs.has(job.id) ? (
                        <CheckSquare
                          className="w-5 h-5"
                          style={{ color: "#D95D39" }}
                        />
                      ) : (
                        <Square className="w-5 h-5 text-gray-400" />
                      )}
                      <span
                        className={
                          selectedJobs.has(job.id)
                            ? "text-[#D95D39] font-medium"
                            : "text-secondary"
                        }
                      >
                        Select for merge
                      </span>
                    </button>

                    <button
                      onClick={() => handleRemoveJob(job.id)}
                      className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Job Info */}
                  <div className="flex items-start gap-3 mb-4">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 font-serif-bold text-white"
                      style={{ backgroundColor: "#D95D39" }}
                    >
                      {job.company.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-serif-bold text-ink line-clamp-2">
                        {job.title}
                      </h3>
                      <p className="text-sm text-secondary">{job.company}</p>
                    </div>
                    {job.score && (
                      <Badge variant="score" score={Math.round(job.score * 100)} />
                    )}
                  </div>

                  {/* Progress Bar */}
                  {job.progress && Object.keys(job.progress).length > 0 && (
                    <div className="mb-4">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-secondary">Learning Progress</span>
                        <span className="text-[#D95D39] font-medium">
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
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
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
                    <div className="mb-4">
                      <p className="text-xs text-secondary mb-2">Missing Skills:</p>
                      <div className="flex flex-wrap gap-1">
                        {job.roadmap_details.missing_skills.slice(0, 4).map((skill, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-1 bg-orange-50 text-orange-700 text-xs rounded-full"
                          >
                            {skill}
                          </span>
                        ))}
                        {job.roadmap_details.missing_skills.length > 4 && (
                          <span className="px-2 py-1 text-xs text-secondary">
                            +{job.roadmap_details.missing_skills.length - 4} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => router.push(`/jobs/${job.original_job_id}`)}
                      className="flex-1"
                    >
                      View Roadmap
                    </Button>
                    {job.link && (
                      <a
                        href={job.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 border border-surface rounded-lg hover:bg-surface transition-colors"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink className="w-4 h-4 text-secondary" />
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
