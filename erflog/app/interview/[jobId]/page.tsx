"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useSession } from "@/lib/SessionContext";
import { useAuth } from "@/lib/AuthContext";
import Link from "next/link";
import {
  MessageCircle,
  Mic,
  MicOff,
  Bot,
  Briefcase,
  Building2,
  MapPin,
  Loader2,
  Send,
  Phone,
  PhoneOff,
  User,
  Volume2,
  AlertCircle,
  ArrowLeft,
  CheckCircle,
  Target,
  Clock,
  ExternalLink,
  History,
  ChevronRight,
  X,
} from "lucide-react";

const WS_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws") ||
  "ws://localhost:8000";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type InterviewMode = "voice" | "text";
type InterviewType = "TECHNICAL" | "HR";
type AudioState = "idle" | "thinking" | "speaking" | "listening";
type PageState = "loading" | "ready" | "active" | "processing" | "feedback";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface RoadmapNode {
  id: string;
  label: string;
  type: string;
  description: string;
  priority: string;
  estimated_hours: number;
  improvement_addressed?: string;
  resources?: Array<{ name: string; url: string; type?: string }>;
}

interface Feedback {
  score?: number;
  verdict?: string;
  summary?: string;
  strengths?: string[];
  improvements?: string[];
  interview_type?: string;
  roadmap_additions?: {
    nodes: RoadmapNode[];
    message: string;
    roadmap_id?: string;
  };
}

interface JobDetails {
  id: number;
  title: string;
  company: string;
  location?: string;
  description?: string;
  link?: string;
  score?: number;
}

interface InterviewHistoryItem {
  id: number;
  created_at: string;
  feedback_report: Feedback;
  job_id?: string;
  interview_type?: string;
}

