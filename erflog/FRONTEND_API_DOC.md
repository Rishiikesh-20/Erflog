# Erflog Frontend API Documentation

This document provides a comprehensive overview of all API calls made by each page in the Erflog frontend application, including the responsible AI Agent/Service, request body, and response body.

---

## 🏠 API Base Configuration

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
```

All requests include JWT authentication via Supabase session token in the `Authorization: Bearer <token>` header.

---

## 📄 Page 1: Home Page (`/`)

**Route:** `/app/page.tsx`

### API Calls: **None**

This is a static landing page that:
- Checks authentication status via `useAuth()` context (uses Supabase client-side)
- Redirects authenticated users to `/dashboard`

**Agent:** N/A (Static page)

---

## 📄 Page 2: Login Page (`/login`)

**Route:** `/app/login/page.tsx`

### API Calls: **Supabase OAuth (Client-side)**

| Action | Method | Type |
|--------|--------|------|
| Google Sign-In | `supabase.auth.signInWithOAuth()` | Supabase SDK |
| GitHub Sign-In | `supabase.auth.signInWithOAuth()` | Supabase SDK |

**Agent:** Supabase Auth (External Service)

#### Auth Flow:
```typescript
// Google Sign-In
supabase.auth.signInWithOAuth({
  provider: "google",
  options: {
    redirectTo: `${window.location.origin}/auth/callback`
  }
})

