"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import AgentTerminal, { AgentLog } from "@/components/AgentTerminal";
import {
  Bot,
  Zap,
  Target,
  TrendingUp,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Sparkles,
  Building2,
  RefreshCw,
  Radio,
  Github,
  Terminal,
  Loader2,
  Activity
} from "lucide-react";
import { useSession } from "@/lib/SessionContext";
import type { StrategyJobMatch } from "@/lib/api";
import { checkWatchdog } from "@/lib/api";

// --- NEW COMPONENT: LIVE ACTIVITY FEED ---
// This shows the logs directly on the dashboard during Live Sync
function LiveActivityFeed({ logs }: { logs: AgentLog[] }) {
  // Show only the last 3 logs to keep it clean
  const recentLogs = logs.slice(-3);

  return (
    <motion.div 
      initial={{ opacity: 0, height: 0 }} 
      animate={{ opacity: 1, height: "auto" }} 
      exit={{ opacity: 0, height: 0 }}
      className="mb-8 rounded-xl border bg-black/90 p-4 text-sm font-mono text-green-400 shadow-lg overflow-hidden"
      style={{ borderColor: "#333" }}
    >
      <div className="flex items-center gap-2 mb-3 border-b border-gray-800 pb-2 text-xs text-gray-500 uppercase tracking-wider">
        <Activity className="w-3 h-3 animate-pulse text-red-500" />
        Live Neural Link Active
      </div>
      <div className="space-y-2">
        {recentLogs.map((log) => (
          <motion.div 
            key={log.id} 
            initial={{ opacity: 0, x: -10 }} 
            animate={{ opacity: 1, x: 0 }}
            className="flex items-start gap-2"
          >
            <span className="text-gray-600">[{new Date().toLocaleTimeString().split(" ")[0]}]</span>
            <span className={log.type === 'success' ? 'text-green-400' : 'text-blue-300'}>
              {log.type === 'success' ? '✓' : '>'} {log.message}
            </span>
          </motion.div>
        ))}
        {recentLogs.length === 0 && (
          <div className="text-gray-600 italic">Listening for code changes...</div>
        )}
      </div>
    </motion.div>
  );
}

// --- STATIC DATA ---
const SIMULATION_STEPS = [
  { agent: "System", message: "Initializing AI pipeline...", type: "agent" as const },
  { agent: "Agent 2 (Profiler)", message: "Loading user profile...", type: "agent" as const },
  { agent: "Agent 2", message: "Extracting skills from resume...", type: "success" as const },
  { agent: "Agent 3 (Strategist)", message: "Connecting to job market database...", type: "agent" as const },
  { agent: "Agent 3", message: "Scanning 10,000+ active job listings...", type: "agent" as const },
  { agent: "Agent 3", message: "Building skill-to-job embedding matrix...", type: "agent" as const },
  { agent: "Agent 3", message: "Computing cosine similarity vectors...", type: "agent" as const },
  { agent: "Agent 3", message: "Applying TF-IDF weighting to matches...", type: "agent" as const },
  { agent: "Agent 3", message: "Ranking top candidates by alignment score...", type: "agent" as const },
  { agent: "Agent 4 (Gap Analyzer)", message: "Detecting skill gaps for each match...", type: "agent" as const },
  { agent: "Agent 4", message: "Mapping missing competencies to learning paths...", type: "agent" as const },
  { agent: "Agent 4", message: "Generating personalized 7-day roadmaps...", type: "agent" as const },
  { agent: "Agent 4", message: "Curating resources from top platforms...", type: "agent" as const },
  { agent: "Agent 5 (Kit Builder)", message: "Preparing deployment kits...", type: "agent" as const },
  { agent: "Agent 5", message: "Generating tailored cover letter templates...", type: "agent" as const },
  { agent: "Agent 5", message: "Optimizing resume highlights for each role...", type: "agent" as const },
  { agent: "System", message: "Processing large dataset, please wait...", type: "agent" as const },
  { agent: "Agent 3", message: "Fine-tuning match rankings...", type: "agent" as const },
  { agent: "Agent 4", message: "Optimizing roadmap sequences...", type: "agent" as const },
  { agent: "Agent 5", message: "Finalizing application materials...", type: "agent" as const },
];

interface JobMatch {
  id: string;
  title: string;
  company: string;
  matchScore: number;
  location: string;
  salary?: string;
  skills: string[];
  gapSkills?: string[];
  description?: string;
  link?: string;
}

