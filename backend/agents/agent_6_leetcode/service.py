"""
LeetCode Problem Solving Service

Business logic for:
- Loading Blind 75 problems
- Generating AI recommendations with Gemini
- Managing user progress in Supabase
"""

import os
import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

from supabase import create_client

logger = logging.getLogger("LeetCodeService")


class LeetCodeService:
    """Service for LeetCode problem solving features"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # Load problems from JSON file
        self._problems_data = None
        self._all_problems = None
    
    @property
    def problems_data(self) -> List[Dict]:
        """Lazy load problems from JSON file"""
        if self._problems_data is None:
            json_path = Path(__file__).parent / "blind75_problems.json"
            with open(json_path, "r", encoding="utf-8") as f:
                self._problems_data = json.load(f)
        return self._problems_data
    
    @property
    def all_problems(self) -> List[Dict]:
        """Get flat list of all problems"""
        if self._all_problems is None:
            self._all_problems = []
            for category in self.problems_data:
                self._all_problems.extend(category["problems"])
        return self._all_problems
    
    def get_all_problems(self) -> Dict[str, Any]:
        """
        Get all Blind 75 problems organized by category.
        
        Returns:
            Dict with categories and total_count
        """
        return {
            "categories": self.problems_data,
            "total_count": len(self.all_problems)
        }
    
    def get_recommendations(
        self,
        user_id: str,
        quiz_answers: Dict[str, str],
        leetcode_profile: Optional[Dict] = None,
        solved_problem_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Get AI-powered problem recommendations.
        
        Uses Gemini if available, otherwise falls back to local algorithm.
        
        Args:
            user_id: User's UUID
            quiz_answers: Category -> skill level mapping
            leetcode_profile: Optional LeetCode stats
            solved_problem_ids: List of already solved problem IDs
            
        Returns:
            Dict with recommended_ids, source, and optional reasoning
        """
        solved_ids = set(solved_problem_ids or [])
        
        # Try Gemini first
        if self.gemini_api_key:
            try:
                recommended_ids = self._get_gemini_recommendations(
                    quiz_answers,
                    leetcode_profile,
                    solved_ids
                )
                if recommended_ids:
                    return {
                        "recommended_ids": recommended_ids,
                        "source": "gemini"
                    }
            except Exception as e:
                logger.warning(f"Gemini recommendation failed, using fallback: {e}")
        
        # Fallback to local algorithm
        recommended_ids = self._get_local_recommendations(quiz_answers, solved_ids)
        return {
            "recommended_ids": recommended_ids,
            "source": "local"
        }
    
    def _get_gemini_recommendations(
        self,
        quiz_answers: Dict[str, str],
        leetcode_profile: Optional[Dict],
        solved_ids: set
    ) -> List[int]:
        """Use Gemini to generate personalized recommendations"""
        import google.generativeai as genai
        
        genai.configure(api_key=self.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # Build prompt
        total_solved = leetcode_profile.get("total_solved", 0) if leetcode_profile else 0
        easy_solved = leetcode_profile.get("easy_solved", 0) if leetcode_profile else 0
        medium_solved = leetcode_profile.get("medium_solved", 0) if leetcode_profile else 0
        hard_solved = leetcode_profile.get("hard_solved", 0) if leetcode_profile else 0
        
        available_problems = [p for p in self.all_problems if p["id"] not in solved_ids]
        
        prompt = f"""You are an expert DSA coach helping a LeetCode user prepare for coding interviews.

USER PROFILE:
- Total Problems Solved: {total_solved}
- Easy: {easy_solved}, Medium: {medium_solved}, Hard: {hard_solved}

SELF-ASSESSMENT (User's confidence in each topic):
{chr(10).join(f'- {topic}: {level}' for topic, level in quiz_answers.items())}

AVAILABLE PROBLEMS (from Blind 75, excluding already solved):
{chr(10).join(f'ID:{p["id"]} "{p["title"]}" [{p["category"]}] [{p["difficulty"]}]' for p in available_problems)}

YOUR TASK:
Select exactly 30 problems from the available list that would be most beneficial for this user. Consider:
1. Focus MORE on topics where user rated themselves as "weak"
2. For "weak" topics, start with easier problems to build confidence
3. For "okay" topics, include a mix of medium problems
4. For "strong" topics, only include the most important/frequently asked problems
5. Ensure good coverage across different categories
6. Prioritize classic interview problems

RESPONSE FORMAT:
Return ONLY a JSON array of problem IDs, nothing else. Example: [1, 121, 217, 238, ...]"""

        response = model.generate_content(prompt)
        text = response.text
        
        # Parse response
        import re
        json_match = re.search(r'\[[\d,\s]+\]', text)
        if json_match:
            ids = json.loads(json_match.group())
            valid_ids = [
                id for id in ids
                if any(p["id"] == id for p in self.all_problems) and id not in solved_ids
            ]
            return valid_ids[:30]
        
        return []
    
    def _get_local_recommendations(
        self,
        quiz_answers: Dict[str, str],
        solved_ids: set
    ) -> List[int]:
        """Local fallback algorithm for recommendations"""
        available = [p for p in self.all_problems if p["id"] not in solved_ids]
        
        scored = []
        for problem in available:
            score = 50  # Base score
            
            # Get quiz answer for this category (or parent category)
            answer = quiz_answers.get(problem["category"])
            if not answer:
                # Try matching DP -> Dynamic Programming
                category_map = {
                    "DP": "Dynamic Programming",
                    "Dynamic Programming": "Dynamic Programming"
                }
                mapped_cat = category_map.get(problem["category"], problem["category"])
                answer = quiz_answers.get(mapped_cat)
            
            # Score based on skill level
            if answer == "weak":
                score += 30
                if problem["difficulty"] == "Easy":
                    score += 20
                elif problem["difficulty"] == "Medium":
                    score += 10
            elif answer == "okay":
                score += 15
                if problem["difficulty"] == "Medium":
                    score += 15
            elif answer == "strong":
                score -= 10
                if problem["difficulty"] == "Hard":
                    score += 10
            
            # Priority bonus
            score += (4 - problem.get("priority", 2)) * 5
            
            # Slight randomization
            score += random.random() * 10
            
            scored.append({"id": problem["id"], "score": score})
        
        scored.sort(key=lambda x: x["score"], reverse=True)
        return [p["id"] for p in scored[:30]]
    
    def get_user_progress(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's LeetCode progress from database.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Dict with solved_problem_ids, quiz_answers, and total_solved
        """
        try:
            response = self.supabase.table("leetcode_progress").select(
                "solved_problem_ids, quiz_answers"
            ).eq("user_id", user_id).execute()
            
            if response.data and len(response.data) > 0:
                data = response.data[0]
                solved_ids = data.get("solved_problem_ids") or []
                quiz_answers = data.get("quiz_answers") or {}
                return {
                    "solved_problem_ids": solved_ids,
                    "quiz_answers": quiz_answers,
                    "total_solved": len(solved_ids)
                }
        except Exception as e:
            logger.warning(f"Failed to fetch progress: {e}")
        
        return {
            "solved_problem_ids": [],
            "quiz_answers": {},
            "total_solved": 0
        }
    
    def save_user_progress(
        self,
        user_id: str,
        solved_problem_ids: List[int],
        quiz_answers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Save user's LeetCode progress to database.
        
        Args:
            user_id: User's UUID
            solved_problem_ids: List of solved problem IDs
            quiz_answers: Optional quiz answers to save
            
        Returns:
            Dict with saved data
        """
        try:
            update_data = {
                "user_id": user_id,
                "solved_problem_ids": solved_problem_ids,
                "updated_at": "now()"
            }
            
            if quiz_answers is not None:
                update_data["quiz_answers"] = quiz_answers
            
            # Upsert to handle both insert and update
            self.supabase.table("leetcode_progress").upsert(
                update_data,
                on_conflict="user_id"
            ).execute()
            
            return {
                "solved_problem_ids": solved_problem_ids,
                "quiz_answers": quiz_answers or {},
                "total_solved": len(solved_problem_ids)
            }
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")
            raise


# Singleton instance
leetcode_service = LeetCodeService()
