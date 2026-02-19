"""
Golden Dataset Builder - Match Resumes to LIVE Jobs via JSearch API
====================================================================
Parses 10 PDF resumes, extracts skills via Gemini, then calls JSearch
RapidAPI to fetch 5 real-time relevant jobs for each resume.

Usage:
    python match_resumes.py

Output:
    - golden_labels.csv    (10 resumes × 5 live jobs = 50 labeled pairs)
    - resume_metadata.csv  (extracted profile data for each resume)
"""

import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import csv
import json
import time
import requests
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from pypdf import PdfReader

# LangChain for structured extraction
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# ============================================================================
# CONFIG
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
RESUMES_DIR = SCRIPT_DIR / "resumes"
OUTPUT_LABELS = SCRIPT_DIR / "golden_labels.csv"
OUTPUT_METADATA = SCRIPT_DIR / "resume_metadata.csv"
TOP_K = 5  # 5 live jobs per resume

# Load env from backend
BACKEND_ENV = SCRIPT_DIR.parent / "backend" / ".env"
load_dotenv(BACKEND_ENV)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY not found in backend/.env")
    sys.exit(1)

if not RAPIDAPI_KEY:
    print("❌ RAPIDAPI_KEY not found in backend/.env")
    sys.exit(1)


# ============================================================================
# STEP 1: Parse PDF
# ============================================================================

def parse_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text.strip()


# ============================================================================
# STEP 2: Extract Structured Data (Gemini)
# ============================================================================

