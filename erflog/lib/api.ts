import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { supabase } from "./supabase";

// API Base URL and Key
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  params: API_KEY ? { key: API_KEY } : {}, // Add API key to all requests
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
  leetcode_url?: string;
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
// GitHub Sync Response
// ============================================================================

export interface SyncGithubResponse {
  status: string;
  insights?: {
    message?: string;
    repos_active?: string[];
    main_focus?: string;
    tech_stack?: string[];
  };
  new_skills?: string[];
  updated_skills?: string[];
  from_cache?: boolean;
  latest_sha?: string;
  repos_touched?: string[];
  analysis?: {
    detected_skills?: Array<{ skill: string; confidence: number }>;
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

// SyncGithubResponse is defined above in GitHub Sync Response section

export interface WatchdogCheckResponse {
  status: "updated" | "no_change" | "error";
  repo_name?: string;
  new_sha?: string;
  updated_skills?: string[];
  analysis?: Record<string, unknown>;
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

export type MatchJobResult = StrategyJobMatch;

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
// Auto-Apply Types (Agent 4 Browser Automation)
// ============================================================================

export interface AutoApplyRequest {
  job_url: string;
  user_data: Record<string, string>;
  user_id?: string;
  resume_path?: string;
  resume_url?: string;
}

export interface AutoApplyResponse {
  success: boolean;
  job_url: string;
  message: string;
  details?: string;
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

/**
 * Auto-fill a job application form using browser automation.
 * Opens a visible browser, clicks Apply, and fills form fields.
 * Does NOT submit - user must review and submit manually.
 */
export async function autoApplyToJob(
  jobUrl: string,
  userData: Record<string, string>
): Promise<AutoApplyResponse> {
  const response = await api.post<AutoApplyResponse>("/agent4/auto-apply", {
    job_url: jobUrl,
    user_data: userData,
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
): Promise<QuizSubmitResponse & { trigger_cold_start?: boolean }> {
  const response = await api.post<
    QuizSubmitResponse & { trigger_cold_start?: boolean }
  >("/api/perception/onboarding/quiz/submit", {
    answers,
  });
  return response.data;
}

/**
 * Trigger cold start processing for a newly onboarded user.
 * This immediately generates personalized data (jobs, hackathons, news, roadmaps)
 * instead of waiting for the 2AM cron job.
 */
export async function triggerColdStart(): Promise<{
  status: string;
  message: string;
  user_id: string;
}> {
  const response = await api.post("/api/strategist/cold-start");
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

// ============================================================================
// Settings API Functions
// ============================================================================

export interface SettingsProfile {
  user_id: string;
  name: string | null;
  email: string | null;
  github_url: string | null;
  linkedin_url: string | null;
  resume_url: string | null;
  sec_resume_url: string | null;
  ats_score: string | null; // ATS compatibility score (0-100)
  skills: string[];
  target_roles: string[];
  onboarding_completed: boolean;
  quiz_completed: boolean;
  updated_at: string | null;
}

export interface SettingsProfileResponse {
  status: string;
  profile: SettingsProfile;
}

export interface ProfileUpdateRequest {
  name?: string;
  github_url?: string;
  linkedin_url?: string;
}

export interface ProfileUpdateResponse {
  status: string;
  updated_fields: string[];
  user_id: string;
  message: string;
}

/**
 * Get full profile for Settings page
 */
export async function getSettingsProfile(): Promise<SettingsProfileResponse> {
  const response = await api.get<SettingsProfileResponse>(
    "/api/perception/settings/profile"
  );
  return response.data;
}

/**
 * Update profile fields (name, github_url, linkedin_url)
 */
export async function updateProfile(
  data: ProfileUpdateRequest
): Promise<ProfileUpdateResponse> {
  const response = await api.patch<ProfileUpdateResponse>(
    "/api/perception/settings/profile",
    data
  );
  return response.data;
}

/**
 * Upload new primary resume (replaces existing)
 */
export async function updatePrimaryResume(file: File): Promise<{
  status: string;
  message: string;
  resume_url: string;
}> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.put("/api/perception/settings/resume", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

/**
 * Calculate ATS score on demand (for existing users without score)
 */
export async function calculateAtsOnDemand(): Promise<{
  status: string;
  ats_score: string | null;
  message: string;
}> {
  const response = await api.post("/api/perception/settings/calculate-ats");
  return response.data;
}

// ============================================================================
// LeetCode Problem Solving API Functions
// ============================================================================

export interface LeetCodeProblem {
  id: number;
  title: string;
  slug: string;
  difficulty: "Easy" | "Medium" | "Hard";
  category: string;
  leetcode_url: string;
  priority: number;
}

export interface LeetCodeCategory {
  name: string;
  icon: string;
  color: string;
  problems: LeetCodeProblem[];
}

export interface LeetCodeProblemsResponse {
  categories: LeetCodeCategory[];
  total_count: number;
}

export interface LeetCodeRecommendRequest {
  quiz_answers: Record<string, string>;
  leetcode_profile?: {
    total_solved?: number;
    easy_solved?: number;
    medium_solved?: number;
    hard_solved?: number;
    ranking?: number;
  };
  solved_problem_ids?: number[];
}

export interface LeetCodeRecommendResponse {
  recommended_ids: number[];
  source: string;
  reasoning?: string;
}

export interface LeetCodeProgressResponse {
  solved_problem_ids: number[];
  quiz_answers: Record<string, string>;
  total_solved: number;
}

/**
 * Get all Blind 75 problems organized by category
 */
export async function getLeetCodeProblems(): Promise<LeetCodeProblemsResponse> {
  const response = await api.get<LeetCodeProblemsResponse>(
    "/api/leetcode/problems"
  );
  return response.data;
}

// ============================================================================
// Saved Jobs API
// ============================================================================

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
    graph?: {
      nodes?: Array<{
        id: string;
        label: string;
        day: number;
        type: string;
        description: string;
      }>;
      edges?: Array<{ source: string; target: string }>;
    };
    resources?: Record<string, Array<{ name: string; url: string }>>;
    full_job_data?: {
      roadmap?: object;
      application_text?: object;
      summary?: string;
      location?: string;
      platform?: string;
      source?: string;
      type?: string;
      needs_improvement?: boolean;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  progress?: Record<string, { completed: boolean; updated_at: string }>;
  created_at: string;
  full_job_data?: Record<string, unknown>;
}

export interface SaveJobRequest {
  user_id: string;
  original_job_id: string;
  title: string;
  company: string;
  description?: string;
  link?: string;
  score?: number;
  roadmap_details?: RoadmapDetails | null;
  full_job_data?: {
    roadmap?: RoadmapDetails | null;
    application_text?: object;
    summary?: string;
    location?: string;
    platform?: string;
    source?: string;
    type?: string;
    needs_improvement?: boolean;
    [key: string]: unknown;
  };
  progress?: Record<string, unknown>;
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
        resources?: string[] | Array<{ name: string; url: string }>;
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
    all_resources?: Array<{
      skill: string;
      resources: Array<{ name: string; url: string } | string>;
    }>;
    source_jobs?: Array<{
      title: string;
      company: string;
      name?: string;
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
 * Get AI-powered problem recommendations
 */
export async function getLeetCodeRecommendations(
  request: LeetCodeRecommendRequest
): Promise<LeetCodeRecommendResponse> {
  const response = await api.post<LeetCodeRecommendResponse>(
    "/api/leetcode/recommend",
    request
  );
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
 * Get user's LeetCode progress
 */
export async function getLeetCodeProgress(): Promise<LeetCodeProgressResponse> {
  const response = await api.get<LeetCodeProgressResponse>(
    "/api/leetcode/progress"
  );
  return response.data;
}

/**
 * Remove a job from saved jobs
 */
export async function removeSavedJob(
  jobId: string
): Promise<{ status: string; message: string }> {
  const response = await api.delete(`/api/saved-jobs/remove/${jobId}`);
  return response.data;
}

/**
 * Save user's LeetCode progress
 */
export async function saveLeetCodeProgress(
  solvedProblemIds: number[],
  quizAnswers?: Record<string, string>
): Promise<LeetCodeProgressResponse> {
  const response = await api.post<LeetCodeProgressResponse>(
    "/api/leetcode/progress",
    {
      solved_problem_ids: solvedProblemIds,
      quiz_answers: quizAnswers,
    }
  );
  return response.data;
}

/**
 * Check if a job is already saved
 */
export async function checkJobSaved(
  userId: string,
  originalJobId: string
): Promise<{ is_saved: boolean; saved_job_id: string | null }> {
  const response = await api.get(
    `/api/saved-jobs/check/${userId}/${originalJobId}`
  );
  return response.data;
}

/**
 * Merge roadmaps from multiple saved jobs
 */
export async function mergeRoadmaps(
  jobIds: string[],
  name?: string
): Promise<GlobalRoadmap> {
  const response = await api.post<GlobalRoadmap>(
    "/api/saved-jobs/merge-roadmaps",
    {
      job_ids: jobIds,
      name: name || "My Master Plan",
    }
  );
  return response.data;
}

/**
 * Get all global (merged) roadmaps for a user
 */
export async function getGlobalRoadmaps(
  userId: string
): Promise<GlobalRoadmap[]> {
  const response = await api.get<GlobalRoadmap[]>(
    `/api/saved-jobs/global-roadmaps/${userId}`
  );
  return response.data;
}

/**
 * Get a specific global roadmap
 */
export async function getGlobalRoadmap(
  roadmapId: string
): Promise<GlobalRoadmap> {
  const response = await api.get<GlobalRoadmap>(
    `/api/saved-jobs/global-roadmap/${roadmapId}`
  );
  return response.data;
}

/**
 * Delete a global roadmap
 */
export async function deleteGlobalRoadmap(
  roadmapId: string
): Promise<{ status: string; message: string }> {
  const response = await api.delete(
    `/api/saved-jobs/global-roadmap/${roadmapId}`
  );
  return response.data;
}

// =============================================================================
// Progress Tracking
// =============================================================================

export interface ProgressUpdate {
  node_id: string;
  completed: boolean;
}

export interface ProgressResponse {
  progress: Record<string, { completed: boolean; updated_at: string }>;
  total_nodes: number;
  completed_nodes: number;
  completion_percentage: number;
}

/**
 * Update progress on a roadmap node
 */
export async function updateProgress(
  jobId: string,
  nodeId: string,
  completed: boolean
): Promise<{ status: string; progress: object; message: string }> {
  const response = await api.put(`/api/saved-jobs/progress/${jobId}`, {
    node_id: nodeId,
    completed,
  });
  return response.data;
}

/**
 * Get progress for a saved job
 */
export async function getProgress(jobId: string): Promise<ProgressResponse> {
  const response = await api.get<ProgressResponse>(
    `/api/saved-jobs/progress/${jobId}`
  );
  return response.data;
}

// =============================================================================
// Roadmap Completion & Skills Update
// =============================================================================

export interface CompleteRoadmapResponse {
  status: string;
  message: string;
  new_skills_added: string[];
  total_skills: number;
}

/**
 * Called when user completes 100% of a roadmap.
 * Analyzes the roadmap and adds learned skills to user's profile.
 */
export async function completeRoadmap(
  userId: string,
  savedJobId: string
): Promise<CompleteRoadmapResponse> {
  console.log("[API] completeRoadmap called with:", { userId, savedJobId });
  try {
    const response = await api.post<CompleteRoadmapResponse>(
      "/api/saved-jobs/complete-roadmap",
      {
        user_id: userId,
        saved_job_id: savedJobId,
      }
    );
    console.log("[API] completeRoadmap response:", response.data);
    return response.data;
  } catch (error: unknown) {
    const err = error as { response?: { data?: unknown }; message?: string };
    console.error(
      "[API] completeRoadmap error:",
      err?.response?.data || err?.message || error
    );
    throw error;
  }
}

export default api;
