# Agent 4 - Application Operative

**Agent 4** automates the job application process by generating ATS-optimized resumes and copy-paste ready application responses.

## Features

- 🎯 **Resume Optimization** - Rewrites resume to match job description keywords
- 📄 **PDF Generation** - Creates professional PDF resumes using WeasyPrint
- ☁️ **Cloud Storage** - Uploads PDFs to Supabase storage with signed URLs
- 📝 **Application Responses** - Generates answers for common application questions
- 🧠 **Learning Loop** - Analyzes rejections and learns from failures

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agent4/health` | GET | Health check |
| `/agent4/generate-resume` | POST | Generate optimized resume PDF |
| `/agent4/generate-responses` | POST | Generate application question responses |
| `/agent4/analyze-rejection` | POST | Analyze rejection and learn |

---

## 1. Health Check

**Endpoint:** `GET /agent4/health`

**Response:**
```json
{
    "status": "healthy",
    "agent": "Agent 4 - Application Operative",
    "version": "1.0.0",
    "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## 2. Generate Resume

Generates an ATS-optimized resume tailored to a specific job description.

**Endpoint:** `POST /agent4/generate-resume`

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | ✅ | UUID of the user from Supabase profiles table |
| `job_description` | string | ✅ | Target job description text |
| `job_id` | string | ❌ | Optional job ID for tracking |

### Example Request

```json
{
    "user_id": "22c91dc9-4238-499b-a107-5b1abf3b919c",
    "job_description": "Full Stack Developer (Python + TypeScript) at Michael Page\n\nLocation: Bengaluru, Karnataka, India\n\nDescription:\nDevelop and maintain web applications using Python and TypeScript. Collaborate with cross-functional teams, ensure code quality, debug technical issues, and contribute to scalable system architectures.\n\nRequirements:\n- Strong proficiency in Python and TypeScript\n- Experience with React.js and Node.js\n- Knowledge of PostgreSQL and MongoDB\n- Experience with Docker and AWS\n- Understanding of RESTful APIs and microservices"
}
```

### Example Response

```json
{
    "success": true,
    "user_id": "22c91dc9-4238-499b-a107-5b1abf3b919c",
    "original_profile": {
        "name": "RISHIIKESH S K",
        "email": "rishiikeshsk@gmail.com",
        "skills": ["Go", "Java", "Python", "TypeScript", "React.js", "Node.js"],
        "experience_summary": "Experienced Full Stack Web Developer..."
    },
    "optimized_resume": {
        "name": "RISHIIKESH S K",
        "email": "rishiikeshsk@gmail.com",
        "summary": "Full Stack Developer with expertise in Python and TypeScript...",
        "experience": [
            {
                "title": "Research Intern",
                "company": "Sony SSUP",
                "bullets": [
                    "Developed scalable backend systems using Node.js and TypeScript",
                    "Integrated REST APIs and implemented Redis caching strategies"
                ]
            }
        ],
        "skills": ["Python", "TypeScript", "React.js", "Node.js", "PostgreSQL", "Docker", "AWS"]
    },
    "pdf_path": "",
    "pdf_url": "https://wbdlwopqghndjeknrbrm.supabase.co/storage/v1/object/sign/Resume/22c91dc9.pdf?token=...",
    "recruiter_email": "recruiter@michaelpage.com",
    "application_status": "ready",
    "processing_time_ms": 15234,
    "message": "Resume generated successfully"
}
```

### cURL Example

```bash
curl -X POST http://localhost:8000/agent4/generate-resume \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "22c91dc9-4238-499b-a107-5b1abf3b919c",
    "job_description": "Full Stack Developer at TechCorp. Requirements: Python, TypeScript, React, Node.js, PostgreSQL, Docker, AWS."
  }'
```

---

## 3. Generate Application Responses

Generates copy-paste ready responses for common job application questions.

**Endpoint:** `POST /agent4/generate-responses`

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | ✅ | UUID of the user from Supabase profiles table |
| `job_description` | string | ✅ | Target job description text |
| `company_name` | string | ✅ | Name of the company applying to |
| `job_title` | string | ✅ | Title of the position |
| `additional_context` | string | ❌ | Any additional context or requirements |

### Example Request

```json
{
    "user_id": "22c91dc9-4238-499b-a107-5b1abf3b919c",
    "company_name": "Michael Page",
    "job_title": "Full Stack Developer",
    "job_description": "Develop and maintain web applications using Python and TypeScript. Collaborate with cross-functional teams, ensure code quality, debug technical issues, and contribute to scalable system architectures.",
    "additional_context": "Remote position, immediate joining preferred"
}
```

### Example Response

```json
{
    "success": true,
    "user_id": "22c91dc9-4238-499b-a107-5b1abf3b919c",
    "company_name": "Michael Page",
    "job_title": "Full Stack Developer",
    "responses": {
        "why_join_company": "I am excited about the opportunity to join Michael Page because of its reputation as a leading recruitment firm that values innovation and technical excellence. The chance to work on scalable web applications using Python and TypeScript aligns perfectly with my passion for building robust, high-performance systems. I am particularly drawn to the collaborative culture and the opportunity to contribute to cross-functional teams.",
        
        "about_yourself": "I am a Full Stack Web Developer currently pursuing Computer Science at Amrita Vishwa Vidya Peetham with a CGPA of 8.86. I have hands-on experience as a Research Intern at Sony SSUP, where I built scalable backend systems using Next.js and Node.js with TypeScript. My expertise spans across Python, TypeScript, React.js, and various database technologies including PostgreSQL and MongoDB.",
        
        "relevant_skills": "My technical expertise includes:\n- **Languages:** Python, TypeScript, JavaScript, Go, Java\n- **Frontend:** React.js, Next.js\n- **Backend:** Node.js, REST APIs, Redis caching\n- **Databases:** PostgreSQL, MongoDB, InfluxDB\n- **DevOps:** Docker, AWS, Git\n- **Real-time Systems:** Server-Sent Events, IIoT data architectures",
        
        "work_experience": "At Sony SSUP, I worked as a Research Intern where I:\n- Developed scalable backend systems using Next.js and Node.js (TypeScript)\n- Integrated REST APIs and implemented Redis caching strategies to optimize performance\n- Designed real-time IIoT data architectures utilizing PostgreSQL, InfluxDB, and GraphDB\n- Implemented Server-Sent Events for real-time data streaming",
        
        "why_good_fit": "I am a strong fit for this Full Stack Developer role because my experience directly aligns with your requirements. I have hands-on experience with Python and TypeScript, have built applications using React.js and Node.js, and am proficient with PostgreSQL and MongoDB. My experience with Docker and cloud technologies, combined with my understanding of RESTful APIs and microservices architecture, makes me well-equipped to contribute from day one.",
        
        "problem_solving": "During my internship at Sony SSUP, I faced a challenge with real-time data synchronization across multiple IoT devices. The existing system had latency issues and data inconsistencies. I designed and implemented a solution using Server-Sent Events combined with Redis caching, which reduced latency by 60% and ensured data consistency across all connected devices. This experience taught me the importance of systematic debugging and iterative optimization.",
        
        "additional_info": "I am passionate about continuous learning and staying updated with the latest technologies. I actively contribute to open-source projects and enjoy solving complex technical challenges. My academic background combined with practical industry experience has given me a strong foundation in both theoretical concepts and real-world application development.",
        
        "availability": "I am available for immediate joining and am flexible with remote work arrangements. I am based in Coimbatore, Tamil Nadu, and am open to relocation if required. I can commit to full-time employment and am excited to start contributing to the team as soon as possible."
    },
    "processing_time_ms": 8542,
    "message": "Application responses generated successfully"
}
```

### cURL Example

```bash
curl -X POST http://localhost:8000/agent4/generate-responses \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "22c91dc9-4238-499b-a107-5b1abf3b919c",
    "company_name": "Google",
    "job_title": "Software Engineer",
    "job_description": "Build next-generation technologies that change how billions of users connect, explore, and interact.",
    "additional_context": "L3 position, Mountain View"
  }'
```

---

## 4. Analyze Rejection

Analyzes why a resume was rejected and learns from the failure.

**Endpoint:** `POST /agent4/analyze-rejection`

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | ✅ | UUID of the user |
| `job_description` | string | ✅ | Job description that led to rejection |
| `rejection_reason` | string | ❌ | Optional rejection feedback from company |

### Example Request

```json
{
    "user_id": "22c91dc9-4238-499b-a107-5b1abf3b919c",
    "job_description": "Senior Backend Engineer at TechCorp. Requirements: 5+ years experience, system design, Kubernetes, distributed systems.",
    "rejection_reason": "Looking for more senior candidates"
}
```

### Example Response

```json
{
    "success": true,
    "user_id": "22c91dc9-4238-499b-a107-5b1abf3b919c",
    "gap_analysis": "1. **Experience Level Mismatch:** The candidate is a current student with intern experience, while the role requires 5+ years of professional experience.\n2. **Missing Senior-Level Keywords:** Resume lacks mentions of 'system design', 'technical leadership', 'mentorship'.\n3. **Kubernetes Gap:** No demonstrated experience with Kubernetes or container orchestration.",
    "recommendations": [
        "Target entry-level or junior positions instead of senior roles",
        "Gain Kubernetes experience through projects or certifications",
        "Build more production-level distributed systems experience"
    ],
    "anti_pattern_created": true
}
```

### cURL Example

```bash
curl -X POST http://localhost:8000/agent4/analyze-rejection \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "22c91dc9-4238-499b-a107-5b1abf3b919c",
    "job_description": "Senior Backend Engineer requiring 5+ years experience",
    "rejection_reason": "Insufficient experience"
  }'
```

---

## Running the Server

```bash
cd /Users/meenakshiganesan/Karthik/Erflog/career-flow-ai/backend
uvicorn main:app --reload --port 8000
```

---

## Environment Variables

Required in `backend/.env`:

```properties
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=https://your-project.supabase.co/
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=ai-verse
```

---

## Architecture

```
Agent 4 - Application Operative
├── state.py        # TypedDict state definitions
├── tools.py        # Core functions (rewrite, upload, generate responses)
├── pdf_engine.py   # PDF generation with Jinja2 + WeasyPrint
├── graph.py        # LangGraph workflow (mutate → render → hunt)
├── evolution.py    # Rejection analysis and learning loop
├── schemas.py      # Pydantic request/response models
├── service.py      # Business logic layer
├── router.py       # FastAPI endpoints
└── __init__.py     # Exports
```

---

## Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   MUTATE    │───▶│   RENDER    │───▶│    HUNT     │
│  (Gemini)   │    │ (WeasyPrint)│    │ (Hunter.io) │
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
  Rewrite resume    Generate PDF      Find recruiter
  for ATS          & upload to S3    email
```
