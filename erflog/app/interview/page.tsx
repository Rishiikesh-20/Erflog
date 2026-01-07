"use client";

import { useState, useEffect, useRef, useCallback, Suspense } from "react";
import { useSession } from "@/lib/SessionContext";
import { useAuth } from "@/lib/AuthContext";
import {
  MessageCircle,
  Mic,
  MicOff,
  Bot,
  Briefcase,
  Clock,
  ChevronRight,
  Loader2,
  Sparkles,
  Send,
  Phone,
  PhoneOff,
  User,
  Volume2,
  AlertCircle,
  GraduationCap,
} from "lucide-react";

const WS_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws") ||
  "ws://localhost:8000";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type InterviewMode = "voice" | "text";
type InterviewType = "TECHNICAL" | "HR";
type AudioState = "idle" | "thinking" | "speaking" | "listening";
type InterviewStage =
  | "intro"
  | "resume"
  | "behavioral"
  | "experience"
  | "challenge"
  | "conclusion"
  | "end";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface Feedback {
  score?: number;
  verdict?: string;
  summary?: string;
  strengths?: string[];
  improvements?: string[];
  interview_type?: string;
  roadmap_additions?: {
    nodes: Array<{
      id: string;
      label: string;
      type: string;
      description: string;
      priority: string;
      estimated_hours: number;
      improvement_addressed?: string;
      resources?: Array<{ name: string; url: string; type?: string }>;
    }>;
    message: string;
    roadmap_id?: string;
  };
}

interface InterviewHistoryItem {
  id: number;
  created_at: string;
  feedback_report: Feedback;
  interview_type?: string;
}

