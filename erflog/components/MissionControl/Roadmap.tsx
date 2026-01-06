'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, Circle, ArrowRight, AlertCircle, CheckCircle, Trophy, Sparkles, Target, ChevronDown, ChevronUp } from 'lucide-react';
import { RoadmapDetails, getProgress, updateProgress, completeRoadmap } from '@/lib/api';
import { useEffect, useRef, useState, useCallback } from 'react';

interface RoadmapProps {
  data: RoadmapDetails | null;
  savedJobId?: string;
  userId?: string;
}

interface CompletionState {
  [nodeId: string]: boolean;
}

export default function Roadmap({ data, savedJobId, userId }: RoadmapProps) {
  const roadmapRef = useRef<HTMLDivElement>(null);
  const [completedNodes, setCompletedNodes] = useState<CompletionState>({});
  const [showCelebration, setShowCelebration] = useState(false);
  const [celebrationMessage, setCelebrationMessage] = useState('');
  const [isLoadingProgress, setIsLoadingProgress] = useState(false);
  const [hasTriggeredCompletion, setHasTriggeredCompletion] = useState(false);
  const [skillAnalysisComplete, setSkillAnalysisComplete] = useState(false);
  const [newSkillsAdded, setNewSkillsAdded] = useState<string[]>([]);
  const [skillUpdateMessage, setSkillUpdateMessage] = useState('');
  const [expandedResources, setExpandedResources] = useState<Set<string>>(new Set());

  // Load progress from backend
  useEffect(() => {
    if (savedJobId) {
      setIsLoadingProgress(true);
      getProgress(savedJobId)
        .then((response) => {
          const loadedProgress: CompletionState = {};
          if (response.progress) {
            Object.entries(response.progress).forEach(([nodeId, data]) => {
              loadedProgress[nodeId] = data.completed;
            });
          }
          setCompletedNodes(loadedProgress);
          
          const totalNodes = data?.graph?.nodes?.length || 0;
          const completedCount = Object.values(loadedProgress).filter(Boolean).length;
          if (totalNodes > 0 && completedCount === totalNodes) {
            setHasTriggeredCompletion(true);
          }
        })
        .catch((err) => console.error('Failed to load progress:', err))
        .finally(() => setIsLoadingProgress(false));
    }
  }, [savedJobId, data?.graph?.nodes?.length]);

  const totalNodes = data?.graph?.nodes?.length || 0;
  const completedCount = Object.values(completedNodes).filter(Boolean).length;
  const completionPercentage = totalNodes > 0 ? Math.round((completedCount / totalNodes) * 100) : 0;

  // Trigger skill update at 100%
  useEffect(() => {
    if (
      completionPercentage === 100 &&
      !hasTriggeredCompletion &&
      savedJobId &&
      userId &&
      totalNodes > 0
    ) {
      setHasTriggeredCompletion(true);
      
      completeRoadmap(userId, savedJobId)
        .then((response) => {
          setSkillAnalysisComplete(true);
          setSkillUpdateMessage(response.message);
          if (response.new_skills_added && response.new_skills_added.length > 0) {
            setNewSkillsAdded(response.new_skills_added);
            setCelebrationMessage(`🎓 ${response.message}`);
            setShowCelebration(true);
            setTimeout(() => setShowCelebration(false), 5000);
          }
        })
        .catch((err) => {
          console.error('Failed to update skills:', err);
          setSkillAnalysisComplete(true);
          setSkillUpdateMessage('Failed to analyze skills. Please try again.');
        });
    }
  }, [completionPercentage, hasTriggeredCompletion, savedJobId, userId, totalNodes]);

  const handleNodeComplete = useCallback(async (nodeId: string, nodeLabel: string) => {
    const wasCompleted = completedNodes[nodeId];
    const newState = { ...completedNodes, [nodeId]: !wasCompleted };
    setCompletedNodes(newState);
    
    if (savedJobId) {
      try {
        await updateProgress(savedJobId, nodeId, !wasCompleted);
      } catch (err) {
        console.error('Failed to save progress:', err);
        setCompletedNodes(completedNodes);
        return;
      }
    }
    
    if (!wasCompleted) {
      const messages = [
        `🎉 Awesome! "${nodeLabel}" completed!`,
        `⭐ Great job on "${nodeLabel}"!`,
        `🚀 You're crushing it! "${nodeLabel}" done!`,
        `💪 Excellent work on "${nodeLabel}"!`,
        `🎯 Perfect! "${nodeLabel}" mastered!`
      ];
      setCelebrationMessage(messages[Math.floor(Math.random() * messages.length)]);
      setShowCelebration(true);
      setTimeout(() => setShowCelebration(false), 3000);
    }
  }, [completedNodes, savedJobId]);

  const toggleResources = (nodeId: string) => {
    setExpandedResources(prev => {
      const newSet = new Set(prev);
      if (newSet.has(nodeId)) {
        newSet.delete(nodeId);
      } else {
        newSet.add(nodeId);
      }
      return newSet;
    });
  };

  if (!data) return <div className="text-gray-500 text-sm">No roadmap data available.</div>;

  // @ts-ignore
  if (data.roadmap && Array.isArray(data.roadmap) && !data.graph) {
    return (
      <div className="mt-6 p-4 border border-amber-200 bg-amber-50 rounded-lg text-amber-800 text-sm flex items-center gap-3">
        <AlertCircle className="w-5 h-5" />
        <div>Legacy Roadmap Detected. Please Refresh.</div>
      </div>
    );
  }

  if (!data.graph || !data.graph.nodes) return <div className="text-gray-500 text-sm">Loading Graph...</div>;

  const { nodes } = data.graph;
  const resources = data.resources || {};
  
  // Group nodes by day
  const nodesByDay: { [key: number]: typeof nodes } = {};
  nodes.forEach(node => {
    if (!nodesByDay[node.day]) {
      nodesByDay[node.day] = [];
    }
    nodesByDay[node.day].push(node);
  });
  
  const days = Object.keys(nodesByDay).map(Number).sort();

  return (
    <div className="mt-6" ref={roadmapRef}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-[#D95D39] flex items-center justify-center shadow-lg">
            <Target className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-gray-900">Learning Roadmap</h3>
            <p className="text-gray-600 text-sm">Your path to success</p>
          </div>
        </div>
        
        {/* Progress */}
        <div className="flex items-center gap-3">
          <div className="px-4 py-2 bg-orange-50 rounded-lg border-2 border-[#D95D39]">
            <div className="text-2xl font-bold text-[#D95D39]">{completionPercentage}%</div>
            <div className="text-xs text-gray-600">Complete</div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-8 bg-gray-200 rounded-full h-2 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${completionPercentage}%` }}
          transition={{ duration: 0.5 }}
          className="h-full bg-[#D95D39]"
        />
      </div>

      {/* Celebration Toast */}
      <AnimatePresence>
        {showCelebration && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-20 left-1/2 transform -translate-x-1/2 z-50 bg-[#D95D39] text-white px-6 py-4 rounded-xl shadow-2xl"
          >
            <div className="flex items-center gap-3">
              <Trophy className="w-6 h-6" />
              <span className="font-bold">{celebrationMessage}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Simple List Layout */}
      <div className="space-y-6">
        {days.map((day, dayIndex) => (
          <div key={day}>
            {/* Day Header */}
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-[#D95D39] flex items-center justify-center text-white font-bold shadow-lg">
                {day}
              </div>
              <h4 className="text-lg font-bold text-gray-900">Day {day}</h4>
            </div>

            {/* Nodes for this day */}
            <div className="space-y-3 ml-5 pl-5 border-l-2 border-gray-200">
              {nodesByDay[day].map((node, nodeIndex) => {
                const isCompleted = completedNodes[node.id];
                const nodeResources = resources[node.id] || [];
                const isExpanded = expandedResources.has(node.id);
                
                return (
                  <motion.div
                    key={node.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: (dayIndex * 0.1) + (nodeIndex * 0.05) }}
                    className="relative"
                  >
                    {/* Connector Dot */}
                    <div className={`absolute -left-[27px] top-4 w-3 h-3 rounded-full ${isCompleted ? 'bg-green-500' : 'bg-gray-300'} border-2 border-white`} />

                    {/* Node Card */}
                    <div className={`bg-white rounded-lg border-2 ${isCompleted ? 'border-green-400 bg-green-50' : 'border-gray-200'} p-4 hover:shadow-md transition-shadow`}>
                      <div className="flex items-start gap-3">
                        {/* Completion Checkbox */}
                        <button
                          onClick={() => handleNodeComplete(node.id, node.label)}
                          className="flex-shrink-0 mt-1"
                        >
                          {isCompleted ? (
                            <div className="w-6 h-6 rounded-full bg-green-500 flex items-center justify-center">
                              <CheckCircle className="w-5 h-5 text-white" />
                            </div>
                          ) : (
                            <Circle className="w-6 h-6 text-gray-400 hover:text-[#D95D39] transition-colors" />
                          )}
                        </button>

                        <div className="flex-1 min-w-0">
                          {/* Type Badge */}
                          <div className="flex items-center justify-between mb-2">
                            <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
                              node.type === 'concept' ? 'bg-blue-100 text-blue-700' :
                              node.type === 'practice' ? 'bg-green-100 text-green-700' :
                              'bg-purple-100 text-purple-700'
                            }`}>
                              {node.type || 'TOPIC'}
                            </span>
                            {isCompleted && (
                              <span className="text-xs text-green-600 font-semibold">✓ Done</span>
                            )}
                          </div>

                          {/* Title */}
                          <h5 className="font-bold text-gray-900 mb-1 break-words">
                            {node.label}
                          </h5>

                          {/* Description */}
                          <p className="text-sm text-gray-600 mb-3 break-words">
                            {node.description}
                          </p>

                          {/* Resources */}
                          {nodeResources.length > 0 && (
                            <div>
                              <button
                                onClick={() => toggleResources(node.id)}
                                className="flex items-center gap-2 text-sm font-semibold text-[#D95D39] hover:text-orange-700 transition-colors"
                              >
                                <BookOpen className="w-4 h-4" />
                                Resources ({nodeResources.length})
                                {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                              </button>
                              
                              <AnimatePresence>
                                {isExpanded && (
                                  <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="mt-2 space-y-1 overflow-hidden"
                                  >
                                    {nodeResources.map((res, idx) => (
                                      <a
                                        key={idx}
                                        href={res.url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center gap-2 px-3 py-2 rounded bg-orange-50 hover:bg-orange-100 border border-orange-200 transition-colors text-sm group"
                                      >
                                        <ArrowRight className="w-4 h-4 text-[#D95D39] group-hover:translate-x-1 transition-transform" />
                                        <span className="text-gray-700 break-words">{res.name}</span>
                                      </a>
                                    ))}
                                  </motion.div>
                                )}
                              </AnimatePresence>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Completion Badge */}
      {completionPercentage === 100 && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mt-8 p-6 bg-green-50 border-2 border-green-400 rounded-xl text-center"
        >
          <Trophy className="w-12 h-12 text-green-500 mx-auto mb-3" />
          <h3 className="text-2xl font-bold text-gray-900 mb-2">🎉 Roadmap Completed!</h3>
          <p className="text-green-700">Amazing work! You've mastered all the learning objectives.</p>
          
          {newSkillsAdded.length > 0 && (
            <div className="mt-4 pt-4 border-t border-green-300">
              <p className="text-green-800 font-semibold mb-2">
                🎓 {newSkillsAdded.length} new skill{newSkillsAdded.length > 1 ? 's' : ''} added!
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {newSkillsAdded.map((skill, idx) => (
                  <span key={idx} className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                    ✓ {skill}
                  </span>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}