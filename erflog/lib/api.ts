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
}

export interface UploadResumeResponse {
  status: string;
  session_id: string;
  profile: UserProfile;
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

// Match endpoint types (Agent 3 with roadmap)
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

// Interview types
export interface InterviewResponse {
  status: string;
  response: string;
  stage: string;
  message_count: number;
}

// Generate Kit types
export interface GenerateKitResponse {
  status: string;
  message: string;
  data: Record<string, unknown>;
}

// Error response type
export interface ApiError {
  detail: string;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Get API info and available endpoints
 */
export async function getApiInfo(): Promise<ApiInfo> {
  const response = await api.get<ApiInfo>("/");
  return response.data;
}

/**
 * Health check endpoint
 */
export async function healthCheck(): Promise<HealthResponse> {
  const response = await api.get<HealthResponse>("/health");
  return response.data;
}

/**
 * Initialize a new session for the agent workflow
 */
export async function initSession(): Promise<InitResponse> {
  const response = await api.post<InitResponse>("/api/init");
  return response.data;
}

/**
 * Upload a resume PDF and run Agent 1 (Perception)
 */
export async function uploadResume(
  file: File,
  sessionId: string
): Promise<UploadResumeResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("session_id", sessionId);

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

/**
 * Run Agent 3 (Strategist) for semantic job matching
 * Uses the provided query (skills/experience) to find best-fit jobs via vector search
 */
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

/**
 * Run Agent 4 (Operative) to generate tailored resume and outreach
 */
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

/**
 * Agent 3: Job Match with Tier classification and Learning Roadmaps
 */
export async function matchJobs(query: string): Promise<MatchResponse> {
  const response = await api.post<MatchResponse>("/api/match", {
    query,
  });
  return response.data;
}

/**
 * Agent 6: Interview Chat - Start or continue conversation
 */
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

/**
 * Generate deployment kit (resume PDF) for a specific job
 */
export async function generateKit(
  userName: string,
  jobTitle: string,
  jobCompany: string
): Promise<GenerateKitResponse | Blob> {
  const response = await api.post(
    "/api/generate-kit",
    {
      user_name: userName,
      job_title: jobTitle,
      job_company: jobCompany,
    },
    {
      responseType: "blob",
    }
  );

  // Check if response is PDF or JSON
  const contentType = response.headers["content-type"];
  if (contentType?.includes("application/pdf")) {
    return response.data as Blob;
  }

  // Parse JSON response
  const text = await (response.data as Blob).text();
  return JSON.parse(text) as GenerateKitResponse;
}

/**
 * Legacy analyze endpoint
 */
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

// ============================================================================
// Error Handling Helper
// ============================================================================

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

// Export the axios instance for custom requests
export default api;

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
