"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/lib/AuthContext";
import * as api from "@/lib/api";
import type {
  DashboardInsightsResponse,
  JobInsight,
  SkillInsight,
  GitHubInsight,
  NewsCard,
  SavedJob,
  RoadmapDetails
} from "@/lib/api";
import {
  Bot,
  Target,
  TrendingUp,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  Building2,
  RefreshCw,
  Github,
  Activity,
  Brain,
  Newspaper,
  GraduationCap,
  ChevronRight,
  Flame,
  GitCommit,
  ExternalLink,
  User,
  Settings,
  LogOut,
  Loader2,
} from "lucide-react";
import AgentTerminal, { AgentLog } from "@/components/AgentTerminal";
import JobCard from "@/components/JobCard";

// ============================================================================
// Types & Interfaces
// ============================================================================

interface JobMatch {
  id: string;
  title: string;
  company: string;
  location: string;
  salary?: string;
  postedDate?: string;
  matchScore: number;
  skills: string[];
  gapSkills?: string[];
  description?: string;
  link?: string;
  // Full job data for saving
  roadmap?: RoadmapDetails;
  application_text?: object;
  summary?: string;
  platform?: string;
  source?: string;
  type?: string;
  needs_improvement?: boolean;
}

interface StrategyJobMatch {
  id?: string;
  title: string;
  company_name: string;
  location: string;
  salary?: string;
  posted_date?: string;
  score: number;
  description?: string;
  link?: string;
  roadmap_details?: {
    missing_skills?: string[];
  };
}

interface SimulationStep {
  agent: string;
  message: string;
  type: "agent" | "status" | "success" | "system";
}

// Simulation Steps Configuration
const SIMULATION_STEPS: SimulationStep[] = [
  { agent: "Agent 1 (Perception)", message: "Analyzing resume embeddings...", type: "agent" },
  { agent: "Agent 1", message: "Extracting Skills, Education, Experience...", type: "agent" },
  { agent: "Agent 1", message: "✓ Profile vector constructed (768 dims)", type: "status" },
  { agent: "Agent 2 (Market Sentinel)", message: "Querying job market with semantic search...", type: "agent" },
  { agent: "Agent 2", message: "Scanning 100,000+ active job listings...", type: "agent" },
  { agent: "Agent 2", message: "✓ Retrieved 50 candidate matches", type: "status" },
  { agent: "Agent 3 (Strategist)", message: "Running Gap Analysis Algorithm...", type: "agent" },
  { agent: "Agent 3", message: "Scoring job-profile alignment...", type: "agent" },
  { agent: "Agent 3", message: "✓ Match scores calculated", type: "status" },
  { agent: "System", message: "✓ Strategy complete. Jobs ready.", type: "success" },
];

// ============================================================================
// Helper Components
// ============================================================================

function AgentStatusCard({ status }: { status: string }) {
  const isActive = status === "active" || status === "syncing";
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-br from-[#D95D39] to-[#c54d2d] rounded-2xl p-6 text-white relative overflow-hidden h-full"
    >
      <div className="absolute inset-0 opacity-20">
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-2 h-2 bg-white rounded-full"
            style={{ left: `${Math.random() * 100}%`, top: `${Math.random() * 100}%` }}
            animate={{ opacity: [0.3, 1, 0.3], scale: [1, 1.5, 1] }}
            transition={{ duration: 2 + Math.random() * 2, repeat: Infinity, delay: Math.random() * 2 }}
          />
        ))}
      </div>
      <div className="relative z-10">
        <div className="flex items-center gap-3 mb-4">
          <motion.div
            animate={{ rotate: isActive ? 360 : 0 }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm"
          >
            <Bot className="w-6 h-6" />
          </motion.div>
          <div>
            <h3 className="font-semibold text-lg">AI Agents Active</h3>
            <div className="flex items-center gap-2 text-white/80 text-sm">
              <span className={`w-2 h-2 rounded-full ${isActive ? "bg-green-400 animate-pulse" : "bg-white/50"}`} />
              {status === "syncing" ? "Analyzing your profile..." : "Monitoring job market"}
            </div>
          </div>
        </div>
        <p className="text-white/90 text-sm leading-relaxed">
          Our AI agents are continuously working on your career profile, scanning job markets, and finding the best opportunities.
        </p>
      </div>
    </motion.div>
  );
}

