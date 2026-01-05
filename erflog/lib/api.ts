import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { supabase } from "./supabase";

// API Base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
    try {
      // First try to get session from Supabase client
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (session?.access_token) {
        config.headers.Authorization = `Bearer ${session.access_token}`;
        return config;
      }

      // Fallback: Try to get token from localStorage directly
      // Supabase stores auth in localStorage with key like sb-<project-ref>-auth-token
      if (typeof window !== "undefined") {
        const keys = Object.keys(localStorage);
        const supabaseAuthKey = keys.find(
          (key) => key.startsWith("sb-") && key.endsWith("-auth-token")
        );

        if (supabaseAuthKey) {
          const authData = localStorage.getItem(supabaseAuthKey);
          if (authData) {
            const parsed = JSON.parse(authData);
            const accessToken = parsed?.access_token;
            if (accessToken) {
              config.headers.Authorization = `Bearer ${accessToken}`;
            }
          }
        }
      }
    } catch (error) {
      console.error("Error getting auth token:", error);
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
// Onboarding Types
// ============================================================================

export interface EducationItem {
  institution: string;
  degree: string;
  course?: string;
  year?: string;
}

export interface OnboardingStatusResponse {
  status: string;
  needs_onboarding: boolean;
  onboarding_step: number | null;
  profile_complete: boolean;
  has_resume: boolean;
  has_quiz_completed: boolean;
}

export interface OnboardingCompleteRequest {
  name: string;
  email?: string;
  skills: string[];
  target_roles: string[];
  education: EducationItem[];
  experience_summary?: string;
  github_url?: string;
  linkedin_url?: string;
  has_resume: boolean;
}

export interface QuizQuestion {
  id: string;
  question: string;
  options: string[];
  correct_index: number;
  skill_being_tested: string;
}

export interface OnboardingQuizResponse {
  status: string;
  questions: QuizQuestion[];
}

export interface QuizAnswer {
  question_id: string;
  selected_index: number;
  correct_index: number;
}

export interface QuizSubmitResponse {
  status: string;
  score: number;
  correct: number;
  total: number;
  message: string;
  onboarding_complete: boolean;
}

// ============================================================================
// Dashboard Types
// ============================================================================

export interface JobInsight {
  id: string;
  title: string;
  company: string;
  match_score: number;
  key_skills: string[];
}

export interface SkillInsight {
  skill: string;
  demand_trend: string;
  reason: string;
}

export interface GitHubInsight {
  repo_name: string;
  recent_commits: number;
  detected_skills: string[];
  insight_text: string;
}

export interface NewsCard {
  title: string;
  summary: string;
  relevance: string;
}

export interface DashboardInsightsResponse {
  status: string;
  user_name: string;
  profile_strength: number;
  top_jobs: JobInsight[];
  hot_skills: SkillInsight[];
  github_insights: GitHubInsight | null;
  news_cards: NewsCard[];
  agent_status: string;
}

// ============================================================================
// Resume Upload Response (from perception)
// ============================================================================

export interface ResumeUploadResponse {
  status: string;
  data: {
    user_id: string;
    name?: string;
    email?: string;
    skills: string[];
    skills_metadata: Record<string, unknown>;
    experience_summary?: string;
    education?: Array<{ institution: string; degree: string }>;
    resume_json?: Record<string, unknown>;
    resume_url?: string;
  };
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

// --- NEW GRAPH TYPES ---
export interface GraphNode {
  id: string;
  label: string;
  day: number;
  type: "concept" | "practice" | "project";
  description: string;
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface RoadmapGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// Updated RoadmapDetails to use the Graph
export interface RoadmapDetails {
  missing_skills: string[];
  graph: RoadmapGraph;
  resources: Record<string, RoadmapResource[]>;
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

export interface MatchJobResult extends StrategyJobMatch {}

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

// Agent 4 - Generate Tailored Resume
export interface GenerateTailoredResumeRequest {
  job_description: string;
  job_id?: string;
}

export interface GenerateTailoredResumeResponse {
  success: boolean;
  status: string;
  user_id: string;
  original_profile: Record<string, unknown>;
  optimized_resume: Record<string, unknown>;
  pdf_path: string;
  pdf_url: string;
  application_status: string;
  processing_time_ms: number;
  message: string;
}

export interface ApiError {
  detail: string;
}

// ============================================================================
// API Functions
// ============================================================================
// (Keeping all existing functions standard)

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
  if (githubUrl) formData.append("github_url", githubUrl);
  const response = await api.post<UploadResumeResponse>(
    "/api/upload-resume",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return response.data;
}

export async function syncGithub(
  sessionId: string,
  githubUrl: string
): Promise<SyncGithubResponse> {
  const response = await api.post<SyncGithubResponse>("/api/sync-github", {
    session_id: sessionId,
    github_url: githubUrl,
  });
  return response.data;
}

export async function checkWatchdog(
  sessionId: string,
  lastKnownSha?: string
): Promise<WatchdogCheckResponse> {
  const response = await api.post<WatchdogCheckResponse>(
    "/api/watchdog/check",
    { session_id: sessionId, last_known_sha: lastKnownSha }
  );
  return response.data;
}

export async function generateStrategy(
  query: string
): Promise<GenerateStrategyResponse> {
  const response = await api.post<GenerateStrategyResponse>(
    "/api/generate-strategy",
    { query }
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
  const response = await api.post<MatchResponse>("/api/match", { query });
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

/**
 * Generate a tailored resume for a specific job using Agent 4's LaTeX engine.
 * This is user-triggered (not part of cron job) to avoid heavy processing.
 */
export async function generateTailoredResume(
  jobDescription: string,
  jobId?: string
): Promise<GenerateTailoredResumeResponse> {
  const response = await api.post("/agent4/generate-resume", {
    job_description: jobDescription,
    job_id: jobId,
  });
  return response.data as GenerateTailoredResumeResponse;
}

export async function generateKit(
  userName: string,
  jobTitle: string,
  jobCompany: string,
  sessionId?: string,
  jobDescription?: string
): Promise<GenerateKitResponse | Blob> {
  const response = await api.post("/api/generate-kit", {
    user_name: userName,
    job_title: jobTitle,
    job_company: jobCompany,
    session_id: sessionId,
    job_description: jobDescription,
  });
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
    if (axiosError.response?.data?.detail)
      return axiosError.response.data.detail;
    if (axiosError.response?.status === 404)
      return "Session not found. Please start a new session.";
    if (axiosError.response?.status === 500)
      return "Server error. Please try again later.";
    return axiosError.message;
  }
  if (error instanceof Error) return error.message;
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

// ============================================================================
// Onboarding API Functions
// ============================================================================

/**
 * Check if user needs to complete onboarding
 */
export async function getOnboardingStatus(): Promise<OnboardingStatusResponse> {
  const response = await api.get<OnboardingStatusResponse>(
    "/api/perception/onboarding/status"
  );
  return response.data;
}

/**
 * Upload resume via perception API
 */
export async function uploadResumePerception(
  file: File
): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post<ResumeUploadResponse>(
    "/api/perception/upload-resume",
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    }
  );
  return response.data;
}

/**
 * Complete onboarding with profile data
 */
export async function completeOnboarding(
  data: OnboardingCompleteRequest
): Promise<{ status: string; message: string; next_step: string }> {
  const response = await api.post("/api/perception/onboarding/complete", data);
  return response.data;
}

/**
 * Generate onboarding quiz questions
 */
export async function generateOnboardingQuiz(
  skills?: string[],
  targetRoles?: string[]
): Promise<OnboardingQuizResponse> {
  const response = await api.post<OnboardingQuizResponse>(
    "/api/perception/onboarding/quiz/generate",
    {
      skills,
      target_roles: targetRoles,
    }
  );
  return response.data;
}

/**
 * Submit onboarding quiz answers
 */
export async function submitOnboardingQuiz(
  answers: QuizAnswer[]
): Promise<QuizSubmitResponse> {
  const response = await api.post<QuizSubmitResponse>(
    "/api/perception/onboarding/quiz/submit",
    {
      answers,
    }
  );
  return response.data;
}

/**
 * Get dashboard insights
 */
export async function getDashboardInsights(): Promise<DashboardInsightsResponse> {
  const response = await api.get<DashboardInsightsResponse>(
    "/api/perception/dashboard"
  );
  return response.data;
}

/**
 * Sync GitHub activity
 */
export async function syncGitHubPerception(): Promise<SyncGithubResponse> {
  const response = await api.post<SyncGithubResponse>(
    "/api/perception/sync-github"
  );
  return response.data;
}

/**
 * Get user profile
 */
export async function getUserProfile(): Promise<{
  status: string;
  profile: UserProfile;
}> {
  const response = await api.get("/api/perception/profile");
  return response.data;
}

export const checkWatchdogStatus = async (
  sessionId: string,
  lastSha?: string
) => {
  // Assuming 'api' is the name of your exported axios instance in this file
  const response = await api.get("/api/perception/watchdog/check", {
    params: { session_id: sessionId, last_sha: lastSha },
  });
  return response.data;
};

// ============================================================================
// Agent 3: Strategist API Types & Functions
// ============================================================================

// Roadmap Types (from Agent 3 Orchestrator)
export interface RoadmapNode {
  id: string;
  label: string;
  day: number;
  type: "concept" | "practice" | "project";
  description: string;
}

export interface RoadmapEdge {
  source: string;
  target: string;
}

export interface RoadmapResource {
  name: string;
  url: string;
}

export interface RoadmapData {
  missing_skills: string[];
  match_percentage: number;
  graph: {
    nodes: RoadmapNode[];
    edges: RoadmapEdge[];
  };
  resources: Record<string, RoadmapResource[]>;
  estimated_hours: number;
  focus_areas: string[];
}

// Application Text Types (from Agent 4)
export interface ApplicationText {
  why_this_company: string;
  why_this_role: string;
  short_intro: string;
  cover_letter_opening: string;
  cover_letter_body: string;
  cover_letter_closing: string;
  key_achievements: string[];
  questions_for_interviewer: string[];
}

export interface TodayDataItem {
  id: string;
  score: number;
  title: string;
  company: string;
  link: string;
  summary: string;
  source: string;
  platform: string;
  location: string;
  type: string;
  supabase_id?: number;
  // New fields from orchestrator
  roadmap?: RoadmapData | null;
  application_text?: ApplicationText | null;
  needs_improvement?: boolean;
  resume_url?: string | null; // Tailored resume URL from Agent 4
}

export interface TodayDataResponse {
  status: string;
  data: {
    jobs: TodayDataItem[];
    hackathons: TodayDataItem[];
    news: TodayDataItem[];
    generated_at: string;
    stats: {
      jobs_count: number;
      hackathons_count: number;
      news_count: number;
    };
  };
  updated_at?: string;
  fresh: boolean;
}

export interface TodayJobsResponse {
  status: string;
  jobs: TodayDataItem[];
  count: number;
  stats?: {
    high_match: number;
    needs_improvement: number;
    with_roadmap: number;
  };
}

export interface TodayHackathonsResponse {
  status: string;
  hackathons: TodayDataItem[];
  count: number;
}

export interface StrategistDashboardResponse {
  status: string;
  jobs: TodayDataItem[];
  hackathons: TodayDataItem[];
  news: TodayDataItem[];
  updated_at: string;
}

/**
 * Get complete today_data for current user
 */
export async function getTodayData(): Promise<TodayDataResponse> {
  const response = await api.get<TodayDataResponse>("/api/strategist/today");
  return response.data;
}

/**
 * Get all 10 matched jobs for current user (for Jobs page)
 */
export async function getTodayJobs(): Promise<TodayJobsResponse> {
  const response = await api.get<TodayJobsResponse>("/api/strategist/jobs");
  return response.data;
}

/**
 * Get all 10 matched hackathons for current user (for Hackathons page)
 */
export async function getTodayHackathons(): Promise<TodayHackathonsResponse> {
  const response = await api.get<TodayHackathonsResponse>(
    "/api/strategist/hackathons"
  );
  return response.data;
}

/**
 * Get dashboard summary data (5 jobs, 2 hackathons, 2 news)
 */
export async function getStrategistDashboard(): Promise<StrategistDashboardResponse> {
  const response = await api.get<StrategistDashboardResponse>(
    "/api/strategist/dashboard"
  );
  return response.data;
}

/**
 * Manually refresh user's today_data
 */
export async function refreshTodayData(): Promise<{
  status: string;
  message: string;
  stats: { jobs_count: number; hackathons_count: number; news_count: number };
}> {
  const response = await api.post("/api/strategist/refresh");
  return response.data;
}

// =============================================================================
// Saved Jobs API
// =============================================================================

export interface SavedJob {
  id: string;
  user_id: string;
  original_job_id: string;
  title: string;
  company: string;
  description?: string;
  link?: string;
  score?: number;
  roadmap_details?: {
    missing_skills?: string[];
    [key: string]: unknown;
  };
  created_at: string;
}

export interface SaveJobRequest {
  user_id: string;
  original_job_id: string;
  title: string;
  company: string;
  description?: string;
  link?: string;
  score?: number;
  roadmap_details?: object;
}

export interface GlobalRoadmap {
  id: string;
  name: string;
  merged_graph: {
    title?: string;
    description?: string;
    total_estimated_weeks?: number;
    skill_categories?: Array<{
      category: string;
      skills: Array<{
        name: string;
        priority: string;
        appears_in_jobs?: string[];
        estimated_weeks?: number;
        resources?: string[];
      }>;
    }>;
    learning_path?: Array<{
      phase: number;
      title: string;
      duration_weeks: number;
      skills: string[];
      milestone: string;
    }>;
    combined_missing_skills?: string[];
    source_jobs?: Array<{
      title: string;
      company: string;
    }>;
  };
  source_job_ids: string[];
  created_at: string;
}

/**
 * Save a job to user's saved jobs list
 */
export async function saveJob(job: SaveJobRequest): Promise<SavedJob> {
  const response = await api.post<SavedJob>("/api/saved-jobs/save", job);
  return response.data;
}

/**
 * Get all saved jobs for a user
 */
export async function getSavedJobs(userId: string): Promise<SavedJob[]> {
  const response = await api.get<SavedJob[]>(`/api/saved-jobs/list/${userId}`);
  return response.data;
}

/**
 * Remove a job from saved jobs
 */
export async function removeSavedJob(jobId: string): Promise<{ status: string; message: string }> {
  const response = await api.delete(`/api/saved-jobs/remove/${jobId}`);
  return response.data;
}

/**
 * Check if a job is already saved
 */
export async function checkJobSaved(userId: string, originalJobId: string): Promise<{ is_saved: boolean; saved_job_id: string | null }> {
  const response = await api.get(`/api/saved-jobs/check/${userId}/${originalJobId}`);
  return response.data;
}

/**
 * Merge roadmaps from multiple saved jobs
 */
export async function mergeRoadmaps(jobIds: string[], name?: string): Promise<GlobalRoadmap> {
  const response = await api.post<GlobalRoadmap>("/api/saved-jobs/merge-roadmaps", {
    job_ids: jobIds,
    name: name || "My Master Plan"
  });
  return response.data;
}

/**
 * Get all global (merged) roadmaps for a user
 */
export async function getGlobalRoadmaps(userId: string): Promise<GlobalRoadmap[]> {
  const response = await api.get<GlobalRoadmap[]>(`/api/saved-jobs/global-roadmaps/${userId}`);
  return response.data;
}

/**
 * Get a specific global roadmap
 */
export async function getGlobalRoadmap(roadmapId: string): Promise<GlobalRoadmap> {
  const response = await api.get<GlobalRoadmap>(`/api/saved-jobs/global-roadmap/${roadmapId}`);
  return response.data;
}

/**
 * Delete a global roadmap
 */
export async function deleteGlobalRoadmap(roadmapId: string): Promise<{ status: string; message: string }> {
  const response = await api.delete(`/api/saved-jobs/global-roadmap/${roadmapId}`);
  return response.data;
}

export default api;
