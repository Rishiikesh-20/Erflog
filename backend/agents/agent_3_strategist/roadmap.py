import os
import json
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY must be set in the environment or a .env file")

client = genai.Client(api_key=GEMINI_API_KEY)

def generate_gap_roadmap(user_skills_text: str, job_description: str):
    """
    Generates a visual dependency graph (DAG) for the learning roadmap with nodes and edges.
    Returns graph structure optimized for visualization with D3.js or Cytoscape.
    """
    prompt = f"""
    You are an expert Technical Curriculum Architect specializing in skill gap analysis.
    
    TASK:
    Analyze the gap between User Skills and Job Requirements.
    Create a 3-day learning roadmap as a DIRECTED ACYCLIC GRAPH (DAG).
    
    INPUTS:
    Current Skills: "{user_skills_text}"
    Target Job: "{job_description}"
    
    REQUIREMENTS:
    1. Identify 4-6 critical learning topics/concepts
    2. Create a dependency graph showing which topics must be learned before others
    3. Distribute topics across 3 days (assign to day 1, 2, or 3)
    4. Include description, type (concept/practice/project), and resources for each topic
    5. Create edges showing dependencies between topics (source -> target means: source must be learned first)
    
    OUTPUT FORMAT (JSON ONLY - NO MARKDOWN):
    {{
      "missing_skills": ["Skill 1", "Skill 2", "Skill 3"],
      "graph": {{
        "nodes": [
          {{
            "id": "node1",
            "label": "Topic/Concept Name",
            "day": 1,
            "type": "concept",
            "description": "What will be learned and why it matters"
          }},
          {{
            "id": "node2",
            "label": "Practical Implementation",
            "day": 2,
            "type": "practice",
            "description": "Hands-on exercises and coding tasks"
          }},
          {{
            "id": "node3",
            "label": "Advanced Patterns",
            "day": 3,
            "type": "project",
            "description": "Build a small project applying all concepts"
          }}
        ],
        "edges": [
          {{ "source": "node1", "target": "node2" }},
          {{ "source": "node2", "target": "node3" }}
        ]
      }},
      "resources": {{
        "node1": [
          {{ "name": "Official Docs", "url": "https://..." }},
          {{ "name": "Tutorial Video", "url": "https://www.youtube.com/results?search_query=..." }}
        ],
        "node2": [
          {{ "name": "Hands-on Guide", "url": "https://..." }},
          {{ "name": "Code Examples", "url": "https://github.com/..." }}
        ],
        "node3": [
          {{ "name": "Project Ideas", "url": "https://..." }},
          {{ "name": "Best Practices", "url": "https://..." }}
        ]
      }}
    }}
    
    CRITICAL: Return ONLY valid JSON, no markdown, no explanations.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        
        # Validate graph structure
        if 'graph' in result and 'nodes' in result['graph']:
            return result
        else:
            raise ValueError("Invalid graph structure in response")
            
    except Exception as e:
        print(f"❌ Roadmap Graph Generation Failed: {e}")
        # Return a fallback structured graph
        return {
            "missing_skills": ["Core Concepts", "Practical Implementation"],
            "graph": {
                "nodes": [
                    {
                        "id": "node1",
                        "label": "Understand Job Requirements",
                        "day": 1,
                        "type": "concept",
                        "description": "Analyze the job description and identify key requirements"
                    },
                    {
                        "id": "node2",
                        "label": "Build Foundation Skills",
                        "day": 2,
                        "type": "practice",
                        "description": "Practice fundamental concepts required for the role"
                    },
                    {
                        "id": "node3",
                        "label": "Practice with Examples",
                        "day": 3,
                        "type": "project",
                        "description": "Work on practical projects to solidify learning"
                    }
                ],
                "edges": [
                    {"source": "node1", "target": "node2"},
                    {"source": "node2", "target": "node3"}
                ]
            },
            "resources": {
                "node1": [{"name": "Official Docs", "url": "https://docs.example.com"}],
                "node2": [{"name": "Tutorial", "url": "https://example.com/tutorial"}],
                "node3": [{"name": "Project Guide", "url": "https://example.com/projects"}]
            }
        }