function ProfileStrengthCard({ strength }: { strength: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm h-full"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900">Profile Strength</h3>
        <GraduationCap className="w-5 h-5 text-[#D95D39]" />
      </div>
      <div className="relative h-4 bg-gray-100 rounded-full overflow-hidden mb-3">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${strength}%` }}
          transition={{ duration: 1, ease: "easeOut" }}
          className="absolute h-full rounded-full"
          style={{
            background: strength >= 80 ? "linear-gradient(90deg, #22c55e, #16a34a)"
              : strength >= 50 ? "linear-gradient(90deg, #D95D39, #c54d2d)"
              : "linear-gradient(90deg, #f59e0b, #d97706)",
          }}
        />
      </div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-500">
          {strength >= 80 ? "Excellent!" : strength >= 50 ? "Good progress" : "Needs attention"}
        </span>
        <span className="font-semibold text-gray-900">{strength}%</span>
      </div>
    </motion.div>
  );
}

function HotSkillCard({ skill, index }: { skill: SkillInsight; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.1 }}
      className="bg-gradient-to-br from-orange-50 to-amber-50 rounded-xl border border-orange-200 p-4"
    >
      <div className="flex items-center gap-2 mb-2">
        <Flame className="w-4 h-4 text-orange-500" />
        <span className="font-medium text-gray-900">{skill.skill}</span>
        {skill.demand_trend === "rising" && <TrendingUp className="w-4 h-4 text-green-500" />}
      </div>
      <p className="text-sm text-gray-600">{skill.reason}</p>
    </motion.div>
  );
}

function NewsCardComponent({ news, index }: { news: NewsCard; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center flex-shrink-0">
          <Newspaper className="w-4 h-4 text-blue-500" />
        </div>
        <div className="flex-1">
          <h4 className="font-medium text-gray-900 mb-1">{news.title}</h4>
          <p className="text-sm text-gray-600 line-clamp-2">{news.summary}</p>
          {news.relevance && (
            <span className="text-xs text-blue-500 mt-2 inline-block">
              {news.relevance}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  );
}


// Watchdog check function
async function checkWatchdog(sessionId: string, lastSha?: string) {
  try {
    // FIX: Call the specific function instead of api.get
    const data = await api.checkWatchdogStatus(sessionId, lastSha);
    return data;
  } catch (error) {
    console.error("Watchdog check failed:", error);
    return { status: "no_change" };
  }
}

// ============================================================================
// Main Dashboard Component
// ============================================================================

export default function Dashboard() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, user, signOut } = useAuth();

  // Unified State
  const [profile, setProfile] = useState<any>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [insights, setInsights] = useState<DashboardInsightsResponse | null>(null);

  // Simulation & Process State
  const [showJobs, setShowJobs] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [agentLogs, setAgentLogs] = useState<AgentLog[]>([]);
  const [jobs, setJobs] = useState<JobMatch[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [apiComplete, setApiComplete] = useState(false);
  const hasRunStrategyRef = useRef(false);

  // Saved Jobs State
  const [savedJobIds, setSavedJobIds] = useState<Set<string>>(new Set());

  // GitHub Sync State (Single button, no auto-polling)
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<{
    insights?: { message?: string; repos_active?: string[]; tech_stack?: string[] };
    newSkills?: string[];
    updatedSkills?: string[];
    fromCache?: boolean;
  } | null>(null);
  const [processMode, setProcessMode] = useState<'onboarding' | 'sync'>('onboarding');
  const hasStartedSimulation = useRef(false);

  // Cold Start State - for new users after onboarding
  const [isColdStarting, setIsColdStarting] = useState(false);
  const [coldStartStep, setColdStartStep] = useState(0);
  const [coldStartElapsed, setColdStartElapsed] = useState(0);
  const coldStartMessages = [
    { agent: "Orchestrator", message: "🚀 Welcome aboard! Initializing your career intelligence...", icon: "🤖" },
    { agent: "Agent 1 (Perception)", message: "Analyzing your profile and skills matrix...", icon: "🔍" },
    { agent: "Agent 1", message: "Building semantic embeddings (768 dimensions)...", icon: "⚡" },
    { agent: "Agent 2 (Market Sentinel)", message: "Scanning 100,000+ job listings worldwide...", icon: "🌐" },
    { agent: "Agent 2", message: "Querying job markets with your skill vector...", icon: "📊" },
    { agent: "Agent 2", message: "Fetching hackathons and competitions...", icon: "🏆" },
    { agent: "Agent 3 (Strategist)", message: "Running Gap Analysis Algorithm...", icon: "🎯" },
    { agent: "Agent 3", message: "Calculating match scores and skill gaps...", icon: "📈" },
    { agent: "Agent 3", message: "Generating personalized learning roadmaps...", icon: "🗺️" },
    { agent: "Agent 3", message: "Curating industry news for you...", icon: "📰" },
    { agent: "System", message: "✨ Your personalized dashboard is ready!", icon: "🎉" },
  ];

  // Mock function for runStrategy (Replace with actual API call)
  const runStrategy = useCallback(async (query?: string, force?: boolean) => {
    try {
        // Simulating API latency
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // This should be your actual API call:
        // const res = await api.getStrategyJobs(query);
        // return res.data;
        
        // Return true to simulate success
        return true; 
    } catch (e) {
        console.error("Strategy run failed", e);
        return false;
    }
  }, []);

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
        company: job.company_name,
        matchScore: score,
        location: job.location,
        skills: skills.length > 0 ? skills : ["Technical Skills"],
        gapSkills: missingSkills.length > 0 ? missingSkills : undefined,
        description: job.description,
        link: job.link,
      };
    });
  }, []);

  // 1. Initial Data Fetch
  useEffect(() => {
    const fetchDashboard = async () => {
      if (!isAuthenticated) return;

      try {
        const status = await api.getOnboardingStatus();
        if (status.needs_onboarding) {
          router.push("/onboarding");
          return;
        }

        // Fetch basic dashboard insights
        const data = await api.getDashboardInsights();
        
        // Check if user just completed onboarding but cold start hasn't finished
        // (no jobs means today_data is empty)
        const hasJobs = data.top_jobs && data.top_jobs.length > 0;
        const isNewUser = data.profile_strength > 0;
        
        if (!hasJobs && isNewUser) {
          console.log("[Dashboard] New user detected, running cold start with polling...");
          setIsColdStarting(true);
          setProfile({ name: data.user_name || "User" });
          
          // Trigger cold start (don't wait for it - it runs in background)
          api.triggerColdStart().then(() => {
            console.log("[Dashboard] Cold start API call completed");
          }).catch(err => {
            console.error("[Dashboard] Cold start API error:", err);
          });
          
          // Start animation loop
          let animationStep = 0;
          const animationInterval = setInterval(() => {
            animationStep = (animationStep + 1) % (coldStartMessages.length - 1);
            setColdStartStep(animationStep);
          }, 2500);

          // Track elapsed time
          const startTime = Date.now();
          const timerInterval = setInterval(() => {
            setColdStartElapsed(Math.floor((Date.now() - startTime) / 1000));
          }, 1000);
          
          // Poll for data until jobs are available
          const maxPollingTime = 120000; // 2 minutes max
          const pollInterval = 10000; // Poll every 10 seconds
          
          const pollForData = async (): Promise<boolean> => {
            while (Date.now() - startTime < maxPollingTime) {
              try {
                console.log("[Dashboard] Polling for data...");
                const pollData = await api.getDashboardInsights();
                
                if (pollData.top_jobs && pollData.top_jobs.length > 0) {
                  console.log("[Dashboard] Jobs found! Cold start complete. Refreshing...");
                  clearInterval(animationInterval);
                  clearInterval(timerInterval);
                  
                  // Show final step
                  setColdStartStep(coldStartMessages.length - 1);
                  await new Promise(resolve => setTimeout(resolve, 1500));
                  
                  // Force reload to ensure fresh state
                  window.location.reload();
                  return true;
                }
                
                // Wait before next poll
                await new Promise(resolve => setTimeout(resolve, pollInterval));
              } catch (pollErr) {
                console.error("[Dashboard] Polling error:", pollErr);
                await new Promise(resolve => setTimeout(resolve, pollInterval));
              }
            }
            return false;
          };
          
          const success = await pollForData();
          
          if (!success) {
            console.log("[Dashboard] Polling timeout - showing dashboard anyway");
            clearInterval(animationInterval);
            clearInterval(timerInterval);
            // If timeout, just set what we have (even if empty)
            setInsights(data);
            setIsColdStarting(false);
          }
        } else {
          // Normal dashboard load - has data
          setInsights(data);
          setProfile({ name: data.user_name || "User" });
        }
        
        const newSessionId = "session-" + Date.now();
        setSessionId(newSessionId);

        // If GitHub insights exist in cache, show them immediately
        if (data.github_insights) {
          console.log("[Dashboard] GitHub cache found, displaying insights...");
          setSyncResult({
            insights: {
              message: data.github_insights.insight_text || "GitHub activity synced!",
              repos_active: [data.github_insights.repo_name],
              tech_stack: data.github_insights.detected_skills?.map((s: any) => s.skill || s) || [],
            },
            newSkills: data.github_insights.detected_skills?.map((s: any) => s.skill || s) || [],
            updatedSkills: [],
            fromCache: true,
          });
        } else if (data.profile_strength > 0 && !isColdStarting) {
          // No cache but user has profile - run FULL GitHub sync (same as clicking button)
          console.log("[Dashboard] No GitHub cache found, running full sync...");
          try {
            const result = await api.syncGitHubPerception();
            if (result.status === "success" && result.insights) {
              setSyncResult({
                insights: result.insights,
                newSkills: result.new_skills || [],
                updatedSkills: result.updated_skills || [],
                fromCache: result.from_cache || false,
              });
            }
          } catch (syncErr) {
            console.log("[Dashboard] Auto-sync skipped:", syncErr);
          }
        }

      } catch (err) {
        console.error("Failed to fetch dashboard:", err);
        setError("Failed to load dashboard. Please try again.");
      } finally {
        setIsLoading(false);
      }
    };

    if (!authLoading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else {
        fetchDashboard();
      }
    }
  }, [isAuthenticated, authLoading, router]);

  // 2. Initial Strategy Run (Simulation Logic)
  useEffect(() => {
    const runAgentWorkflow = async () => {
      if (!sessionId || !profile || hasRunStrategyRef.current) return;
      hasRunStrategyRef.current = true;

      const success = await runStrategy();
      setApiComplete(true);

      if (processMode === 'onboarding') {
        setAgentLogs((prev) => [...prev, {
          id: crypto.randomUUID(),
          agent: "System",
          message: success ? "✓ Strategy Board Ready - Found matching opportunities!" : "✓ Loaded from cache",
          type: "success",
          delay: 100,
        }]);
      }
    };
    runAgentWorkflow();
  }, [sessionId, profile, processMode, runStrategy]);

  // 3. Simulation Animation
  useEffect(() => {
    if (!isInitializing || apiComplete || processMode !== 'onboarding') return;

    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        const nextStep = prev + 1;
        const stepIndex = nextStep >= SIMULATION_STEPS.length ? SIMULATION_STEPS.length - 4 + (nextStep % 4) : nextStep;
        
        if (stepIndex < SIMULATION_STEPS.length) {
          const step = SIMULATION_STEPS[stepIndex];
          setAgentLogs((logs) => [...logs, {
            id: crypto.randomUUID(),
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
        if (prev.length > 0) return prev; // Already initialized
        return [{
          id: crypto.randomUUID(),
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

  // 4. GitHub Sync Handler (Single button click - no auto-polling)
  const handleGitHubSync = useCallback(async () => {
    if (!sessionId || isSyncing) return;
    
    setIsSyncing(true);
    setSyncResult(null);
    
    try {
      const result = await checkWatchdog(sessionId);
      
      if (result.status === "updated") {
        setSyncResult({
          insights: result.insights,
          newSkills: result.new_skills || [],
          updatedSkills: result.updated_skills || [],
          fromCache: result.from_cache || false,
        });
        
        // Show success log with cache indicator
        const cacheIndicator = result.from_cache ? " (from cache)" : " (fresh analysis)";
        setAgentLogs(prev => [...prev, {
          id: crypto.randomUUID(),
          agent: "GitHub Watchdog",
          message: `✓ ${result.insights?.message || "GitHub synced!"}${cacheIndicator}`,
          type: "success",
          delay: 0
        }]);
      } else if (result.status === "no_activity") {
        setSyncResult({
          insights: { message: "No recent GitHub activity found. Push some code to see your skills!" }
        });
      } else if (result.status === "no_github") {
        setSyncResult({
          insights: { message: "GitHub URL not configured. Add it in settings to sync your activity." }
        });
      } else {
        setSyncResult({
          insights: { message: "Your profile is already up to date!" }
        });
      }
    } catch (e) {
      console.error("GitHub sync error:", e);
      setSyncResult({
        insights: { message: "Failed to sync GitHub. Please try again." }
      });
    } finally {
      setIsSyncing(false);
    }
  }, [sessionId, isSyncing]);

  // 5. Fetch Saved Jobs on mount
  useEffect(() => {
    const fetchSavedJobs = async () => {
      if (!user?.id) return;
      try {
        const savedJobs = await api.getSavedJobs(user.id);
        const ids = new Set(savedJobs.map((j: SavedJob) => j.original_job_id));
        setSavedJobIds(ids);
      } catch (err) {
        console.error("Failed to fetch saved jobs:", err);
      }
    };
    if (isAuthenticated && user?.id) {
      fetchSavedJobs();
    }
  }, [isAuthenticated, user?.id]);

  // Save Job Handler
  const handleSaveJob = useCallback(async (job: { 
    id: string; 
    title: string; 
    company: string; 
    description?: string; 
    link?: string; 
    score: number; 
    roadmap_details?: RoadmapDetails | null;
    full_job_data?: object;
  }) => {
    if (!user?.id) return;
    try {
      await api.saveJob({
        user_id: user.id,
        original_job_id: job.id,
        title: job.title,
        company: job.company,
        description: job.description || "",
        link: job.link || "",
        score: job.score / 100, // Convert back to 0-1 scale
        roadmap_details: job.roadmap_details || null,
        full_job_data: (job.full_job_data as any) || null,
      });
      setSavedJobIds(prev => new Set([...prev, job.id]));
    } catch (err) {
      console.error("Failed to save job:", err);
      throw err;
    }
  }, [user?.id]);

  // Unsave Job Handler
  const handleUnsaveJob = useCallback(async (jobId: string) => {
    if (!user?.id) return;
    try {
      // Find the saved job by original_job_id to get its UUID
      const savedJobs = await api.getSavedJobs(user.id);
      const savedJob = savedJobs.find((j: SavedJob) => j.original_job_id === jobId);
      if (savedJob) {
        await api.removeSavedJob(savedJob.id);
        setSavedJobIds(prev => {
          const newSet = new Set(prev);
          newSet.delete(jobId);
          return newSet;
        });
      }
    } catch (err) {
      console.error("Failed to unsave job:", err);
      throw err;
    }
  }, [user?.id]);

  // Fetch full job data with roadmaps
  useEffect(() => {
    const fetchFullJobs = async () => {
      if (!isAuthenticated) return;
      try {
        const data = await api.getTodayJobs();
        const mapped = (data.jobs || []).map((job: any) => ({
          id: job.id || String(Math.random()),
          title: job.title,
          company: job.company,
          matchScore: Math.round(job.score * 100),
          location: job.location || "Remote",
          skills: job.roadmap?.missing_skills || [],
          description: job.summary || job.description,
          link: job.link,
          // Full job data for saving
          roadmap: job.roadmap || null,
          application_text: job.application_text || null,
          summary: job.summary,
          platform: job.platform,
          source: job.source,
          type: job.type,
          needs_improvement: job.needs_improvement,
        }));
        setJobs(mapped);
      } catch (err) {
        console.error("Failed to fetch full jobs:", err);
        // Fallback to insights if full jobs fail
        if (insights?.top_jobs) {
          const mapped = insights.top_jobs.map(j => ({
            id: j.id,
            title: j.title,
            company: j.company,
            matchScore: j.match_score,
            location: "Remote",
            skills: j.key_skills,
            postedDate: "Recent"
          }));
          setJobs(mapped);
        }
      }
    };
    
    if (isAuthenticated && !authLoading) {
      fetchFullJobs();
    }
  }, [isAuthenticated, authLoading, insights]);


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
      id: crypto.randomUUID(),
      agent: "System",
      message: "Force refresh initiated...",
      type: "agent",
      delay: 100,
    }]);
    setCurrentStep(1);

    const success = await runStrategy(undefined, true);
    setApiComplete(true);

    setAgentLogs((prev) => [...prev, {
      id: crypto.randomUUID(),
      agent: "System",
      message: success ? "✓ Refreshed!" : "✓ Done",
      type: "success",
      delay: 100,
    }]);
  };

  // Loading state
  if (authLoading || (isLoading && !isInitializing && !isColdStarting)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F7F5F0]">
        <div className="text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="w-14 h-14 bg-[#D95D39] rounded-xl flex items-center justify-center mx-auto mb-4"
          >
            <Bot className="w-7 h-7 text-white" />
          </motion.div>
          <p className="text-gray-600">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  // ========== COLD START FULL-SCREEN LOADING EXPERIENCE ==========
  if (isColdStarting) {
    const currentMessage = coldStartMessages[coldStartStep];
    const progress = ((coldStartStep + 1) / coldStartMessages.length) * 100;
    
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center overflow-hidden relative">
        {/* Animated background particles */}
        <div className="absolute inset-0 overflow-hidden">
          {[...Array(30)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-2 h-2 bg-[#D95D39] rounded-full opacity-20"
              initial={{ 
                x: Math.random() * (typeof window !== 'undefined' ? window.innerWidth : 1920), 
                y: Math.random() * (typeof window !== 'undefined' ? window.innerHeight : 1080) 
              }}
              animate={{ 
                y: [-20, 20, -20],
                opacity: [0.1, 0.3, 0.1],
              }}
              transition={{ 
                duration: 3 + Math.random() * 2, 
                repeat: Infinity, 
                delay: Math.random() * 2 
              }}
            />
          ))}
        </div>

        {/* Glowing orb in background */}
        <motion.div 
          className="absolute w-[600px] h-[600px] bg-[#D95D39] rounded-full opacity-5 blur-3xl"
          animate={{ scale: [1, 1.2, 1], opacity: [0.03, 0.08, 0.03] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        />

        <div className="relative z-10 max-w-2xl mx-auto px-8 text-center">
          {/* Logo/Bot Animation */}
          <motion.div
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", duration: 0.8 }}
            className="mb-8"
          >
            <motion.div 
              className="w-24 h-24 bg-gradient-to-br from-[#D95D39] to-[#ff7654] rounded-3xl flex items-center justify-center mx-auto shadow-2xl shadow-[#D95D39]/30"
              animate={{ rotate: 360 }}
              transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            >
              <Bot className="w-12 h-12 text-white" />
            </motion.div>
          </motion.div>

          {/* Welcome Text */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <h1 className="text-4xl font-bold text-white mb-3">
              {profile?.name ? `Welcome, ${profile.name.split(' ')[0]}!` : 'Welcome to Erflog!'}
            </h1>
            <p className="text-lg text-gray-400 mb-12">
              Our AI agents are preparing your personalized career dashboard
            </p>
          </motion.div>

          {/* Agent Animation Card */}
          <motion.div 
            className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-8 mb-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <AnimatePresence mode="wait">
              <motion.div
                key={coldStartStep}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
                className="flex items-center gap-4"
              >
                <div className="w-16 h-16 bg-gradient-to-br from-[#D95D39]/20 to-[#ff7654]/20 rounded-2xl flex items-center justify-center flex-shrink-0 border border-[#D95D39]/30">
                  <span className="text-3xl">{currentMessage?.icon}</span>
                </div>
                <div className="text-left flex-1">
                  <div className="text-sm text-[#D95D39] font-medium mb-1">
                    {currentMessage?.agent}
                  </div>
                  <div className="text-white text-lg">
                    {currentMessage?.message}
                  </div>
                </div>
                <motion.div 
                  className="w-3 h-3 bg-[#D95D39] rounded-full"
                  animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
              </motion.div>
            </AnimatePresence>
          </motion.div>

          {/* Progress Bar & Timer */}
          <div className="w-full max-w-md mx-auto">
            <div className="h-2 bg-white/10 rounded-full overflow-hidden mb-3">
              <motion.div 
                className="h-full bg-gradient-to-r from-[#D95D39] to-[#ff7654] rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </div>
            <div className="flex justify-between text-sm text-gray-500 mb-2">
              <span>Initializing... {coldStartElapsed > 0 && `(${coldStartElapsed}s)`}</span>
              <span>{Math.round(progress)}%</span>
            </div>
            
            {/* Reassurance Message if taking long */}
            {coldStartElapsed > 30 && (
              <motion.p 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-xs text-orange-400 mt-2"
              >
                Generating detailed insights takes a moment. Thanks for your patience!
              </motion.p>
            )}
          </div>

          {/* Fun fact/tip */}
          <motion.p 
            className="text-gray-500 text-sm mt-8 italic"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
          >
            💡 Tip: Our agents analyze 100,000+ jobs daily to find your perfect match
          </motion.p>
        </div>
      </div>
    );
  }

  const readyJobs = jobs.filter((j) => j.matchScore >= 80).length;
  const gapJobs = jobs.filter((j) => j.matchScore < 80).length;
  const avgMatch = jobs.length > 0 ? Math.round(jobs.reduce((acc, j) => acc + j.matchScore, 0) / jobs.length) : 0;

  return (
    <div className="min-h-screen bg-[#F7F5F0]">
      {/* ==================== 1. Header ==================== */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#D95D39] rounded-xl flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-gray-900">Erflog</h1>
              <p className="text-xs text-gray-500">AI Career Platform</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
             <button onClick={() => router.push("/settings")} className="p-2 text-gray-600 hover:text-gray-900"><Settings className="w-5 h-5" /></button>
             <button onClick={() => signOut()} className="p-2 text-red-600 hover:bg-red-50 rounded"><LogOut className="w-5 h-5" /></button>
          </div>
        </div>
      </header>

      {/* ==================== 2. Agent Overlay (Onboarding) ==================== */}
      <AnimatePresence>
        {isInitializing && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-center justify-center bg-[#F7F5F0]/95 backdrop-blur-sm">
            <div className="w-full max-w-2xl px-8">
              <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-8">
                <div className="flex items-center justify-center gap-3 mb-4">
                  <motion.div animate={{ rotate: 360 }} transition={{ duration: 3, repeat: Infinity, ease: "linear" }} className="w-14 h-14 rounded-xl flex items-center justify-center" style={{ backgroundColor: "#D95D39" }}>
                    <Bot className="w-7 h-7 text-white" />
                  </motion.div>
                </div>
                <h2 className="text-3xl font-bold text-gray-900 mb-2">Multi-Agent Orchestration</h2>
                <p className="text-gray-600 mb-3">{profile ? `Analyzing career opportunities for ${profile.name}...` : "Coordinating swarm intelligence..."}</p>
                <div className="max-w-md mx-auto mb-4">
                  <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <motion.div className="h-full rounded-full" style={{ backgroundColor: "#D95D39" }} initial={{ width: "0%" }} animate={{ width: apiComplete ? "100%" : ["0%", "70%", "85%", "90%"] }} transition={{ duration: apiComplete ? 0.3 : 30, ease: apiComplete ? "easeOut" : "easeInOut" }} />
                  </div>
                </div>
              </motion.div>
              <AgentTerminal logs={agentLogs} onComplete={handleAgentComplete} title="Swarm Coordinator v2.0" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ==================== 3. Main Content ==================== */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        
        {/* Welcome Section */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-8 flex justify-between items-end">
          <div>
            <h2 className="text-3xl font-bold text-gray-900 mb-2">Welcome back, {insights?.user_name?.split(" ")[0] || "there"}! 👋</h2>
            <p className="text-gray-600">Your AI career assistant is working 24/7 to find opportunities for you.</p>
          </div>
          
          {/* Controls */}
          <div className="flex items-center gap-3">
              <button
                onClick={handleGitHubSync}
                disabled={isSyncing}
                className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm border transition-all ${
                  isSyncing 
                    ? "bg-gray-100 border-gray-300 text-gray-500" 
                    : "bg-white hover:bg-gray-50 border-gray-200 hover:border-gray-300"
                }`}
              >
                {isSyncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Github className="w-4 h-4" />}
                {isSyncing ? "Syncing..." : "Sync GitHub"}
              </button>

              <button onClick={handleRefresh} disabled={isLoading} className="flex items-center gap-2 px-4 py-2 rounded-full text-sm border bg-white border-gray-200 hover:bg-gray-50">
                <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} /> Refresh
              </button>
          </div>
        </motion.div>

        {/* GitHub Sync Result Card */}
        <AnimatePresence>
          {syncResult && (
            <motion.div 
              initial={{ opacity: 0, y: -10, scale: 0.98 }} 
              animate={{ opacity: 1, y: 0, scale: 1 }} 
              exit={{ opacity: 0, y: -10, scale: 0.98 }}
              transition={{ type: "spring", duration: 0.5 }}
              className="mb-6 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-6 text-white shadow-xl border border-slate-700/50"
            >
              <div className="flex items-start gap-4">
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0 ${
                  syncResult.fromCache 
                    ? "bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/30" 
                    : "bg-gradient-to-br from-green-500/20 to-emerald-500/20 border border-green-500/30"
                }`}>
                  <Github className={`w-7 h-7 ${syncResult.fromCache ? "text-amber-400" : "text-green-400"}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-bold text-xl">GitHub Sync Complete</h3>
                    {/* Cache indicator badge */}
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                      syncResult.fromCache 
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/30" 
                        : "bg-green-500/20 text-green-300 border border-green-500/30"
                    }`}>
                      {syncResult.fromCache ? "⚡ Cached" : "✨ Fresh Analysis"}
                    </span>
                  </div>
                  <p className="text-slate-300 text-sm mb-4">{syncResult.insights?.message}</p>
                  
                  {/* Skills Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Skills (New or Detected based on cache) */}
                    {syncResult.newSkills && syncResult.newSkills.length > 0 && (
                      <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                        <div className="flex items-center gap-2 mb-3">
                          <Sparkles className={`w-4 h-4 ${syncResult.fromCache ? "text-amber-400" : "text-green-400"}`} />
                          <span className={`text-xs font-semibold uppercase tracking-wide ${syncResult.fromCache ? "text-amber-400" : "text-green-400"}`}>
                            {syncResult.fromCache ? "Detected Skills" : "New Skills"}
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {syncResult.newSkills.slice(0, 5).map((skill, idx) => (
                            <span key={idx} className={`px-3 py-1.5 rounded-lg text-sm font-medium border ${
                              syncResult.fromCache 
                                ? "bg-amber-500/10 text-amber-300 border-amber-500/20" 
                                : "bg-green-500/10 text-green-300 border-green-500/20"
                            }`}>
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Tech Stack */}
                    {syncResult.insights?.tech_stack && syncResult.insights.tech_stack.length > 0 && (
                      <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                        <div className="flex items-center gap-2 mb-3">
                          <Brain className="w-4 h-4 text-blue-400" />
                          <span className="text-xs text-blue-400 font-semibold uppercase tracking-wide">Tech Stack</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {syncResult.insights.tech_stack.map((tech, idx) => (
                            <span key={idx} className="px-3 py-1.5 bg-blue-500/10 text-blue-300 rounded-lg text-sm font-medium border border-blue-500/20">
                              {tech}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Active Repos */}
                    {syncResult.insights?.repos_active && syncResult.insights.repos_active.length > 0 && (
                      <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                        <div className="flex items-center gap-2 mb-3">
                          <GitCommit className="w-4 h-4 text-purple-400" />
                          <span className="text-xs text-purple-400 font-semibold uppercase tracking-wide">Active Repos</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {syncResult.insights.repos_active.map((repo, idx) => (
                            <span key={idx} className="px-3 py-1.5 bg-purple-500/10 text-purple-300 rounded-lg text-sm font-medium border border-purple-500/20">
                              {repo.split('/').pop()}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Close button */}
                <button 
                  onClick={() => setSyncResult(null)}
                  className="text-slate-500 hover:text-white transition-colors p-1 hover:bg-slate-700/50 rounded-lg"
                >
                  ✕
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Top Stats Row */}
        <div className="grid grid-cols-1 mb-8">
          <div className="w-full">
            <AgentStatusCard status={insights?.agent_status || "active"} />
          </div>
        </div>

        {/* Strategy / Job Board */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left: Job Matches (Wide) */}
          <div className="lg:col-span-2 space-y-6">
             <div className="flex gap-4 mb-4">
                 <div className="flex-1 bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center gap-3">
                    <CheckCircle2 className="text-green-500" />
                    <div><div className="font-bold text-xl">{readyJobs}</div><div className="text-xs text-gray-500">Ready</div></div>
                 </div>
                 <div className="flex-1 bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center gap-3">
                    <Target className="text-amber-500" />
                    <div><div className="font-bold text-xl">{gapJobs}</div><div className="text-xs text-gray-500">Gaps</div></div>
                 </div>
                 <div className="flex-1 bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center gap-3">
                    <TrendingUp className="text-[#D95D39]" />
                    <div><div className="font-bold text-xl">{avgMatch}%</div><div className="text-xs text-gray-500">Match</div></div>
                 </div>
             </div>

             <div className="space-y-4">
              <h3 className="text-lg font-bold text-gray-900 mb-3 ml-1">Top 3 Recommended Jobs for you</h3>
              {jobs.length > 0 ? (
                jobs.slice(0, 3).map((job) => (
                  <JobCard 
                    key={job.id}
                    id={job.id}
                    companyName={job.company}
                    jobTitle={job.title}
                    matchScore={job.matchScore}
                    description={job.description}
                    link={job.link}
                    roadmap_details={job.roadmap}
                    fullJobData={{
                      roadmap: job.roadmap,
                      application_text: job.application_text,
                      summary: job.summary,
                      location: job.location,
                      platform: job.platform,
                      source: job.source,
                      type: job.type,
                      needs_improvement: job.needs_improvement,
                    }}
                    isSaved={savedJobIds.has(job.id)}
                    onSave={handleSaveJob}
                    onUnsave={handleUnsaveJob}
                    onAnalyzeGap={(id) => console.log("Analyze gap for:", id)}
                    onDeploy={(id) => console.log("Deploy:", id)}
                  />
                ))
              ) : (
                <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
                  <p className="text-gray-500">No job matches found yet.</p>
                </div>
              )}
              
              {/* View All Jobs Button */}
              {jobs.length > 3 && (
                <button
                  onClick={() => router.push("/jobs")}
                  className="w-full mt-4 py-3 px-4 bg-surface hover:bg-gray-100 rounded-xl border border-gray-200 text-secondary hover:text-ink font-medium transition-colors flex items-center justify-center gap-2"
                >
                  View All {jobs.length} Jobs
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}
             </div>
          </div>

          {/* Right: Insights & News */}
          <div className="space-y-6">
            {/* Hot Skills */}
            <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-orange-100 rounded-xl flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-orange-500" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Hot Skills</h3>
                  <p className="text-sm text-gray-500">Trending to learn</p>
                </div>
              </div>
              <div className="space-y-3">
                {insights?.hot_skills?.map((skill, idx) => (
                  <HotSkillCard key={skill.skill} skill={skill} index={idx} />
                ))}
              </div>
            </div>

            {/* News */}
            <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
                  <Newspaper className="w-5 h-5 text-blue-500" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Industry News</h3>
                </div>
              </div>
              <div className="space-y-3">
                {insights?.news_cards?.map((news, idx) => (
                  <NewsCardComponent key={idx} news={news} index={idx} />
                ))}
              </div>
            </div>
            
          </div>
        </div>
      </main>
    </div>
  );
}
