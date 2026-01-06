"use client";

import { useState, useEffect, useRef, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useSession } from "@/lib/SessionContext";
import { useAuth } from "@/lib/AuthContext";
import {
  Mic,
  MicOff,
  Phone,
  PhoneOff,
  Loader2,
  Volume2,
  Bot,
  User,
  AlertCircle,
  Clock,
  ChevronRight,
  Briefcase,
  GraduationCap,
} from "lucide-react";

const WS_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws") ||
  "ws://localhost:8000";

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

interface TranscriptEntry {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: Date;
}

interface Feedback {
  score?: number;
  verdict?: string;
  summary?: string;
  strengths?: string[];
  improvements?: string[];
  interview_type?: string;
}

interface InterviewHistoryItem {
  id: number;
  created_at: string;
  feedback_report: Feedback;
  interview_type?: string;
}

const TECHNICAL_STAGES = ["intro", "resume", "challenge", "conclusion"];
const HR_STAGES = ["intro", "behavioral", "experience", "conclusion"];

function VoiceInterviewContent() {
  const searchParams = useSearchParams();
  const jobId = searchParams.get("jobId") || "1";
  const { session, accessToken, profile } = useSession();
  const { userMetadata } = useAuth();

  // Get user ID from auth context
  const userId = userMetadata.userId;

  const [interviewType, setInterviewType] =
    useState<InterviewType>("TECHNICAL");
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [audioState, setAudioState] = useState<AudioState>("idle");
  const [currentStage, setCurrentStage] = useState<InterviewStage>("intro");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [history, setHistory] = useState<InterviewHistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [jobTitle, setJobTitle] = useState<string>("");
  const [currentTurn, setCurrentTurn] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioQueueRef = useRef<Blob[]>([]);
  const isPlayingRef = useRef(false);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const audioStateRef = useRef<AudioState>("idle");

  // Keep ref in sync with state
  useEffect(() => {
    audioStateRef.current = audioState;
    console.log(`[Frontend] Audio State Changed: ${audioState}`);
  }, [audioState]);

  // Get stage progress
  const getStageProgress = () => {
    const stages = interviewType === "TECHNICAL" ? TECHNICAL_STAGES : HR_STAGES;
    const currentIdx = stages.indexOf(currentStage);
    return ((currentIdx + 1) / stages.length) * 100;
  };

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  // Fetch history using auth user ID
  useEffect(() => {
    if (!userId) return;

    const fetchHistory = async () => {
      try {
        const response = await fetch(
          `${
            process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
          }/api/interviews/${userId}`
        );
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

  // Play audio from queue - when audio finishes, set state to listening
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

      // When audio finishes playing, check if more in queue
      if (audioQueueRef.current.length > 0) {
        playNextAudio();
      } else {
        // No more audio, switch to listening
        console.log("[Frontend] Audio finished, switching to LISTENING");
        setAudioState("listening");
      }
    };

    audio.onerror = () => {
      URL.revokeObjectURL(audioUrl);
      isPlayingRef.current = false;
      setAudioState("listening");
      playNextAudio();
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
      if (event.data instanceof Blob) {
        // Audio data received - add to queue and play
        console.log("[Frontend] Received audio blob");
        audioQueueRef.current.push(event.data);
        playNextAudio();

        setTranscript((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && last.text === "AI is speaking...") {
            return prev;
          }
          return [
            ...prev,
            {
              id: `assistant-${Date.now()}`,
              role: "assistant",
              text: "AI is speaking...",
              timestamp: new Date(),
            },
          ];
        });
      } else {
        try {
          const data = JSON.parse(event.data);
          console.log("[Frontend] Received message:", data);

          if (data.type === "config") {
            setJobTitle(data.job_title || "");
          } else if (data.type === "event") {
            if (data.event === "audio_state") {
              // Backend telling us what state to be in
              console.log(`[Frontend] Backend audio_state: ${data.state}`);
              setAudioState(data.state);
            } else if (data.event === "thinking") {
              if (data.status === "start") {
                setAudioState("thinking");
              }
              // Don't set to listening here, wait for audio to finish
            } else if (data.event === "stage_change") {
              setCurrentStage(data.stage as InterviewStage);
              setCurrentTurn((prev) => prev + 1);
            }
          } else if (data.type === "feedback") {
            setFeedback(data.data);
          } else if (data.type === "error") {
            setError(data.message);
          }
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
        }
      }
    },
    [playNextAudio]
  );

  // Start WebSocket connection
  const startInterview = useCallback(async () => {
    setError(null);
    setTranscript([]);
    setCurrentTurn(0);
    setAudioState("thinking"); // Start in thinking state

    try {
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
      processorRef.current = processor;

      const ws = new WebSocket(`${WS_URL}/ws/interview/${jobId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[Frontend] WebSocket connected");

        // Send auth and config first
        ws.send(
          JSON.stringify({
            access_token: accessToken || "test",
            interview_type: interviewType,
            user_id: userId,
          })
        );

        setIsConnected(true);

        // CRITICAL: Only send audio when in LISTENING state
        processor.onaudioprocess = (e) => {
          // Only send audio if we're in listening state and not muted
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

        monitorAudioLevel();
      };

      ws.onmessage = handleMessage;

      ws.onerror = (e) => {
        console.error("WebSocket error:", e);
        setError("Connection error. Please try again.");
      };

      ws.onclose = () => {
        console.log("WebSocket closed");
        setIsConnected(false);
        setAudioState("idle");
      };
    } catch (e) {
      console.error("Failed to start interview:", e);
      setError("Failed to access microphone. Please grant permission.");
    }
  }, [handleMessage, accessToken, interviewType, jobId, isMuted]);

  // Monitor audio level
  const monitorAudioLevel = useCallback(() => {
    if (!analyserRef.current) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);

    const updateLevel = () => {
      if (!analyserRef.current) return;

      analyserRef.current.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
      setAudioLevel(average / 255);

      if (isConnected) {
        requestAnimationFrame(updateLevel);
      }
    };

    updateLevel();
  }, [isConnected]);

  // End interview
  const endInterview = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    setIsConnected(false);
    setAudioState("idle");
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      endInterview();
    };
  }, [endInterview]);

  // Toggle mute
  const toggleMute = useCallback(() => {
    setIsMuted((prev) => !prev);
  }, []);

  // Stage display info
  const getStageInfo = (stage: InterviewStage) => {
    const stages: Record<InterviewStage, { label: string; color: string }> = {
      intro: { label: "Introduction", color: "#10B981" },
      resume: { label: "Resume Deep-Dive", color: "#3B82F6" },
      behavioral: { label: "Behavioral Questions", color: "#8B5CF6" },
      experience: { label: "Experience & Motivation", color: "#F59E0B" },
      challenge: { label: "Technical Challenge", color: "#EF4444" },
      conclusion: { label: "Conclusion", color: "#D95D39" },
      end: { label: "Complete", color: "#6B7280" },
    };
    return stages[stage] || stages.intro;
  };

  const stageInfo = getStageInfo(currentStage);

  // Audio state display
  const getAudioStateDisplay = () => {
    switch (audioState) {
      case "thinking":
        return {
          icon: Loader2,
          text: "AI is thinking...",
          color: "#F59E0B",
          animate: true,
          bgColor: "bg-yellow-50",
        };
      case "speaking":
        return {
          icon: Volume2,
          text: "AI is speaking...",
          color: "#D95D39",
          animate: true,
          bgColor: "bg-orange-50",
        };
      case "listening":
        return {
          icon: Mic,
          text: "Your turn - speak now!",
          color: "#10B981",
          animate: false,
          bgColor: "bg-green-50",
        };
      default:
        return {
          icon: Mic,
          text: "Ready",
          color: "#6B7280",
          animate: false,
          bgColor: "bg-slate-50",
        };
    }
  };

  const audioStateDisplay = getAudioStateDisplay();
  const AudioStateIcon = audioStateDisplay.icon;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-orange-50 flex flex-col">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4">
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
                  Voice Interview
                </h1>
                <p className="text-sm text-slate-500">
                  {jobTitle ? `${jobTitle}` : `Job #${jobId}`} • {interviewType}
                </p>
              </div>
            </div>

            {/* Stage Badge */}
            <div className="flex items-center gap-3">
              {isConnected && (
                <span className="text-sm text-slate-500">
                  Turn {currentTurn}/6
                </span>
              )}
              <div
                className="px-4 py-2 rounded-full text-sm font-medium text-white shadow-md"
                style={{ backgroundColor: stageInfo.color }}
              >
                {stageInfo.label}
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          {isConnected && (
            <div className="mt-3 h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full transition-all duration-500 ease-out rounded-full"
                style={{
                  width: `${getStageProgress()}%`,
                  background:
                    "linear-gradient(90deg, #10B981, #3B82F6, #8B5CF6, #D95D39)",
                }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 max-w-4xl mx-auto w-full px-6 py-8">
        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 shadow-sm">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <p className="text-red-700 flex-1">{error}</p>
            <button
              onClick={() => setError(null)}
              className="text-red-500 hover:text-red-700 font-medium"
            >
              ✕
            </button>
          </div>
        )}

        {/* Not Connected State */}
        {!isConnected && !feedback && (
          <div className="flex flex-col items-center justify-center py-12">
            {/* Interview Type Toggle */}
            <div className="mb-8 bg-white rounded-2xl p-2 shadow-lg border border-slate-200">
              <div className="flex gap-2">
                <button
                  onClick={() => setInterviewType("TECHNICAL")}
                  className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
                    interviewType === "TECHNICAL"
                      ? "bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-md"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  <Briefcase className="w-4 h-4" />
                  Technical
                </button>
                <button
                  onClick={() => setInterviewType("HR")}
                  className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
                    interviewType === "HR"
                      ? "bg-gradient-to-r from-purple-500 to-pink-600 text-white shadow-md"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  <GraduationCap className="w-4 h-4" />
                  HR / Behavioral
                </button>
              </div>
            </div>

            <div
              className="w-28 h-28 rounded-full flex items-center justify-center mb-6 shadow-xl"
              style={{
                background: "linear-gradient(135deg, #FFF7ED 0%, #FED7AA 100%)",
              }}
            >
              <Mic className="w-14 h-14" style={{ color: "#D95D39" }} />
            </div>

            <h2 className="text-3xl font-bold text-slate-900 mb-3">
              Ready to Practice?
            </h2>
            <p className="text-slate-600 mb-8 text-center max-w-md">
              Start a voice interview session. The AI interviewer will ask you
              questions and provide real-time feedback.
            </p>

            <button
              onClick={startInterview}
              className="px-8 py-4 rounded-xl text-white font-medium flex items-center gap-3 transition-all hover:scale-105 shadow-lg hover:shadow-xl"
              style={{
                background: "linear-gradient(135deg, #D95D39 0%, #F97316 100%)",
              }}
            >
              <Phone className="w-5 h-5" />
              Start {interviewType} Interview
            </button>

            {/* History Section */}
            <div className="w-full max-w-2xl mt-16 pt-8 border-t border-slate-200">
              <h3 className="text-lg font-bold text-slate-900 mb-6 flex items-center gap-2">
                <Clock className="w-5 h-5 text-slate-400" />
                Past Sessions
              </h3>

              {isLoadingHistory ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                </div>
              ) : history.length === 0 ? (
                <div className="text-center py-8 bg-slate-50 rounded-xl border border-dashed border-slate-300">
                  <p className="text-slate-500">No past interviews found.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {history.slice(0, 5).map((item) => (
                    <button
                      key={item.id}
                      onClick={() => setFeedback(item.feedback_report)}
                      className="w-full bg-white p-4 rounded-xl border border-slate-200 hover:border-orange-300 hover:shadow-md transition-all flex items-center justify-between group text-left"
                    >
                      <div className="flex items-center gap-4">
                        <div
                          className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 font-bold ${
                            item.feedback_report?.verdict
                              ?.toLowerCase()
                              .includes("hire")
                              ? "bg-green-100 text-green-600"
                              : "bg-orange-100 text-orange-600"
                          }`}
                        >
                          {item.feedback_report?.score || "?"}
                        </div>
                        <div>
                          <div className="font-medium text-slate-900">
                            {new Date(item.created_at).toLocaleDateString(
                              undefined,
                              {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              }
                            )}
                          </div>
                          <div className="text-xs text-slate-500 flex items-center gap-1 mt-1">
                            <Clock className="w-3 h-3" />
                            {new Date(item.created_at).toLocaleTimeString(
                              undefined,
                              {
                                hour: "2-digit",
                                minute: "2-digit",
                              }
                            )}
                            {item.feedback_report?.interview_type && (
                              <span className="ml-2 px-2 py-0.5 bg-slate-100 rounded text-xs">
                                {item.feedback_report.interview_type}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-4">
                        <span
                          className={`text-sm font-medium px-3 py-1 rounded-full ${
                            item.feedback_report?.verdict
                              ?.toLowerCase()
                              .includes("hire")
                              ? "bg-green-50 text-green-700"
                              : "bg-orange-50 text-orange-700"
                          }`}
                        >
                          {item.feedback_report?.verdict || "Incomplete"}
                        </span>
                        <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-orange-500 transition-colors" />
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Feedback Display */}
        {feedback && (
          <div className="max-w-2xl mx-auto w-full">
            <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-lg">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-14 h-14 rounded-full bg-gradient-to-br from-green-400 to-emerald-600 flex items-center justify-center shadow-lg">
                  <Bot className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-slate-900">
                    Interview Feedback
                  </h2>
                  <p className="text-slate-500">Here's how you performed</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6 mb-8">
                <div className="p-5 bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl border border-slate-200">
                  <span className="text-sm text-slate-500 block mb-1">
                    Overall Score
                  </span>
                  <span className="text-4xl font-bold text-slate-900">
                    {feedback.score}
                    <span className="text-lg text-slate-400">/100</span>
                  </span>
                </div>
                <div className="p-5 bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl border border-slate-200">
                  <span className="text-sm text-slate-500 block mb-1">
                    Verdict
                  </span>
                  <span
                    className={`text-2xl font-bold ${
                      feedback.verdict?.toLowerCase().includes("hire")
                        ? "text-green-600"
                        : "text-orange-600"
                    }`}
                  >
                    {feedback.verdict}
                  </span>
                </div>
              </div>

              <div className="mb-6">
                <h3 className="font-semibold text-slate-900 mb-3">Summary</h3>
                <p className="text-slate-600 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-200">
                  {feedback.summary}
                </p>
              </div>

              {feedback.strengths && feedback.strengths.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-semibold text-green-700 mb-3">
                    ✓ Strengths
                  </h3>
                  <ul className="space-y-2">
                    {feedback.strengths.map((s, i) => (
                      <li
                        key={i}
                        className="text-slate-600 flex items-start gap-2"
                      >
                        <span className="text-green-500 mt-1">•</span> {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {feedback.improvements && feedback.improvements.length > 0 && (
                <div className="mb-8">
                  <h3 className="font-semibold text-orange-700 mb-3">
                    ↑ Areas to Improve
                  </h3>
                  <ul className="space-y-2">
                    {feedback.improvements.map((s, i) => (
                      <li
                        key={i}
                        className="text-slate-600 flex items-start gap-2"
                      >
                        <span className="text-orange-500 mt-1">•</span> {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <button
                onClick={() => {
                  setFeedback(null);
                  setTranscript([]);
                  setCurrentStage("intro");
                  setCurrentTurn(0);
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

        {/* Connected State */}
        {isConnected && !feedback && (
          <div className="space-y-6">
            {/* PROMINENT Audio State Indicator */}
            <div
              className={`p-6 rounded-2xl border-2 ${audioStateDisplay.bgColor} border-current shadow-lg`}
              style={{ borderColor: audioStateDisplay.color }}
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
                      ? "Microphone is active - speak clearly"
                      : audioState === "thinking"
                      ? "Please wait..."
                      : audioState === "speaking"
                      ? "Listen to the AI interviewer"
                      : "Connecting..."}
                  </p>
                </div>
              </div>
            </div>

            {/* Transcript */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 h-[300px] overflow-y-auto shadow-lg">
              <h3 className="text-sm font-semibold text-slate-500 mb-4 uppercase tracking-wide">
                Transcript
              </h3>

              {transcript.length === 0 && (
                <div className="flex items-center justify-center h-full text-slate-400">
                  <Loader2 className="w-6 h-6 animate-spin mr-2" />
                  Waiting for interviewer...
                </div>
              )}

              <div className="space-y-4">
                {transcript.map((entry) => (
                  <div
                    key={entry.id}
                    className={`flex gap-3 ${
                      entry.role === "user" ? "flex-row-reverse" : ""
                    }`}
                  >
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm"
                      style={{
                        background:
                          entry.role === "user"
                            ? "linear-gradient(135deg, #3B82F6, #1D4ED8)"
                            : "linear-gradient(135deg, #D95D39, #F97316)",
                      }}
                    >
                      {entry.role === "user" ? (
                        <User className="w-4 h-4 text-white" />
                      ) : (
                        <Bot className="w-4 h-4 text-white" />
                      )}
                    </div>
                    <div
                      className={`max-w-[80%] p-3 rounded-xl ${
                        entry.role === "user"
                          ? "bg-blue-50 text-blue-900"
                          : "bg-slate-50 text-slate-900"
                      }`}
                    >
                      <p className="text-sm">{entry.text}</p>
                      <p className="text-xs text-slate-400 mt-1">
                        {entry.timestamp.toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
                <div ref={transcriptEndRef} />
              </div>
            </div>

            {/* Audio Level Visualization - only show when listening */}
            {audioState === "listening" && (
              <div className="flex items-center justify-center">
                <div className="flex items-end gap-1 h-10">
                  {[...Array(20)].map((_, i) => (
                    <div
                      key={i}
                      className="w-1.5 rounded-full transition-all duration-75"
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

            {/* Controls */}
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={toggleMute}
                disabled={audioState !== "listening"}
                className={`w-16 h-16 rounded-full flex items-center justify-center transition-all shadow-lg ${
                  audioState !== "listening"
                    ? "bg-slate-200 cursor-not-allowed"
                    : isMuted
                    ? "bg-red-100 hover:bg-red-200 border-2 border-red-300"
                    : "bg-white hover:bg-slate-50 border-2 border-green-400"
                }`}
              >
                {isMuted ? (
                  <MicOff className="w-7 h-7 text-red-600" />
                ) : (
                  <Mic
                    className={`w-7 h-7 ${
                      audioState === "listening"
                        ? "text-green-600"
                        : "text-slate-400"
                    }`}
                  />
                )}
              </button>

              <button
                onClick={endInterview}
                className="w-20 h-20 rounded-full flex items-center justify-center bg-gradient-to-br from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 transition-all shadow-lg hover:shadow-xl"
              >
                <PhoneOff className="w-8 h-8 text-white" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function VoiceInterviewPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
        </div>
      }
    >
      <VoiceInterviewContent />
    </Suspense>
  );
}
