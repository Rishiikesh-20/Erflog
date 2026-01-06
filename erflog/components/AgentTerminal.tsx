"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, CheckCircle2, Loader2 } from "lucide-react";

export interface AgentLog {
  id: string;
  agent?: string;
  message: string;
  type: "system" | "agent" | "status" | "success" | "error";
  delay?: number; // delay before showing this message (ms)
}

interface AgentTerminalProps {
  logs: AgentLog[];
  onComplete?: () => void;
  title?: string;
  showHeader?: boolean;
  className?: string;
  typingSpeed?: number; // characters per second
}

function TypewriterText({
  text,
  speed = 50,
  onComplete,
}: {
  text: string;
  speed?: number;
  onComplete?: () => void;
}) {
  const [displayedText, setDisplayedText] = useState("");
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    setDisplayedText("");
    setIsComplete(false);
    let index = 0;

    const interval = setInterval(() => {
      if (index < text.length) {
        setDisplayedText(text.slice(0, index + 1));
        index++;
      } else {
        clearInterval(interval);
        setIsComplete(true);
        onComplete?.();
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed, onComplete]);

  return (
    <span>
      {displayedText}
      {!isComplete && (
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.5, repeat: Infinity }}
          className="inline-block w-2 h-4 ml-0.5 bg-current align-middle"
        />
      )}
    </span>
  );
}

function LogLine({
  log,
  isTyping,
  onTypingComplete,
}: {
  log: AgentLog;
  isTyping: boolean;
  onTypingComplete: () => void;
}) {
  const getPrefix = () => {
    switch (log.type) {
      case "system":
        return <span className="text-blue-400">System:</span>;
      case "agent":
        return (
          <span className="text-orange-400 flex items-center gap-1.5">
            <Bot className="w-3.5 h-3.5" />
            {log.agent}:
          </span>
        );
      case "status":
        return <span className="text-yellow-400">Status:</span>;
      case "success":
        return (
          <span className="text-green-400 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Complete:
          </span>
        );
      case "error":
        return <span className="text-red-400">Error:</span>;
      default:
        return null;
    }
  };

  const getMessageColor = () => {
    switch (log.type) {
      case "system":
        return "text-blue-300";
      case "agent":
        return "text-gray-300";
      case "status":
        return "text-yellow-300";
      case "success":
        return "text-green-300";
      case "error":
        return "text-red-300";
      default:
        return "text-gray-300";
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2 }}
      className="flex items-start gap-2 font-mono text-sm"
    >
      <span className="text-gray-500 select-none">›</span>
      <div className="flex items-start gap-2 flex-wrap">
        {getPrefix()}
        <span className={getMessageColor()}>
          {isTyping ? (
            <TypewriterText
              text={log.message}
              speed={2}
              onComplete={onTypingComplete}
            />
          ) : (
            log.message
          )}
        </span>
      </div>
    </motion.div>
  );
}

export default function AgentTerminal({
  logs,
  onComplete,
  title = "Agent Terminal",
  showHeader = true,
  className = "",
}: AgentTerminalProps) {
  const [visibleLogs, setVisibleLogs] = useState<AgentLog[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isTypingCurrent, setIsTypingCurrent] = useState(true);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (currentIndex >= logs.length) {
      setIsComplete(true);
      onComplete?.();
      return;
    }

    const currentLog = logs[currentIndex];
    const delay = currentLog.delay || 300;

    const timer = setTimeout(() => {
      setVisibleLogs((prev) => {
        // Prevent duplicates if effect runs multiple times for same log
        if (prev.some(l => l.id === currentLog.id)) return prev;
        return [...prev, currentLog];
      });
      setIsTypingCurrent(true);
    }, delay);

    return () => clearTimeout(timer);
  }, [currentIndex, logs, onComplete]);

  const handleTypingComplete = () => {
    setIsTypingCurrent(false);
    setTimeout(() => {
      setCurrentIndex((prev) => prev + 1);
    }, 200);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={`w-full max-w-2xl mx-auto ${className}`}
    >
      <div
        className="rounded-xl overflow-hidden shadow-2xl border"
        style={{
          backgroundColor: "#1A1A1A",
          borderColor: "#333",
        }}
      >
        {/* Terminal Header */}
        {showHeader && (
          <div
            className="flex items-center gap-2 px-4 py-3 border-b"
            style={{
              backgroundColor: "#252525",
              borderColor: "#333",
            }}
          >
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <div className="w-3 h-3 rounded-full bg-yellow-500" />
              <div className="w-3 h-3 rounded-full bg-green-500" />
            </div>
            <div className="flex-1 text-center">
              <span className="text-gray-400 text-xs font-mono flex items-center justify-center gap-2">
                <Bot className="w-3.5 h-3.5" />
                {title}
              </span>
            </div>
            {!isComplete && (
              <Loader2 className="w-4 h-4 text-orange-400 animate-spin" />
            )}
            {isComplete && <CheckCircle2 className="w-4 h-4 text-green-400" />}
          </div>
        )}

        {/* Terminal Body */}
        <div className="p-4 space-y-2 min-h-[200px] max-h-[400px] overflow-y-auto">
          <AnimatePresence>
            {visibleLogs.map((log, index) => (
              <LogLine
                key={`${log.id}-${index}`}
                log={log}
                isTyping={isTypingCurrent && index === visibleLogs.length - 1}
                onTypingComplete={handleTypingComplete}
              />
            ))}
          </AnimatePresence>

          {/* Blinking cursor when waiting */}
          {!isComplete && visibleLogs.length === 0 && (
            <motion.div
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.5, repeat: Infinity }}
              className="font-mono text-sm text-gray-500"
            >
              › Initializing...
            </motion.div>
          )}
        </div>

        {/* Progress Bar */}
        <div className="h-1" style={{ backgroundColor: "#252525" }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${(currentIndex / logs.length) * 100}%` }}
            transition={{ duration: 0.3 }}
            className="h-full"
            style={{ backgroundColor: "#D95D39" }}
          />
        </div>
      </div>
    </motion.div>
  );
}