// GitHub Sign-In
supabase.auth.signInWithOAuth({
  provider: "github",
  options: {
    redirectTo: `${window.location.origin}/auth/callback`
  }
})
```

---

## 📄 Page 3: Auth Callback (`/auth/callback`)

**Route:** `/app/auth/callback/route.ts`

### API Calls: **Supabase Code Exchange**

| Action | Method | Type |
|--------|--------|------|
| Exchange Code | `supabase.auth.exchangeCodeForSession(code)` | Server-side Route |

**Agent:** Supabase Auth (External Service)

After successful exchange, redirects to `/onboarding`.

---

## 📄 Page 4: Onboarding Page (`/onboarding`)

**Route:** `/app/onboarding/page.tsx`

### API Calls Summary:

| # | Endpoint | Method | Agent |
|---|----------|--------|-------|
| 1 | `/api/perception/onboarding/status` | GET | Agent 1 (Perception) |
| 2 | `/api/perception/profile` | GET | Agent 1 (Perception) |
| 3 | `/api/perception/upload-resume` | POST | Agent 1 (Perception) |
| 4 | `/api/perception/onboarding/complete` | POST | Agent 1 (Perception) |
| 5 | `/api/perception/onboarding/quiz/generate` | POST | Agent 1 (Perception) |
| 6 | `/api/perception/onboarding/quiz/submit` | POST | Agent 1 (Perception) |

---

### 1. Check Onboarding Status

**Function:** `getOnboardingStatus()`  
**Method:** `GET`  
**Endpoint:** `/api/perception/onboarding/status`  
**Agent:** **Agent 1 (Perception)** - Resume & Profile Analysis

#### Request:
```typescript
// Headers only (JWT in Authorization header)
{}
```

#### Response:
```typescript
interface OnboardingStatusResponse {
  status: string;
  needs_onboarding: boolean;
  onboarding_step: number | null;
  profile_complete: boolean;
  has_resume: boolean;
  has_quiz_completed: boolean;
}
```

---

### 2. Get User Profile

**Function:** `getUserProfile()`  
**Method:** `GET`  
**Endpoint:** `/api/perception/profile`  
**Agent:** **Agent 1 (Perception)**

#### Request:
```typescript
// Headers only
{}
```

#### Response:
```typescript
{
  status: string;
  profile: {
    name: string;
    email: string;
    skills: string[];
    experience_summary: string;
    education: string;
    user_id: string;
    latest_code_analysis?: Record<string, unknown>;
  }
}
```

---

### 3. Upload Resume

**Function:** `uploadResumePerception(file: File)`  
**Method:** `POST`  
**Endpoint:** `/api/perception/upload-resume`  
**Agent:** **Agent 1 (Perception)** - Resume Analysis & Skill Extraction

#### Request:
```typescript
// Content-Type: multipart/form-data
FormData {
  file: File  // PDF file
}
```

#### Response:
```typescript
interface ResumeUploadResponse {
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
  }
}
```

---

### 4. Complete Onboarding

**Function:** `completeOnboarding(data)`  
**Method:** `POST`  
**Endpoint:** `/api/perception/onboarding/complete`  
**Agent:** **Agent 1 (Perception)**

#### Request:
```typescript
interface OnboardingCompleteRequest {
  name: string;
  email?: string;
  skills: string[];
  target_roles: string[];
  education: Array<{
    institution: string;
    degree: string;
    course?: string;
    year?: string;
  }>;
  experience_summary?: string;
  github_url?: string;
  linkedin_url?: string;
  has_resume: boolean;
}
```

#### Response:
```typescript
{
  status: string;
  message: string;
  next_step: string;
}
```

---

### 5. Generate Onboarding Quiz

**Function:** `generateOnboardingQuiz(skills?, targetRoles?)`  
**Method:** `POST`  
**Endpoint:** `/api/perception/onboarding/quiz/generate`  
**Agent:** **Agent 1 (Perception)** - Skills Validation

#### Request:
```typescript
{
  skills?: string[];
  target_roles?: string[];
}
```

#### Response:
```typescript
interface OnboardingQuizResponse {
  status: string;
  questions: Array<{
    id: string;
    question: string;
    options: string[];
    correct_index: number;
    skill_being_tested: string;
  }>;
}
```

---

### 6. Submit Onboarding Quiz

**Function:** `submitOnboardingQuiz(answers)`  
**Method:** `POST`  
**Endpoint:** `/api/perception/onboarding/quiz/submit`  
**Agent:** **Agent 1 (Perception)**

#### Request:
```typescript
{
  answers: Array<{
    question_id: string;
    selected_index: number;
    correct_index: number;
  }>;
}
```

#### Response:
```typescript
interface QuizSubmitResponse {
  status: string;
  score: number;
  correct: number;
  total: number;
  message: string;
  onboarding_complete: boolean;
}
```

---

## 📄 Page 5: Dashboard (`/dashboard`)

**Route:** `/app/dashboard/page.tsx`

### API Calls Summary:

| # | Endpoint | Method | Agent |
|---|----------|--------|-------|
| 1 | `/api/perception/onboarding/status` | GET | Agent 1 (Perception) |
| 2 | `/api/perception/dashboard` | GET | Agent 1 (Perception) |
| 3 | `/api/perception/watchdog/check` | GET | Agent 1 (Perception) / Digital Twin Watchdog |

---

### 1. Check Onboarding Status

(Same as Onboarding page - see above)

---

### 2. Get Dashboard Insights

**Function:** `getDashboardInsights()`  
**Method:** `GET`  
**Endpoint:** `/api/perception/dashboard`  
**Agent:** **Agent 1 (Perception)** - Profile Intelligence

#### Request:
```typescript
// Headers only
{}
```

#### Response:
```typescript
interface DashboardInsightsResponse {
  status: string;
  user_name: string;
  profile_strength: number;  // 0-100
  top_jobs: Array<{
    id: string;
    title: string;
    company: string;
    match_score: number;
    key_skills: string[];
  }>;
  hot_skills: Array<{
    skill: string;
    demand_trend: string;  // "rising" | "stable" | "declining"
    reason: string;
  }>;
  github_insights: {
    repo_name: string;
    recent_commits: number;
    detected_skills: string[];
    insight_text: string;
  } | null;
  news_cards: Array<{
    title: string;
    summary: string;
    relevance: string;
  }>;
  agent_status: string;  // "active" | "syncing" | "idle"
}
```

---

### 3. Check Watchdog Status (Live Mode)

**Function:** `checkWatchdogStatus(sessionId, lastSha?)`  
**Method:** `GET`  
**Endpoint:** `/api/perception/watchdog/check`  
**Agent:** **Digital Twin Watchdog** (GitHub Monitoring)

#### Request:
```typescript
// Query Parameters
{
  session_id: string;
  last_sha?: string;  // Last known commit SHA
}
```

#### Response:
```typescript
interface WatchdogCheckResponse {
  status: "updated" | "no_change" | "error";
  repo_name?: string;
  new_sha?: string;
  updated_skills?: string[];
  analysis?: any;
}
```

---

## 📄 Page 6: Jobs List (`/jobs`)

**Route:** `/app/jobs/page.tsx`

### API Calls: **None (Uses Context Data)**

This page reads job data from `SessionContext` which was populated during Dashboard/Strategy generation.

**Data Source:** `useSession().strategyJobs`

The strategy jobs are populated from the Dashboard page via:
- `generateStrategy()` → `/api/generate-strategy`

---

## 📄 Page 7: Job Detail (`/jobs/[id]`)

**Route:** `/app/jobs/[id]/page.tsx`

### API Calls: **None (Uses Context Data)**

This page reads specific job data from `SessionContext.strategyJobs` by job ID.

**Data Source:** `useSession().strategyJobs.find(j => j.id === jobId)`

---

## 📄 Page 8: Apply Page (`/jobs/[id]/apply`)

**Route:** `/app/jobs/[id]/apply/page.tsx`

### API Calls Summary:

| # | Endpoint | Method | Agent |
|---|----------|--------|-------|
| 1 | `/api/generate-kit` | POST | Agent 4 (Operative) |

---

### 1. Generate Application Kit

**Function:** `generateKit(userName, jobTitle, jobCompany, sessionId?, jobDescription?)`  
**Method:** `POST`  
**Endpoint:** `/api/generate-kit`  
**Agent:** **Agent 4 (Operative)** - Resume Tailoring & Application Kit

#### Request:
```typescript
{
  user_name: string;
  job_title: string;
  job_company: string;
  session_id?: string;
  job_description?: string;
}
```

#### Response:
```typescript
// Option 1: Blob (PDF file for direct download)
Blob

