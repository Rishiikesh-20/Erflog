'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { type RoadmapDetails } from '@/lib/api';
import { Mic, MessageSquare, X, Bookmark, BookmarkCheck, MapPin, Building2, ExternalLink, Target } from 'lucide-react';

interface JobCardProps {
  id: string;
  companyLogo?: string;
  companyName: string;
  jobTitle: string;
  matchScore: number;
  description?: string;
  link?: string;
  roadmap_details?: RoadmapDetails;
  fullJobData?: {
    roadmap?: RoadmapDetails;
    application_text?: object;
    summary?: string;
    location?: string;
    platform?: string;
    source?: string;
    type?: string;
    needs_improvement?: boolean;
    [key: string]: unknown;
  };
  isSaved?: boolean;
  onAnalyzeGap?: (id: string) => void;
  onDeploy?: (id: string) => void;
  onSave?: (job: { 
    id: string; 
    title: string; 
    company: string; 
    description?: string; 
    link?: string; 
    score: number; 
    roadmap_details?: RoadmapDetails | null;
    full_job_data?: object;
  }) => void;
  onUnsave?: (id: string) => void;
  onViewRoadmap?: (id: string) => void;
  onApply?: (id: string) => void;
}

export default function JobCard({
  id,
  companyName,
  jobTitle,
  matchScore,
  description,
  link,
  roadmap_details,
  fullJobData,
  isSaved = false,
  onSave,
  onUnsave,
  onViewRoadmap,
  onApply,
}: JobCardProps) {
  const router = useRouter();
  const [saved, setSaved] = useState(isSaved);
  const [saving, setSaving] = useState(false);
  const [showInterviewModal, setShowInterviewModal] = useState(false);

  const handleViewRoadmap = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onViewRoadmap) {
      onViewRoadmap(id);
    } else {
      router.push(`/jobs/${id}`);
    }
  };

  const handleApply = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onApply) {
      onApply(id);
    } else {
      router.push(`/jobs/${id}/apply`);
    }
  };

  const handleCardClick = () => {
    router.push(`/jobs/${id}`);
  };

  const handleSaveToggle = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setSaving(true);
    
    try {
      if (saved) {
        await onUnsave?.(id);
        setSaved(false);
      } else {
        await onSave?.({
          id,
          title: jobTitle,
          company: companyName,
          description,
          link,
          score: matchScore,
          roadmap_details,
          full_job_data: fullJobData,
        });
        setSaved(true);
      }
    } catch (error) {
      console.error('Failed to save/unsave job:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleMockInterview = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowInterviewModal(true);
  };

  const handleInterviewChoice = (mode: 'voice' | 'text') => {
    setShowInterviewModal(false);
    router.push(`/interview/${id}?mode=${mode}`);
  };

  const getMatchColor = () => {
    if (matchScore >= 80) return 'bg-green-500';
    if (matchScore >= 60) return 'bg-amber-500';
    return 'bg-orange-500';
  };

  const getMatchBgColor = () => {
    if (matchScore >= 80) return 'bg-green-50 border-green-200';
    if (matchScore >= 60) return 'bg-amber-50 border-amber-200';
    return 'bg-orange-50 border-orange-200';
  };

  return (
    <>
      <div 
        className="bg-white rounded-xl border-2 border-gray-200 p-6 hover:shadow-xl hover:border-[#D95D39] transition-all cursor-pointer group"
        onClick={handleCardClick}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex-1 min-w-0">
            <h3 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-[#D95D39] transition-colors">
              {jobTitle}
            </h3>
            <div className="flex items-center gap-2 text-gray-600 text-sm">
              <Building2 className="w-4 h-4 flex-shrink-0" />
              <span className="font-medium">{companyName}</span>
              {fullJobData?.location && (
                <>
                  <span className="text-gray-400">•</span>
                  <MapPin className="w-4 h-4 flex-shrink-0" />
                  <span>{fullJobData.location}</span>
                </>
              )}
            </div>
          </div>
          
          {/* Match Score Badge */}
          <div className={`px-4 py-2 rounded-xl border-2 ${getMatchBgColor()} flex-shrink-0`}>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${getMatchColor()}`} />
              <span className="font-bold text-gray-900">{matchScore}%</span>
            </div>
            <div className="text-xs text-gray-600 mt-0.5">Match</div>
          </div>
        </div>

        {/* Description */}
        {description && (
          <p className="text-sm text-gray-600 line-clamp-2 mb-4">
            {description}
          </p>
        )}

        {/* Divider */}
        <div className="h-px bg-gray-200 mb-4" />

        {/* Action Buttons */}
        <div className="flex items-center gap-2 mb-3">
          <button
            onClick={handleViewRoadmap}
            className="flex-1 px-4 py-2.5 bg-[#D95D39] text-white rounded-lg font-semibold hover:bg-orange-700 transition-all shadow-md hover:shadow-lg"
          >
            View Roadmap
          </button>
          
          <button
            onClick={handleApply}
            className="flex-1 px-4 py-2.5 bg-white border-2 border-gray-200 text-gray-900 rounded-lg font-semibold hover:border-[#D95D39] hover:text-[#D95D39] transition-all"
          >
            Apply
          </button>
          
          <button
            onClick={handleSaveToggle}
            disabled={saving}
            className={`p-2.5 rounded-lg border-2 transition-all ${
              saved 
                ? 'bg-orange-50 border-[#D95D39] text-[#D95D39]' 
                : 'bg-white border-gray-200 text-gray-600 hover:border-[#D95D39] hover:text-[#D95D39]'
            }`}
          >
            {saving ? (
              <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : saved ? (
              <BookmarkCheck className="w-5 h-5" />
            ) : (
              <Bookmark className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Mock Interview Button */}
        <button
          onClick={handleMockInterview}
          className="w-full px-4 py-2.5 bg-gray-50 border-2 border-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-100 hover:border-gray-300 transition-all flex items-center justify-center gap-2"
        >
          <Mic className="w-4 h-4" />
          Mock Interview
        </button>
      </div>

      {/* Interview Modal */}
      {showInterviewModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={(e) => {
            e.stopPropagation();
            setShowInterviewModal(false);
          }}
        >
          <div 
            className="w-full max-w-md mx-4 bg-white rounded-2xl shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xl font-bold text-gray-900">Choose Interview Mode</h3>
                <button
                  onClick={() => setShowInterviewModal(false)}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <p className="text-sm text-gray-600">
                Practice for <span className="font-semibold text-gray-900">{jobTitle}</span>
              </p>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-3">
              <button
                onClick={() => handleInterviewChoice('voice')}
                className="w-full p-4 bg-white border-2 border-gray-200 rounded-xl hover:border-[#D95D39] hover:bg-orange-50 transition-all text-left group"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center group-hover:bg-[#D95D39] transition-colors">
                    <Mic className="w-6 h-6 text-[#D95D39] group-hover:text-white transition-colors" />
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-gray-900 mb-1">Voice Interview</div>
                    <div className="text-sm text-gray-600">Practice with speech-to-text AI</div>
                  </div>
                </div>
              </button>
              
              <button
                onClick={() => handleInterviewChoice('text')}
                className="w-full p-4 bg-white border-2 border-gray-200 rounded-xl hover:border-[#D95D39] hover:bg-orange-50 transition-all text-left group"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center group-hover:bg-[#D95D39] transition-colors">
                    <MessageSquare className="w-6 h-6 text-[#D95D39] group-hover:text-white transition-colors" />
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-gray-900 mb-1">Chat Interview</div>
                    <div className="text-sm text-gray-600">Text-based interview with AI</div>
                  </div>
                </div>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
