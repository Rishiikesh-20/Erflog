'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Badge from '@/components/Badge';
import Button from '@/components/Button';
import { Bookmark, BookmarkCheck } from 'lucide-react';

interface JobCardProps {
  id: string;
  companyLogo?: string;
  companyName: string;
  jobTitle: string;
  matchScore: number;
  description?: string;
  link?: string;
  roadmap_details?: {
    missing_skills?: string[];
    graph?: object;
    resources?: object;
    [key: string]: unknown;
  };
  // Full job data for complete save
  fullJobData?: {
    roadmap?: object;
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
    roadmap_details?: object;
    full_job_data?: object;
  }) => void;
  onUnsave?: (id: string) => void;
}

export default function JobCard({
  id,
  companyLogo,
  companyName,
  jobTitle,
  matchScore,
  description,
  link,
  roadmap_details,
  fullJobData,
  isSaved = false,
  onAnalyzeGap,
  onDeploy,
  onSave,
  onUnsave,
}: JobCardProps) {
  const router = useRouter();
  const [saved, setSaved] = useState(isSaved);
  const [saving, setSaving] = useState(false);

  const handleAnalyzeGap = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onAnalyzeGap?.(id);
    router.push(`/jobs/${id}`);
  };

  const handleDeploy = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onDeploy?.(id);
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

  return (
    <div
      className="group relative flex flex-col overflow-hidden rounded-lg border border-surface bg-surface shadow-md transition-all duration-200 hover:shadow-lg hover:scale-[1.02] cursor-pointer"
      style={{ borderColor: '#E5E0D8' }}
      onClick={handleCardClick}
    >
      {/* Score Badge - Top Right */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
        {/* Save Button */}
        <button
          onClick={handleSaveToggle}
          disabled={saving}
          className={`p-2.5 rounded-full transition-all duration-200 ${
            saved 
              ? 'bg-[#D95D39] text-white' 
              : 'bg-white/80 text-gray-600 hover:bg-[#D95D39] hover:text-white'
          } shadow-md`}
          title={saved ? 'Remove from saved' : 'Save job'}
        >
          {saving ? (
            <div className="w-6 h-6 border-2 border-current border-t-transparent rounded-full animate-spin" />
          ) : saved ? (
            <BookmarkCheck className="w-6 h-6" />
          ) : (
            <Bookmark className="w-6 h-6" />
          )}
        </button>
        <Badge variant="score" score={matchScore} />
      </div>

      {/* Card Header with Logo and Title */}
      <div className="border-b border-surface p-6" style={{ borderColor: '#E5E0D8' }}>
        <div className="flex items-start gap-4">
          {/* Logo Placeholder */}
          <div
            className="h-12 w-12 rounded-full flex-shrink-0 flex items-center justify-center font-serif-bold text-lg text-white"
            style={{ backgroundColor: '#D95D39' }}
          >
            {companyName.charAt(0)}
          </div>

          {/* Job Title */}
          <div className="flex-1 pr-16">
            <h3 className="font-serif-bold text-lg text-ink line-clamp-2">{jobTitle}</h3>
          </div>
        </div>
      </div>

      {/* Company Name - Middle */}
      <div className="px-6 py-3 border-b border-surface" style={{ borderColor: '#E5E0D8' }}>
        <p className="text-sm text-secondary">{companyName}</p>
      </div>

      {/* Action Buttons - Bottom */}
      <div className="flex flex-col gap-2 p-6">
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="md"
            onClick={handleAnalyzeGap}
            className="flex-1 text-sm"
          >
            Analyze Gap
          </Button>
          <Button
            variant="black"
            size="md"
            onClick={handleDeploy}
            className="flex-1 text-sm"
          >
            Deploy
          </Button>
        </div>
        <Button
          variant="outline"
          size="md"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            router.push(`/interview/voice?jobId=${id}`);
          }}
          className="w-full text-sm"
          style={{ borderColor: '#D95D39', color: '#D95D39' }}
        >
          🎤 Mock Interview
        </Button>
      </div>
    </div>
  );
}