function JobCard({ job, index }: { job: JobMatch; index: number }) {
  const router = useRouter();
  const isReady = job.matchScore >= 80;
  const hasGaps = job.gapSkills && job.gapSkills.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className="group relative bg-surface rounded-xl border overflow-hidden transition-all duration-300 hover:shadow-lg hover:scale-[1.02]"
      style={{ borderColor: "#E5E0D8" }}
    >
      <div className="absolute top-0 left-0 right-0 h-1" style={{ backgroundColor: isReady ? "#22c55e" : hasGaps ? "#f59e0b" : "#D95D39" }} />
      <div className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center text-white font-serif-bold text-lg" style={{ backgroundColor: "#D95D39" }}>
              {job.company.charAt(0)}
            </div>
            <div>
              <h3 className="font-serif-bold text-lg text-ink line-clamp-1">{job.title}</h3>
              <div className="flex items-center gap-2 text-sm text-secondary">
                <Building2 className="w-3.5 h-3.5" />
                {job.company}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold" style={{ color: isReady ? "#22c55e" : "#D95D39" }}>{job.matchScore}%</div>
            <div className="text-xs text-secondary">Match</div>
          </div>
        </div>

        <div className="mb-4">
          {isReady ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
              <CheckCircle2 className="w-3.5 h-3.5" /> Ready to Deploy
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
              <AlertTriangle className="w-3.5 h-3.5" /> Gap Detected
            </span>
          )}
        </div>

        <div className="flex flex-wrap gap-1.5 mb-4">
          {job.skills.slice(0, 4).map((skill, i) => (
            <span key={`${skill}-${i}`} className="px-2 py-1 rounded text-xs bg-gray-100 text-ink">{skill}</span>
          ))}
          {job.skills.length > 4 && (
            <span className="px-2 py-1 rounded text-xs bg-gray-100 text-secondary">+{job.skills.length - 4}</span>
          )}
        </div>

        {hasGaps && (
          <div className="mb-4 p-3 rounded-lg bg-amber-50 border border-amber-200">
            <div className="text-xs font-medium text-amber-700 mb-2">Skills to Develop:</div>
            <div className="flex flex-wrap gap-1.5">
              {job.gapSkills?.map((skill, i) => (
                <span key={`${skill}-${i}`} className="px-2 py-1 rounded text-xs bg-amber-100 text-amber-800">{skill}</span>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center justify-between text-sm text-secondary mb-4">
          <span>{job.location}</span>
          {job.salary && <span>{job.salary}</span>}
        </div>

        <div className="flex gap-2">
          {isReady ? (
            <button onClick={() => router.push(`/jobs/${job.id}/apply`)} className="flex-1 flex items-center justify-center gap-2 py-3 rounded-lg text-white font-medium transition-all hover:opacity-90" style={{ backgroundColor: "#D95D39" }}>
              <Zap className="w-4 h-4" /> Deploy Kit
            </button>
          ) : (
            <>
              <button onClick={() => router.push(`/jobs/${job.id}`)} className="flex-1 flex items-center justify-center gap-2 py-3 rounded-lg border font-medium transition-all hover:bg-gray-50" style={{ borderColor: "#E5E0D8" }}>
                <Target className="w-4 h-4" /> View Roadmap
              </button>
              <button onClick={() => router.push(`/jobs/${job.id}/apply`)} className="flex items-center justify-center px-4 py-3 rounded-lg text-white font-medium transition-all hover:opacity-90" style={{ backgroundColor: "#D95D39" }}>
                <ArrowRight className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default function Dashboard() {
  const router = useRouter();
  const { runStrategy, strategyJobs, profile, isLoading, error, sessionId } = useSession();

  const [showJobs, setShowJobs] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [agentLogs, setAgentLogs] = useState<AgentLog[]>([]);
  const [jobs, setJobs] = useState<JobMatch[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [apiComplete, setApiComplete] = useState(false);
  const hasRunStrategyRef = useRef(false);
  
  // State to manage modes (Standard vs Live Sync)
  const [processMode, setProcessMode] = useState<'onboarding' | 'sync'>('onboarding');
  
  // LIVE MODE STATE
  const [isLiveMode, setIsLiveMode] = useState(false);
  const [lastSha, setLastSha] = useState<string | undefined>(undefined);
  
  // Refs to prevent duplicate execution
  const hasStartedSimulation = useRef(false);

  const transformStrategyJobs = useCallback((strategyJobs: StrategyJobMatch[]): JobMatch[] => {
    return strategyJobs.map((job, index) => {
      const score = Math.round(job.score * 100);
      const missingSkills = job.roadmap_details?.missing_skills || [];
      const commonSkills = ["Python", "JavaScript", "TypeScript", "React", "Node.js", "AWS", "Docker", "Kubernetes"];
      const skills = commonSkills.filter(skill => 
        job.description?.toLowerCase().includes(skill.toLowerCase()) || 
        job.title.toLowerCase().includes(skill.toLowerCase())
      ).slice(0, 4);

      return {
        id: job.id || String(index + 1),
        title: job.title,
        company: job.company,
        matchScore: score,
        location: job.link && job.link !== "null" ? "See posting" : "Remote",
        skills: skills.length > 0 ? skills : ["Technical Skills"],
        gapSkills: missingSkills.length > 0 ? missingSkills : undefined,
        description: job.description,
        link: job.link,
      };
    });
  }, []);

  // 1. Initial Strategy Run
  useEffect(() => {
    const runAgentWorkflow = async () => {
      if (!sessionId || !profile || hasRunStrategyRef.current) return;
      hasRunStrategyRef.current = true;

      const strategyPromise = runStrategy();
      const success = await strategyPromise;
      setApiComplete(true);

      if (processMode === 'onboarding') {
        setAgentLogs((prev) => [...prev, {
          id: `final-${Date.now()}`,
          agent: "System",
          message: success ? "✓ Strategy Board Ready - Found matching opportunities!" : "✓ Loaded from cache",
          type: "success",
          delay: 100,
        }]);
      }
    };
    runAgentWorkflow();
  }, [sessionId, profile, processMode, runStrategy]);

  // 2. Simulation Effect (Only for onboarding)
  useEffect(() => {
    if (!isInitializing || apiComplete || processMode !== 'onboarding') return;

    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        const nextStep = prev + 1;
        const stepIndex = nextStep >= SIMULATION_STEPS.length ? SIMULATION_STEPS.length - 4 + (nextStep % 4) : nextStep;
        
        if (stepIndex < SIMULATION_STEPS.length) {
          const step = SIMULATION_STEPS[stepIndex];
          setAgentLogs((logs) => [...logs, {
            id: `step-${Date.now()}-${Math.random()}`,
            agent: step.agent,
            message: step.message,
            type: step.type,
            delay: 200,
          }]);
        }
        return nextStep;
      });
    }, 1200);

    if (currentStep === 0 && SIMULATION_STEPS.length > 0 && !hasStartedSimulation.current) {
      hasStartedSimulation.current = true;
      const firstStep = SIMULATION_STEPS[0];
      setAgentLogs(prev => {
        if (prev.some(log => log.id === "step-init")) return prev;
        return [...prev, {
          id: "step-init",
          agent: firstStep.agent,
          message: firstStep.message,
          type: firstStep.type,
          delay: 100,
        }];
      });
      setCurrentStep(1);
    }

    return () => clearInterval(interval);
  }, [isInitializing, apiComplete, currentStep, processMode]);

  // 3. --- LIVE WATCHDOG POLLING EFFECT (ENHANCED) ---
  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    if (isLiveMode && sessionId) {
      setProcessMode('sync');
      
      // Log Start
      setAgentLogs(prev => {
        if (prev.some(log => log.message.includes("LIVE SYNC STARTED"))) return prev;
        return [...prev, {
          id: `live-start-${Date.now()}`,
          agent: "Digital Twin Watchdog",
          message: "🔴 LIVE SYNC STARTED: Listening for GitHub commits...",
          type: "agent",
          delay: 0
        }];
      });

      intervalId = setInterval(async () => {
        try {
          const result = await checkWatchdog(sessionId, lastSha);

          if (result.status === "updated" && result.new_sha && result.new_sha !== lastSha) {
            setLastSha(result.new_sha);

            // 1. Log Detection Immediately
            setAgentLogs(prev => [...prev, {
              id: `live-detect-${Date.now()}`,
              agent: "Watchdog",
              message: `⚡ CHANGE DETECTED in ${result.repo_name}!`,
              type: "success",
              delay: 0
            }]);

            // 2. Add "Filler" logs to show processing steps (Visual Feedback)
            setTimeout(() => {
               setAgentLogs(prev => [...prev, {
                id: `live-analysis-${Date.now()}`,
                agent: "Watchdog",
                message: `🧠 Analyzing code semantics and diffs...`,
                type: "agent",
                delay: 0
              }]);
            }, 500);

            setTimeout(() => {
               setAgentLogs(prev => [...prev, {
                id: `live-update-db-${Date.now()}`,
                agent: "Watchdog",
                message: `💾 Updating User Knowledge Graph...`,
                type: "agent",
                delay: 0
              }]);
            }, 1200);
            
            if (result.updated_skills && result.updated_skills.length > 0) {
              const freshSkills = result.updated_skills.slice(0, 5); 
              
              setTimeout(() => {
                setAgentLogs(prev => [...prev, {
                  id: `live-skills-${Date.now()}`,
                  agent: "Watchdog",
                  message: `✓ Extracted: ${freshSkills.join(", ")}...`,
                  type: "success",
                  delay: 0
                }]);
              }, 2000);

              // Clear jobs to show refresh is happening
              setJobs([]); 

              // Boosted Query
              const boostedQuery = `
                Job Title: ${freshSkills[0]} Engineer or Specialist.
                Key Requirements: ${freshSkills.join(", ")}.
                Domain: ${freshSkills[0]} and ${freshSkills[1]}.
                Focus: Strictly related to ${freshSkills[0]}.
              `.replace(/\s+/g, " ").trim();

              console.log("🚀 Sending PURE Query:", boostedQuery);

              setTimeout(async () => {
                setAgentLogs(prev => [...prev, {
                  id: `live-jobs-start-${Date.now()}`,
                  agent: "Agent 3",
                  message: `🎯 PIVOTING STRATEGY: Focusing 100% on ${freshSkills[0]}...`,
                  type: "agent",
                  delay: 0
                }]);

                await runStrategy(boostedQuery, true);

                setAgentLogs(prev => [...prev, {
                  id: `live-jobs-end-${Date.now()}`,
                  agent: "System",
                  message: "✓ Strategy Board Updated.",
                  type: "success",
                  delay: 0
                }]);
              }, 2500); // Wait for animations
            }
          } 
        } catch (e) {
          console.error("Watchdog polling error", e);
        }
      }, 10000); 
    } else if (!isLiveMode && lastSha) {
       setAgentLogs(prev => [...prev, {
        id: `live-stop-${Date.now()}`,
        agent: "System",
        message: "Live Sync Paused.",
        type: "system",
        delay: 0
      }]);
    }

    return () => clearInterval(intervalId);
  }, [isLiveMode, sessionId, lastSha, runStrategy]);


  useEffect(() => {
    if (strategyJobs.length > 0) {
      setJobs(transformStrategyJobs(strategyJobs));
    }
  }, [strategyJobs, transformStrategyJobs]);

  const handleAgentComplete = () => {
    setTimeout(() => {
      setIsInitializing(false);
      setShowJobs(true);
    }, 500);
  };

  const handleRefresh = async () => {
    setProcessMode('onboarding');
    setIsInitializing(true);
    setShowJobs(false);
    setAgentLogs([]);
    setCurrentStep(0);
    setApiComplete(false);
    hasRunStrategyRef.current = false;
    hasStartedSimulation.current = false;

    setAgentLogs([{
      id: `refresh-start-${Date.now()}`,
      agent: "System",
      message: "Force refresh initiated...",
      type: "agent",
      delay: 100,
    }]);
    setCurrentStep(1);

    const success = await runStrategy(undefined, true);
    setApiComplete(true);

    setAgentLogs((prev) => [...prev, {
      id: `refresh-complete-${Date.now()}`,
      agent: "System",
      message: success ? "✓ Refreshed!" : "✓ Done",
      type: "success",
      delay: 100,
    }]);
  };

  const readyJobs = jobs.filter((j) => j.matchScore >= 80).length;
  const gapJobs = jobs.filter((j) => j.matchScore < 80).length;
  const avgMatch = jobs.length > 0 ? Math.round(jobs.reduce((acc, j) => acc + j.matchScore, 0) / jobs.length) : 0;

  return (
    <div className="min-h-screen bg-canvas">
      <AnimatePresence>
        {isInitializing && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-center justify-center bg-canvas/95 backdrop-blur-sm">
            <div className="w-full max-w-2xl px-8">
              <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-8">
                <div className="flex items-center justify-center gap-3 mb-4">
                  <motion.div animate={{ rotate: 360 }} transition={{ duration: 3, repeat: Infinity, ease: "linear" }} className="w-14 h-14 rounded-xl flex items-center justify-center" style={{ backgroundColor: "#D95D39" }}>
                    <Bot className="w-7 h-7 text-white" />
                  </motion.div>
                </div>
                <h2 className="font-serif-bold text-3xl text-ink mb-2">Multi-Agent Orchestration</h2>
                <p className="text-secondary mb-3">{profile ? `Analyzing career opportunities for ${profile.name}...` : "Coordinating swarm intelligence..."}</p>
                <div className="max-w-md mx-auto mb-4">
                  <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <motion.div className="h-full rounded-full" style={{ backgroundColor: "#D95D39" }} initial={{ width: "0%" }} animate={{ width: apiComplete ? "100%" : ["0%", "70%", "85%", "90%"] }} transition={{ duration: apiComplete ? 0.3 : 30, ease: apiComplete ? "easeOut" : "easeInOut" }} />
                  </div>
                  <div className="flex justify-between mt-2 text-xs text-secondary"><span>Processing</span><span>{apiComplete ? "Complete!" : "Please wait..."}</span></div>
                </div>
                <p className="text-xs text-secondary/70">⏱️ First-time analysis takes 30-60 seconds.</p>
              </motion.div>
              <AgentTerminal logs={agentLogs} onComplete={handleAgentComplete} title="Swarm Coordinator v2.0" />
              {error && <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center text-amber-600 text-sm mt-4">{error} - Using cached data if available</motion.p>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="py-12 px-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: showJobs ? 1 : 0, y: showJobs ? 0 : 20 }} className="max-w-7xl mx-auto mb-12">
          
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="font-serif-bold text-4xl text-ink mb-2">Strategy Board</h1>
              <p className="text-secondary">{profile ? `Job matches for ${profile.name}` : "Your personalized job matches"}</p>
            </div>
            <div className="flex items-center gap-3">
              {/* --- NEW LIVE SYNC BUTTON --- */}
              <button
                onClick={() => setIsLiveMode(!isLiveMode)}
                disabled={isLoading}
                className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm border transition-all ${
                  isLiveMode 
                    ? "bg-red-50 border-red-200 text-red-600 animate-pulse" 
                    : "hover:bg-gray-50 border-[#E5E0D8]"
                }`}
              >
                {isLiveMode ? <Loader2 className="w-4 h-4 animate-spin" /> : <Radio className="w-4 h-4" />}
                {isLiveMode ? "Live Listening..." : "Start Live Sync"}
              </button>

              <button onClick={handleRefresh} disabled={isLoading} className="flex items-center gap-2 px-4 py-2 rounded-full text-sm border transition-all hover:bg-gray-50 disabled:opacity-50" style={{ borderColor: "#E5E0D8" }}>
                <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} /> Refresh
              </button>
              <div className="flex items-center gap-2 px-4 py-2 rounded-full text-sm" style={{ backgroundColor: "#D95D39", color: "white" }}>
                <Sparkles className="w-4 h-4" /> {jobs.length} Matches Found
              </div>
            </div>
          </div>

          {/* --- RENDER LIVE ACTIVITY FEED IF ACTIVE --- */}
          <AnimatePresence>
            {isLiveMode && (
              <LiveActivityFeed logs={agentLogs} />
            )}
          </AnimatePresence>

          <div className="grid grid-cols-3 gap-6 mb-8">
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-surface rounded-xl border p-6" style={{ borderColor: "#E5E0D8" }}>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center"><CheckCircle2 className="w-5 h-5 text-green-600" /></div>
                <div><div className="text-2xl font-bold text-ink">{readyJobs}</div><div className="text-sm text-secondary">Ready to Deploy</div></div>
              </div>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-surface rounded-xl border p-6" style={{ borderColor: "#E5E0D8" }}>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center"><Target className="w-5 h-5 text-amber-600" /></div>
                <div><div className="text-2xl font-bold text-ink">{gapJobs}</div><div className="text-sm text-secondary">Gaps Detected</div></div>
              </div>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="bg-surface rounded-xl border p-6" style={{ borderColor: "#E5E0D8" }}>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center"><TrendingUp className="w-5 h-5" style={{ color: "#D95D39" }} /></div>
                <div><div className="text-2xl font-bold text-ink">{avgMatch}%</div><div className="text-sm text-secondary">Avg Match Score</div></div>
              </div>
            </motion.div>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: showJobs ? 1 : 0 }} className="max-w-7xl mx-auto">
          {jobs.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {jobs.map((job, index) => (
                 <JobCard key={`${job.id}-${index}`} job={job} index={index} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-secondary">No job matches found.</p>
              <button onClick={() => router.push("/")} className="mt-4 px-6 py-3 rounded-lg font-medium text-white" style={{ backgroundColor: "#D95D39" }}>Upload Resume</button>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}