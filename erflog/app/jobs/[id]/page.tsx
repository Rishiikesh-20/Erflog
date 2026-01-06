"use client";

import { useParams, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { useAuth } from "@/lib/AuthContext";
import * as api from "@/lib/api";
import { ArrowLeft, ExternalLink, Briefcase, Loader2 } from "lucide-react";
// 1. IMPORT THE NEW COMPONENT
import Roadmap from "@/components/MissionControl/Roadmap";
// 2. IMPORT CORRECT TYPES
import { RoadmapDetails, TodayDataItem } from "@/lib/api";

interface JobWithDetails extends TodayDataItem {
  roadmap_details?: RoadmapDetails | null;
  needs_improvement?: boolean;
}

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();

  const [job, setJob] = useState<JobWithDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savedJobId, setSavedJobId] = useState<string | null>(null);

  // Fetch job from API
  useEffect(() => {
    const fetchJob = async () => {
      if (!isAuthenticated || !user) return;

      try {
        setIsLoading(true);
        const data = await api.getTodayJobs();

        // Find the job by ID (handle both "192" and "192.0" formats)
        const foundJob = data.jobs?.find((j: TodayDataItem) => {
          const jId = String(j.id);
          const searchId = String(jobId);
          // Compare with and without decimal suffix
          return (
            jId === searchId ||
            jId === searchId.replace(".0", "") ||
            jId + ".0" === searchId
          );
        });

        if (foundJob) {
          setJob({
            ...foundJob,
            roadmap_details: foundJob.roadmap || null,
            needs_improvement: foundJob.needs_improvement,
          });
          
          // Check if this job is saved and get the saved_job_id for progress tracking
          try {
            const savedCheck = await api.checkJobSaved(user.id, String(foundJob.id));
            if (savedCheck.is_saved && savedCheck.saved_job_id) {
              setSavedJobId(savedCheck.saved_job_id);
            }
          } catch (err) {
            console.error("Failed to check saved status:", err);
          }
        } else {
          setError("Job not found");
        }
      } catch (err) {
        console.error("Failed to fetch job:", err);
        setError("Failed to load job details");
      } finally {
        setIsLoading(false);
      }
    };

    if (!authLoading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else {
        fetchJob();
      }
    }
  }, [isAuthenticated, authLoading, jobId, router, user]);

  // Loading state
  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F7F5F0]">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-[#D95D39] mx-auto mb-4" />
          <p className="text-gray-600">Loading job details...</p>
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="min-h-screen bg-canvas py-12 px-8 flex items-center justify-center">
        <div className="text-center">
          <h1 className="font-serif-bold text-3xl text-ink mb-4">
            Job Not Found
          </h1>
          <p className="text-secondary mb-6">
            The job you&apos;re looking for doesn&apos;t exist or was cleared.
          </p>
          <button
            onClick={() => router.push("/jobs")}
            className="px-6 py-3 rounded-lg font-medium text-white bg-[#D95D39]"
          >
            Back to Jobs
          </button>
        </div>
      </div>
    );
  }

  const matchPercentage = Math.round(job.score * 100);

  return (
    <div className="min-h-screen bg-canvas py-12 px-8">
      <button
        onClick={() => router.push("/jobs")}
        className="mb-8 flex items-center gap-2 text-secondary hover:text-ink transition-colors"
      >
        <ArrowLeft className="w-5 h-5" /> Back to Jobs
      </button>

      <div className="max-w-4xl mx-auto">
        {/* Job Header */}
        <div className="bg-surface rounded-xl border border-[#E5E0D8] p-8 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="h-16 w-16 rounded-full flex items-center justify-center font-serif-bold text-2xl text-white bg-[#D95D39]">
                {job.company.charAt(0)}
              </div>
              <div>
                <h1 className="font-serif-bold text-3xl text-ink">
                  {job.title}
                </h1>
                <p className="text-xl text-secondary mt-1 flex items-center gap-2">
                  <Briefcase size={18} /> {job.company}
                </p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-[#D95D39]">
                {matchPercentage}%
              </div>
              <div className="text-sm text-secondary">Match Score</div>
              {job.needs_improvement && (
                <span className="inline-block mt-2 px-2 py-1 text-xs rounded-full bg-orange-100 text-orange-700">
                  Roadmap Available
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Job Description */}
        <div className="bg-surface rounded-xl border border-[#E5E0D8] p-6 mb-6">
          <h2 className="font-serif-bold text-xl text-ink mb-4">
            Job Description
          </h2>
          <p className="text-secondary leading-relaxed whitespace-pre-line">
            {job.summary || "No description available"}
          </p>
          {job.link && job.link !== "null" && (
            <a
              href={job.link}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 mt-4 text-sm font-medium text-[#D95D39]"
            >
              View Original Posting <ExternalLink className="w-4 h-4" />
            </a>
          )}
        </div>

        {/* Missing Skills */}
        {job.roadmap_details &&
          job.roadmap_details.missing_skills &&
          job.roadmap_details.missing_skills.length > 0 && (
            <div className="bg-surface rounded-xl border border-[#E5E0D8] p-6 mb-6">
              <h2 className="font-serif-bold text-xl text-ink mb-4">
                Skills to Develop
              </h2>
              <div className="flex flex-wrap gap-2">
                {job.roadmap_details.missing_skills.map((skill, idx) => (
                  <span
                    key={idx}
                    className="px-4 py-2 rounded-full text-sm font-medium bg-orange-100 text-[#D95D39]"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

        {/* --- ROADMAP SECTION --- */}
        {job.roadmap_details && job.roadmap_details.graph ? (
          <div className="bg-surface rounded-xl border border-[#E5E0D8] p-6 mb-6">
            <Roadmap data={job.roadmap_details as RoadmapDetails} savedJobId={savedJobId || undefined} userId={user?.id} />
          </div>
        ) : matchPercentage >= 80 ? (
          <div className="bg-green-50 rounded-xl border border-green-200 p-6 mb-6 text-center">
            <p className="text-green-700 font-medium">
              🎉 Great Match! No additional learning needed.
            </p>
            <p className="text-green-600 text-sm mt-1">
              Your skills are well-aligned with this position.
            </p>
          </div>
        ) : (
          <div className="bg-surface rounded-xl border border-dashed border-[#E5E0D8] p-8 text-center mb-6">
            <p className="text-gray-500 italic">
              Roadmap generation pending...
            </p>
          </div>
        )}

        {/* Apply Button */}
        <button
          onClick={() => router.push(`/jobs/${job.id}/apply`)}
          className="w-full py-4 rounded-xl font-medium text-white text-lg transition-all hover:opacity-90 bg-[#D95D39]"
        >
          Apply Now
        </button>
      </div>
    </div>
  );
}
