'use client';

import { motion } from 'framer-motion';
import { BookOpen, Circle, ArrowRight, AlertCircle } from 'lucide-react';
import { RoadmapDetails } from '@/lib/api';
import { useEffect, useRef } from 'react';

interface RoadmapProps {
  data: RoadmapDetails | null;
}

export default function Roadmap({ data }: RoadmapProps) {
  const svgRef = useRef<SVGSVGElement>(null);

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
    <div className="mt-6 border-t border-gray-700 pt-6">
      <h3 className="font-serif-bold text-white mb-6 text-lg flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
        Neuro-Adaptive Learning Path
      </h3>

      <div className="relative w-full overflow-hidden bg-black/20 rounded-xl border border-white/5 p-6">
        {/* SVG Layer for edges */}
        <svg
          ref={svgRef}
          className="absolute top-0 left-0 w-full h-full pointer-events-none"
          style={{ zIndex: 1 }}
        >
          <defs>
            <linearGradient id="edgeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#ea580c" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#ea580c" stopOpacity="0.8" />
            </linearGradient>
          </defs>
        </svg>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative z-10">
          {days.map((day, i) => (
            <div key={day} className="flex flex-col gap-6 relative">
              <div className="flex items-center gap-3 text-xs font-mono text-gray-500 uppercase tracking-widest mb-2">
                <span className="w-6 h-6 rounded-full border border-gray-700 flex items-center justify-center bg-gray-900 text-orange-500 font-bold">
                  {day}
                </span>
                Phase 0{day}
              </div>
              {nodesByDay[i].map((node) => (
                <motion.div
                  key={node.id}
                  id={`node-${node.id}`}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: day * 0.2 }}
                  className="group relative bg-gray-900/80 border border-gray-700 rounded-lg p-4 hover:border-orange-500/50 transition-colors shadow-lg"
                >
                  <div className="absolute top-0 bottom-0 left-1/2 w-px bg-gradient-to-b from-transparent via-gray-800 to-transparent -z-10" />
                  <div className="flex items-start justify-between mb-2">
                    <span className={`text-[10px] px-2 py-0.5 rounded border font-mono ${
                      node.type === 'concept' ? 'border-blue-900 text-blue-400 bg-blue-900/20' : 
                      node.type === 'practice' ? 'border-green-900 text-green-400 bg-green-900/20' :
                      'border-purple-900 text-purple-400 bg-purple-900/20'
                    }`}>
                      {node.type?.toUpperCase() || 'TOPIC'}
                    </span>
                    <Circle className="w-2 h-2 text-gray-600" />
                  </div>
                  <h4 className="text-white font-medium text-sm mb-1">{node.label}</h4>
                  <p className="text-xs text-gray-400 mb-3 leading-relaxed line-clamp-2">{node.description}</p>
                  {resources[node.id] && resources[node.id].length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2 pt-2 border-t border-gray-800">
                      {resources[node.id].map((res, idx) => (
                        <a key={idx} href={res.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-orange-400 transition-colors bg-black/40 px-2 py-1 rounded">
                          {res.name.toLowerCase().includes("video") ? <ArrowRight size={10} /> : <BookOpen size={10} />}
                          {res.name}
                        </a>
                      ))}
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}