import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { supabase } from "./supabase";

// API Base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// ============================================================================
// Auth Interceptor - Automatically attach JWT to all requests
// ============================================================================

api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// ============================================================================
// Auth Types
// ============================================================================

export interface AuthUser {
  user_id: string;
  email: string | null;
  provider: string | null;
}

// ============================================================================
// Type Definitions
// ============================================================================

export interface ApiInfo {
  message: string;
  version: string;
  agents_active: number;
  endpoints: {
    workflow: string[];
    interview: string;
    legacy: string[];
    agent4: string;
  };
}

export interface HealthResponse {
  status: string;
  message: string;
  active_sessions: number;
}

export interface InitResponse {
  status: string;
  session_id: string;
  message: string;
}

export interface UserProfile {
  name: string;
  email: string;
  skills: string[];
  experience_summary: string;
  education: string;
  user_id: string;
  latest_code_analysis?: Record<string, unknown>;
}

export interface UploadResumeResponse {
  status: string;
  session_id: string;
  profile: UserProfile;
}

export interface SyncGithubResponse {
  status: string;
  analysis: {
    detected_skills: Array<{ skill: string; level: string; evidence: string }>;
  };
  updated_skills: string[];
}

// --- NEW INTERFACE FOR WATCHDOG CHECK ---
export interface WatchdogCheckResponse {
  status: "updated" | "no_change" | "error";
  repo_name?: string;
  new_sha?: string;
  updated_skills?: string[];
  analysis?: any;
}

export interface RoadmapResource {
  name: string;
  url: string;
}

export interface RoadmapDay {
  day: number;
  topic: string;
  task: string;
  resources: RoadmapResource[];
}

export interface RoadmapDetails {
  missing_skills: string[];
  roadmap: RoadmapDay[];
}

export interface StrategyJobMatch {
  id: string;
  score: number;
  title: string;
  company: string;
  description: string;
  link: string;
  tier?: string;
  status?: string;
  action?: string;
  ui_color?: string;
  roadmap_details?: RoadmapDetails | null;
}

export interface TierSummary {
  A_ready: number;
  B_roadmap: number;
  C_low: number;
}

export interface Strategy {
  matched_jobs: StrategyJobMatch[];
  total_matches: number;
  query_used: string;
  tier_summary: TierSummary;
}

export interface GenerateStrategyResponse {
  status: string;
  strategy: Strategy;
}

export interface Application {
  pdf_path: string;
  pdf_url: string;
  recruiter_email: string;
  application_status: string;
  rewritten_content: Record<string, unknown>;
}

export interface GenerateApplicationResponse {
  status: string;
  session_id: string;
  application: Application;
}

export interface MatchJobResult {
  id: string;
  score: number;
  title: string;
  company: string;
  description: string;
  link: string;
  tier: string;
  status: string;
  action: string;
  ui_color: string;
  roadmap_details: RoadmapDetails | null;
}

export interface MatchResponse {
  status: string;
  count: number;
  matches: MatchJobResult[];
}

export interface InterviewResponse {
  status: string;
  response: string;
  stage: string;
  message_count: number;
}

export interface GenerateKitResponse {
  status: string;
  message: string;
  data?: {
    pdf_url?: string;
    pdf_path?: string;
    user_name?: string;
    job_title?: string;
    job_company?: string;
    application_status?: string;
  };
}

export interface ApiError {
  detail: string;
}

// ============================================================================
// API Functions
// ============================================================================

export async function getApiInfo(): Promise<ApiInfo> {
  const response = await api.get<ApiInfo>("/");
  return response.data;
}

export async function healthCheck(): Promise<HealthResponse> {
  const response = await api.get<HealthResponse>("/health");
  return response.data;
}

export async function initSession(): Promise<InitResponse> {
  const response = await api.post<InitResponse>("/api/init");
  return response.data;
}

export async function uploadResume(
  file: File,
  sessionId: string,
  githubUrl?: string
): Promise<UploadResumeResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("session_id", sessionId);
  
  if (githubUrl) {
    formData.append("github_url", githubUrl);
  }

  const response = await api.post<UploadResumeResponse>(
    "/api/upload-resume", 
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );
  return response.data;
}

export async function syncGithub(
  sessionId: string, 
  githubUrl: string
): Promise<SyncGithubResponse> {
  const response = await api.post<SyncGithubResponse>("/api/sync-github", {
    session_id: sessionId,
    github_url: githubUrl
  });
  return response.data;
}

// --- NEW FUNCTION: CHECK WATCHDOG STATUS ---
export async function checkWatchdog(
  sessionId: string,
  lastKnownSha?: string
): Promise<WatchdogCheckResponse> {
  const response = await api.post<WatchdogCheckResponse>("/api/watchdog/check", {
    session_id: sessionId,
    last_known_sha: lastKnownSha
  });
  return response.data;
}

export async function generateStrategy(
  query: string
): Promise<GenerateStrategyResponse> {
  const response = await api.post<GenerateStrategyResponse>(
    "/api/generate-strategy",
    {
      query,
    }
  );
  return response.data;
}

export async function generateApplication(
  sessionId: string,
  jobDescription?: string
): Promise<GenerateApplicationResponse> {
  const response = await api.post<GenerateApplicationResponse>(
    "/api/generate-application",
    {
      session_id: sessionId,
      ...(jobDescription && { job_description: jobDescription }),
    }
  );
  return response.data;
}

export async function matchJobs(query: string): Promise<MatchResponse> {
  const response = await api.post<MatchResponse>("/api/match", {
    query,
  });
  return response.data;
}

export async function interviewChat(
  sessionId: string,
  jobContext: string,
  userMessage: string = ""
): Promise<InterviewResponse> {
  const response = await api.post<InterviewResponse>("/api/interview/chat", {
    session_id: sessionId,
    user_message: userMessage,
    job_context: jobContext,
  });
  return response.data;
}

export async function generateKit(
  userName: string,
  jobTitle: string,
  jobCompany: string,
  sessionId?: string,
  jobDescription?: string
): Promise<GenerateKitResponse | Blob> {
  const response = await api.post(
    "/api/generate-kit",
    {
      user_name: userName,
      job_title: jobTitle,
      job_company: jobCompany,
      session_id: sessionId,
      job_description: jobDescription,
    }
  );

  // Check if response is JSON (which it should be now)
  return response.data as GenerateKitResponse;
}

export async function analyze(
  userInput: string,
  context: Record<string, unknown> = {}
): Promise<{ status: string; message: string; data: Record<string, unknown> }> {
  const response = await api.post("/analyze", {
    user_input: userInput,
    context,
  });
  return response.data;
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiError>;
    if (axiosError.response?.data?.detail) {
      return axiosError.response.data.detail;
    }
    if (axiosError.response?.status === 404) {
      return "Session not found. Please start a new session.";
    }
    if (axiosError.response?.status === 500) {
      return "Server error. Please try again later.";
    }
    return axiosError.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred";
}

// ============================================================================
// Auth API Functions
// ============================================================================

/**
 * Get current authenticated user info from backend
 */
export async function getCurrentUser(): Promise<AuthUser> {
  const response = await api.get<AuthUser>("/api/me");
  return response.data;
}

/**
 * Simple fetch wrapper with JWT for non-axios calls
 */
export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session?.access_token}`,
      ...options.headers,
    },
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return res.json();
}
export default api;
