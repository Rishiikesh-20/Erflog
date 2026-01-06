'use client';

import { motion } from 'framer-motion';
import { Loader2, Sparkles } from 'lucide-react';

interface LoadingProps {
  message?: string;
  fullScreen?: boolean;
}

export default function Loading({ message = "Loading...", fullScreen = true }: LoadingProps) {
  if (fullScreen) {
    return (
      <div className="fixed inset-0 bg-background flex items-center justify-center z-50">
        <div className="text-center">
          {/* Animated logo/icon */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="mb-8"
          >
            <div className="relative w-24 h-24 mx-auto">
              {/* Outer rotating ring */}
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                className="absolute inset-0 rounded-full border-4 border-orange-200 border-t-orange-500"
              />
              
              {/* Inner pulsing circle */}
              <motion.div
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="absolute inset-4 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center"
              >
                <Sparkles className="w-8 h-8 text-white" />
              </motion.div>
            </div>
          </motion.div>

          {/* Loading text */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <h3 className="text-xl font-semibold text-foreground mb-2">{message}</h3>
            <div className="flex items-center justify-center gap-2 text-muted-foreground">
              <motion.span
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 1.5, repeat: Infinity, delay: 0 }}
              >
                •
              </motion.span>
              <motion.span
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 1.5, repeat: Infinity, delay: 0.2 }}
              >
                •
              </motion.span>
              <motion.span
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 1.5, repeat: Infinity, delay: 0.4 }}
              >
                •
              </motion.span>
            </div>
          </motion.div>

          {/* Progress bar */}
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: "100%" }}
            transition={{ duration: 2, ease: "easeInOut" }}
            className="mt-8 h-1 bg-gradient-to-r from-orange-400 to-orange-600 rounded-full max-w-xs mx-auto"
          />
        </div>
      </div>
    );
  }

  // Inline loading
  return (
    <div className="flex items-center justify-center p-8">
      <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
      <span className="ml-2 text-muted-foreground">{message}</span>
    </div>
  );
}

// Skeleton loader for cards
export function CardSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6 space-y-4">
      <div className="flex items-start justify-between">
        <div className="space-y-2 flex-1">
          <div className="h-5 w-3/4 bg-muted rounded shimmer" />
          <div className="h-4 w-1/2 bg-muted rounded shimmer" />
        </div>
        <div className="h-6 w-20 bg-muted rounded-full shimmer" />
      </div>
      <div className="space-y-2">
        <div className="h-4 w-full bg-muted rounded shimmer" />
        <div className="h-4 w-5/6 bg-muted rounded shimmer" />
      </div>
      <div className="flex gap-2">
        <div className="h-9 w-24 bg-muted rounded shimmer" />
        <div className="h-9 w-24 bg-muted rounded shimmer" />
      </div>
    </div>
  );
}
