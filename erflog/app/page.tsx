"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import DropZone from "@/components/DropZone";
import AgentTerminal, { AgentLog } from "@/components/AgentTerminal";
import { Sparkles, AlertCircle, Github } from "lucide-react";
import { useSession } from "@/lib/SessionContext";

export default function Nexus() {
  const router = useRouter();
  const {
    initialize,
    uploadUserResume, // NOTE: You need to update your SessionContext to accept githubUrl
    isLoading,
    error,
    clearError,
    profile,
    sessionId,
    checkHealth,
    isApiHealthy,
  } = useSession();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [agentLogs, setAgentLogs] = useState<AgentLog[]>([]);
  const [processingError, setProcessingError] = useState<string | null>(null);

  // Check API health on mount (run only once)
  useEffect(() => {
    checkHealth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFileSelect = async (file: File) => {
    setSelectedFile(file);
    setIsProcessing(true);
    setProcessingError(null);
    clearError();

    // Start with initial logs
    setAgentLogs([
      {
        id: "1",
        message: "Handshake Initiated...",
        type: "system",
        delay: 100,
      },
    ]);

    try {
      // Step 1: Initialize session
      setAgentLogs((prev) => [
        ...prev,
        {
          id: "2",
          agent: "System",
          message: "Initializing session...",
          type: "agent",
          delay: 200,
        },
      ]);

      const newSessionId = await initialize();

      if (!newSessionId) {
        throw new Error("Failed to initialize session");
      }

      setAgentLogs((prev) => [
        ...prev,
        {
          id: "3",
          message: `Session created: ${newSessionId.substring(0, 8)}...`,
          type: "status",
          delay: 300,
        },
      ]);

      // Step 2: Upload resume & GitHub Link
      setAgentLogs((prev) => [
        ...prev,
        {
          id: "4",
          agent: "Agent 1 (Perception)",
          message: "Ingesting PDF Blob...",
          type: "agent",
          delay: 400,
        },
      ]);

      // Log GitHub Watchdog if URL is present
      if (githubUrl) {
        setAgentLogs((prev) => [
          ...prev,
          {
            id: "4b",
            agent: "Digital Twin Watchdog",
            message: `Scanning Codebase: ${githubUrl.split('/').slice(-2).join('/')}...`,
            type: "agent",
            delay: 500,
          },
        ]);
      }

      setAgentLogs((prev) => [
        ...prev,
        {
          id: "5",
          agent: "Agent 1",
          message: "Extracting Semantic Layers...",
          type: "agent",
          delay: 600,
        },
      ]);

      // Pass githubUrl to the context function
      // NOTE: Ensure your SessionContext's uploadUserResume accepts this second argument
      const uploadSuccess = await uploadUserResume(file, newSessionId, githubUrl);

      if (!uploadSuccess) {
        throw new Error("Failed to process resume");
      }

      setAgentLogs((prev) => [
        ...prev,
        {
          id: "6",
          agent: "Agent 1",
          message: "Vectorizing User Skills (768 dimensions)...",
          type: "agent",
          delay: 800,
        },
      ]);
      
      if (githubUrl) {
         setAgentLogs((prev) => [
        ...prev,
        {
          id: "6b",
          agent: "Agent 1",
          message: "Merging GitHub Analysis with Resume Vector...",
          type: "success",
          delay: 900,
        },
      ]);
      }

      setAgentLogs((prev) => [
        ...prev,
        {
          id: "7",
          message: "Skill Graph Constructed.",
          type: "status",
          delay: 1000,
        },
      ]);

      setAgentLogs((prev) => [
        ...prev,
        {
          id: "8",
          message: "Identity Archetype Created.",
          type: "success",
          delay: 1200,
        },
      ]);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "An error occurred";
      setProcessingError(errorMessage);
      setAgentLogs((prev) => [
        ...prev,
        {
          id: "error",
          message: `Error: ${errorMessage}`,
          type: "system",
          delay: 500,
        },
      ]);
    }
  };

  const handleAgentComplete = () => {
    // Only navigate if processing was successful
    if (!processingError && profile) {
      setTimeout(() => {
        router.push("/dashboard");
      }, 500);
    }
  };

  const handleRetry = () => {
    setIsProcessing(false);
    setSelectedFile(null);
    setAgentLogs([]);
    setProcessingError(null);
    clearError();
  };

  return (
    <div className="min-h-screen bg-canvas py-16 px-8 flex flex-col items-center justify-center">
      {/* API Health Warning */}
      {!isApiHealthy && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-lg bg-amber-100 border border-amber-300 text-amber-800"
        >
          <AlertCircle className="w-5 h-5" />
          <span className="text-sm font-medium">
            API server may be unavailable
          </span>
        </motion.div>
      )}

      <AnimatePresence mode="wait">
        {!isProcessing ? (
          <motion.div
            key="upload"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5 }}
            className="w-full max-w-2xl"
          >
            {/* Hero Section */}
            <section className="mb-12 text-center">
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.6 }}
              >
                <div className="flex items-center justify-center gap-3 mb-6">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center"
                    style={{ backgroundColor: "#D95D39" }}
                  >
                    <Sparkles className="w-6 h-6 text-white" />
                  </div>
                </div>
                <h1 className="font-serif-bold text-5xl md:text-6xl text-ink mb-4 leading-tight">
                  Initialize Career Protocol
                </h1>
                <p className="text-lg text-secondary max-w-xl mx-auto">
                  Upload your professional dossier to activate the agent swarm.
                </p>
              </motion.div>
            </section>

            {/* Error Display */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-center"
              >
                <p className="text-sm">{error}</p>
                <button
                  onClick={clearError}
                  className="mt-2 text-xs underline hover:no-underline"
                >
                  Dismiss
                </button>
              </motion.div>
            )}

            {/* Upload Section */}
            <motion.section
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="max-w-2xl mx-auto"
            >
              <div className="space-y-6">
                
                {/* 1. Resume Drop Zone */}
                <div>
                   <DropZone onFileSelect={handleFileSelect} disabled={isLoading} />
                   <p className="text-center text-sm text-secondary mt-2">
                    Accepted format: PDF Resume (up to 5MB)
                  </p>
                </div>

                {/* 2. GitHub Input (Optional) */}
                <div className="bg-white p-4 rounded-xl border border-gray-200">
                  <div className="flex items-center gap-2 mb-2">
                    <Github className="w-4 h-4 text-ink" />
                    <label htmlFor="github" className="text-sm font-medium text-ink">
                      Connect GitHub (Digital Twin)
                    </label>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-secondary">Optional</span>
                  </div>
                  <input
                    type="url"
                    id="github"
                    placeholder="https://github.com/username/repo"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#D95D39]/20 focus:border-[#D95D39] transition-all text-sm"
                  />
                  <p className="text-xs text-secondary mt-1.5 ml-1">
                    The Watchdog Agent will scan your code commits to verify skills in real-time.
                  </p>
                </div>

              </div>

              {/* Session Info */}
              {sessionId && (
                <p className="text-center text-xs text-secondary mt-6">
                  Active Session: {sessionId.substring(0, 8)}...
                </p>
              )}

              {/* Feature Highlights */}
              <div className="mt-12 grid grid-cols-3 gap-6">
                {[
                  { title: "Perception Agent", desc: "Semantic Analysis" },
                  { title: "Market Agent", desc: "Job Matching" },
                  { title: "Strategist Agent", desc: "Gap Analysis" },
                ].map((feature, index) => (
                  <motion.div
                    key={feature.title}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.4 + index * 0.1 }}
                    className="text-center"
                  >
                    <div className="text-sm font-medium text-ink">
                      {feature.title}
                    </div>
                    <div className="text-xs text-secondary mt-1">
                      {feature.desc}
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.section>
          </motion.div>
        ) : (
          <motion.div
            key="processing"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.5 }}
            className="w-full max-w-2xl"
          >
            {/* Processing Header */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center mb-8"
            >
              <h2 className="font-serif-bold text-3xl text-ink mb-2">
                {processingError
                  ? "Processing Failed"
                  : "Processing Your Resume"}
              </h2>
              <p className="text-secondary">{selectedFile?.name}</p>
            </motion.div>

            {/* Agent Terminal */}
            <AgentTerminal
              logs={agentLogs}
              onComplete={handleAgentComplete}
              title="Perception Agent v1.0"
            />

            {/* Error State */}
            {processingError && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-6 text-center"
              >
                <p className="text-red-600 mb-4">{processingError}</p>
                <button
                  onClick={handleRetry}
                  className="px-6 py-3 rounded-lg font-medium text-white transition-all hover:opacity-90"
                  style={{ backgroundColor: "#D95D39" }}
                >
                  Try Again
                </button>
              </motion.div>
            )}

            {/* Status Text */}
            {!processingError && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 }}
                className="text-center text-sm text-secondary mt-6"
              >
                {isLoading
                  ? "Analyzing your professional identity..."
                  : "Processing complete!"}
              </motion.p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}