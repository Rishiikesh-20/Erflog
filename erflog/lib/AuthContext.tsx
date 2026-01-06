"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { supabase } from "./supabase";
import type { Session, User } from "@supabase/supabase-js";

// ============================================================================
// Types
// ============================================================================

interface UserMetadata {
  avatarUrl: string | null;
  fullName: string | null;
  email: string | null;
  userId: string | null;
}

interface AuthState {
  session: Session | null;
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  userMetadata: UserMetadata;
}

interface AuthContextType extends AuthState {
  signInWithGoogle: () => Promise<void>;
  signInWithGitHub: () => Promise<void>;
  signOut: () => Promise<void>;
}

// ============================================================================
// Context
// ============================================================================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ============================================================================
// Provider
// ============================================================================

// Helper to extract user metadata from Supabase user
const extractUserMetadata = (user: User | null): UserMetadata => {
  if (!user) {
    return { avatarUrl: null, fullName: null, email: null, userId: null };
  }
  const meta = user.user_metadata || {};
  return {
    avatarUrl: meta.avatar_url || meta.picture || null,
    fullName: meta.full_name || meta.name || null,
    email: user.email || meta.email || null,
    userId: user.id || null,
  };
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    session: null,
    user: null,
    isLoading: true,
    isAuthenticated: false,
    userMetadata: {
      avatarUrl: null,
      fullName: null,
      email: null,
      userId: null,
    },
  });

  // Initialize auth state and listen for changes
  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      const user = session?.user ?? null;
      setState({
        session,
        user,
        isLoading: false,
        isAuthenticated: !!session,
        userMetadata: extractUserMetadata(user),
      });
    });

    // Listen for auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      const user = session?.user ?? null;
      setState({
        session,
        user,
        isLoading: false,
        isAuthenticated: !!session,
        userMetadata: extractUserMetadata(user),
      });
    });

    return () => subscription.unsubscribe();
  }, []);

  // Sign in with Google - redirect to onboarding after auth
  const signInWithGoogle = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
  };

  // Sign in with GitHub - redirect to onboarding after auth
  const signInWithGitHub = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "github",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
  };

  // Sign out
  const signOut = async () => {
    await supabase.auth.signOut();
  };

  return (
    <AuthContext.Provider
      value={{
        ...state,
        signInWithGoogle,
        signInWithGitHub,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ============================================================================
// Hook
// ============================================================================

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
