'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, Circle, ArrowRight, AlertCircle, Download, CheckCircle, Trophy, Sparkles, Target } from 'lucide-react';
import { RoadmapDetails, getProgress, updateProgress, completeRoadmap } from '@/lib/api';
import { useEffect, useRef, useState, useCallback } from 'react';

interface RoadmapProps {
  data: RoadmapDetails | null;
  savedJobId?: string; // Optional: If provided, progress will be persisted to backend
  userId?: string; // Required for completing roadmap and updating skills
}

interface CompletionState {
  [nodeId: string]: boolean;
}

export default function Roadmap({ data, savedJobId, userId }: RoadmapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const roadmapRef = useRef<HTMLDivElement>(null);
  const [completedNodes, setCompletedNodes] = useState<CompletionState>({});
  const [showCelebration, setShowCelebration] = useState(false);
  const [celebrationMessage, setCelebrationMessage] = useState('');
  const [isLoadingProgress, setIsLoadingProgress] = useState(false);
  const [hasTriggeredCompletion, setHasTriggeredCompletion] = useState(false);
  const [skillAnalysisComplete, setSkillAnalysisComplete] = useState(false);
  const [newSkillsAdded, setNewSkillsAdded] = useState<string[]>([]);
  const [skillUpdateMessage, setSkillUpdateMessage] = useState('');

  // Load progress from backend when component mounts (if savedJobId is provided)
  useEffect(() => {
    if (savedJobId) {
      setIsLoadingProgress(true);
      getProgress(savedJobId)
        .then((response) => {
          // Convert backend format to local format
          const loadedProgress: CompletionState = {};
          if (response.progress) {
            Object.entries(response.progress).forEach(([nodeId, data]) => {
              loadedProgress[nodeId] = data.completed;
            });
          }
          setCompletedNodes(loadedProgress);
          
          // Check if already 100% completed
          const totalNodes = data?.graph?.nodes?.length || 0;
          const completedCount = Object.values(loadedProgress).filter(Boolean).length;
          if (totalNodes > 0 && completedCount === totalNodes) {
            setHasTriggeredCompletion(true); // Already completed before
          }
        })
        .catch((err) => {
          console.error('Failed to load progress:', err);
        })
        .finally(() => {
          setIsLoadingProgress(false);
        });
    }
  }, [savedJobId, data?.graph?.nodes?.length]);

  // Calculate completion percentage
  const totalNodes = data?.graph?.nodes?.length || 0;
  const completedCount = Object.values(completedNodes).filter(Boolean).length;
  const completionPercentage = totalNodes > 0 ? Math.round((completedCount / totalNodes) * 100) : 0;

  // Trigger skill update when 100% is reached
  useEffect(() => {
    console.log('[Roadmap] Completion check:', { 
      completionPercentage, 
      hasTriggeredCompletion, 
      savedJobId, 
      userId, 
      totalNodes 
    });
    
    if (
      completionPercentage === 100 &&
      !hasTriggeredCompletion &&
      savedJobId &&
      userId &&
      totalNodes > 0
    ) {
      console.log('[Roadmap] 🎯 Triggering skill update API call...');
      setHasTriggeredCompletion(true);
      
      // Call the backend to analyze roadmap and update skills
      completeRoadmap(userId, savedJobId)
        .then((response) => {
          console.log('[Roadmap] ✅ Skills updated:', response);
          setSkillAnalysisComplete(true);
          setSkillUpdateMessage(response.message);
          if (response.new_skills_added && response.new_skills_added.length > 0) {
            setNewSkillsAdded(response.new_skills_added);
            setCelebrationMessage(`🎓 ${response.message}`);
            setShowCelebration(true);
            setTimeout(() => setShowCelebration(false), 5000);
          } else {
            console.log('[Roadmap] No new skills to add (already have them all)');
          }
        })
        .catch((err) => {
          console.error('[Roadmap] ❌ Failed to update skills:', err);
          setSkillAnalysisComplete(true);
          setSkillUpdateMessage('Failed to analyze skills. Please try again.');
        });
    }
  }, [completionPercentage, hasTriggeredCompletion, savedJobId, userId, totalNodes]);

  const handleNodeComplete = useCallback(async (nodeId: string, nodeLabel: string) => {
    const wasCompleted = completedNodes[nodeId];
    const newState = { ...completedNodes, [nodeId]: !wasCompleted };
    setCompletedNodes(newState);
    
    // Persist to backend if savedJobId is provided
    if (savedJobId) {
      try {
        await updateProgress(savedJobId, nodeId, !wasCompleted);
      } catch (err) {
        console.error('Failed to save progress:', err);
        // Revert on error
        setCompletedNodes(completedNodes);
        return;
      }
    }
    
    if (!wasCompleted) {
      // Node just completed
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

  const downloadRoadmap = async () => {
    if (!data?.graph?.nodes) return;

    try {
      const printWindow = window.open('', '_blank');
      if (!printWindow) {
        alert('Please allow popups to download the roadmap');
        return;
      }

      const { nodes, edges } = data.graph;
      const nodesByDay = [1, 2, 3].map(day => nodes.filter(n => n.day === day));

      const htmlContent = `
        <!DOCTYPE html>
        <html>
        <head>
          <title>Learning Roadmap</title>
          <meta charset="utf-8">
          <style>
            * {
              margin: 0;
              padding: 0;
              box-sizing: border-box;
            }
            
            body {
              font-family: 'Segoe UI', Arial, sans-serif;
              padding: 30px;
              background: white;
              color: #333;
              line-height: 1.5;
            }
            
            .header {
              text-align: center;
              margin-bottom: 40px;
              padding-bottom: 20px;
              border-bottom: 3px solid #ea580c;
            }
            
            .header h1 {
              color: #1f2937;
              font-size: 32px;
              margin-bottom: 10px;
            }
            
            .progress-info {
              display: inline-block;
              background: #fff7ed;
              padding: 8px 16px;
              border-radius: 20px;
              border: 2px solid #fb923c;
              color: #ea580c;
              font-weight: 600;
              font-size: 14px;
            }
            
            .roadmap-container {
              display: grid;
              grid-template-columns: repeat(3, 1fr);
              gap: 30px;
              margin-top: 30px;
            }
            
            .day-column {
              break-inside: avoid;
            }
            
            .day-header {
              text-align: center;
              margin-bottom: 20px;
              padding-bottom: 10px;
              border-bottom: 2px solid #fed7aa;
            }
            
            .day-number {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              width: 40px;
              height: 40px;
              border-radius: 50%;
              background: #fff7ed;
              border: 2px solid #fb923c;
              color: #ea580c;
              font-weight: bold;
              font-size: 18px;
              margin-bottom: 8px;
            }
            
            .day-label {
              display: block;
              color: #6b7280;
              font-size: 12px;
              text-transform: uppercase;
              letter-spacing: 1px;
              font-weight: 600;
            }
            
            .node-card {
              background: #ffffff;
              border: 2px solid #e5e7eb;
              border-radius: 12px;
              padding: 16px;
              margin-bottom: 20px;
              box-shadow: 0 1px 3px rgba(0,0,0,0.1);
              page-break-inside: avoid;
            }
            
            .node-card.completed {
              background: #f0fdf4;
              border-color: #86efac;
            }
            
            .node-header {
              display: flex;
              justify-content: space-between;
              align-items: center;
              margin-bottom: 12px;
            }
            
            .node-type {
              display: inline-block;
              padding: 4px 10px;
              border-radius: 6px;
              font-size: 10px;
              font-weight: bold;
              text-transform: uppercase;
              letter-spacing: 0.5px;
            }
            
            .type-concept {
              background: #dbeafe;
              color: #1e40af;
              border: 1px solid #60a5fa;
            }
            
            .type-practice {
              background: #d1fae5;
              color: #065f46;
              border: 1px solid #34d399;
            }
            
            .type-project {
              background: #e9d5ff;
              color: #6b21a8;
              border: 1px solid #a855f7;
            }
            
            .completion-badge {
              color: #ea580c;
              font-size: 12px;
              font-weight: 600;
            }
            
            .node-title {
              color: #1f2937;
              font-size: 16px;
              font-weight: bold;
              margin-bottom: 8px;
            }
            
            .node-description {
              color: #4b5563;
              font-size: 13px;
              line-height: 1.6;
              margin-bottom: 12px;
            }
            
            .resources {
              padding-top: 12px;
              border-top: 1px solid #e5e7eb;
            }
            
            .resources-title {
              color: #6b7280;
              font-size: 11px;
              font-weight: 600;
              text-transform: uppercase;
              margin-bottom: 8px;
            }
            
            .resource-item {
              display: block;
              color: #ea580c;
              text-decoration: none;
              font-size: 12px;
              padding: 4px 0;
              font-weight: 500;
            }
            
            .resource-item::before {
              content: "📄 ";
              margin-right: 4px;
            }
            
            .footer {
              margin-top: 40px;
              padding-top: 20px;
              border-top: 2px solid #e5e7eb;
              text-align: center;
              color: #6b7280;
              font-size: 12px;
            }
            
            @media print {
              body {
                padding: 20px;
              }
              
              .roadmap-container {
                gap: 20px;
              }
              
              @page {
                margin: 1cm;
                size: A4 portrait;
              }
            }
          </style>
        </head>
        <body>
          <div class="header">
            <h1>🎯 My Learning Roadmap</h1>
            <div class="progress-info">
              ✨ ${completionPercentage}% Complete | ${completedCount} of ${totalNodes} Tasks Done
            </div>
          </div>
          
          <div class="roadmap-container">
            ${nodesByDay.map((dayNodes, dayIndex) => {
              const day = dayIndex + 1;
              return `
                <div class="day-column">
                  <div class="day-header">
                    <div class="day-number">${day}</div>
                    <span class="day-label">Day ${day}</span>
                  </div>
                  
                  ${dayNodes.map(node => {
                    const isCompleted = completedNodes[node.id];
                    const nodeResources = resources[node.id] || [];
                    
                    return `
                      <div class="node-card ${isCompleted ? 'completed' : ''}">
                        <div class="node-header">
                          <span class="node-type type-${node.type || 'concept'}">
                            ${node.type || 'TOPIC'}
                          </span>
                          ${isCompleted ? '<span class="completion-badge">✓ Done</span>' : ''}
                        </div>
                        
                        <div class="node-title">${node.label}</div>
                        <div class="node-description">${node.description}</div>
                        
                        ${nodeResources.length > 0 ? `
                          <div class="resources">
                            <div class="resources-title">Resources:</div>
                            ${nodeResources.map(res => 
                              `<a href="${res.url}" class="resource-item">${res.name}</a>`
                            ).join('')}
                          </div>
                        ` : ''}
                      </div>
                    `;
                  }).join('')}
                </div>
              `;
            }).join('')}
          </div>
          
          <div class="footer">
            <p>Generated on ${new Date().toLocaleDateString('en-US', { 
              year: 'numeric', 
              month: 'long', 
              day: 'numeric' 
            })}</p>
            <p style="margin-top: 8px;">Keep learning and growing! 🚀</p>
          </div>
          
          <script>
            window.onload = function() {
              setTimeout(function() {
                window.print();
                setTimeout(function() {
                  window.close();
                }, 100);
              }, 500);
            };
          </script>
        </body>
        </html>
      `;

      printWindow.document.write(htmlContent);
      printWindow.document.close();
    } catch (error) {
      console.error('Download failed:', error);
      alert('Unable to generate PDF. Please try again.');
    }
  };

  // Helper function to draw edges between nodes
  const drawGraphEdges = (nodes: any[], edges: any[]) => {
    if (!svgRef.current) return;
    
    // Get node positions from DOM
    const nodePositions: Record<string, { x: number; y: number }> = {};
    
    nodes.forEach(node => {
      const element = document.getElementById(`node-${node.id}`);
      if (element) {
        const rect = element.getBoundingClientRect();
        const svgRect = svgRef.current!.getBoundingClientRect();
        nodePositions[node.id] = {
          x: rect.left - svgRect.left + rect.width / 2,
          y: rect.top - svgRect.top + rect.height / 2
        };
      }
    });

    // Clear previous paths
    const svg = svgRef.current;
    while (svg.firstChild) {
      svg.removeChild(svg.firstChild);
    }

    // Draw edges
    edges.forEach(edge => {
      const startPos = nodePositions[edge.source];
      const endPos = nodePositions[edge.target];

      if (startPos && endPos) {
        // Calculate curved path
        const midX = (startPos.x + endPos.x) / 2;
        const midY = (startPos.y + endPos.y) / 2 + 30; // Control point for curve

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute(
          'd',
          `M ${startPos.x} ${startPos.y} Q ${midX} ${midY} ${endPos.x} ${endPos.y}`
        );
        path.setAttribute('stroke', 'url(#edgeGradient)');
        path.setAttribute('stroke-width', '2');
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke-dasharray', '5,5');

        // Add arrowhead
        const arrowSize = 8;
        const angle = Math.atan2(endPos.y - midY, endPos.x - midX);
        const arrowPoints = [
          [endPos.x, endPos.y],
          [endPos.x - arrowSize * Math.cos(angle - Math.PI / 6), endPos.y - arrowSize * Math.sin(angle - Math.PI / 6)],
          [endPos.x - arrowSize * Math.cos(angle + Math.PI / 6), endPos.y - arrowSize * Math.sin(angle + Math.PI / 6)]
        ];

        const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        arrow.setAttribute('points', arrowPoints.map(p => p.join(',')).join(' '));
        arrow.setAttribute('fill', '#ea580c');
        arrow.setAttribute('opacity', '0.6');

        svg.appendChild(path);
        svg.appendChild(arrow);
      }
    });
  };

  if (!data) return <div className="text-secondary text-sm">No roadmap data available.</div>;

  // Legacy Check
  // @ts-ignore
  if (data.roadmap && Array.isArray(data.roadmap) && !data.graph) {
    return (
      <div className="mt-6 p-4 border border-amber-200 bg-amber-50 rounded-lg text-amber-800 text-sm flex items-center gap-3">
        <AlertCircle className="w-5 h-5" />
        <div>Legacy Roadmap Detected. Please Refresh.</div>
      </div>
    );
  }

  if (!data.graph || !data.graph.nodes) return <div className="text-secondary text-sm">Loading Graph...</div>;

  const { nodes, edges } = data.graph;
  const resources = data.resources || {};
  const days = [1, 2, 3];
  const nodesByDay = days.map(day => nodes.filter(n => n.day === day));

  // Redraw edges when component mounts or updates
  useEffect(() => {
    const handleResize = () => {
      drawGraphEdges(nodes, edges || []);
    };

    const timer = setTimeout(() => {
      drawGraphEdges(nodes, edges || []);
    }, 100);

    window.addEventListener('resize', handleResize);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', handleResize);
    };
  }, [nodes, edges, drawGraphEdges]);

  return (
    <div className="mt-6 border-t border-gray-700 pt-6" ref={roadmapRef}>
      {/* Header with Progress and Download */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h3 className="font-serif-bold text-gray-800 text-lg flex items-center gap-2">
            <Target className="w-5 h-5 text-orange-500" />
            Learning Roadmap
          </h3>
          <div className="flex items-center gap-2 px-3 py-1 bg-orange-50 rounded-full border border-orange-200">
            <Sparkles className="w-4 h-4 text-orange-500" />
            <span className="text-sm text-orange-700 font-medium">{completionPercentage}% Complete</span>
          </div>
        </div>
        <button
          onClick={downloadRoadmap}
          className="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg transition-all shadow-md hover:shadow-lg transform hover:scale-105"
        >
          <Download className="w-4 h-4" />
          <span className="text-sm font-medium">Download PDF</span>
        </button>
      </div>

      {/* Progress Bar */}
      <div className="mb-6 bg-gray-200 rounded-full h-3 overflow-hidden border border-gray-300">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${completionPercentage}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="h-full bg-gradient-to-r from-orange-400 via-orange-500 to-orange-600 relative"
        >
          <div className="absolute inset-0 bg-white/20 animate-pulse" />
        </motion.div>
      </div>

      {/* Celebration Modal */}
      <AnimatePresence>
        {showCelebration && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: -20 }}
            className="fixed top-20 left-1/2 transform -translate-x-1/2 z-50 bg-gradient-to-r from-orange-400 to-orange-500 text-white px-6 py-4 rounded-xl shadow-2xl"
          >
            <div className="flex items-center gap-3">
              <Trophy className="w-6 h-6 animate-bounce" />
              <span className="font-bold text-lg">{celebrationMessage}</span>
              <Sparkles className="w-5 h-5 animate-spin" />
            </div>
            {/* Show new skills added */}
            {newSkillsAdded.length > 0 && (
              <div className="mt-3 pt-3 border-t border-white/30">
                <p className="text-sm text-white/90 mb-2">New skills added to your profile:</p>
                <div className="flex flex-wrap gap-2">
                  {newSkillsAdded.map((skill, idx) => (
                    <span key={idx} className="px-2 py-1 bg-white/20 rounded-full text-xs font-medium">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="relative w-full overflow-visible bg-gradient-to-br from-orange-50 via-white to-orange-50 rounded-2xl border border-orange-200 p-8 shadow-xl">
        {/* SVG Layer for edges */}
        <svg
          ref={svgRef}
          className="absolute top-0 left-0 w-full h-full pointer-events-none"
          style={{ zIndex: 1 }}
        >
          <defs>
            <linearGradient id="edgeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#f97316" stopOpacity="0.5" />
              <stop offset="50%" stopColor="#ea580c" stopOpacity="0.7" />
              <stop offset="100%" stopColor="#f97316" stopOpacity="0.5" />
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
        </svg>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-10 relative z-10">
          {days.map((day, i) => (
            <div key={day} className="flex flex-col gap-6 relative">
              {/* Day Header */}
              <motion.div 
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="flex flex-col items-center gap-2 mb-2"
              >
                <div className="relative">
                  <div className="absolute inset-0 bg-orange-400 blur-xl opacity-20 animate-pulse" />
                  <div className="relative w-12 h-12 rounded-full border-2 border-orange-500 flex items-center justify-center bg-white shadow-lg">
                    <span className="text-orange-600 font-bold text-lg">{day}</span>
                  </div>
                </div>
                <span className="text-xs font-mono text-gray-600 uppercase tracking-widest font-semibold">Day {day}</span>
                <div className="h-px w-16 bg-gradient-to-r from-transparent via-orange-400 to-transparent" />
              </motion.div>

              {/* Nodes */}
              {nodesByDay[i].map((node, idx) => {
                const isCompleted = completedNodes[node.id];
                return (
                  <motion.div
                    key={node.id}
                    id={`node-${node.id}`}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: (i * 0.1) + (idx * 0.1) }}
                    className="group relative"
                  >
                    {/* Completion Checkbox */}
                    <button
                      onClick={() => handleNodeComplete(node.id, node.label)}
                      className="absolute -left-4 top-4 z-20 transform hover:scale-110 transition-transform"
                    >
                      {isCompleted ? (
                        <Trophy className="w-6 h-6 text-orange-500 fill-orange-500 animate-bounce" />
                      ) : (
                        <Circle className="w-6 h-6 text-gray-400 hover:text-orange-500 transition-colors" />
                      )}
                    </button>

                    {/* Node Card */}
                    <div className="relative bg-white border-2 border-gray-300 rounded-xl p-5 transition-all duration-300 hover:border-orange-400 hover:shadow-lg backdrop-blur-sm transform hover:-translate-y-1">
                      
                      {/* Glow effect */}
                      <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity bg-orange-50 blur-xl" />
                      
                      {/* Content */}
                      <div className="relative z-10">
                        <div className="flex items-start justify-between mb-3">
                          <span className={`text-[10px] px-2 py-1 rounded-md border font-mono font-bold uppercase tracking-wider ${
                            node.type === 'concept' ? 'border-blue-400 text-blue-600 bg-blue-50' : 
                            node.type === 'practice' ? 'border-green-400 text-green-600 bg-green-50' :
                            'border-purple-400 text-purple-600 bg-purple-50'
                          }`}>
                            {node.type || 'TOPIC'}
                          </span>
                          {isCompleted && (
                            <motion.div
                              initial={{ scale: 0, rotate: -180 }}
                              animate={{ scale: 1, rotate: 0 }}
                              className="flex items-center gap-1 text-orange-600 text-xs font-medium"
                            >
                              <CheckCircle className="w-3 h-3" />
                              Done
                            </motion.div>
                          )}
                        </div>
                        
                        <h4 className="text-gray-800 font-bold text-base mb-2">
                          {node.label}
                        </h4>
                        
                        <p className="text-xs text-gray-600 leading-relaxed mb-4">
                          {node.description}
                        </p>
                        
                        {/* Resources */}
                        {resources[node.id] && resources[node.id].length > 0 && (
                          <div className="flex flex-wrap gap-2 pt-3 border-t border-gray-200">
                            {resources[node.id].map((res, idx) => (
                              <a 
                                key={idx} 
                                href={res.url} 
                                target="_blank" 
                                rel="noreferrer" 
                                className="flex items-center gap-1.5 text-[10px] px-3 py-1.5 rounded-md transition-all transform hover:scale-105 bg-gray-50 text-gray-700 hover:text-orange-600 hover:bg-orange-50 border border-gray-300 hover:border-orange-400 shadow-sm"
                              >
                                {res.name.toLowerCase().includes("video") ? 
                                  <ArrowRight className="w-3 h-3" /> : 
                                  <BookOpen className="w-3 h-3" />
                                }
                                <span className="font-medium">{res.name}</span>
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          ))}
        </div>

        {/* Completion Badge */}
        {completionPercentage === 100 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mt-8 p-6 bg-gradient-to-r from-orange-100 via-orange-50 to-orange-100 border-2 border-orange-400 rounded-xl text-center"
          >
            <Trophy className="w-12 h-12 text-orange-500 mx-auto mb-3 animate-bounce" />
            <h3 className="text-2xl font-bold text-gray-800 mb-2">🎉 Roadmap Completed! 🎉</h3>
            <p className="text-orange-700">Amazing work! You've completed all the learning objectives. Ready to apply?</p>
            
            {/* Show new skills added to profile */}
            {newSkillsAdded.length > 0 && (
              <div className="mt-4 pt-4 border-t border-orange-300">
                <p className="text-green-700 font-semibold mb-2">
                  🎓 {newSkillsAdded.length} new skill{newSkillsAdded.length > 1 ? 's' : ''} added to your profile!
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  {newSkillsAdded.map((skill, idx) => (
                    <span key={idx} className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium border border-green-300">
                      ✓ {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            {/* Show loading state while updating skills */}
            {hasTriggeredCompletion && !skillAnalysisComplete && savedJobId && userId && (
              <div className="mt-4 pt-4 border-t border-orange-300">
                <p className="text-orange-600 text-sm">
                  ⏳ Analyzing your learned skills...
                </p>
              </div>
            )}
            
            {/* Show message when analysis complete but no new skills */}
            {skillAnalysisComplete && newSkillsAdded.length === 0 && skillUpdateMessage && (
              <div className="mt-4 pt-4 border-t border-orange-300">
                <p className="text-green-600 text-sm">
                  ✅ {skillUpdateMessage}
                </p>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}