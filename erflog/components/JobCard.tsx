'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Badge from '@/components/Badge';
import Button from '@/components/Button';
import { Mic, MessageSquare, X } from 'lucide-react';

interface JobCardProps {
  id: string;
  companyLogo?: string;
  companyName: string;
  jobTitle: string;
  matchScore: number;
  onViewRoadmap?: (id: string) => void;
  onApply?: (id: string) => void;
}

export default function JobCard({
  id,
  companyLogo,
  companyName,
  jobTitle,
  matchScore,
  onViewRoadmap,
  onApply,
}: JobCardProps) {
  const router = useRouter();
  const [showInterviewModal, setShowInterviewModal] = useState(false);

  const handleViewRoadmap = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onViewRoadmap?.(id);
    router.push(`/jobs/${id}`);
  };

  const handleApply = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onApply?.(id);
    router.push(`/jobs/${id}/apply`);
  };

  const handleCardClick = () => {
    router.push(`/jobs/${id}`);
  };

  const handleMockInterview = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowInterviewModal(true);
  };

  const handleInterviewChoice = (type: 'voice' | 'text') => {
    setShowInterviewModal(false);
    router.push(`/interview/${type}?jobId=${id}`);
  };

  return (
    <>
      <div
        className="group relative flex flex-col overflow-hidden rounded-lg border border-surface bg-surface shadow-md transition-all duration-200 hover:shadow-lg hover:scale-[1.02] cursor-pointer"
        style={{ borderColor: '#E5E0D8' }}
        onClick={handleCardClick}
      >
        {/* Score Badge - Top Right */}
        <div className="absolute top-4 right-4 z-10">
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
            <div className="flex-1 pr-12">
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
              onClick={handleViewRoadmap}
              className="flex-1 text-sm"
            >
              View Roadmap
            </Button>
            <Button
              variant="black"
              size="md"
              onClick={handleApply}
              className="flex-1 text-sm"
            >
              Apply
            </Button>
          </div>
          <Button
            variant="outline"
            size="md"
            onClick={handleMockInterview}
            className="w-full text-sm"
            style={{ borderColor: '#D95D39', color: '#D95D39' }}
          >
            🎤 Mock Interview
          </Button>
        </div>
      </div>

      {/* Interview Type Modal */}
      {showInterviewModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={(e) => {
            e.stopPropagation();
            setShowInterviewModal(false);
          }}
        >
          <div 
            className="bg-white rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button
              onClick={() => setShowInterviewModal(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X size={24} />
            </button>

            <h2 className="text-2xl font-bold text-gray-900 mb-2 text-center">
              Choose Interview Mode
            </h2>
            <p className="text-gray-600 text-center mb-6">
              How would you like to practice for <span className="font-medium">{jobTitle}</span>?
            </p>

            <div className="flex flex-col gap-4">
              {/* Voice Option */}
              <button
                onClick={() => handleInterviewChoice('voice')}
                className="flex items-center gap-4 p-5 rounded-xl border-2 border-gray-200 hover:border-[#D95D39] hover:bg-[#D95D39]/5 transition-all group"
              >
                <div className="w-14 h-14 rounded-full bg-[#D95D39]/10 flex items-center justify-center group-hover:bg-[#D95D39]/20 transition-colors">
                  <Mic size={28} className="text-[#D95D39]" />
                </div>
                <div className="text-left">
                  <h3 className="font-semibold text-lg text-gray-900">Voice Interview</h3>
                  <p className="text-sm text-gray-500">Practice with speech-to-text AI interviewer</p>
                </div>
              </button>

              {/* Chat Option */}
              <button
                onClick={() => handleInterviewChoice('text')}
                className="flex items-center gap-4 p-5 rounded-xl border-2 border-gray-200 hover:border-[#D95D39] hover:bg-[#D95D39]/5 transition-all group"
              >
                <div className="w-14 h-14 rounded-full bg-[#D95D39]/10 flex items-center justify-center group-hover:bg-[#D95D39]/20 transition-colors">
                  <MessageSquare size={28} className="text-[#D95D39]" />
                </div>
                <div className="text-left">
                  <h3 className="font-semibold text-lg text-gray-900">Chat Interview</h3>
                  <p className="text-sm text-gray-500">Text-based interview with AI</p>
                </div>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