export default function InterviewJobPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const { accessToken } = useSession();
  const { userMetadata } = useAuth();

  const jobId = params.jobId as string;
  const modeParam = searchParams.get("mode") as InterviewMode | null;
  const typeParam = searchParams.get("type") as InterviewType | null;

  const userId = userMetadata?.userId;

  // Page state
  const [pageState, setPageState] = useState<PageState>("loading");
  const [job, setJob] = useState<JobDetails | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Interview config
  const [mode, setMode] = useState<InterviewMode>(modeParam || "text");
  const [interviewType, setInterviewType] = useState<InterviewType>(typeParam || "TECHNICAL");

  // Interview state
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [currentStage, setCurrentStage] = useState("intro");
  const [currentTurn, setCurrentTurn] = useState(0);
  const [isThinking, setIsThinking] = useState(false);

  // Voice state
  const [audioState, setAudioState] = useState<AudioState>("idle");
  const [isMuted, setIsMuted] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);

  // History state
  const [history, setHistory] = useState<InterviewHistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [selectedHistoryItem, setSelectedHistoryItem] = useState<Feedback | null>(null);
  const [showHistory, setShowHistory] = useState(false);

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

  // Fetch job details
  useEffect(() => {
    const fetchJob = async () => {
      try {
        // Try to get from saved jobs first, then from jobs table
        const response = await fetch(`${API_URL}/api/jobs/${jobId}`);
        if (response.ok) {
          const data = await response.json();
          setJob(data);
          setPageState("ready");
        } else {
          // Fallback: create minimal job info
          setJob({
            id: parseInt(jobId),
            title: "Interview Session",
            company: "Company",
          });
          setPageState("ready");
        }
      } catch (e) {
        console.error("Error fetching job:", e);
        // Still allow interview with minimal info
        setJob({
          id: parseInt(jobId),
          title: "Interview Session",
          company: "Company",
        });
        setPageState("ready");
      }
    };

    if (jobId) {
      fetchJob();
    }
  }, [jobId]);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Fetch interview history
  useEffect(() => {
    if (!userId) {
      setIsLoadingHistory(false);
      return;
    }

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
  }, [userId, feedback]); // Re-fetch when feedback changes (new interview completed)

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
      } else {
        try {
          const data = JSON.parse(
            typeof event.data === "string"
              ? event.data
              : await event.data.text()
          );

          if (data.type === "event") {
            if (data.event === "audio_state") {
              setAudioState(data.state);
            } else if (data.event === "thinking") {
              setIsThinking(data.status === "start");
              if (data.status === "start") setAudioState("thinking");
            } else if (data.event === "stage_change") {
              setCurrentStage(data.stage);
              setCurrentTurn((prev) => prev + 1);
              // Auto-transition to processing when stage is "end"
              if (data.stage === "end") {
                setPageState("processing");
              }
            } else if (data.event === "processing") {
              // Backend is generating feedback/roadmap
              setPageState("processing");
            }
          } else if (data.type === "message") {
            setMessages((prev) => [
              ...prev,
              {
                id: `${data.role}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                role: data.role,
                content: data.content,
                timestamp: new Date(),
              },
            ]);
          } else if (data.type === "feedback") {
            setFeedback(data.data);
            setPageState("feedback");
            setIsConnected(false);
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
    if (!userId) {
      setError("Please login to start an interview");
      return;
    }

    setError(null);
    setMessages([]);
    setFeedback(null);
    setCurrentTurn(0);
    setCurrentStage("intro");
    setIsConnecting(true);
    setAudioState(mode === "voice" ? "thinking" : "idle");

    const wsPath =
      mode === "voice"
        ? `/ws/interview/${jobId}`
        : `/ws/interview/text/${jobId}`;

    try {
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
          setPageState("active");

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

          const updateLevel = () => {
            if (!analyserRef.current) return;
            const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
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
        };
      } else {
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
          setPageState("active");
        };

        ws.onmessage = handleMessage;
        ws.onerror = () => setError("Connection error");
        ws.onclose = () => {
          setIsConnected(false);
        };
      }
    } catch (e) {
      console.error("Start error:", e);
      setError(mode === "voice" ? "Failed to access microphone" : "Failed to connect");
      setIsConnecting(false);
    }
  }, [mode, jobId, accessToken, interviewType, handleMessage, isMuted, isConnected, userId]);

  // Send text message
  const sendMessage = useCallback(() => {
    if (!inputMessage.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

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
    setAudioState("idle");
  }, []);

  // Cleanup
  useEffect(() => {
    return () => endInterview();
  }, [endInterview]);

  // Get audio state display
  const getAudioStateDisplay = () => {
    switch (audioState) {
      case "thinking":
        return { icon: Loader2, text: "AI is thinking...", color: "#F59E0B", animate: true };
      case "speaking":
        return { icon: Volume2, text: "AI is speaking...", color: "#D95D39", animate: true };
      case "listening":
        return { icon: Mic, text: "Your turn - speak now!", color: "#10B981", animate: false };
      default:
        return { icon: Mic, text: "Ready", color: "#6B7280", animate: false };
    }
  };

  // =========================================================================
  // RENDER
  // =========================================================================

  // Loading state
  if (pageState === "loading") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-orange-100 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-orange-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading interview...</p>
        </div>
      </div>
    );
  }

  // Processing state - Generating feedback and roadmap
  if (pageState === "processing") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-orange-100 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-6">
          <div className="w-24 h-24 mx-auto mb-8 relative">
            {/* Outer ring */}
            <div className="absolute inset-0 rounded-full border-4 border-orange-200"></div>
            {/* Spinning progress */}
            <div
              className="absolute inset-0 rounded-full border-4 border-t-orange-500 border-r-transparent border-b-transparent border-l-transparent animate-spin"
              style={{ animationDuration: "1.5s" }}
            ></div>
            {/* Inner icon */}
            <div className="absolute inset-4 rounded-full bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center shadow-lg">
              <Bot className="w-8 h-8 text-white" />
            </div>
          </div>
          
          <h2 className="text-2xl font-bold text-gray-800 mb-3">
            Analyzing Your Interview
          </h2>
          <p className="text-gray-500 mb-8">
            Our AI is reviewing your responses and generating personalized feedback...
          </p>
          
          {/* Progress steps */}
          <div className="space-y-4 text-left bg-white rounded-2xl p-6 shadow-lg border border-orange-200">
            <div className="flex items-center gap-3 text-gray-700">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span>Interview completed</span>
            </div>
            <div className="flex items-center gap-3 text-gray-700">
              <Loader2 className="w-5 h-5 text-orange-500 animate-spin" />
              <span>Generating performance analysis...</span>
            </div>
            <div className="flex items-center gap-3 text-gray-400">
              <div className="w-5 h-5 rounded-full border-2 border-gray-300"></div>
              <span>Updating your learning roadmap</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Ready state - Show job details and start button
  if (pageState === "ready") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-orange-100">
        {/* Header */}
        <div className="bg-white/80 backdrop-blur-sm border-b border-orange-200 shadow-sm">
          <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
            <Link href="/jobs" className="inline-flex items-center gap-2 text-gray-600 hover:text-orange-600 transition-colors">
              <ArrowLeft className="w-4 h-4" />
              Back to Jobs
            </Link>
            <button
              onClick={() => setShowHistory(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-100 text-orange-600 hover:bg-orange-200 transition-colors font-medium"
            >
              <History className="w-4 h-4" />
              Past Interviews
              {history.length > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-orange-500 text-white text-xs">
                  {history.length}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* History Sidebar */}
        {showHistory && (
          <div className="fixed inset-0 z-50 flex">
            <div
              className="absolute inset-0 bg-black/30 backdrop-blur-sm"
              onClick={() => setShowHistory(false)}
            ></div>
            <div className="relative ml-auto w-96 max-w-full h-full bg-white shadow-2xl p-6 overflow-y-auto">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                  <History className="w-5 h-5 text-orange-500" />
                  Past Interviews
                </h2>
                <button
                  onClick={() => setShowHistory(false)}
                  className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>

              {isLoadingHistory ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
                </div>
              ) : history.length === 0 ? (
                <div className="text-center py-12">
                  <History className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No past interviews yet</p>
                  <p className="text-sm text-gray-400 mt-2">Complete your first interview to see history here</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {history.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => {
                        setSelectedHistoryItem(item.feedback_report);
                        setPageState("feedback");
                        setShowHistory(false);
                      }}
                      className="w-full p-4 rounded-xl border-2 border-gray-100 hover:border-orange-300 bg-white hover:bg-orange-50 transition-all text-left shadow-sm"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-500">
                          {new Date(item.created_at).toLocaleDateString()}
                        </span>
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-bold ${
                            (item.feedback_report?.score || 0) >= 70
                              ? "bg-green-100 text-green-600"
                              : (item.feedback_report?.score || 0) >= 50
                              ? "bg-amber-100 text-amber-600"
                              : "bg-red-100 text-red-600"
                          }`}
                        >
                          {item.feedback_report?.score || 0}%
                        </span>
                      </div>
                      <p className="text-gray-800 font-semibold">
                        {item.feedback_report?.verdict || "Interview"}
                      </p>
                      <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                        {item.feedback_report?.summary || "No summary available"}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="max-w-4xl mx-auto px-6 py-12">
          {/* Job Details Card */}
          <div className="bg-white rounded-2xl border border-orange-200 shadow-lg p-8 mb-8">
            <div className="flex items-start gap-6">
              <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center flex-shrink-0 shadow-lg">
                <Briefcase className="w-8 h-8 text-white" />
              </div>
              <div className="flex-1">
                <h1 className="text-2xl font-bold text-gray-800 mb-2">{job?.title}</h1>
                <div className="flex items-center gap-4 text-gray-500 mb-4">
                  <span className="flex items-center gap-1">
                    <Building2 className="w-4 h-4" />
                    {job?.company}
                  </span>
                  {job?.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="w-4 h-4" />
                      {job.location}
                    </span>
                  )}
                </div>
                {job?.description && (
                  <p className="text-gray-600 text-sm line-clamp-3">{job.description}</p>
                )}
              </div>
            </div>
          </div>

          {/* Interview Mode Selection */}
          <div className="bg-white rounded-2xl border border-orange-200 shadow-lg p-8 mb-8">
            <h2 className="text-lg font-bold text-gray-800 mb-6">Interview Settings</h2>
            
            {/* Mode Toggle */}
            <div className="mb-6">
              <label className="text-sm text-gray-500 mb-3 block font-medium">Interview Mode</label>
              <div className="flex gap-4">
                <button
                  onClick={() => setMode("text")}
                  className={`flex-1 flex items-center justify-center gap-3 px-6 py-4 rounded-xl font-semibold transition-all border-2 ${
                    mode === "text"
                      ? "bg-orange-500 text-white border-orange-500 shadow-lg"
                      : "bg-white text-gray-600 border-gray-200 hover:border-orange-300 hover:bg-orange-50"
                  }`}
                >
                  <MessageCircle className="w-5 h-5" />
                  Chat
                </button>
                <button
                  onClick={() => setMode("voice")}
                  className={`flex-1 flex items-center justify-center gap-3 px-6 py-4 rounded-xl font-semibold transition-all border-2 ${
                    mode === "voice"
                      ? "bg-orange-500 text-white border-orange-500 shadow-lg"
                      : "bg-white text-gray-600 border-gray-200 hover:border-orange-300 hover:bg-orange-50"
                  }`}
                >
                  <Mic className="w-5 h-5" />
                  Voice
                </button>
              </div>
            </div>

            {/* Type Toggle */}
            <div>
              <label className="text-sm text-gray-500 mb-3 block font-medium">Interview Type</label>
              <div className="flex gap-4">
                <button
                  onClick={() => setInterviewType("TECHNICAL")}
                  className={`flex-1 px-4 py-3 rounded-xl font-semibold transition-all border-2 ${
                    interviewType === "TECHNICAL"
                      ? "bg-gray-800 text-white border-gray-800"
                      : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                  }`}
                >
                  Technical
                </button>
                <button
                  onClick={() => setInterviewType("HR")}
                  className={`flex-1 px-4 py-3 rounded-xl font-semibold transition-all border-2 ${
                    interviewType === "HR"
                      ? "bg-gray-800 text-white border-gray-800"
                      : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                  }`}
                >
                  HR / Behavioral
                </button>
              </div>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-500" />
              <p className="text-red-600 flex-1">{error}</p>
              <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">✕</button>
            </div>
          )}

          {/* Start Button */}
          <button
            onClick={startInterview}
            disabled={isConnecting}
            className="w-full py-5 rounded-xl text-white font-bold text-lg flex items-center justify-center gap-3 transition-all hover:scale-[1.02] shadow-xl disabled:opacity-50 disabled:cursor-not-allowed bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600"
          >
            {isConnecting ? (
              <>
                <Loader2 className="w-6 h-6 animate-spin" />
                Connecting...
              </>
            ) : mode === "voice" ? (
              <>
                <Phone className="w-6 h-6" />
                Start Voice Interview
              </>
            ) : (
              <>
                <MessageCircle className="w-6 h-6" />
                Start Chat Interview
              </>
            )}
          </button>

          {/* Quick Stats */}
          {history.length > 0 && (
            <div className="mt-8 p-6 bg-orange-50 rounded-2xl border border-orange-200">
              <h3 className="text-sm font-semibold text-orange-600 mb-4 flex items-center gap-2">
                <History className="w-4 h-4" />
                Your Interview Stats
              </h3>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold text-gray-800">{history.length}</p>
                  <p className="text-xs text-gray-500">Total Interviews</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-800">
                    {Math.round(
                      history.reduce((acc, h) => acc + (h.feedback_report?.score || 0), 0) / history.length
                    )}%
                  </p>
                  <p className="text-xs text-gray-500">Avg Score</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-green-600">
                    {history.filter(h => h.feedback_report?.verdict?.toLowerCase().includes("hire")).length}
                  </p>
                  <p className="text-xs text-gray-500">Hire Verdicts</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Active interview state
  if (pageState === "active") {
    const audioStateDisplay = getAudioStateDisplay();
    const AudioStateIcon = audioStateDisplay.icon;

    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        {/* Header */}
        <div className="bg-slate-800/50 backdrop-blur-sm border-b border-slate-700 sticky top-0 z-10">
          <div className="max-w-4xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="font-bold text-white">{job?.title}</h1>
                  <p className="text-sm text-slate-400">{interviewType} • {mode === "voice" ? "Voice" : "Chat"}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm text-slate-400">Turn {currentTurn}</span>
                <span className="px-3 py-1 rounded-full text-xs font-medium bg-orange-500/20 text-orange-400">
                  {currentStage}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-6 py-8">
          {/* Voice Mode UI */}
          {mode === "voice" && (
            <div className="space-y-6">
              {/* Audio State Indicator */}
              <div
                className="p-6 rounded-2xl border-2"
                style={{
                  borderColor: audioStateDisplay.color,
                  backgroundColor: `${audioStateDisplay.color}15`,
                }}
              >
                <div className="flex items-center justify-center gap-4">
                  <div
                    className="w-16 h-16 rounded-full flex items-center justify-center shadow-lg"
                    style={{ backgroundColor: audioStateDisplay.color }}
                  >
                    <AudioStateIcon
                      className={`w-8 h-8 text-white ${audioStateDisplay.animate ? "animate-pulse" : ""}`}
                    />
                  </div>
                  <div>
                    <p className="text-2xl font-bold" style={{ color: audioStateDisplay.color }}>
                      {audioStateDisplay.text}
                    </p>
                    <p className="text-sm text-slate-400">
                      {audioState === "listening" ? "Microphone active" : "Please wait..."}
                    </p>
                  </div>
                </div>
              </div>

              {/* Audio Level */}
              {audioState === "listening" && (
                <div className="flex items-center justify-center">
                  <div className="flex items-end gap-1 h-10">
                    {[...Array(20)].map((_, i) => (
                      <div
                        key={i}
                        className="w-1.5 rounded-full transition-all"
                        style={{
                          height: `${Math.max(4, audioLevel * 40 * (Math.sin(i * 0.5) + 1))}px`,
                          background: "linear-gradient(to top, #10B981, #34D399)",
                        }}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Transcript */}
              <div className="bg-slate-800/50 rounded-2xl border border-slate-700 p-6 h-[300px] overflow-y-auto">
                {messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                    Waiting for interviewer...
                  </div>
                ) : (
                  <div className="space-y-4">
                    {messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                      >
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                          style={{
                            background: msg.role === "user"
                              ? "linear-gradient(135deg, #3B82F6, #6366F1)"
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
                              ? "bg-blue-500/20 text-blue-200"
                              : "bg-slate-700 text-slate-200"
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

              {/* Voice Controls */}
              <div className="flex items-center justify-center gap-4">
                <button
                  onClick={() => setIsMuted(!isMuted)}
                  disabled={audioState !== "listening"}
                  className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${
                    audioState !== "listening"
                      ? "bg-slate-700 cursor-not-allowed"
                      : isMuted
                      ? "bg-red-500/20 border-2 border-red-500"
                      : "bg-slate-700 border-2 border-green-500"
                  }`}
                >
                  {isMuted ? (
                    <MicOff className="w-6 h-6 text-red-400" />
                  ) : (
                    <Mic className={`w-6 h-6 ${audioState === "listening" ? "text-green-400" : "text-slate-400"}`} />
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

          {/* Text Mode UI */}
          {mode === "text" && (
            <div className="space-y-6">
              {/* Messages */}
              <div className="bg-slate-800/50 rounded-2xl border border-slate-700 p-6 h-[400px] overflow-y-auto">
                {messages.length === 0 && isThinking ? (
                  <div className="flex items-center justify-center h-full text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                    AI is preparing...
                  </div>
                ) : (
                  <div className="space-y-4">
                    {messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                      >
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                          style={{
                            background: msg.role === "user"
                              ? "linear-gradient(135deg, #3B82F6, #6366F1)"
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
                              ? "bg-blue-500/20 text-blue-200"
                              : "bg-slate-700 text-slate-200"
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
                          style={{ background: "linear-gradient(135deg, #D95D39, #F97316)" }}
                        >
                          <Bot className="w-4 h-4 text-white" />
                        </div>
                        <div className="px-4 py-3 bg-slate-700 rounded-xl">
                          <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                )}
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
                  className="flex-1 px-4 py-3 rounded-xl border border-slate-600 bg-slate-800 text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 disabled:opacity-50"
                />
                <button
                  onClick={sendMessage}
                  disabled={!inputMessage.trim() || isThinking}
                  className="px-6 py-3 rounded-xl text-white font-medium flex items-center gap-2 disabled:opacity-50 bg-gradient-to-r from-blue-500 to-indigo-600"
                >
                  <Send className="w-5 h-5" />
                </button>
                <button
                  onClick={endInterview}
                  className="px-4 py-3 rounded-xl bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
                >
                  End
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Feedback state
  if (pageState === "feedback" && (feedback || selectedHistoryItem)) {
    const displayFeedback = selectedHistoryItem || feedback;
    
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-orange-100">
        {/* History Sidebar */}
        {showHistory && (
          <div className="fixed inset-0 z-50 flex">
            {/* Backdrop */}
            <div
              className="absolute inset-0 bg-black/30 backdrop-blur-sm"
              onClick={() => setShowHistory(false)}
            ></div>
            {/* Sidebar */}
            <div className="relative ml-auto w-96 max-w-full h-full bg-white shadow-2xl p-6 overflow-y-auto">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                  <History className="w-5 h-5 text-orange-500" />
                  Past Interviews
                </h2>
                <button
                  onClick={() => setShowHistory(false)}
                  className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>

              {isLoadingHistory ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
                </div>
              ) : history.length === 0 ? (
                <div className="text-center py-12">
                  <History className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No past interviews yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {history.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => {
                        setSelectedHistoryItem(item.feedback_report);
                        setShowHistory(false);
                      }}
                      className={`w-full p-4 rounded-xl border-2 transition-all text-left shadow-sm ${
                        selectedHistoryItem === item.feedback_report
                          ? "bg-orange-50 border-orange-400"
                          : "bg-white border-gray-100 hover:border-orange-300"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-500">
                          {new Date(item.created_at).toLocaleDateString()}
                        </span>
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            (item.feedback_report?.score || 0) >= 70
                              ? "bg-green-100 text-green-600"
                              : (item.feedback_report?.score || 0) >= 50
                              ? "bg-amber-100 text-amber-600"
                              : "bg-red-100 text-red-600"
                          }`}
                        >
                          {item.feedback_report?.score || 0}%
                        </span>
                      </div>
                      <p className="text-gray-800 font-medium truncate">
                        {item.feedback_report?.verdict || "Interview"}
                      </p>
                      <p className="text-sm text-gray-500 truncate mt-1">
                        {item.feedback_report?.summary?.slice(0, 60)}...
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="max-w-4xl mx-auto px-6 py-12">
          {/* Header with History Button */}
          <div className="flex items-center justify-between mb-8">
            <Link
              href="/jobs"
              className="inline-flex items-center gap-2 text-gray-600 hover:text-orange-600 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Jobs
            </Link>
            <button
              onClick={() => setShowHistory(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-100 text-orange-600 hover:bg-orange-200 transition-colors font-medium"
            >
              <History className="w-4 h-4" />
              History
              {history.length > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-orange-500 text-white text-xs">
                  {history.length}
                </span>
              )}
            </button>
          </div>

          {/* Viewing History Notice */}
          {selectedHistoryItem && (
            <div className="mb-6 p-3 bg-orange-50 rounded-lg flex items-center justify-between border border-orange-200">
              <p className="text-sm text-gray-600">
                Viewing past interview result
              </p>
              <button
                onClick={() => setSelectedHistoryItem(null)}
                className="text-sm text-orange-600 hover:text-orange-700 font-medium"
              >
                View Latest →
              </button>
            </div>
          )}

          {/* Success Header */}
          <div className="text-center mb-12">
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center shadow-lg">
              <CheckCircle className="w-10 h-10 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-gray-800 mb-2">Interview Complete!</h1>
            <p className="text-gray-500">Here&apos;s your performance analysis</p>
          </div>

          {/* Score Card */}
          <div className="bg-white rounded-2xl border border-orange-200 shadow-lg p-8 mb-8">
            <div className="grid grid-cols-2 gap-6 mb-8">
              <div className="p-6 bg-orange-50 rounded-xl text-center border border-orange-200">
                <p className="text-sm text-gray-500 mb-2">Score</p>
                <p className="text-5xl font-bold text-gray-800">
                  {displayFeedback?.score}
                  <span className="text-xl text-gray-400">/100</span>
                </p>
              </div>
              <div className="p-6 bg-orange-50 rounded-xl text-center border border-orange-200">
                <p className="text-sm text-gray-500 mb-2">Verdict</p>
                <p className={`text-3xl font-bold ${
                  displayFeedback?.verdict?.toLowerCase().includes("hire") ? "text-green-600" : "text-orange-600"
                }`}>
                  {displayFeedback?.verdict}
                </p>
              </div>
            </div>

            {/* Summary */}
            {displayFeedback?.summary && (
              <div className="mb-6">
                <h3 className="font-semibold text-gray-800 mb-2">Summary</h3>
                <p className="text-gray-600 bg-gray-50 p-4 rounded-xl border border-gray-200">{displayFeedback?.summary}</p>
              </div>
            )}

            {/* Strengths */}
            {displayFeedback?.strengths && displayFeedback?.strengths.length > 0 && (
              <div className="mb-6">
                <h3 className="font-semibold text-green-600 mb-3 flex items-center gap-2">
                  <CheckCircle className="w-5 h-5" />
                  Strengths
                </h3>
                <ul className="space-y-2">
                  {displayFeedback?.strengths.map((s, i) => (
                    <li key={i} className="text-gray-700 flex gap-2">
                      <span className="text-green-500">•</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Improvements */}
            {displayFeedback?.improvements && displayFeedback?.improvements.length > 0 && (
              <div>
                <h3 className="font-semibold text-orange-600 mb-3 flex items-center gap-2">
                  <Target className="w-5 h-5" />
                  Areas to Improve
                </h3>
                <ul className="space-y-2">
                  {displayFeedback?.improvements.map((s, i) => (
                    <li key={i} className="text-gray-700 flex gap-2">
                      <span className="text-orange-500">•</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Roadmap Additions */}
          {displayFeedback?.roadmap_additions?.nodes && displayFeedback?.roadmap_additions.nodes.length > 0 && (
            <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-2xl border border-emerald-200 shadow-lg p-8 mb-8">
              <h2 className="text-xl font-bold text-emerald-600 mb-2 flex items-center gap-2">
                📚 Added to Your Learning Roadmap
              </h2>
              <p className="text-emerald-700/70 mb-6">
                Based on your interview feedback, we&apos;ve added these learning blocks to help you improve:
              </p>

              <div className="space-y-4">
                {displayFeedback?.roadmap_additions.nodes.map((node, i) => (
                  <div
                    key={node.id || i}
                    className="bg-white rounded-xl p-5 border border-emerald-200 shadow-sm"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <h4 className="font-semibold text-gray-800">{node.label}</h4>
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${
                          node.priority === "high"
                            ? "bg-red-100 text-red-600"
                            : node.priority === "medium"
                            ? "bg-amber-100 text-amber-600"
                            : "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {node.priority} priority
                      </span>
                    </div>
                    <p className="text-gray-600 text-sm mb-3">{node.description}</p>
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        {node.estimated_hours}h
                      </span>
                      <span className="capitalize">{node.type}</span>
                    </div>
                    {node.resources && node.resources.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <p className="text-xs text-gray-500 mb-2">Resources:</p>
                        <div className="flex flex-wrap gap-2">
                          {node.resources.map((res, ri) => (
                            <a
                              key={ri}
                              href={res.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-xs px-3 py-1.5 bg-emerald-100 text-emerald-600 rounded-lg hover:bg-emerald-200 transition-colors font-medium"
                            >
                              {res.name}
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <Link
                href="/roadmaps"
                className="mt-6 inline-flex items-center gap-2 text-emerald-600 hover:text-emerald-700 font-medium"
              >
                View Full Roadmap →
              </Link>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-4">
            <Link
              href="/jobs"
              className="flex-1 py-4 rounded-xl text-center font-semibold bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors border border-gray-300"
            >
              Back to Jobs
            </Link>
            <button
              onClick={() => {
                setFeedback(null);
                setSelectedHistoryItem(null);
                setMessages([]);
                setPageState("ready");
              }}
              className="flex-1 py-4 rounded-xl text-center font-semibold text-white bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 shadow-lg transition-all"
            >
              Practice Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
