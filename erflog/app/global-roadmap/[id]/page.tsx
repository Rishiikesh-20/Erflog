"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import * as api from "@/lib/api";
import type { GlobalRoadmap } from "@/lib/api";
import {
  GitMerge,
  Loader2,
  ArrowLeft,
  Clock,
  Target,
  CheckCircle,
  Circle,
  ChevronDown,
  ChevronRight,
  BookOpen,
  Sparkles,
  Briefcase,
} from "lucide-react";
import Button from "@/components/Button";

export default function GlobalRoadmapPage() {
  const router = useRouter();
  const params = useParams();
  const roadmapId = params.id as string;

  const [roadmap, setRoadmap] = useState<GlobalRoadmap | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedPhases, setExpandedPhases] = useState<Set<number>>(new Set([1]));
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fetchRoadmap = async () => {
      try {
        const data = await api.getGlobalRoadmap(roadmapId);
        setRoadmap(data);
        // Auto-expand first category
        if (data.merged_graph.skill_categories?.[0]) {
          setExpandedCategories(new Set([data.merged_graph.skill_categories[0].category]));
        }
      } catch (error) {
        console.error("Failed to fetch roadmap:", error);
      } finally {
        setIsLoading(false);
      }
    };

    if (roadmapId) {
      fetchRoadmap();
    }
  }, [roadmapId]);

  const togglePhase = (phase: number) => {
    setExpandedPhases((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(phase)) {
        newSet.delete(phase);
      } else {
        newSet.add(phase);
      }
      return newSet;
    });
  };

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(category)) {
        newSet.delete(category);
      } else {
        newSet.add(category);
      }
      return newSet;
    });
  };

  const getPriorityColor = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case "high":
        return "bg-red-100 text-red-700 border-red-200";
      case "medium":
        return "bg-yellow-100 text-yellow-700 border-yellow-200";
      case "low":
        return "bg-green-100 text-green-700 border-green-200";
      default:
        return "bg-gray-100 text-gray-700 border-gray-200";
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <div className="flex items-center gap-3 text-secondary">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Loading roadmap...</span>
        </div>
      </div>
    );
  }

  if (!roadmap) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <div className="text-center">
          <h2 className="font-serif-bold text-xl text-ink mb-2">Roadmap not found</h2>
          <Button variant="outline" onClick={() => router.push("/saved-jobs")}>
            Back to Saved Jobs
          </Button>
        </div>
      </div>
    );
  }

  const { merged_graph } = roadmap;

  return (
    <div className="min-h-screen bg-cream">
      {/* Header */}
      <header className="bg-white border-b border-surface sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <button
            onClick={() => router.push("/saved-jobs")}
            className="flex items-center gap-2 text-secondary hover:text-ink transition-colors mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Saved Jobs
          </button>

          <div className="flex items-center gap-4">
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center"
              style={{ backgroundColor: "#D95D39" }}
            >
              <GitMerge className="w-7 h-7 text-white" />
            </div>
            <div className="flex-1">
              <h1 className="font-serif-bold text-2xl text-ink">
                {roadmap.name}
              </h1>
              <p className="text-secondary">
                {merged_graph.description}
              </p>
            </div>
          </div>

          {/* Stats Bar */}
          <div className="flex items-center gap-6 mt-6 pb-2">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-secondary" />
              <span className="text-sm">
                <strong>{merged_graph.total_estimated_weeks || "?"}</strong> weeks total
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4 text-secondary" />
              <span className="text-sm">
                <strong>{merged_graph.combined_missing_skills?.length || 0}</strong> skills to learn
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-secondary" />
              <span className="text-sm">
                <strong>{merged_graph.source_jobs?.length || roadmap.source_job_ids.length}</strong> jobs merged
              </span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content - Learning Path */}
          <div className="lg:col-span-2 space-y-6">
            {/* Learning Path Timeline */}
            {merged_graph.learning_path && merged_graph.learning_path.length > 0 && (
              <section>
                <h2 className="font-serif-bold text-xl text-ink mb-4 flex items-center gap-2">
                  <Sparkles className="w-5 h-5" style={{ color: "#D95D39" }} />
                  Learning Path
                </h2>
                <div className="space-y-4">
                  {merged_graph.learning_path.map((phase, idx) => (
                    <div
                      key={idx}
                      className="bg-white rounded-xl border border-surface overflow-hidden"
                    >
                      <button
                        onClick={() => togglePhase(phase.phase)}
                        className="w-full flex items-center justify-between p-4 hover:bg-surface/50 transition-colors"
                      >
                        <div className="flex items-center gap-4">
                          <div
                            className="w-10 h-10 rounded-full flex items-center justify-center font-serif-bold text-white"
                            style={{ backgroundColor: "#D95D39" }}
                          >
                            {phase.phase}
                          </div>
                          <div className="text-left">
                            <h3 className="font-serif-bold text-ink">
                              {phase.title}
                            </h3>
                            <p className="text-sm text-secondary">
                              {phase.duration_weeks} weeks • {phase.skills?.length || 0} skills
                            </p>
                          </div>
                        </div>
                        {expandedPhases.has(phase.phase) ? (
                          <ChevronDown className="w-5 h-5 text-secondary" />
                        ) : (
                          <ChevronRight className="w-5 h-5 text-secondary" />
                        )}
                      </button>

                      {expandedPhases.has(phase.phase) && (
                        <div className="px-4 pb-4 border-t border-surface">
                          <div className="pt-4">
                            {/* Milestone */}
                            <div className="flex items-start gap-3 mb-4 p-3 bg-green-50 rounded-lg">
                              <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                              <div>
                                <p className="text-sm font-medium text-green-800">Milestone</p>
                                <p className="text-sm text-green-700">{phase.milestone}</p>
                              </div>
                            </div>

                            {/* Skills */}
                            <div className="flex flex-wrap gap-2">
                              {phase.skills?.map((skill, skillIdx) => (
                                <span
                                  key={skillIdx}
                                  className="px-3 py-1.5 bg-surface rounded-full text-sm text-ink"
                                >
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Skill Categories */}
            {merged_graph.skill_categories && merged_graph.skill_categories.length > 0 && (
              <section>
                <h2 className="font-serif-bold text-xl text-ink mb-4 flex items-center gap-2">
                  <BookOpen className="w-5 h-5" style={{ color: "#D95D39" }} />
                  Skills by Category
                </h2>
                <div className="space-y-3">
                  {merged_graph.skill_categories.map((category, idx) => (
                    <div
                      key={idx}
                      className="bg-white rounded-xl border border-surface overflow-hidden"
                    >
                      <button
                        onClick={() => toggleCategory(category.category)}
                        className="w-full flex items-center justify-between p-4 hover:bg-surface/50 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <span className="font-serif-bold text-ink">
                            {category.category}
                          </span>
                          <span className="text-sm text-secondary">
                            ({category.skills?.length || 0} skills)
                          </span>
                        </div>
                        {expandedCategories.has(category.category) ? (
                          <ChevronDown className="w-5 h-5 text-secondary" />
                        ) : (
                          <ChevronRight className="w-5 h-5 text-secondary" />
                        )}
                      </button>

                      {expandedCategories.has(category.category) && (
                        <div className="px-4 pb-4 border-t border-surface">
                          <div className="pt-4 space-y-3">
                            {category.skills?.map((skill, skillIdx) => (
                              <div
                                key={skillIdx}
                                className="flex items-start gap-3 p-3 bg-surface/50 rounded-lg"
                              >
                                <Circle className="w-4 h-4 text-secondary mt-0.5 flex-shrink-0" />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="font-medium text-ink">
                                      {skill.name}
                                    </span>
                                    <span
                                      className={`px-2 py-0.5 text-xs rounded-full border ${getPriorityColor(
                                        skill.priority
                                      )}`}
                                    >
                                      {skill.priority}
                                    </span>
                                    {skill.estimated_weeks && (
                                      <span className="text-xs text-secondary">
                                        ~{skill.estimated_weeks} weeks
                                      </span>
                                    )}
                                  </div>
                                  {skill.appears_in_jobs && skill.appears_in_jobs.length > 0 && (
                                    <p className="text-xs text-secondary mt-1">
                                      Required for: {skill.appears_in_jobs.join(", ")}
                                    </p>
                                  )}
                                  {skill.resources && skill.resources.length > 0 && (
                                    <div className="mt-2">
                                      <p className="text-xs text-secondary mb-1">Resources:</p>
                                      <div className="flex flex-wrap gap-1">
                                        {skill.resources.map((resource: any, rIdx: number) => (
                                          typeof resource === 'string' ? (
                                            <span
                                              key={rIdx}
                                              className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded"
                                            >
                                              {resource}
                                            </span>
                                          ) : (
                                            <a
                                              key={rIdx}
                                              href={resource.url}
                                              target="_blank"
                                              rel="noopener noreferrer"
                                              className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded hover:bg-blue-100 transition-colors"
                                            >
                                              {resource.name || resource.url}
                                            </a>
                                          )
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Source Jobs */}
            <div className="bg-white rounded-xl border border-surface p-5">
              <h3 className="font-serif-bold text-lg text-ink mb-4">
                Source Jobs
              </h3>
              <div className="space-y-3">
                {merged_graph.source_jobs?.map((job, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-3 p-3 bg-surface/50 rounded-lg"
                  >
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center text-white font-serif-bold text-sm"
                      style={{ backgroundColor: "#D95D39" }}
                    >
                      {job.company.charAt(0)}
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium text-ink text-sm truncate">
                        {job.title}
                      </p>
                      <p className="text-xs text-secondary">{job.company}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* All Skills Summary */}
            <div className="bg-white rounded-xl border border-surface p-5">
              <h3 className="font-serif-bold text-lg text-ink mb-4">
                All Skills to Learn
              </h3>
              <div className="flex flex-wrap gap-2">
                {merged_graph.combined_missing_skills?.map((skill, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-orange-50 text-orange-700 text-xs rounded-full"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>

            {/* All Resources Section */}
            {merged_graph.all_resources && merged_graph.all_resources.length > 0 && (
              <div className="bg-white rounded-xl border border-surface p-5">
                <h3 className="font-serif-bold text-lg text-ink mb-4 flex items-center gap-2">
                  <BookOpen className="w-5 h-5" style={{ color: "#D95D39" }} />
                  Learning Resources
                </h3>
                <div className="space-y-4">
                  {merged_graph.all_resources.map((item: any, idx: number) => (
                    <div key={idx} className="border-b border-surface pb-3 last:border-0 last:pb-0">
                      <p className="font-medium text-ink text-sm mb-2">{item.skill}</p>
                      <div className="flex flex-wrap gap-2">
                        {item.resources?.map((resource: any, rIdx: number) => (
                          typeof resource === 'string' ? (
                            <span
                              key={rIdx}
                              className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded"
                            >
                              {resource}
                            </span>
                          ) : resource?.url ? (
                            <a
                              key={rIdx}
                              href={resource.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded hover:bg-blue-100 transition-colors flex items-center gap-1"
                            >
                              📚 {resource.name || resource.url}
                            </a>
                          ) : null
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Quick Actions */}
            <div className="bg-white rounded-xl border border-surface p-5">
              <h3 className="font-serif-bold text-lg text-ink mb-4">
                Quick Actions
              </h3>
              <div className="space-y-2">
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => router.push("/saved-jobs")}
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Saved Jobs
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => router.push("/jobs")}
                >
                  <Target className="w-4 h-4 mr-2" />
                  Find More Jobs
                </Button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
