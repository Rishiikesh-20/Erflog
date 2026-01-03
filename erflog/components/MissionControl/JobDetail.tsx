import { motion } from 'framer-motion';
import { Briefcase, MapPin, DollarSign, Clock, ExternalLink, Globe } from 'lucide-react';
import Roadmap from './Roadmap'; 
import { StrategyJobMatch, RoadmapDetails } from '@/lib/api';

interface JobDetailProps {
  job: StrategyJobMatch;
  onApply: () => void;
}

export default function JobDetail({ job, onApply }: JobDetailProps) {
  // Safe check: Ensure roadmap_details exists
  const hasRoadmap = job.roadmap_details;

  return (
    <div className="bg-surface rounded-xl border border-[#E5E0D8] overflow-hidden shadow-sm">
      <div className="p-8">
        {/* Header Section */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="font-serif-bold text-3xl text-ink mb-2">{job.title}</h2>
            <div className="flex items-center gap-2 text-lg text-secondary">
              <Briefcase className="w-5 h-5" />
              {job.company}
            </div>
          </div>
          {job.score >= 80 && (
            <div className="px-4 py-2 bg-green-100 text-green-700 rounded-lg font-medium text-sm flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-600 animate-pulse" />
              High Match
            </div>
          )}
        </div>

        {/* Job Metadata Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
            <div className="text-xs text-gray-500 mb-1 flex items-center gap-1"><MapPin size={12}/> Location</div>
            <div className="font-medium text-ink">Remote / Hybrid</div>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
             <div className="text-xs text-gray-500 mb-1 flex items-center gap-1"><DollarSign size={12}/> Salary</div>
             <div className="font-medium text-ink">Competitive</div>
          </div>
           <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
             <div className="text-xs text-gray-500 mb-1 flex items-center gap-1"><Clock size={12}/> Posted</div>
             <div className="font-medium text-ink">Recently</div>
          </div>
           <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
             <div className="text-xs text-gray-500 mb-1 flex items-center gap-1"><Globe size={12}/> Source</div>
             <div className="font-medium text-ink">LinkedIn</div>
          </div>
        </div>

        {/* Description */}
        <div className="prose prose-sm max-w-none text-secondary mb-8">
          <h3 className="text-ink font-bold text-lg mb-2">About the Role</h3>
          <p className="leading-relaxed whitespace-pre-line">{job.description}</p>
        </div>

        {/* --- ROADMAP SECTION --- */}
        {hasRoadmap ? (
           // FIX: Explicitly cast type to satisfy TypeScript
           <Roadmap data={job.roadmap_details as RoadmapDetails} />
        ) : (
          <div className="mt-8 p-6 bg-gray-50 rounded-xl border border-dashed border-gray-300 text-center">
            <p className="text-gray-500 italic">
              AI Analysis in progress... Roadmap will appear here shortly.
            </p>
          </div>
        )}
      </div>

      {/* Footer Action */}
      <div className="p-6 bg-gray-50 border-t border-gray-200 flex justify-end">
        <button 
          onClick={onApply}
          className="px-8 py-3 bg-[#D95D39] text-white font-medium rounded-lg hover:opacity-90 transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
        >
          Apply Now
        </button>
      </div>
    </div>
  );
}