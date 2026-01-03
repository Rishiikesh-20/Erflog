"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { supabase } from "@/lib/supabase";
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
  Calendar,
  ChevronRight,
} from "lucide-react";

// Hardcoded for testing
const JOB_ID = "1";
const USER_ID = "9f3eef8e-635b-46cc-a088-affae97c9a2b";
const WS_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws") ||
  "ws://localhost:8000";

type InterviewStage = "intro" | "resume" | "challenge" | "conclusion" | "end";

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
}

interface InterviewHistoryItem {
  id: number;
  created_at: string;
  feedback_report: Feedback;
}

export default function VoiceInterviewPage() {
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [currentStage, setCurrentStage] = useState<InterviewStage>("intro");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [history, setHistory] = useState<InterviewHistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioQueueRef = useRef<Blob[]>([]);
  const isPlayingRef = useRef(false);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  // Fetch history
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        // Use backend API instead of direct Supabase call to bypass RLS
        const response = await fetch(
          `${
            process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
          }/api/interviews/${USER_ID}`
        );
        if (!response.ok) throw new Error("Failed to fetch history");

        const data = await response.json();
        setHistory(data || []);
      } catch (e) {
        console.error("Error fetching history:", e);
      } finally {
        setIsLoadingHistory(false);
      }
    };

    fetchHistory();
  }, [feedback]); // Refresh when new feedback is added

  // Play audio from queue
  const playNextAudio = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;

    isPlayingRef.current = true;
    setIsSpeaking(true);

    const audioBlob = audioQueueRef.current.shift()!;
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);

    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      isPlayingRef.current = false;
      setIsSpeaking(false);
      playNextAudio(); // Play next in queue
    };

    audio.onerror = () => {
      URL.revokeObjectURL(audioUrl);
      isPlayingRef.current = false;
      setIsSpeaking(false);
      playNextAudio();
    };

    try {
      await audio.play();
    } catch (e) {
      console.error("Audio play error:", e);
      isPlayingRef.current = false;
      setIsSpeaking(false);
    }
  }, []);

  // Handle WebSocket messages
  const handleMessage = useCallback(
    async (event: MessageEvent) => {
      if (event.data instanceof Blob) {
        // Audio data from TTS
        audioQueueRef.current.push(event.data);
        playNextAudio();

        // Add assistant message placeholder (actual text comes from thinking status)
        setTranscript((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && last.text === "...") {
            return prev; // Already has placeholder
          }
          return [
            ...prev,
            {
              id: `assistant-${Date.now()}`,
              role: "assistant",
              text: "Speaking...",
              timestamp: new Date(),
            },
          ];
        });
      } else {
        // JSON event
        try {
          const data = JSON.parse(event.data);

          if (data.type === "event") {
            if (data.event === "thinking") {
              setIsThinking(data.status === "start");
            } else if (data.event === "stage_change") {
              setCurrentStage(data.stage as InterviewStage);

              if (data.stage === "end" || data.stage === "save_and_end") {
                // Interview complete
                setTranscript((prev) => [
                  ...prev,
                  {
                    id: `system-${Date.now()}`,
                    role: "assistant",
                    text: "Interview completed. Thank you!",
                    timestamp: new Date(),
                  },
                ]);
              }
            }
          } else if (data.type === "feedback") {
            setFeedback(data.data);
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

    try {
      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;

      // Setup audio context for processing raw PCM
      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      // Create analyser for level visualization
      analyserRef.current = audioContext.createAnalyser();
      analyserRef.current.fftSize = 256;

      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyserRef.current);

      // Create ScriptProcessor to capture raw PCM audio
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      source.connect(processor);
      processor.connect(audioContext.destination);

      // Store processor reference for cleanup
      (audioContextRef.current as any).processor = processor;

      // Connect WebSocket
      const ws = new WebSocket(`${WS_URL}/ws/interview/${JOB_ID}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected");
        setIsConnected(true);
        setIsRecording(true);

        // Start sending audio when processor receives data
        processor.onaudioprocess = (e) => {
          if (ws.readyState === WebSocket.OPEN) {
            const inputData = e.inputBuffer.getChannelData(0);
            // Convert Float32 to Int16 PCM
            const pcmData = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
              const s = Math.max(-1, Math.min(1, inputData[i]));
              pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
            }
            ws.send(pcmData.buffer);
          }
        };

        // Start audio level monitoring
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
        setIsRecording(false);
      };
    } catch (e) {
      console.error("Failed to start interview:", e);
      setError("Failed to access microphone. Please grant permission.");
    }
  }, [handleMessage]);

  // Monitor audio level for visualization
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

  // Stop recording
  const stopRecording = useCallback(() => {
    setIsRecording(false);
  }, []);

  // End interview
  const endInterview = useCallback(() => {
    stopRecording();

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
  }, [stopRecording]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      endInterview();
    };
  }, [endInterview]);

  // Toggle mute
  const toggleMute = useCallback(() => {
    if (streamRef.current) {
      const audioTrack = streamRef.current.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setIsRecording(audioTrack.enabled);
      }
    }
  }, []);

  // Stage display info
  const getStageInfo = (stage: InterviewStage) => {
    const stages: Record<InterviewStage, { label: string; color: string }> = {
      intro: { label: "Introduction", color: "#10B981" },
      resume: { label: "Resume Deep-Dive", color: "#3B82F6" },
      challenge: { label: "Challenging Questions", color: "#8B5CF6" },
      conclusion: { label: "Conclusion", color: "#D95D39" },
      end: { label: "Complete", color: "#6B7280" },
    };
    return stages[stage] || stages.intro;
  };

  const stageInfo = getStageInfo(currentStage);

  return (
    <div className="min-h-screen bg-canvas flex flex-col">
      {/* Header */}
      <div className="bg-white border-b" style={{ borderColor: "#E5E0D8" }}>
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center"
                style={{ backgroundColor: "#D95D39" }}
              >
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="font-serif-bold text-xl text-ink">
                  Voice Interview
                </h1>
                <p className="text-sm text-secondary">
                  Job ID: {JOB_ID} | User: {USER_ID.slice(0, 8)}...
                </p>
              </div>
            </div>

            {/* Stage Badge */}
            <div
              className="px-4 py-2 rounded-full text-sm font-medium text-white"
              style={{ backgroundColor: stageInfo.color }}
            >
              {stageInfo.label}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 max-w-4xl mx-auto w-full px-6 py-8">
        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <p className="text-red-700">{error}</p>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-red-500 hover:text-red-700"
            >
              ✕
            </button>
          </div>
        )}

        {/* Not Connected State */}
        {!isConnected && !feedback && (
          <div className="flex flex-col items-center justify-center py-20">
            <div
              className="w-24 h-24 rounded-full flex items-center justify-center mb-6"
              style={{ backgroundColor: "#F0EFE9" }}
            >
              <Mic className="w-12 h-12" style={{ color: "#D95D39" }} />
            </div>
            <h2 className="text-2xl font-serif-bold text-ink mb-2">
              Ready to Practice?
            </h2>
            <p className="text-secondary mb-8 text-center max-w-md">
              Start a voice interview session. The AI interviewer will ask you
              questions and provide real-time feedback.
            </p>
            <button
              onClick={startInterview}
              className="px-8 py-4 rounded-xl text-white font-medium flex items-center gap-3 transition-all hover:scale-105"
              style={{ backgroundColor: "#D95D39" }}
            >
              <Phone className="w-5 h-5" />
              Start Interview
            </button>

            {/* History Section */}
            <div
              className="w-full max-w-2xl mt-16 border-t pt-8"
              style={{ borderColor: "#E5E0D8" }}
            >
              <h3 className="text-lg font-serif-bold text-ink mb-6 flex items-center gap-2">
                <Clock className="w-5 h-5 text-secondary" />
                Past Sessions
              </h3>

              {isLoadingHistory ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-secondary" />
                </div>
              ) : history.length === 0 ? (
                <div className="text-center py-8 bg-gray-50 rounded-xl border border-dashed border-gray-200">
                  <p className="text-secondary">No past interviews found.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {history.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => setFeedback(item.feedback_report)}
                      className="w-full bg-white p-4 rounded-xl border hover:border-orange-300 hover:shadow-sm transition-all flex items-center justify-between group text-left"
                      style={{ borderColor: "#E5E0D8" }}
                    >
                      <div className="flex items-center gap-4">
                        <div
                          className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ${
                            item.feedback_report?.verdict
                              ?.toLowerCase()
                              .includes("hire")
                              ? "bg-green-100 text-green-600"
                              : "bg-orange-100 text-orange-600"
                          }`}
                        >
                          <span className="font-bold text-sm">
                            {item.feedback_report?.score || "?"}
                          </span>
                        </div>
                        <div>
                          <div className="font-medium text-ink flex items-center gap-2">
                            {new Date(item.created_at).toLocaleDateString(
                              undefined,
                              {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              }
                            )}
                          </div>
                          <div className="text-xs text-secondary flex items-center gap-1 mt-1">
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
                        <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-orange-500 transition-colors" />
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
            <div
              className="bg-white rounded-xl border p-8 shadow-sm"
              style={{ borderColor: "#E5E0D8" }}
            >
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                  <Bot className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <h2 className="text-2xl font-serif-bold text-ink">
                    Interview Feedback
                  </h2>
                  <p className="text-secondary">Here is how you performed</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6 mb-8">
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                  <span className="text-sm text-gray-500 block mb-1">
                    Overall Score
                  </span>
                  <span className="text-3xl font-bold text-ink">
                    {feedback.score}/100
                  </span>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                  <span className="text-sm text-gray-500 block mb-1">
                    Verdict
                  </span>
                  <span
                    className={`text-xl font-bold ${
                      feedback.verdict?.toLowerCase().includes("hire")
                        ? "text-green-600"
                        : "text-orange-600"
                    }`}
                  >
                    {feedback.verdict}
                  </span>
                </div>
              </div>

              <div className="mb-8">
                <h3 className="font-medium text-ink mb-3">Summary</h3>
                <p className="text-gray-600 leading-relaxed bg-gray-50 p-4 rounded-lg border border-gray-100">
                  {feedback.summary}
                </p>
              </div>

              <button
                onClick={() => {
                  setFeedback(null);
                  setTranscript([]);
                  setCurrentStage("intro");
                }}
                className="w-full py-3 rounded-lg text-white font-medium transition-all hover:opacity-90"
                style={{ backgroundColor: "#D95D39" }}
              >
                Start New Interview
              </button>
            </div>
          </div>
        )}
        {/* Connected State */}
        {isConnected && !feedback && (
          <div className="space-y-6">
            {/* Transcript */}
            <div
              className="bg-white rounded-xl border p-6 h-[400px] overflow-y-auto"
              style={{ borderColor: "#E5E0D8" }}
            >
              <h3 className="text-sm font-medium text-secondary mb-4">
                Transcript
              </h3>

              {transcript.length === 0 && (
                <div className="flex items-center justify-center h-full text-secondary">
                  <Loader2 className="w-6 h-6 animate-spin mr-2" />
                  Connecting to interviewer...
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
                      className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                      style={{
                        backgroundColor:
                          entry.role === "user" ? "#3B82F6" : "#D95D39",
                      }}
                    >
                      {entry.role === "user" ? (
                        <User className="w-4 h-4 text-white" />
                      ) : (
                        <Bot className="w-4 h-4 text-white" />
                      )}
                    </div>
                    <div
                      className={`max-w-[80%] p-3 rounded-lg ${
                        entry.role === "user"
                          ? "bg-blue-50 text-blue-900"
                          : "bg-gray-50 text-gray-900"
                      }`}
                    >
                      <p className="text-sm">{entry.text}</p>
                      <p className="text-xs text-gray-400 mt-1">
                        {entry.timestamp.toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
                <div ref={transcriptEndRef} />
              </div>
            </div>

            {/* Status Indicators */}
            <div className="flex items-center justify-center gap-6">
              {/* Thinking Indicator */}
              {isThinking && (
                <div className="flex items-center gap-2 text-secondary">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span className="text-sm">AI is thinking...</span>
                </div>
              )}

              {/* Speaking Indicator */}
              {isSpeaking && (
                <div className="flex items-center gap-2 text-secondary">
                  <Volume2
                    className="w-5 h-5 animate-pulse"
                    style={{ color: "#D95D39" }}
                  />
                  <span className="text-sm">AI is speaking...</span>
                </div>
              )}

              {/* Recording Indicator */}
              {isRecording && !isThinking && !isSpeaking && (
                <div className="flex items-center gap-2 text-secondary">
                  <div
                    className="w-3 h-3 rounded-full animate-pulse"
                    style={{ backgroundColor: "#EF4444" }}
                  />
                  <span className="text-sm">Listening...</span>
                </div>
              )}
            </div>

            {/* Audio Level Visualization */}
            <div className="flex items-center justify-center">
              <div className="flex items-end gap-1 h-8">
                {[...Array(20)].map((_, i) => (
                  <div
                    key={i}
                    className="w-1 rounded-full transition-all duration-75"
                    style={{
                      height: `${Math.max(
                        4,
                        audioLevel * 32 * (Math.sin(i * 0.5) + 1)
                      )}px`,
                      backgroundColor: isRecording ? "#D95D39" : "#E5E0D8",
                    }}
                  />
                ))}
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center justify-center gap-4">
              {/* Mute Button */}
              <button
                onClick={toggleMute}
                className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${
                  isRecording
                    ? "bg-gray-100 hover:bg-gray-200"
                    : "bg-red-100 hover:bg-red-200"
                }`}
              >
                {isRecording ? (
                  <Mic className="w-6 h-6 text-gray-700" />
                ) : (
                  <MicOff className="w-6 h-6 text-red-600" />
                )}
              </button>

              {/* End Call Button */}
              <button
                onClick={endInterview}
                className="w-16 h-16 rounded-full flex items-center justify-center bg-red-500 hover:bg-red-600 transition-all"
              >
                <PhoneOff className="w-7 h-7 text-white" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
