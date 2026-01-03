"use client";

import { useParams, useRouter } from "next/navigation";
import { useSession } from "@/lib/SessionContext";
import { ArrowLeft, ExternalLink, Briefcase } from "lucide-react";
// 1. IMPORT THE NEW COMPONENT
import Roadmap from "@/components/MissionControl/Roadmap";
// 2. IMPORT CORRECT TYPES
import { RoadmapDetails } from "@/lib/api";

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;
  const { strategyJobs } = useSession();

  const foundJob = strategyJobs.find((j) => j.id === jobId);

  if (!foundJob) {
    return (
      <div className="min-h-screen bg-canvas py-12 px-8 flex items-center justify-center">
        <div className="text-center">
          <h1 className="font-serif-bold text-3xl text-ink mb-4">Job Not Found</h1>
          <p className="text-secondary mb-6">The job you&apos;re looking for doesn&apos;t exist or was cleared.</p>
          <button onClick={() => router.push("/jobs")} className="px-6 py-3 rounded-lg font-medium text-white bg-[#D95D39]">
            Back to Jobs
          </button>
        </div>
      </div>
    );
  }

  const matchPercentage = Math.round(foundJob.score * 100);

  return (
    <div className="min-h-screen bg-canvas py-12 px-8">
      <button onClick={() => router.push("/jobs")} className="mb-8 flex items-center gap-2 text-secondary hover:text-ink transition-colors">
        <ArrowLeft className="w-5 h-5" /> Back to Jobs
      </button>

      <div className="max-w-4xl mx-auto">
        <div className="bg-surface rounded-xl border border-[#E5E0D8] p-8 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="h-16 w-16 rounded-full flex items-center justify-center font-serif-bold text-2xl text-white bg-[#D95D39]">
                {foundJob.company.charAt(0)}
              </div>
              <div>
                <h1 className="font-serif-bold text-3xl text-ink">{foundJob.title}</h1>
                <p className="text-xl text-secondary mt-1 flex items-center gap-2"><Briefcase size={18} /> {foundJob.company}</p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-[#D95D39]">{matchPercentage}%</div>
              <div className="text-sm text-secondary">Match Score</div>
            </div>
          </div>
        </div>

        <div className="bg-surface rounded-xl border border-[#E5E0D8] p-6 mb-6">
          <h2 className="font-serif-bold text-xl text-ink mb-4">Job Description</h2>
          <p className="text-secondary leading-relaxed whitespace-pre-line">{foundJob.description}</p>
          {foundJob.link && foundJob.link !== "null" && (
            <a href={foundJob.link} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 mt-4 text-sm font-medium text-[#D95D39]">
              View Original Posting <ExternalLink className="w-4 h-4" />
            </a>
          )}
        </div>

        {foundJob.roadmap_details && foundJob.roadmap_details.missing_skills.length > 0 && (
          <div className="bg-surface rounded-xl border border-[#E5E0D8] p-6 mb-6">
            <h2 className="font-serif-bold text-xl text-ink mb-4">Skills to Develop</h2>
            <div className="flex flex-wrap gap-2">
              {foundJob.roadmap_details.missing_skills.map((skill, idx) => (
                <span key={idx} className="px-4 py-2 rounded-full text-sm font-medium bg-orange-100 text-[#D95D39]">{skill}</span>
              ))}
            </div>
          </div>
        )}

        {/* --- ROADMAP SECTION --- */}
        {foundJob.roadmap_details ? (
          <div className="bg-surface rounded-xl border border-[#E5E0D8] p-6 mb-6">
             <Roadmap data={foundJob.roadmap_details as RoadmapDetails} />
          </div>
        ) : (
          <div className="bg-surface rounded-xl border border-dashed border-[#E5E0D8] p-8 text-center mb-6">
            <p className="text-gray-500 italic">Roadmap generation pending...</p>
          </div>
        )}

        <button onClick={() => router.push(`/jobs/${foundJob.id}/apply`)} className="w-full py-4 rounded-xl font-medium text-white text-lg transition-all hover:opacity-90 bg-[#D95D39]">
          Apply Now
        </button>
      </div>
    </div>
  );
}