"use client";

import { useState, useEffect, useRef, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useSession } from "@/lib/SessionContext";
import { useAuth } from "@/lib/AuthContext";
import {
  Send,
  Loader2,
  Bot,
  User,
  AlertCircle,
  RotateCcw,
  Briefcase,
  GraduationCap,
  Clock,
  ChevronRight,
} from "lucide-react";

const WS_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws") ||
  "ws://localhost:8000";

type InterviewType = "TECHNICAL" | "HR";
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
}

interface InterviewHistoryItem {
  id: number;
  created_at: string;
  feedback_report: Feedback;
  interview_type?: string;
}

const TECHNICAL_STAGES = ["intro", "resume", "challenge", "conclusion"];
const HR_STAGES = ["intro", "behavioral", "experience", "conclusion"];

function TextInterviewContent() {
  const searchParams = useSearchParams();
  const jobId = searchParams.get("jobId") || "1";
  const { session, accessToken, profile } = useSession();
  const { userMetadata } = useAuth();

  // Get user ID from auth context
  const userId = userMetadata.userId;

  const [interviewType, setInterviewType] =
    useState<InterviewType>("TECHNICAL");
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [currentStage, setCurrentStage] = useState<InterviewStage>("intro");
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [jobTitle, setJobTitle] = useState<string>("");
  const [currentTurn, setCurrentTurn] = useState(0);
  const [history, setHistory] = useState<InterviewHistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Get stage progress
  const getStageProgress = () => {
    const stages = interviewType === "TECHNICAL" ? TECHNICAL_STAGES : HR_STAGES;
    const currentIdx = stages.indexOf(currentStage);
    return ((currentIdx + 1) / stages.length) * 100;
  };

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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

  // Handle WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === "config") {
        setJobTitle(data.job_title || "");
      } else if (data.type === "event") {
        if (data.event === "thinking") {
          setIsThinking(data.status === "start");
        } else if (data.event === "stage_change") {
          setCurrentStage(data.stage as InterviewStage);
          setCurrentTurn((prev) => prev + 1);
        }
      } else if (data.type === "message") {
        setMessages((prev) => [
          ...prev,
          {
            id: `${data.role}-${Date.now()}`,
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
      console.error("Failed to parse message:", e);
    }
  }, []);

  // Start WebSocket connection
  const startInterview = useCallback(() => {
    // Skip auth check since backend uses hardcoded user_id for now
    setError(null);
    setMessages([]);
    setFeedback(null);
    setIsConnecting(true);
    setCurrentTurn(0);

    const ws = new WebSocket(`${WS_URL}/ws/interview/text/${jobId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connected");

      // Send auth and config
      ws.send(
        JSON.stringify({
          access_token: accessToken,
          interview_type: interviewType,
          user_id: userId,
        })
      );

      setIsConnected(true);
      setIsConnecting(false);
    };

    ws.onmessage = handleMessage;

    ws.onerror = (e) => {
      console.error("WebSocket error:", e);
      setError("Connection error. Make sure the backend is running.");
      setIsConnecting(false);
    };

    ws.onclose = () => {
      console.log("WebSocket closed");
      setIsConnected(false);
      setIsConnecting(false);
    };
  }, [handleMessage, accessToken, interviewType, jobId]);

  // Send message
  const sendMessage = useCallback(() => {
    if (
      !inputMessage.trim() ||
      !wsRef.current ||
      wsRef.current.readyState !== WebSocket.OPEN
    )
      return;

    const msg = inputMessage.trim();
    setInputMessage("");

    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        role: "user",
        content: msg,
        timestamp: new Date(),
      },
    ]);

    wsRef.current.send(JSON.stringify({ message: msg }));
  }, [inputMessage]);

  // Handle Enter key
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Reset interview
  const resetInterview = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setMessages([]);
    setCurrentStage("intro");
    setFeedback(null);
    setError(null);
    setCurrentTurn(0);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Stage display info
  const getStageInfo = (stage: InterviewStage) => {
    const stages: Record<
      InterviewStage,
      { label: string; color: string; progress: number }
    > = {
      intro: { label: "Introduction", color: "#10B981", progress: 20 },
      resume: { label: "Resume Deep-Dive", color: "#3B82F6", progress: 40 },
      behavioral: {
        label: "Behavioral Questions",
        color: "#8B5CF6",
        progress: 40,
      },
      experience: {
        label: "Experience & Motivation",
        color: "#F59E0B",
        progress: 60,
      },
      challenge: {
        label: "Technical Challenge",
        color: "#EF4444",
        progress: 70,
      },
      conclusion: { label: "Wrapping Up", color: "#D95D39", progress: 90 },
      end: { label: "Complete ✓", color: "#6B7280", progress: 100 },
    };
    return stages[stage] || stages.intro;
  };

  const stageInfo = getStageInfo(currentStage);

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
                  AI Interview (Text)
                </h1>
                <p className="text-sm text-slate-500">
                  {jobTitle ? `${jobTitle}` : `Job #${jobId}`} • {interviewType}
                </p>
              </div>
            </div>

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

              {isConnected && (
                <button
                  onClick={resetInterview}
                  className="p-2.5 rounded-xl hover:bg-slate-100 transition-colors border border-slate-200"
                  title="Reset Interview"
                >
                  <RotateCcw className="w-5 h-5 text-slate-600" />
                </button>
              )}
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
      <div className="flex-1 max-w-4xl mx-auto w-full px-6 py-8 flex flex-col">
        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 shadow-sm">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
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
        {!isConnected && !isConnecting && !feedback && (
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
              <Bot className="w-14 h-14" style={{ color: "#D95D39" }} />
            </div>

            <h2 className="text-3xl font-bold text-slate-900 mb-3">
              Ready to Practice?
            </h2>
            <p className="text-slate-600 mb-8 text-center max-w-md">
              Start a text-based interview session. The AI interviewer will ask
              you questions based on your profile and the job requirements.
            </p>

            {!session ? (
              <div className="text-center">
                <p className="text-slate-500 mb-4">
                  Please login to start an interview
                </p>
                <a
                  href="/login"
                  className="px-8 py-4 rounded-xl text-white font-medium flex items-center gap-3 transition-all hover:scale-105 shadow-lg"
                  style={{
                    background:
                      "linear-gradient(135deg, #D95D39 0%, #F97316 100%)",
                  }}
                >
                  Login to Continue
                </a>
              </div>
            ) : (
              <button
                onClick={startInterview}
                className="px-8 py-4 rounded-xl text-white font-medium flex items-center gap-3 transition-all hover:scale-105 shadow-lg hover:shadow-xl"
                style={{
                  background:
                    "linear-gradient(135deg, #D95D39 0%, #F97316 100%)",
                }}
              >
                <Bot className="w-5 h-5" />
                Start {interviewType} Interview
              </button>
            )}

            {/* History Section */}
            {session && (
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
            )}
          </div>
        )}

        {/* Connecting State */}
        {isConnecting && (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2
              className="w-12 h-12 animate-spin mb-4"
              style={{ color: "#D95D39" }}
            />
            <p className="text-slate-500">Connecting to interviewer...</p>
          </div>
        )}

        {/* Feedback Display */}
        {feedback && !isConnected && (
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
                  setMessages([]);
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
        {isConnected && (
          <>
            {/* Messages */}
            <div
              className="flex-1 bg-white rounded-2xl border border-slate-200 p-6 overflow-y-auto mb-4 shadow-lg"
              style={{ minHeight: "400px", maxHeight: "500px" }}
            >
              {messages.length === 0 && (
                <div className="flex items-center justify-center h-full text-slate-400">
                  <Loader2 className="w-6 h-6 animate-spin mr-2" />
                  Waiting for interviewer...
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
                      className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm"
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
                      className={`max-w-[80%] p-4 rounded-2xl ${
                        msg.role === "user"
                          ? "bg-blue-50 text-blue-900"
                          : "bg-slate-50 text-slate-900"
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">
                        {msg.content}
                      </p>
                      <p className="text-xs text-slate-400 mt-2">
                        {msg.timestamp.toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}

                {/* Thinking indicator */}
                {isThinking && (
                  <div className="flex gap-3">
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center shadow-sm"
                      style={{
                        background: "linear-gradient(135deg, #D95D39, #F97316)",
                      }}
                    >
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                    <div className="bg-slate-50 p-4 rounded-2xl">
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin text-slate-500" />
                        <span className="text-sm text-slate-500">
                          Thinking...
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Inline Feedback Display */}
            {feedback && (
              <div className="mb-4 p-5 bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-xl shadow-sm">
                <h3 className="font-semibold text-green-800 mb-3">
                  🎉 Interview Complete!
                </h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  {feedback.score !== undefined && (
                    <div>
                      <span className="text-green-700">Score:</span>{" "}
                      <span className="font-bold text-lg">
                        {feedback.score}/100
                      </span>
                    </div>
                  )}
                  {feedback.verdict && (
                    <div>
                      <span className="text-green-700">Verdict:</span>{" "}
                      <span className="font-bold">{feedback.verdict}</span>
                    </div>
                  )}
                  {feedback.summary && (
                    <div className="col-span-2 mt-2 p-3 bg-white rounded-lg">
                      <span className="text-green-700 font-medium">
                        Summary:
                      </span>{" "}
                      <span className="text-slate-700">{feedback.summary}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Input Area */}
            <div className="bg-white rounded-2xl border border-slate-200 p-4 flex gap-3 shadow-lg">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your response..."
                disabled={isThinking || currentStage === "end"}
                className="flex-1 px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent disabled:bg-slate-50 disabled:text-slate-400 transition-all"
              />
              <button
                onClick={sendMessage}
                disabled={
                  !inputMessage.trim() || isThinking || currentStage === "end"
                }
                className="px-6 py-3 rounded-xl text-white font-medium flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg"
                style={{
                  background:
                    "linear-gradient(135deg, #D95D39 0%, #F97316 100%)",
                }}
              >
                <Send className="w-4 h-4" />
                Send
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function TextInterviewPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
        </div>
      }
    >
      <TextInterviewContent />
    </Suspense>
  );
}
