import os
from dotenv import load_dotenv
from pinecone import Pinecone
from google import genai

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INDEX_NAME = os.getenv("INDEX_NAME", "ai-verse")

if not PINECONE_API_KEY or not GEMINI_API_KEY:
  raise RuntimeError("PINECONE_API_KEY and GEMINI_API_KEY must be set in the environment or a .env file")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)
client = genai.Client(api_key=GEMINI_API_KEY)

jobs_data = [
  {
    "id": 1,
    "title": "Full Stack Developer (Python + TypeScript)",
    "company_name": "Michael Page",
    "location": "Bengaluru, Karnataka, India",
    "description": "Develop and maintain web applications using Python and TypeScript. Collaborate with cross-functional teams, ensure code quality, debug technical issues, and contribute to scalable system architectures.",
    "link_to_apply": "null"
  },
  {
    "id": 2,
    "title": "Software Development Engineer, Checkout Purchase Experience",
    "company_name": "Amazon",
    "location": "Bengaluru, Karnataka, India",
    "description": "Work with the Checkout Experience team to deliver high-visibility innovation for Address & Checkout services. Develop multi-tiered, low-latency, highly resilient distributed systems. Requires 3+ years experience, proficiency in at least one programming language, and system design experience.",
    "link_to_apply": "https://www.linkedin.com/jobs/view/4341559296/"
  },
  {
    "id": 3,
    "title": "Full Stack Engineer",
    "company_name": "Eazy AI",
    "location": "Brookefield Bengaluru, Karnataka, India",
    "description": "Develop and maintain the MERN stack-based chat SDK and admin portal. Implement microservices APIs, webhook systems, and integrate AI models for chat and recommendations. Requires 1-2 years experience with React, Node.js, and TypeScript.",
    "link_to_apply": "https://www.linkedin.com/jobs/view/4350828611/"
  },
  {
    "id": 4,
    "title": "Software Development Engineer (Java Fullstack)",
    "company_name": "Adobe",
    "location": "Bengaluru East, Karnataka, India",
    "description": "Work on Adobe Pass (TV Everywhere industry). Design and maintain end-to-end web apps. Requires 4+ years experience, proficiency in Java, Spring Boot, Microservices, and frontend tech like JavaScript/TypeScript/React. Knowledge of distributed systems (Spark, Hadoop) and security (OAuth2, JWT) is essential.",
    "link_to_apply": "https://www.linkedin.com/jobs/view/4324990234/"
  },
  {
    "id": 5,
    "title": "SDE - I ( Backend )",
    "company_name": "Eloelo",
    "location": "Bengaluru, Karnataka, India",
    "description": "Build Eloelo Live Streaming Games. Design and develop highly scalable, reliable, and fault-tolerant systems. Requires strong knowledge of Data Structures/Algorithms, OOP, Concurrency, Java, and Distributed queue systems like Kafka.",
    "link_to_apply": "null"
  },
  {
    "id": 6,
    "title": "Technical Lead - Backend",
    "company_name": "Kuku FM",
    "location": "Bengaluru, Karnataka, India",
    "description": "Design and maintain scalable payments infrastructure handling millions of transactions. Manage multiple payment gateways (Razorpay, Stripe, etc.) and own the end-to-end transaction lifecycle. Involves high availability architecture and compliance with RBI guidelines.",
    "link_to_apply": "null"
  },
  {
    "id": 7,
    "title": "Senior Software Engineer (Backend)",
    "company_name": "HackerEarth",
    "location": "Bengaluru, Karnataka, India",
    "description": "Build and scale systems for a developer assessment platform. Requires 3+ years experience with Node.js, Python, or Go. Must have experience with RESTful APIs, databases (MySQL, ElasticSearch, Redis), and cloud platforms (AWS/GCP/Azure).",
    "link_to_apply": "null"
  },
  {
    "id": 8,
    "title": "DevOps Engineer",
    "company_name": "Sustainability Economics.ai",
    "location": "Bengaluru, Karnataka, India",
    "description": "Design and optimize cloud-based infrastructure and pipelines for an AI + clean energy platform. Requires 2-5 years experience with AWS, CI/CD, GitOps (ArgoCD), Terraform/CloudFormation, and Kubernetes/EKS.",
    "link_to_apply": "null"
  },
  {
    "id": 9,
    "title": "Software Engineer (Site Reliability Engineer)",
    "company_name": "Anyscale",
    "location": "Bengaluru, Karnataka, India",
    "description": "Ensure smooth operation of user-facing services and the Ray ecosystem. Involves provisioning, cost management, observability (metrics, logging, tracing), and establishing SLOs. Focus on distributed computing.",
    "link_to_apply": "null"
  },
  {
    "id": 10,
    "title": "DevOps/ Software Engineer",
    "company_name": "Broadridge India",
    "location": "Greater Bengaluru Area, India",
    "description": "Design and develop solutions for technology needs including systems architecture and application infrastructure. Reviews system requirements, codes, tests, and debugs in an Agile environment.",
    "link_to_apply": "null"
  }
]

vectors_to_upsert = []

print(f"Starting Vectorization for {len(jobs_data)} jobs...")

for job in jobs_data:
    # FIX 1: Used 'company_name' instead of 'company'
    text_to_embed = f"{job['title']} {job['description']} {job['company_name']}"
    
    response = client.models.embed_content(
        model="text-embedding-004",  # 768 dimensions - ensure Pinecone index matches!
        contents=text_to_embed,
    )
    
    vectors_to_upsert.append({
        "id": str(job["id"]), # FIX 2: Converted ID to String
        "values": response.embeddings[0].values,
        "metadata": job
    })

# Batch Upsert
index.upsert(vectors=vectors_to_upsert)
print("✅ Upsert complete. Jobs are live in the Vector DB.")