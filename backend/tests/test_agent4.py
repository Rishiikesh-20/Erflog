import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# ------------------------------------------------------------------
# IMPORT YOUR AGENT MODULE HERE
# Adjust these imports to match your actual folder structure
# Example: from backend.agents.agent_4_operative.main import OperativeAgent
# ------------------------------------------------------------------
# from agents.agent_4_operative.core import OperativeAgent  <-- UNCOMMENT/ADJUST THIS

# MOCK CLASS FOR TESTING (Remove this if importing your actual class)
class OperativeAgent:
    """Mock structure of Agent 4 based on project description"""
    def __init__(self, llm_client, db_client):
        self.llm = llm_client
        self.db = db_client

    def tailor_resume(self, base_resume: str, job_description: str) -> str:
        if not base_resume or not job_description:
            raise ValueError("Missing resume or job description")
        # Logic to call LLM would go here
        return "Tailored Resume Content"

    def generate_cover_letter(self, user_profile: dict, job_details: dict) -> str:
        if "name" not in user_profile:
            raise KeyError("User profile missing name")
        # Logic to call LLM would go here
        return f"Dear Hiring Manager, I am {user_profile['name']}..."

    def submit_application(self, application_packet: dict) -> bool:
        required_keys = ["resume", "cover_letter", "job_id"]
        if not all(k in application_packet for k in required_keys):
            return False
        # Logic to log submission to DB would go here
        return True

# ------------------------------------------------------------------
# TEST SUITE
# ------------------------------------------------------------------

@pytest.fixture
def mock_dependencies():
    """Setup mock LLM and DB clients to avoid real API calls"""
    mock_llm = Mock()
    mock_db = Mock()
    return mock_llm, mock_db

@pytest.fixture
def agent(mock_dependencies):
    """Initialize Agent 4 with mocked dependencies"""
    llm, db = mock_dependencies
    return OperativeAgent(llm, db)

class TestAgent4Operative:

    # --- TEST 1: Resume Tailoring (Core Feature) ---
    def test_tailor_resume_success(self, agent):
        """Test if the agent successfully accepts a resume and JD to produce a new resume"""
        base_resume = "Skilled in Python and AWS."
        job_desc = "Looking for Python and Azure expert."
        
        # Mock the LLM response within the agent (if applicable)
        agent.llm.generate.return_value = "Skilled in Python and Azure."
        
        result = agent.tailor_resume(base_resume, job_desc)
        
        # Assertions
        assert result is not None
        assert isinstance(result, str)
        # Verify it didn't return an empty string
        assert len(result) > 0 

    def test_tailor_resume_missing_input(self, agent):
        """Test error handling when inputs are missing"""
        with pytest.raises(ValueError):
            agent.tailor_resume("", "Valid JD")

    # --- TEST 2: Cover Letter Generation (Application Kit) ---
    def test_generate_cover_letter_content(self, agent):
        """Test if a personalized cover letter is generated"""
        user_profile = {"name": "Rishiikesh", "skills": ["Next.js", "Go"]}
        job_details = {"role": "Backend Engineer", "company": "Sony"}
        
        result = agent.generate_cover_letter(user_profile, job_details)
        
        assert "Rishiikesh" in result
        assert isinstance(result, str)
        # Ensure it's substantial content
        assert len(result) > 20 

    def test_generate_cover_letter_missing_data(self, agent):
        """Test failure when user profile data is incomplete"""
        incomplete_profile = {"skills": ["Java"]} # Missing 'name'
        job_details = {"role": "Dev", "company": "TestCorp"}
        
        with pytest.raises(KeyError):
            agent.generate_cover_letter(incomplete_profile, job_details)

    # --- TEST 3: Application Submission Logic ---
    def test_submit_application_success(self, agent):
        """Test the logic that finalizes the application package"""
        packet = {
            "resume": "Final_Resume.pdf",
            "cover_letter": "Cover_Letter.txt",
            "job_id": "12345",
            "timestamp": datetime.now()
        }
        
        success = agent.submit_application(packet)
        assert success is True

    def test_submit_application_incomplete_packet(self, agent):
        """Test rejection of incomplete application packets"""
        bad_packet = {
            "resume": "Just_Resume.pdf"
            # Missing cover_letter and job_id
        }
        
        success = agent.submit_application(bad_packet)
        assert success is False

   # --- TEST 4: Integration Mock (End-to-End Flow) ---
    # We use patch.object to mock the method on the class directly, 
    # regardless of where it is located (Mock class or Real class).
    @patch.object(OperativeAgent, 'tailor_resume')
    def test_full_application_flow(self, mock_tailor, agent):
        """Simulate the full flow: Tailor Resume -> Generate Letter -> Submit"""
        
        # 1. Setup Data
        raw_resume = "My generic resume"
        jd = "Job requirements"
        
        # 2. Mock the internal method response
        mock_tailor.return_value = "Tailored Resume V2"
        
        # 3. Execute 'tailor_resume' (step 1 of agent flow)
        tailored = agent.tailor_resume(raw_resume, jd)
        
        # 4. Verify step 1 output
        assert tailored == "Tailored Resume V2"
        
        # 5. Create packet based on step 1
        packet = {
            "resume": tailored,
            "cover_letter": "Auto-generated letter",
            "job_id": "JOB-101",
             # Adding timestamp to match the success logic if strict
            "timestamp": datetime.now()
        }
        
        # 6. Verify submission
        submission_status = agent.submit_application(packet)
        assert submission_status is True