export default function InterviewPage() {
  const { profile, strategyJobs, accessToken } = useSession();
  const { userMetadata, isAuthenticated } = useAuth();

  // Get user ID from auth context
  const userId = userMetadata.userId;

  // Mode selection state
  const [mode, setMode] = useState<InterviewMode>("text");
  const [interviewType, setInterviewType] =
    useState<InterviewType>("TECHNICAL");
  const [isActive, setIsActive] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string>("");

  // Interview state
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [currentStage, setCurrentStage] = useState<InterviewStage>("intro");
  const [currentTurn, setCurrentTurn] = useState(0);
  const [isThinking, setIsThinking] = useState(false);
  const [jobTitle, setJobTitle] = useState("");

  // Voice-specific state
  const [audioState, setAudioState] = useState<AudioState>("idle");
  const [isMuted, setIsMuted] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);

  // History state
  const [history, setHistory] = useState<InterviewHistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [selectedHistory, setSelectedHistory] = useState<Feedback | null>(null);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioQueueRef = useRef<Blob[]>([]);
  const isPlayingRef = useRef(false);
  const audioStateRef = useRef<AudioState>("idle");

  // Keep ref in sync
  useEffect(() => {
    audioStateRef.current = audioState;
  }, [audioState]);

  // Auto-start ref to prevent double-start
  const autoStartTriggered = useRef(false);

  // Auto-select first job when strategyJobs loads, or use sessionStorage for dynamic route
  useEffect(() => {
    // Check for auto-start from dynamic route (/interview/[jobId]?mode=voice)
    const storedJobId = sessionStorage.getItem("interview_jobId");
    const storedMode = sessionStorage.getItem("interview_mode");
    const storedType = sessionStorage.getItem("interview_type");
    const shouldAutoStart = sessionStorage.getItem("interview_autoStart") === "true";

    if (storedJobId && !autoStartTriggered.current) {
      // Set the job ID and mode from sessionStorage
      setSelectedJobId(storedJobId);
      if (storedMode === "voice" || storedMode === "text") {
        setMode(storedMode as InterviewMode);
      }
      if (storedType === "HR" || storedType === "TECHNICAL") {
        setInterviewType(storedType as InterviewType);
      }

      // Clear sessionStorage
      sessionStorage.removeItem("interview_jobId");
      sessionStorage.removeItem("interview_mode");
      sessionStorage.removeItem("interview_type");
      sessionStorage.removeItem("interview_autoStart");

      // Mark as triggered to prevent re-running
      if (shouldAutoStart) {
        autoStartTriggered.current = true;
      }
    } else if (strategyJobs.length > 0 && !selectedJobId) {
      const firstJob = strategyJobs[0];
      setSelectedJobId(String(firstJob.id));
      setJobTitle(`${firstJob.title} at ${firstJob.company}`);
    }
  }, [strategyJobs, selectedJobId]);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Fetch history
  useEffect(() => {
    if (!userId) return;

    const fetchHistory = async () => {
      try {
        const response = await fetch(`${API_URL}/api/interviews/${userId}`);
        if (response.ok) {
          const data = await response.json();
          setHistory(data || []);
        }
      } catch (e) {
        console.error("Error fetching history:", e);
      } finally {
        setIsLoadingHistory(false);
      }
    };
    fetchHistory();
  }, [feedback, userId]);

  // Auto-start interview when coming from dynamic route
  useEffect(() => {
    if (autoStartTriggered.current && selectedJobId && !isActive && !isConnecting) {
      // Small delay to ensure state is fully set
      const timer = setTimeout(() => {
        if (!isActive && !isConnecting) {
          console.log("[Interview] Auto-starting with job:", selectedJobId, "mode:", mode);
          // Trigger start - we need to call startInterview after it's defined
          // This will be picked up by the next render cycle
          autoStartTriggered.current = false;
          // Set a flag that startInterview will check
          sessionStorage.setItem("interview_triggerStart", "true");
        }
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [selectedJobId, isActive, isConnecting, mode]);

  // Handle job change
  const handleJobChange = (value: string) => {
    const job = strategyJobs.find((j) => String(j.id) === value);
    setSelectedJobId(value);
    if (job) {
      setJobTitle(`${job.title} at ${job.company}`);
    }
  };

  // Play audio queue (voice mode)
  const playNextAudio = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;

    isPlayingRef.current = true;
    setAudioState("speaking");

    const audioBlob = audioQueueRef.current.shift()!;
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);

    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      isPlayingRef.current = false;
      if (audioQueueRef.current.length > 0) {
        playNextAudio();
      } else {
        setAudioState("listening");
      }
    };

    audio.onerror = () => {
      URL.revokeObjectURL(audioUrl);
      isPlayingRef.current = false;
      setAudioState("listening");
    };

    try {
      await audio.play();
    } catch (e) {
      console.error("Audio play error:", e);
      isPlayingRef.current = false;
      setAudioState("listening");
    }
  }, []);

  // Handle WebSocket messages
  const handleMessage = useCallback(
    async (event: MessageEvent) => {
      if (mode === "voice" && event.data instanceof Blob) {
        audioQueueRef.current.push(event.data);
        playNextAudio();
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && last.content === "Speaking...")
            return prev;
          return [
            ...prev,
            {
              id: `assistant-speaking-${Date.now()}-${Math.random()
                .toString(36)
                .substr(2, 9)}`,
              role: "assistant",
              content: "Speaking...",
              timestamp: new Date(),
            },
          ];
        });
      } else {
        try {
          const data = JSON.parse(
            typeof event.data === "string"
              ? event.data
              : await event.data.text()
          );

          if (data.type === "config") {
            setJobTitle(data.job_title || "");
          } else if (data.type === "event") {
            if (data.event === "audio_state") {
              setAudioState(data.state);
            } else if (data.event === "thinking") {
              setIsThinking(data.status === "start");
              if (data.status === "start") setAudioState("thinking");
            } else if (data.event === "stage_change") {
              setCurrentStage(data.stage);
              setCurrentTurn((prev) => prev + 1);
            }
          } else if (data.type === "message") {
            setMessages((prev) => [
              ...prev,
              {
                id: `${data.role}-${Date.now()}-${Math.random()
                  .toString(36)
                  .substr(2, 9)}`,
                role: data.role,
                content: data.content,
                timestamp: new Date(),
              },
            ]);
          } else if (data.type === "feedback") {
            setFeedback(data.data);
          } else if (data.type === "error") {
            setError(data.message);
          }
        } catch (e) {
          console.error("Message parse error:", e);
        }
      }
    },
    [mode, playNextAudio]
  );

  // Start interview
  const startInterview = useCallback(async () => {
    setError(null);
    setMessages([]);
    setFeedback(null);
    setCurrentTurn(0);
    setCurrentStage("intro");
    setIsConnecting(true);
    setAudioState(mode === "voice" ? "thinking" : "idle");

    const wsPath =
      mode === "voice"
        ? `/ws/interview/${selectedJobId}`
        : `/ws/interview/text/${selectedJobId}`;

    try {
      // For voice mode, setup audio
      if (mode === "voice") {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            sampleRate: 16000,
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
          },
        });
        streamRef.current = stream;

        const audioContext = new AudioContext({ sampleRate: 16000 });
        audioContextRef.current = audioContext;

        analyserRef.current = audioContext.createAnalyser();
        analyserRef.current.fftSize = 256;

        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyserRef.current);

        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        source.connect(processor);
        processor.connect(audioContext.destination);

        const ws = new WebSocket(`${WS_URL}${wsPath}`);
        wsRef.current = ws;

        ws.onopen = () => {
          ws.send(
            JSON.stringify({
              access_token: accessToken || "test",
              interview_type: interviewType,
              user_id: userId,
            })
          );
          setIsConnected(true);
          setIsConnecting(false);
          setIsActive(true);

          processor.onaudioprocess = (e) => {
            if (
              ws.readyState === WebSocket.OPEN &&
              audioStateRef.current === "listening" &&
              !isMuted
            ) {
              const inputData = e.inputBuffer.getChannelData(0);
              const pcmData = new Int16Array(inputData.length);
              for (let i = 0; i < inputData.length; i++) {
                const s = Math.max(-1, Math.min(1, inputData[i]));
                pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
              }
              ws.send(pcmData.buffer);
            }
          };

          // Monitor audio level
          const updateLevel = () => {
            if (!analyserRef.current) return;
            const dataArray = new Uint8Array(
              analyserRef.current.frequencyBinCount
            );
            analyserRef.current.getByteFrequencyData(dataArray);
            const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
            setAudioLevel(avg / 255);
            if (isConnected) requestAnimationFrame(updateLevel);
          };
          updateLevel();
        };

        ws.onmessage = handleMessage;
        ws.onerror = () => setError("Connection error");
        ws.onclose = () => {
          setIsConnected(false);
          setIsActive(false);
          setAudioState("idle");
        };
      } else {
        // Text mode
        const ws = new WebSocket(`${WS_URL}${wsPath}`);
        wsRef.current = ws;

        ws.onopen = () => {
          ws.send(
            JSON.stringify({
              access_token: accessToken || "test",
              interview_type: interviewType,
              user_id: userId,
            })
          );
          setIsConnected(true);
          setIsConnecting(false);
          setIsActive(true);
        };

        ws.onmessage = handleMessage;
        ws.onerror = () => setError("Connection error");
        ws.onclose = () => {
          setIsConnected(false);
          setIsActive(false);
        };
      }
    } catch (e) {
      console.error("Start error:", e);
      setError(
        mode === "voice" ? "Failed to access microphone" : "Failed to connect"
      );
      setIsConnecting(false);
    }
  }, [
    mode,
    selectedJobId,
    accessToken,
    interviewType,
    handleMessage,
    isMuted,
    isConnected,
  ]);

  // Auto-trigger start from dynamic route
  useEffect(() => {
    const shouldTrigger = sessionStorage.getItem("interview_triggerStart") === "true";
    if (shouldTrigger && selectedJobId && !isActive && !isConnecting) {
      sessionStorage.removeItem("interview_triggerStart");
      console.log("[Interview] Auto-triggering start for job:", selectedJobId);
      startInterview();
    }
  }, [selectedJobId, isActive, isConnecting, startInterview]);

  // Send text message
  const sendMessage = useCallback(() => {
    if (
      !inputMessage.trim() ||
      !wsRef.current ||
      wsRef.current.readyState !== WebSocket.OPEN
    )
      return;

    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        role: "user",
        content: inputMessage,
        timestamp: new Date(),
      },
    ]);
    wsRef.current.send(JSON.stringify({ message: inputMessage }));
    setInputMessage("");
  }, [inputMessage]);

  // End interview
  const endInterview = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    setIsConnected(false);
    setIsActive(false);
    setAudioState("idle");
  }, []);

  // Cleanup
  useEffect(() => {
    return () => endInterview();
  }, [endInterview]);

  // Get stage color
  const getStageColor = (stage: InterviewStage) => {
    const colors: Record<InterviewStage, string> = {
      intro: "#10B981",
      resume: "#3B82F6",
      behavioral: "#8B5CF6",
      experience: "#F59E0B",
      challenge: "#EF4444",
      conclusion: "#D95D39",
      end: "#6B7280",
    };
    return colors[stage] || "#6B7280";
  };

  // Audio state display
  const getAudioStateDisplay = () => {
    switch (audioState) {
      case "thinking":
        return {
          icon: Loader2,
          text: "AI is thinking...",
          color: "#F59E0B",
          animate: true,
        };
      case "speaking":
        return {
          icon: Volume2,
          text: "AI is speaking...",
          color: "#D95D39",
          animate: true,
        };
      case "listening":
        return {
          icon: Mic,
          text: "Your turn - speak now!",
          color: "#10B981",
          animate: false,
        };
      default:
        return { icon: Mic, text: "Ready", color: "#6B7280", animate: false };
    }
  };

  const audioStateDisplay = getAudioStateDisplay();
  const AudioStateIcon = audioStateDisplay.icon;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-orange-50">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center shadow-lg"
                style={{
                  background:
                    "linear-gradient(135deg, #D95D39 0%, #F97316 100%)",
                }}
              >
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-xl text-slate-900">
                  Mock Interview
                </h1>
                <p className="text-sm text-slate-500">
                  {isActive
                    ? `${interviewType} • ${
                        mode === "voice" ? "Voice" : "Text"
                      }`
                    : "AI-Powered Practice"}
                </p>
              </div>
            </div>

            {isActive && (
              <div className="flex items-center gap-3">
                <span className="text-sm text-slate-500">
                  Turn {currentTurn}/6
                </span>
                <div
                  className="px-4 py-2 rounded-full text-sm font-medium text-white"
                  style={{ backgroundColor: getStageColor(currentStage) }}
                >
                  {currentStage.charAt(0).toUpperCase() + currentStage.slice(1)}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <p className="text-red-700 flex-1">{error}</p>
            <button
              onClick={() => setError(null)}
              className="text-red-500 hover:text-red-700"
            >
              ✕
            </button>
          </div>
        )}

        {/* Pre-Interview Setup */}
        {!isActive && !feedback && !selectedHistory && (
          <div className="space-y-8">
            {/* Hero */}
            <div className="text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-orange-100 text-orange-700 rounded-full text-sm font-medium mb-4">
                <Sparkles className="w-4 h-4" />
                AI-Powered Interview Simulation
              </div>
              <h2 className="text-4xl font-bold text-slate-900 mb-4">
                Practice Your Interview Skills
              </h2>
              <p className="text-lg text-slate-600 max-w-2xl mx-auto">
                Choose your preferred mode and interview type, then start
                practicing.
              </p>
            </div>

            {/* Mode & Type Selection */}
            <div className="max-w-2xl mx-auto space-y-6">
              {/* Mode Toggle */}
              <div className="bg-white rounded-2xl p-2 shadow-lg border border-slate-200 flex gap-2">
                <button
                  onClick={() => setMode("text")}
                  className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 rounded-xl font-medium transition-all ${
                    mode === "text"
                      ? "bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-md"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  <MessageCircle className="w-5 h-5" />
                  Chat Mode
                </button>
                <button
                  onClick={() => setMode("voice")}
                  className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 rounded-xl font-medium transition-all ${
                    mode === "voice"
                      ? "bg-gradient-to-r from-orange-500 to-red-500 text-white shadow-md"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  <Mic className="w-5 h-5" />
                  Voice Mode
                </button>
              </div>

              {/* Interview Type Toggle */}
              <div className="bg-white rounded-2xl p-2 shadow-lg border border-slate-200 flex gap-2">
                <button
                  onClick={() => setInterviewType("TECHNICAL")}
                  className={`flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
                    interviewType === "TECHNICAL"
                      ? "bg-slate-900 text-white shadow-md"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  <Briefcase className="w-4 h-4" />
                  Technical
                </button>
                <button
                  onClick={() => setInterviewType("HR")}
                  className={`flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
                    interviewType === "HR"
                      ? "bg-slate-900 text-white shadow-md"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  <GraduationCap className="w-4 h-4" />
                  HR / Behavioral
                </button>
              </div>

              {/* Job Selection */}
              {strategyJobs.length > 0 ? (
                <select
                  value={selectedJobId}
                  onChange={(e) => handleJobChange(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 bg-white focus:outline-none focus:border-orange-500 transition-all"
                >
                  {strategyJobs.map((job) => (
                    <option key={job.id} value={String(job.id)}>
                      {job.title} at {job.company}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="w-full px-4 py-3 rounded-xl border-2 border-amber-200 bg-amber-50 text-amber-700 text-sm">
                  No jobs available. Please add jobs from the Jobs page first.
                </div>
              )}

              {/* Start Button */}
              <button
                onClick={startInterview}
                disabled={isConnecting || !selectedJobId}
                className="w-full py-4 rounded-xl text-white font-medium flex items-center justify-center gap-3 transition-all hover:scale-[1.02] shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  background:
                    mode === "voice"
                      ? "linear-gradient(135deg, #D95D39 0%, #F97316 100%)"
                      : "linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)",
                }}
              >
                {isConnecting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" /> Connecting...
                  </>
                ) : mode === "voice" ? (
                  <>
                    <Phone className="w-5 h-5" /> Start Voice Interview
                  </>
                ) : (
                  <>
                    <MessageCircle className="w-5 h-5" /> Start Chat Interview
                  </>
                )}
              </button>
            </div>

            {/* History Section */}
            <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-lg">
              <h3 className="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">
                <Clock className="w-5 h-5 text-slate-400" />
                Interview History
              </h3>

              {isLoadingHistory ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                </div>
              ) : history.length === 0 ? (
                <div className="text-center py-8 bg-slate-50 rounded-xl border-dashed border-2 border-slate-200">
                  <Bot className="w-12 h-12 text-slate-300 mx-auto mb-2" />
                  <p className="text-slate-500">
                    No interviews yet. Start practicing!
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {history.slice(0, 5).map((item) => (
                    <button
                      key={item.id}
                      onClick={() => setSelectedHistory(item.feedback_report)}
                      className="w-full flex items-center justify-between p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors text-left"
                    >
                      <div className="flex items-center gap-4">
                        <div
                          className={`w-12 h-12 rounded-full flex items-center justify-center font-bold ${
                            item.feedback_report?.verdict
                              ?.toLowerCase()
                              .includes("hire")
                              ? "bg-green-100 text-green-600"
                              : "bg-orange-100 text-orange-600"
                          }`}
                        >
                          {item.feedback_report?.score ?? "?"}
                        </div>
                        <div>
                          <div className="font-medium text-slate-900">
                            {new Date(item.created_at).toLocaleDateString()}
                          </div>
                          <div className="text-sm text-slate-500">
                            {item.feedback_report?.interview_type ||
                              "Interview"}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-3 py-1 rounded-full text-sm font-medium ${
                            item.feedback_report?.verdict
                              ?.toLowerCase()
                              .includes("hire")
                              ? "bg-green-100 text-green-700"
                              : "bg-orange-100 text-orange-700"
                          }`}
                        >
                          {item.feedback_report?.verdict || "Incomplete"}
                        </span>
                        <ChevronRight className="w-5 h-5 text-slate-300" />
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Active Interview - Voice Mode */}
        {isActive && mode === "voice" && (
          <div className="space-y-6">
            {/* Audio State Indicator */}
            <div
              className="p-6 rounded-2xl border-2 shadow-lg"
              style={{
                borderColor: audioStateDisplay.color,
                backgroundColor: `${audioStateDisplay.color}10`,
              }}
            >
              <div className="flex items-center justify-center gap-4">
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center shadow-lg"
                  style={{ backgroundColor: audioStateDisplay.color }}
                >
                  <AudioStateIcon
                    className={`w-8 h-8 text-white ${
                      audioStateDisplay.animate ? "animate-pulse" : ""
                    }`}
                  />
                </div>
                <div>
                  <p
                    className="text-2xl font-bold"
                    style={{ color: audioStateDisplay.color }}
                  >
                    {audioStateDisplay.text}
                  </p>
                  <p className="text-sm text-slate-500">
                    {audioState === "listening"
                      ? "Microphone active"
                      : "Please wait..."}
                  </p>
                </div>
              </div>
            </div>

            {/* Audio Level Visualization */}
            {audioState === "listening" && (
              <div className="flex items-center justify-center">
                <div className="flex items-end gap-1 h-10">
                  {[...Array(20)].map((_, i) => (
                    <div
                      key={i}
                      className="w-1.5 rounded-full transition-all"
                      style={{
                        height: `${Math.max(
                          4,
                          audioLevel * 40 * (Math.sin(i * 0.5) + 1)
                        )}px`,
                        background: "linear-gradient(to top, #10B981, #34D399)",
                      }}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Transcript */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 h-[300px] overflow-y-auto shadow-lg">
              {messages.length === 0 ? (
                <div className="flex items-center justify-center h-full text-slate-400">
                  <Loader2 className="w-6 h-6 animate-spin mr-2" /> Waiting for
                  interviewer...
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex gap-3 ${
                        msg.role === "user" ? "flex-row-reverse" : ""
                      }`}
                    >
                      <div
                        className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                        style={{
                          background:
                            msg.role === "user"
                              ? "linear-gradient(135deg, #3B82F6, #1D4ED8)"
                              : "linear-gradient(135deg, #D95D39, #F97316)",
                        }}
                      >
                        {msg.role === "user" ? (
                          <User className="w-4 h-4 text-white" />
                        ) : (
                          <Bot className="w-4 h-4 text-white" />
                        )}
                      </div>
                      <div
                        className={`max-w-[80%] p-3 rounded-xl ${
                          msg.role === "user"
                            ? "bg-blue-50 text-blue-900"
                            : "bg-slate-50 text-slate-900"
                        }`}
                      >
                        <p className="text-sm">{msg.content}</p>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Controls */}
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={() => setIsMuted(!isMuted)}
                disabled={audioState !== "listening"}
                className={`w-14 h-14 rounded-full flex items-center justify-center transition-all shadow-lg ${
                  audioState !== "listening"
                    ? "bg-slate-200 cursor-not-allowed"
                    : isMuted
                    ? "bg-red-100 border-2 border-red-300"
                    : "bg-white border-2 border-green-400"
                }`}
              >
                {isMuted ? (
                  <MicOff className="w-6 h-6 text-red-600" />
                ) : (
                  <Mic
                    className={`w-6 h-6 ${
                      audioState === "listening"
                        ? "text-green-600"
                        : "text-slate-400"
                    }`}
                  />
                )}
              </button>
              <button
                onClick={endInterview}
                className="w-16 h-16 rounded-full flex items-center justify-center bg-gradient-to-br from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 transition-all shadow-lg"
              >
                <PhoneOff className="w-7 h-7 text-white" />
              </button>
            </div>
          </div>
        )}

        {/* Active Interview - Text Mode */}
        {isActive && mode === "text" && (
          <div className="space-y-6">
            {/* Messages */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 h-[400px] overflow-y-auto shadow-lg">
              {messages.length === 0 && isThinking && (
                <div className="flex items-center justify-center h-full text-slate-400">
                  <Loader2 className="w-6 h-6 animate-spin mr-2" /> AI is
                  preparing...
                </div>
              )}
              <div className="space-y-4">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex gap-3 ${
                      msg.role === "user" ? "flex-row-reverse" : ""
                    }`}
                  >
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                      style={{
                        background:
                          msg.role === "user"
                            ? "linear-gradient(135deg, #3B82F6, #1D4ED8)"
                            : "linear-gradient(135deg, #D95D39, #F97316)",
                      }}
                    >
                      {msg.role === "user" ? (
                        <User className="w-4 h-4 text-white" />
                      ) : (
                        <Bot className="w-4 h-4 text-white" />
                      )}
                    </div>
                    <div
                      className={`max-w-[80%] p-4 rounded-xl ${
                        msg.role === "user"
                          ? "bg-blue-50 text-blue-900"
                          : "bg-slate-50 text-slate-900"
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                ))}
                {isThinking && (
                  <div className="flex gap-3">
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center"
                      style={{
                        background: "linear-gradient(135deg, #D95D39, #F97316)",
                      }}
                    >
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                    <div className="px-4 py-3 bg-slate-100 rounded-xl">
                      <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Input */}
            <div className="flex gap-3">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                placeholder="Type your response..."
                disabled={isThinking}
                className="flex-1 px-4 py-3 rounded-xl border-2 border-slate-200 focus:outline-none focus:border-blue-500 disabled:bg-slate-100"
              />
              <button
                onClick={sendMessage}
                disabled={!inputMessage.trim() || isThinking}
                className="px-6 py-3 rounded-xl text-white font-medium flex items-center gap-2 disabled:opacity-50"
                style={{
                  background:
                    "linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)",
                }}
              >
                <Send className="w-5 h-5" />
              </button>
              <button
                onClick={endInterview}
                className="px-4 py-3 rounded-xl bg-red-100 text-red-600 hover:bg-red-200 transition-colors"
              >
                End
              </button>
            </div>
          </div>
        )}

        {/* Feedback Display */}
        {(feedback || selectedHistory) && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-lg">
              <h2 className="text-2xl font-bold text-slate-900 mb-6 flex items-center gap-3">
                <Bot className="w-7 h-7 text-orange-500" />
                Interview Feedback
              </h2>

              <div className="grid grid-cols-2 gap-6 mb-8">
                <div className="p-5 bg-slate-50 rounded-xl">
                  <span className="text-sm text-slate-500 block mb-1">
                    Score
                  </span>
                  <span className="text-4xl font-bold text-slate-900">
                    {(feedback || selectedHistory)?.score}
                    <span className="text-lg text-slate-400">/100</span>
                  </span>
                </div>
                <div className="p-5 bg-slate-50 rounded-xl">
                  <span className="text-sm text-slate-500 block mb-1">
                    Verdict
                  </span>
                  <span
                    className={`text-2xl font-bold ${
                      (feedback || selectedHistory)?.verdict
                        ?.toLowerCase()
                        .includes("hire")
                        ? "text-green-600"
                        : "text-orange-600"
                    }`}
                  >
                    {(feedback || selectedHistory)?.verdict}
                  </span>
                </div>
              </div>

              {(feedback || selectedHistory)?.summary && (
                <div className="mb-6">
                  <h3 className="font-semibold text-slate-900 mb-2">Summary</h3>
                  <p className="text-slate-600 bg-slate-50 p-4 rounded-xl">
                    {(feedback || selectedHistory)?.summary}
                  </p>
                </div>
              )}

              {(feedback || selectedHistory)?.strengths && (
                <div className="mb-6">
                  <h3 className="font-semibold text-green-700 mb-2">
                    ✓ Strengths
                  </h3>
                  <ul className="space-y-2">
                    {(feedback || selectedHistory)?.strengths?.map((s, i) => (
                      <li key={i} className="text-slate-600 flex gap-2">
                        <span className="text-green-500">•</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {(feedback || selectedHistory)?.improvements && (
                <div className="mb-6">
                  <h3 className="font-semibold text-orange-700 mb-2">
                    ↑ Areas to Improve
                  </h3>
                  <ul className="space-y-2">
                    {(feedback || selectedHistory)?.improvements?.map(
                      (s, i) => (
                        <li key={i} className="text-slate-600 flex gap-2">
                          <span className="text-orange-500">•</span>
                          {s}
                        </li>
                      )
                    )}
                  </ul>
                </div>
              )}

              {/* Roadmap Additions from Feedback Loop */}
              {(() => {
                const additions = (feedback || selectedHistory)?.roadmap_additions;
                return additions?.nodes && additions.nodes.length > 0 && (
                <div className="mb-8 p-5 bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl border border-emerald-200">
                  <h3 className="font-semibold text-emerald-700 mb-3 flex items-center gap-2">
                    <span className="text-lg">📚</span>
                    Added to Your Roadmap
                  </h3>
                  <p className="text-sm text-emerald-600 mb-4">
                    Based on your interview feedback, we&apos;ve added these learning blocks to help you improve:
                  </p>
                  <div className="space-y-3">
                    {(feedback || selectedHistory)?.roadmap_additions?.nodes.map((node, i) => (
                      <div
                        key={node.id || i}
                        className="bg-white rounded-lg p-4 border border-emerald-100 shadow-sm"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <h4 className="font-medium text-slate-800">{node.label}</h4>
                          <span
                            className={`px-2 py-1 rounded-full text-xs font-medium ${
                              node.priority === "high"
                                ? "bg-red-100 text-red-700"
                                : node.priority === "medium"
                                ? "bg-amber-100 text-amber-700"
                                : "bg-slate-100 text-slate-600"
                            }`}
                          >
                            {node.priority}
                          </span>
                        </div>
                        <p className="text-sm text-slate-600 mb-2">{node.description}</p>
                        <div className="flex items-center gap-4 text-xs text-slate-500">
                          <span className="flex items-center gap-1">
                            <span>⏱</span> {node.estimated_hours}h
                          </span>
                          <span className="flex items-center gap-1">
                            <span>📝</span> {node.type}
                          </span>
                        </div>
                        {node.resources && node.resources.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-emerald-100">
                            <p className="text-xs text-slate-500 mb-2">Resources:</p>
                            <div className="flex flex-wrap gap-2">
                              {node.resources.slice(0, 3).map((res, ri) => (
                                <a
                                  key={ri}
                                  href={res.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs px-2 py-1 bg-emerald-100 text-emerald-700 rounded hover:bg-emerald-200 transition-colors"
                                >
                                  {res.name}
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  <a
                    href="/roadmaps"
                    className="mt-4 inline-flex items-center gap-2 text-sm text-emerald-600 hover:text-emerald-700 font-medium"
                  >
                    View Full Roadmap →
                  </a>
                </div>
              );
              })()}

              <button
                onClick={() => {
                  setFeedback(null);
                  setSelectedHistory(null);
                  setMessages([]);
                }}
                className="w-full py-4 rounded-xl text-white font-medium transition-all hover:opacity-90 shadow-lg"
                style={{
                  background:
                    "linear-gradient(135deg, #D95D39 0%, #F97316 100%)",
                }}
              >
                Start New Interview
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
