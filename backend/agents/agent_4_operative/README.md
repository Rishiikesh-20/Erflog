# Agent 4 - Application Operative 🕵️‍♂️💼

**Agent 4** is an autonomous AI operative designed to automate and optimize the job application process. It handles everything from tailoring resumes to specific job descriptions to auto-filling application forms and analyzing rejection feedback to improve future chances.

## 🚀 Key Features

* **📄 Resume Mutation (Tailoring):**
* Takes a user's master resume (PDF) and a Job Description (JD).
* Uses Gemini AI to rewrite bullet points, skills, and summaries to match the JD.
* Renders a high-quality LaTeX PDF and uploads it to Supabase Storage.


* **🤖 Auto-Apply Bot:**
* Launches a visible browser instance (via `browser-use`).
* Navigates to job links (Ashby, Greenhouse, etc.).
* Intelligently fills out forms (Name, Email, LinkedIn, Custom Questions).
* **Safety First:** Stops *before* the final submit button for user review.


* **📝 Response Generator:**
* Generates personalized, high-quality answers for common application questions (e.g., "Why do you want to join us?", "Tell us about yourself").
* Uses context from the user's profile and the specific company/JD.


* **📉 Rejection Analysis & Coaching:**
* Analyzes rejection emails or feedback against the original JD.
* Identifies root causes (e.g., "Lack of Rust experience").
* Creates an actionable "Improvement Plan" and saves "Anti-Patterns" to vector memory (Pinecone) to avoid similar rejections in the future.


* **📊 ATS Scorer:**
* Scans resume text against standard ATS (Applicant Tracking System) rules.
* Provides a compatibility score (0-100) and lists missing keywords.



## 🛠️ Tech Stack

* **Core:** Python 3.10+, FastAPI
* **AI/LLM:** Google Gemini 2.0 Flash (via LangChain)
* **Browser Automation:** `browser-use`, Playwright
* **Document Processing:** `pdfminer.six` (PDF Text), `pdflatex` (Resume Rendering)
* **Database:** Supabase (PostgreSQL), Supabase Storage
* **Vector Memory:** Pinecone (for learning from rejections)

## ⚙️ Setup & Installation

### 1. System Requirements (Linux/Fedora)

You must install LaTeX and Playwright browsers for the document generation and auto-apply features to work.

```bash
# Install LaTeX compilers (for Resume Generation)
sudo dnf install texlive-scheme-basic texlive-collection-latexrecommend

# Install Playwright browsers (for Auto-Apply)
playwright install chromium

```

### 2. Environment Variables

Ensure your `.env` file contains the following keys:

```env
GEMINI_API_KEY=your_google_gemini_key
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_key
PINECONE_API_KEY=your_pinecone_key (Optional, for memory)

```

### 3. Database Schema

Ensure your Supabase `applications` table has the required columns:

```sql
ALTER TABLE public.applications
ADD COLUMN IF NOT EXISTS application_metadata jsonb DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS screenshot_url text;

```

## 🔌 API Endpoints

### 1. Generate Tailored Resume

**POST** `/agent4/generate-resume`
Downloads the user's base resume, rewrites it for the JD, and returns a new PDF URL.

```json
{
  "user_id": "uuid-string",
  "job_description": "Full text of the target job...",
  "job_id": "optional-job-id"
}

```

### 2. Auto-Apply to Job

**POST** `/agent4/auto-apply`
Opens a browser on the server to fill out the application form.

```json
{
  "job_url": "https://jobs.ashbyhq.com/company/job-id/application",
  "user_data": {
    "name": "Rishi",
    "email": "rishi@example.com",
    "linkedin": "linkedin.com/in/rishi"
  }
}

```

### 3. Generate Application Responses

**POST** `/agent4/generate-responses`
Creates copy-paste answers for "Why us?" and other questions.

```json
{
  "user_id": "uuid-string",
  "company_name": "Google",
  "job_title": "AI Engineer",
  "job_description": "JD text...",
  "additional_context": "I used Gemini in my hackathon..."
}

```

### 4. Analyze Rejection

**POST** `/agent4/analyze-rejection`
Diagnoses why a user was rejected and updates the AI's memory.

```json
{
  "user_id": "uuid-string",
  "job_description": "JD text...",
  "rejection_reason": "They wanted more systems programming experience."
}

```

## 📂 Project Structure

```
agent_4_operative/
├── __init__.py          # Exports router & service
├── router.py            # FastAPI endpoints
├── service.py           # Business logic layer (Bridge)
├── tools.py             # Core functions (Auto-apply, Mutation, etc.)
├── schemas.py           # Pydantic models for request/response
├── evolution.py         # Pinecone memory integration
├── latex_engine.py      # LaTeX rendering logic
└── docx_engine.py       # DOCX processing logic

```