// Option 2: JSON with URL
interface GenerateKitResponse {
  status: string;
  message: string;
  data?: {
    pdf_url?: string;
    pdf_path?: string;
    user_name?: string;
    job_title?: string;
    job_company?: string;
    application_status?: string;
  }
}
```

---

## 📄 Page 9: Interview Practice (`/interview`)

**Route:** `/app/interview/page.tsx`

### API Calls Summary:

| # | Endpoint | Method | Agent |
|---|----------|--------|-------|
| 1 | `/api/interview/chat` | POST | Agent 5 (Interview Coach) |

---

### 1. Interview Chat

**Function:** `interviewChat(sessionId, jobContext, userMessage)`  
**Method:** `POST`  
**Endpoint:** `/api/interview/chat`  
**Agent:** **Agent 5 (Interview Coach)** - Mock Interview Simulation

#### Request:
```typescript
{
  session_id: string;
  user_message: string;       // Empty string to start interview
  job_context: string;        // Job description or profile summary
}
```

#### Response:
```typescript
interface InterviewResponse {
  status: string;
  response: string;           // AI interviewer's response
  stage: string;              // "Introduction" | "Technical Questions" | "Behavioral Questions" | "Problem Solving" | "Feedback"
  message_count: number;      // Total messages in interview
}
```

---

## 📄 Page 10: Settings (`/settings`)

**Route:** `/app/settings/page.tsx`

### API Calls: **None (Currently Static)**

This is currently a static settings page with no active API integrations.

---

## 🔧 Additional API Functions (Available but not directly page-bound)

These API functions are defined in `lib/api.ts` and may be used by various components:

### General APIs

| Endpoint | Method | Function | Agent |
|----------|--------|----------|-------|
| `/` | GET | `getApiInfo()` | System |
| `/health` | GET | `healthCheck()` | System |
| `/api/init` | POST | `initSession()` | System |
| `/api/me` | GET | `getCurrentUser()` | Auth |

### Resume & GitHub

| Endpoint | Method | Function | Agent |
|----------|--------|----------|-------|
| `/api/upload-resume` | POST | `uploadResume()` | Agent 1 (Perception) |
| `/api/sync-github` | POST | `syncGithub()` | Agent 1 (Perception) |
| `/api/perception/sync-github` | POST | `syncGitHubPerception()` | Agent 1 (Perception) |
| `/api/watchdog/check` | POST | `checkWatchdog()` | Digital Twin Watchdog |

### Strategy & Matching

| Endpoint | Method | Function | Agent |
|----------|--------|----------|-------|
| `/api/generate-strategy` | POST | `generateStrategy()` | Agent 3 (Strategist) |
| `/api/generate-application` | POST | `generateApplication()` | Agent 4 (Operative) |
| `/api/match` | POST | `matchJobs()` | Agent 2 (Market Sentinel) + Agent 3 (Strategist) |

### Analysis

| Endpoint | Method | Function | Agent |
|----------|--------|----------|-------|
| `/analyze` | POST | `analyze()` | Agent 6 (Chat Assistant) |

---

## 🤖 AI Agents Summary

| Agent | Name | Responsibilities |
|-------|------|------------------|
| **Agent 1** | Perception | Resume Analysis, GitHub Analysis, Profile Management, Onboarding, Skills Extraction |
| **Agent 2** | Market Sentinel | Job Market Scanning, Job Search, Market Intelligence |
| **Agent 3** | Strategist | Match & Roadmap Generation, Gap Analysis, Strategy Planning |
| **Agent 4** | Operative | Resume Tailoring, Application Kit Generation |
| **Agent 5** | Interview Coach | Mock Interviews, Interview Practice |
| **Agent 6** | Chat Assistant | General Analysis, Conversational AI |
| **Watchdog** | Digital Twin Watchdog | GitHub Commit Monitoring, Real-time Skill Updates |

---

## 📊 Request/Response Type Definitions

All TypeScript interfaces are defined in `lib/api.ts`. Key types include:

- `AuthUser`
- `OnboardingStatusResponse`
- `OnboardingCompleteRequest`
- `QuizQuestion` / `QuizAnswer` / `QuizSubmitResponse`
- `DashboardInsightsResponse`
- `ResumeUploadResponse`
- `StrategyJobMatch` / `GenerateStrategyResponse`
- `InterviewResponse`
- `GenerateKitResponse`
- `RoadmapDetails` / `RoadmapGraph` / `GraphNode` / `GraphEdge`

---

## 🔐 Authentication Flow

1. User clicks Google/GitHub sign-in on `/login`
2. Supabase OAuth redirects to provider
3. After auth, redirects to `/auth/callback`
4. Server exchanges code for session
5. Redirects to `/onboarding`
6. Onboarding checks status and routes appropriately:
   - If `needs_onboarding: true` → Stay on onboarding
   - If `needs_onboarding: false` → Redirect to `/dashboard`

All subsequent API calls include JWT token from Supabase session in `Authorization: Bearer <token>` header (handled automatically by axios interceptor in `lib/api.ts`).