def extract_resume_data(text: str) -> dict:
    """Extract name, email, skills, experience from resume text."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        google_api_key=GEMINI_API_KEY
    )
    parser = JsonOutputParser()

    prompt = PromptTemplate(
        template="""
        You are an expert Resume Parser.
        Extract the following from the resume into a JSON object:
        - "name": string (full name)
        - "email": string (email address, or null if not found)
        - "skills": array of strings (flat list of ALL technical skills)
        - "experience_summary": string (2-3 sentence summary of experience)
        - "category": string (one of: "fresher", "backend", "frontend", "data_science", "fullstack", "devops")
        - "target_role": string (the single BEST job title to search for, e.g. "Frontend Developer", "Data Scientist", "Backend Engineer")

        RULES:
        1. "skills" must be a FLAT LIST of strings like ["Python", "React", "Docker"]
        2. "category" should reflect the PRIMARY career focus based on skills and experience
        3. "target_role" should be the most specific, searchable job title
        4. Return ONLY valid JSON, no markdown

        RESUME TEXT:
        {text}

        Return the JSON object:
        """,
        input_variables=["text"],
    )

    chain = prompt | llm | parser

    try:
        data = chain.invoke({"text": text})

        # Flatten skills (handle edge cases)
        raw_skills = data.get("skills", [])
        if isinstance(raw_skills, list):
            flat = []
            for item in raw_skills:
                if isinstance(item, str):
                    flat.append(item)
                elif isinstance(item, dict):
                    for v in item.values():
                        if isinstance(v, list):
                            flat.extend([str(x) for x in v])
                        else:
                            flat.append(str(v))
            data["skills"] = list(set(flat))

        return data
    except Exception as e:
        print(f"   ⚠️ Extraction error: {e}")
        return {
            "name": None, "email": None,
            "skills": [], "experience_summary": "Extraction failed",
            "category": "unknown", "target_role": "Software Developer"
        }


# ============================================================================
# STEP 3: Search Live Jobs via JSearch RapidAPI
# ============================================================================

def search_jsearch_jobs(query: str, num_results: int = 5, max_retries: int = 3) -> list[dict]:
    """
    Search for jobs using RapidAPI JSearch with retry logic.
    Directly adapted from agent_2_market/tools.py
    """
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    params = {
        "query": query,
        "page": "1",
        "num_pages": "1",
        "country": "in",
        "date_posted": "month"
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=45)
            response.raise_for_status()

            data = response.json()
            raw_jobs = data.get("data", [])[:num_results]

            jobs = []
            for job in raw_jobs:
                # Build location string
                city = job.get("job_city", "")
                state = job.get("job_state", "")
                country_name = job.get("job_country", "")
                location_parts = [p for p in [city, state, country_name] if p]
                location = ", ".join(location_parts)

                # Parse posted date
                posted_at = None
                if job.get("job_posted_at_timestamp"):
                    try:
                        posted_at = datetime.fromtimestamp(
                            job["job_posted_at_timestamp"],
                            tz=timezone.utc
                        ).isoformat()
                    except:
                        pass

                jobs.append({
                    "job_id": job.get("job_id", ""),
                    "title": job.get("job_title", "Unknown Title"),
                    "company": job.get("employer_name", "Unknown Company"),
                    "link": job.get("job_apply_link") or job.get("job_google_link", ""),
                    "description": job.get("job_description", ""),
                    "location": location,
                    "posted_at": posted_at,
                    "source": "JSearch (Live)",
                    "platform": job.get("job_publisher", "JSearch"),
                })

            return jobs

        except requests.exceptions.RequestException as e:
            wait_time = 3 * attempt
            if attempt < max_retries:
                print(f"   ⚠️ Attempt {attempt}/{max_retries} failed: {str(e)[:50]}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"   ❌ All {max_retries} attempts failed for query: {query[:40]}")
                return []
        except Exception as e:
            print(f"   ⚠️ JSearch error: {str(e)}")
            return []

    return []


def build_search_query(extracted: dict) -> str:
    """Build an optimized search query from extracted resume data."""
    target_role = extracted.get("target_role", "Software Developer")
    # Add top 3 skills for specificity
    top_skills = extracted.get("skills", [])[:3]
    if top_skills:
        return f"{target_role} {' '.join(top_skills)} India"
    return f"{target_role} India"


# ============================================================================
# STEP 4: Assess Relevance with Gemini
# ============================================================================

def assess_relevance(resume_data: dict, job: dict) -> tuple:
    """
    Use Gemini to assess if a job is relevant to a resume.
    Returns (is_relevant: int, reason: str)
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        google_api_key=GEMINI_API_KEY
    )
    parser = JsonOutputParser()

    prompt = PromptTemplate(
        template="""
        You are an expert Job-Resume Matcher for building a golden evaluation dataset.
        Assess whether this job is RELEVANT to the candidate's resume.

        CANDIDATE PROFILE:
        - Name: {name}
        - Category: {category}
        - Target Role: {target_role}
        - Skills: {skills}
        - Experience: {experience}

        JOB POSTING:
        - Title: {job_title}
        - Company: {job_company}
        - Description: {job_description}

        RULES for labeling:
        - is_relevant = 1 if the candidate's skills and experience are a reasonable match for the job requirements
        - is_relevant = 0 if there is a clear MISMATCH (e.g., job needs 10+ years but candidate is a fresher, 
          job requires completely different tech stack, job is for a fundamentally different role)
        - Be realistic but not overly strict. If 50%+ of key skills overlap, mark as relevant.
        - Consider experience level: a fresher applying to a Senior/Lead role = NOT relevant

        Return a JSON object:
        {{
            "is_relevant": 0 or 1,
            "reason": "Brief 1-sentence explanation of why relevant or not"
        }}

        Return ONLY valid JSON, no markdown:
        """,
        input_variables=["name", "category", "target_role", "skills", "experience",
                         "job_title", "job_company", "job_description"],
    )

    chain = prompt | llm | parser

    try:
        result = chain.invoke({
            "name": resume_data.get("name", "Unknown"),
            "category": resume_data.get("category", "unknown"),
            "target_role": resume_data.get("target_role", "Software Developer"),
            "skills": ", ".join(resume_data.get("skills", [])[:15]),
            "experience": resume_data.get("experience_summary", "N/A"),
            "job_title": job["title"],
            "job_company": job["company"],
            "job_description": job["description"][:2000],
        })
        return (int(result.get("is_relevant", 1)), result.get("reason", "Auto-assessed"))
    except Exception as e:
        print(f"      ⚠️ Relevance check failed: {e}")
        return (1, "Assessment failed - defaulted to relevant")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("  🎯 GOLDEN DATASET BUILDER - Resume ↔ LIVE Job Matcher")
    print("  📡 Using JSearch RapidAPI for real-time job fetching")
    print("=" * 70)
    print()

    # --- Load Resumes ---
    pdf_files = sorted(RESUMES_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in {RESUMES_DIR}")
        sys.exit(1)

    print(f"📄 Found {len(pdf_files)} resumes:")
    for f in pdf_files:
        print(f"   • {f.name}")
    print()

    # --- Process Each Resume ---
    all_resume_data = []
    all_labels = []
    total_jobs = 0

    for idx, pdf_path in enumerate(pdf_files):
        resume_id = pdf_path.stem  # e.g., "fresher_01"
        print(f"{'─' * 60}")
        print(f"📋 [{idx + 1}/{len(pdf_files)}] Processing: {resume_id}")
        print(f"{'─' * 60}")

        # 1. Parse PDF
        print("   📖 Parsing PDF...")
        resume_text = parse_pdf(str(pdf_path))
        print(f"   ✅ Extracted {len(resume_text)} characters")

        # 2. Extract structured data
        print("   🤖 Extracting profile with Gemini...")
        extracted = extract_resume_data(resume_text)
        print(f"   ✅ Name: {extracted.get('name')}")
        print(f"   ✅ Skills: {', '.join(extracted.get('skills', [])[:8])}...")
        print(f"   ✅ Category: {extracted.get('category')}")
        print(f"   ✅ Target Role: {extracted.get('target_role')}")

        # 3. Build search query
        query = build_search_query(extracted)
        print(f"   🔎 Search Query: \"{query}\"")

        # 4. Call JSearch API for live jobs (try multiple queries to ensure 5)
        target_role = extracted.get("target_role", "Software Developer")
        category = extracted.get("category", "software")
        skills = extracted.get("skills", [])

        query_variants = [
            query,                                                    # Full: "Backend Engineer SQL Terraform PostgreSQL India"
            f"{target_role} {category} India",                        # Role+category: "Backend Engineer backend India"
            f"{target_role} India",                                   # Role only: "Backend Engineer India"
            f"{category} developer India",                            # Broad: "backend developer India"
        ]

        live_jobs = []
        seen_job_ids = set()

        for qi, q in enumerate(query_variants):
            if len(live_jobs) >= TOP_K:
                break
            needed = TOP_K - len(live_jobs)
            print(f"   📡 Query {qi+1}: \"{q}\" (need {needed} more)...")
            fetched = search_jsearch_jobs(q, num_results=needed + 2)  # fetch extra to account for dupes
            for job in fetched:
                if job["job_id"] not in seen_job_ids and len(live_jobs) < TOP_K:
                    seen_job_ids.add(job["job_id"])
                    live_jobs.append(job)
            print(f"   ✅ Running total: {len(live_jobs)}/{TOP_K} unique jobs")
            if len(live_jobs) < TOP_K and qi < len(query_variants) - 1:
                time.sleep(1)  # brief delay between queries

        print(f"   {'✅' if len(live_jobs) >= TOP_K else '⚠️'} Final: {len(live_jobs)} live jobs")

        # 5. Assess relevance and record matches
        if live_jobs:
            print(f"\n   🏆 Top {len(live_jobs)} LIVE Job Matches for {resume_id}:")
            print(f"   {'Rank':<5} {'Label':<7} {'Title':<35} {'Company':<22} {'Reason'}")
            print(f"   {'─' * 95}")

            for rank, job in enumerate(live_jobs, 1):
                # Assess relevance with Gemini
                is_relevant, reason = assess_relevance(extracted, job)

                label_str = "✅ 1" if is_relevant else "❌ 0"
                title_short = job["title"][:34]
                company_short = job["company"][:21]
                reason_short = reason[:40]
                print(f"   {rank:<5} {label_str:<7} {title_short:<35} {company_short:<22} {reason_short}")

                all_labels.append({
                    "resume_id": resume_id,
                    "resume_name": extracted.get("name", ""),
                    "resume_category": extracted.get("category", ""),
                    "search_query": query,
                    "job_rank": rank,
                    "job_id": job["job_id"],
                    "job_title": job["title"],
                    "job_company": job["company"],
                    "job_location": job["location"],
                    "job_link": job["link"],
                    "job_posted_at": job.get("posted_at", ""),
                    "job_description_preview": job["description"][:500],
                    "source": job["source"],
                    "is_relevant": is_relevant,
                    "relevance_reason": reason
                })
                total_jobs += 1

        # Save resume metadata
        all_resume_data.append({
            "resume_id": resume_id,
            "name": extracted.get("name", ""),
            "email": extracted.get("email", ""),
            "category": extracted.get("category", ""),
            "target_role": extracted.get("target_role", ""),
            "skills": "; ".join(extracted.get("skills", [])),
            "experience_summary": extracted.get("experience_summary", ""),
            "search_query_used": query,
            "num_skills": len(extracted.get("skills", [])),
            "jobs_found": len(live_jobs),
        })

        print()

        # Rate limit: small delay between API calls
        if idx < len(pdf_files) - 1:
            print("   ⏳ Waiting 2s (API rate limit)...")
            time.sleep(2)

    # --- Write Output CSVs ---
    print("=" * 70)
    print("  📊 WRITING OUTPUT FILES")
    print("=" * 70)

    def safe_write_csv(filepath, fieldnames, rows):
        """Write CSV, handling PermissionError if file is open in editor."""
        temp_path = filepath.parent / f"_temp_{filepath.name}"
        # Write to temp file first
        with open(temp_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        # Try to replace the original
        try:
            import shutil
            shutil.move(str(temp_path), str(filepath))
            print(f"   ✅ {filepath.name} ({len(rows)} rows)")
        except PermissionError:
            # File locked (open in editor) — save as _new file
            alt_path = filepath.parent / f"{filepath.stem}_new{filepath.suffix}"
            import shutil
            shutil.move(str(temp_path), str(alt_path))
            print(f"   ⚠️ {filepath.name} is locked! Saved as {alt_path.name} ({len(rows)} rows)")
            print(f"   💡 Close {filepath.name} in VS Code, then rename {alt_path.name}")

    # Golden Labels
    safe_write_csv(OUTPUT_LABELS, [
        "resume_id", "resume_name", "resume_category", "search_query",
        "job_rank", "job_id", "job_title", "job_company", "job_location",
        "job_link", "job_posted_at", "job_description_preview",
        "source", "is_relevant", "relevance_reason"
    ], all_labels)

    # Resume Metadata
    safe_write_csv(OUTPUT_METADATA, [
        "resume_id", "name", "email", "category", "target_role",
        "skills", "experience_summary", "search_query_used",
        "num_skills", "jobs_found"
    ], all_resume_data)

    # --- Summary ---
    relevant_count = sum(1 for l in all_labels if l["is_relevant"] == 1)
    non_relevant_count = sum(1 for l in all_labels if l["is_relevant"] == 0)

    print()
    print("=" * 70)
    print("  ✅ GOLDEN DATASET COMPLETE!")
    print("=" * 70)
    print(f"  • Resumes processed: {len(pdf_files)}")
    print(f"  • Total LIVE jobs fetched: {total_jobs}")
    print(f"  • Average jobs per resume: {total_jobs / len(pdf_files):.1f}")
    print(f"  • ✅ Relevant (1): {relevant_count}")
    print(f"  • ❌ Non-relevant (0): {non_relevant_count}")
    print(f"  • Label distribution: {relevant_count}/{total_jobs} = {relevant_count/max(total_jobs,1)*100:.0f}% relevant")
    print()
    print("  📝 NEXT STEPS:")
    print(f"  1. Open {OUTPUT_LABELS.name}")
    print(f"  2. Review Gemini's auto-labels and adjust if needed")
    print(f"  3. Both relevant(1) and non-relevant(0) are kept for evaluation")
    print(f"  4. This becomes your ground truth for Day 2 benchmarking")
    print()


if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception as e:
        print(f"\n\n!!! SCRIPT ERROR: {e}")
        with open(SCRIPT_DIR / "error.log", "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        print(f"Full traceback saved to error.log")
        sys.exit(1)
