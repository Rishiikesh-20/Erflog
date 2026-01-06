"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import { createClient, Session } from "@supabase/supabase-js";
import * as api from "./api";
import {
  UserProfile,
  StrategyJobMatch,
  MatchResponse,
  Strategy,
} from "./api";

// Supabase client initialization
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";
const supabase = createClient(supabaseUrl, supabaseAnonKey);

// 1. Define the Shape of the Context
interface SessionContextType {
  sessionId: string | null;
  profile: UserProfile | null;
  isLoading: boolean;
  error: string | null;
  strategyJobs: StrategyJobMatch[];
  isApiHealthy: boolean;

  // Supabase Auth
  session: Session | null;
  accessToken: string | null;

  // Actions
  initialize: () => Promise<string | null>;
  checkHealth: () => Promise<boolean>;
  
  // UPDATED SIGNATURE HERE: Added githubUrl as optional
  uploadUserResume: (file: File, sessionId: string, githubUrl?: string) => Promise<boolean>;
  
  runStrategy: (query?: string, forceRefresh?: boolean) => Promise<boolean>;
  clearError: () => void;
  resetSession: () => void;
  signOut: () => Promise<void>;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export const useSession = () => {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
};

interface SessionProviderProps {
  children: ReactNode;
}

export const SessionProvider: React.FC<SessionProviderProps> = ({
  children,
}) => {
  // State
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [strategyJobs, setStrategyJobs] = useState<StrategyJobMatch[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isApiHealthy, setIsApiHealthy] = useState<boolean>(true);
  
  // Supabase Auth State
  const [session, setSession] = useState<Session | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  // Load Supabase session on mount
  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setAccessToken(session?.access_token || null);
    });

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setAccessToken(session?.access_token || null);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Load session from localStorage on mount
  useEffect(() => {
    const storedSession = localStorage.getItem("erflog_session_id");
    const storedProfile = localStorage.getItem("erflog_profile");
    
    if (storedSession) {
      setSessionId(storedSession);
    }
    
    if (storedProfile) {
      try {
        setProfile(JSON.parse(storedProfile));
      } catch (e) {
        console.error("Failed to parse stored profile", e);
        localStorage.removeItem("erflog_profile");
      }
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const checkHealth = useCallback(async () => {
    try {
      await api.healthCheck();
      setIsApiHealthy(true);
      return true;
    } catch (err) {
      console.error("Health check failed", err);
      setIsApiHealthy(false);
      return false;
    }
  }, []);

  const initialize = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.initSession();
      if (response.status === "success") {
        setSessionId(response.session_id);
        localStorage.setItem("erflog_session_id", response.session_id);
        return response.session_id;
      }
      throw new Error("Failed to initialize session");
    } catch (err) {
      const msg = api.getErrorMessage(err);
      setError(msg);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // --- THE FIX IS HERE ---
  const uploadUserResume = useCallback(
    async (file: File, activeSessionId: string, githubUrl?: string) => {
      setIsLoading(true);
      setError(null);
      try {
        // Pass the githubUrl to the API call
        const response = await api.uploadResume(file, activeSessionId, githubUrl);
        
        if (response.status === "success" && response.profile) {
          setProfile(response.profile);
          localStorage.setItem("erflog_profile", JSON.stringify(response.profile));
          return true;
        }
        return false;
      } catch (err) {
        const msg = api.getErrorMessage(err);
        setError(msg);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const runStrategy = useCallback(
    async (query?: string, forceRefresh: boolean = false) => {
      if (!sessionId || !profile) {
        setError("Session or profile missing");
        return false;
      }

      // If we already have jobs and aren't forcing refresh, return true (cache)
      if (strategyJobs.length > 0 && !forceRefresh) {
        return true;
      }

      setIsLoading(true);
      setError(null);

      try {
        // Use user skills as default query if none provided
        const searchQuery = query || profile.skills.join(", ");
        
        // Use matchJobs (Agent 3) which includes roadmaps
        const response = await api.matchJobs(searchQuery);
        
        if (response.status === "success" && response.matches) {
          // Convert MatchJobResult to StrategyJobMatch type if needed
          // or ensure types align in api.ts. Here we assume they are compatible.
          setStrategyJobs(response.matches as unknown as StrategyJobMatch[]);
          return true;
        }
        return false;
      } catch (err) {
        const msg = api.getErrorMessage(err);
        setError(msg);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, profile, strategyJobs.length]
  );

  const resetSession = useCallback(() => {
    setSessionId(null);
    setProfile(null);
    setStrategyJobs([]);
    localStorage.removeItem("erflog_session_id");
    localStorage.removeItem("erflog_profile");
    setError(null);
  }, []);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setSession(null);
    setAccessToken(null);
    resetSession();
  }, [resetSession]);

  const value = {
    sessionId,
    profile,
    isLoading,
    error,
    strategyJobs,
    isApiHealthy,
    session,
    accessToken,
    initialize,
    checkHealth,
    uploadUserResume,
    runStrategy,
    clearError,
    resetSession,
    signOut,
  };

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
};
