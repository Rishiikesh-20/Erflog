import { NextRequest, NextResponse } from "next/server";
import { GoogleGenerativeAI } from "@google/generative-ai";

// Blind 75 problem list for reference
const BLIND_75_PROBLEMS = [
    // Array
    { id: 1, title: "Two Sum", category: "Array", difficulty: "Easy" },
    { id: 121, title: "Best Time to Buy and Sell Stock", category: "Array", difficulty: "Easy" },
    { id: 217, title: "Contains Duplicate", category: "Array", difficulty: "Easy" },
    { id: 238, title: "Product of Array Except Self", category: "Array", difficulty: "Medium" },
    { id: 53, title: "Maximum Subarray", category: "Array", difficulty: "Medium" },
    { id: 152, title: "Maximum Product Subarray", category: "Array", difficulty: "Medium" },
    { id: 153, title: "Find Minimum in Rotated Sorted Array", category: "Array", difficulty: "Medium" },
    { id: 33, title: "Search in Rotated Sorted Array", category: "Array", difficulty: "Medium" },
    { id: 15, title: "3Sum", category: "Array", difficulty: "Medium" },
    { id: 11, title: "Container With Most Water", category: "Array", difficulty: "Medium" },
    // Binary
    { id: 371, title: "Sum of Two Integers", category: "Binary", difficulty: "Medium" },
    { id: 191, title: "Number of 1 Bits", category: "Binary", difficulty: "Easy" },
    { id: 338, title: "Counting Bits", category: "Binary", difficulty: "Easy" },
    { id: 268, title: "Missing Number", category: "Binary", difficulty: "Easy" },
    { id: 190, title: "Reverse Bits", category: "Binary", difficulty: "Easy" },
    // DP
    { id: 70, title: "Climbing Stairs", category: "Dynamic Programming", difficulty: "Easy" },
    { id: 322, title: "Coin Change", category: "Dynamic Programming", difficulty: "Medium" },
    { id: 300, title: "Longest Increasing Subsequence", category: "Dynamic Programming", difficulty: "Medium" },
    { id: 1143, title: "Longest Common Subsequence", category: "Dynamic Programming", difficulty: "Medium" },
    { id: 139, title: "Word Break", category: "Dynamic Programming", difficulty: "Medium" },
    { id: 39, title: "Combination Sum", category: "Dynamic Programming", difficulty: "Medium" },
    { id: 198, title: "House Robber", category: "Dynamic Programming", difficulty: "Medium" },
    { id: 213, title: "House Robber II", category: "Dynamic Programming", difficulty: "Medium" },
    { id: 91, title: "Decode Ways", category: "Dynamic Programming", difficulty: "Medium" },
    { id: 62, title: "Unique Paths", category: "Dynamic Programming", difficulty: "Medium" },
    { id: 55, title: "Jump Game", category: "Dynamic Programming", difficulty: "Medium" },
    // Graph
    { id: 133, title: "Clone Graph", category: "Graph", difficulty: "Medium" },
    { id: 207, title: "Course Schedule", category: "Graph", difficulty: "Medium" },
    { id: 417, title: "Pacific Atlantic Water Flow", category: "Graph", difficulty: "Medium" },
    { id: 200, title: "Number of Islands", category: "Graph", difficulty: "Medium" },
    { id: 128, title: "Longest Consecutive Sequence", category: "Graph", difficulty: "Medium" },
    { id: 269, title: "Alien Dictionary", category: "Graph", difficulty: "Hard" },
    { id: 261, title: "Graph Valid Tree", category: "Graph", difficulty: "Medium" },
    { id: 323, title: "Number of Connected Components", category: "Graph", difficulty: "Medium" },
    // Interval
    { id: 57, title: "Insert Interval", category: "Interval", difficulty: "Medium" },
    { id: 56, title: "Merge Intervals", category: "Interval", difficulty: "Medium" },
    { id: 435, title: "Non-overlapping Intervals", category: "Interval", difficulty: "Medium" },
    { id: 252, title: "Meeting Rooms", category: "Interval", difficulty: "Easy" },
    { id: 253, title: "Meeting Rooms II", category: "Interval", difficulty: "Medium" },
    // Linked List
    { id: 206, title: "Reverse Linked List", category: "Linked List", difficulty: "Easy" },
    { id: 141, title: "Linked List Cycle", category: "Linked List", difficulty: "Easy" },
    { id: 21, title: "Merge Two Sorted Lists", category: "Linked List", difficulty: "Easy" },
    { id: 23, title: "Merge K Sorted Lists", category: "Linked List", difficulty: "Hard" },
    { id: 19, title: "Remove Nth Node From End", category: "Linked List", difficulty: "Medium" },
    { id: 143, title: "Reorder List", category: "Linked List", difficulty: "Medium" },
    // Matrix
    { id: 73, title: "Set Matrix Zeroes", category: "Matrix", difficulty: "Medium" },
    { id: 54, title: "Spiral Matrix", category: "Matrix", difficulty: "Medium" },
    { id: 48, title: "Rotate Image", category: "Matrix", difficulty: "Medium" },
    { id: 79, title: "Word Search", category: "Matrix", difficulty: "Medium" },
    // String
    { id: 3, title: "Longest Substring Without Repeating", category: "String", difficulty: "Medium" },
    { id: 424, title: "Longest Repeating Character Replacement", category: "String", difficulty: "Medium" },
    { id: 76, title: "Minimum Window Substring", category: "String", difficulty: "Hard" },
    { id: 242, title: "Valid Anagram", category: "String", difficulty: "Easy" },
    { id: 49, title: "Group Anagrams", category: "String", difficulty: "Medium" },
    { id: 20, title: "Valid Parentheses", category: "String", difficulty: "Easy" },
    { id: 125, title: "Valid Palindrome", category: "String", difficulty: "Easy" },
    { id: 5, title: "Longest Palindromic Substring", category: "String", difficulty: "Medium" },
    { id: 647, title: "Palindromic Substrings", category: "String", difficulty: "Medium" },
    { id: 271, title: "Encode and Decode Strings", category: "String", difficulty: "Medium" },
    // Tree
    { id: 104, title: "Maximum Depth of Binary Tree", category: "Tree", difficulty: "Easy" },
    { id: 100, title: "Same Tree", category: "Tree", difficulty: "Easy" },
    { id: 226, title: "Invert Binary Tree", category: "Tree", difficulty: "Easy" },
    { id: 124, title: "Binary Tree Maximum Path Sum", category: "Tree", difficulty: "Hard" },
    { id: 102, title: "Binary Tree Level Order Traversal", category: "Tree", difficulty: "Medium" },
    { id: 297, title: "Serialize and Deserialize Binary Tree", category: "Tree", difficulty: "Hard" },
    { id: 572, title: "Subtree of Another Tree", category: "Tree", difficulty: "Easy" },
    { id: 105, title: "Construct Binary Tree from Preorder and Inorder", category: "Tree", difficulty: "Medium" },
    { id: 98, title: "Validate Binary Search Tree", category: "Tree", difficulty: "Medium" },
    { id: 230, title: "Kth Smallest Element in a BST", category: "Tree", difficulty: "Medium" },
    { id: 235, title: "LCA of a Binary Search Tree", category: "Tree", difficulty: "Medium" },
    { id: 208, title: "Implement Trie (Prefix Tree)", category: "Tree", difficulty: "Medium" },
    { id: 211, title: "Design Add and Search Words", category: "Tree", difficulty: "Medium" },
    { id: 212, title: "Word Search II", category: "Tree", difficulty: "Hard" },
    // Heap
    { id: 347, title: "Top K Frequent Elements", category: "Heap", difficulty: "Medium" },
    { id: 295, title: "Find Median from Data Stream", category: "Heap", difficulty: "Hard" },
];

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const { quizAnswers, profile, solvedProblemIds } = body;

        // Initialize Gemini
        const apiKey = process.env.GEMINI_API_KEY;
        if (!apiKey) {
            // Fallback to local algorithm if no API key
            return NextResponse.json({
                recommendedIds: getLocalRecommendations(quizAnswers, profile, solvedProblemIds),
                source: "local"
            });
        }

        const genAI = new GoogleGenerativeAI(apiKey);
        const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });

        // Build prompt for Gemini
        const prompt = buildGeminiPrompt(quizAnswers, profile, solvedProblemIds);

        const result = await model.generateContent(prompt);
        const response = await result.response;
        const text = response.text();

        // Parse the response to extract problem IDs
        const recommendedIds = parseGeminiResponse(text, solvedProblemIds);

        return NextResponse.json({
            recommendedIds,
            source: "gemini",
            reasoning: text
        });

    } catch (error) {
        console.error("Gemini API error:", error);
        // Fallback to local recommendations
        const body = await request.json().catch(() => ({}));
        return NextResponse.json({
            recommendedIds: getLocalRecommendations(body.quizAnswers || {}, body.profile, body.solvedProblemIds || []),
            source: "fallback"
        });
    }
}

function buildGeminiPrompt(
    quizAnswers: Record<string, string>,
    profile: any,
    solvedProblemIds: number[]
): string {
    const totalSolved = profile?.submitStats?.acSubmissionNum?.find((s: any) => s.difficulty === "All")?.count || 0;
    const easySolved = profile?.submitStats?.acSubmissionNum?.find((s: any) => s.difficulty === "Easy")?.count || 0;
    const mediumSolved = profile?.submitStats?.acSubmissionNum?.find((s: any) => s.difficulty === "Medium")?.count || 0;
    const hardSolved = profile?.submitStats?.acSubmissionNum?.find((s: any) => s.difficulty === "Hard")?.count || 0;

    const availableProblems = BLIND_75_PROBLEMS.filter(p => !solvedProblemIds.includes(p.id));

    return `You are an expert DSA coach helping a LeetCode user prepare for coding interviews.

USER PROFILE:
- Total Problems Solved: ${totalSolved}
- Easy: ${easySolved}, Medium: ${mediumSolved}, Hard: ${hardSolved}
- LeetCode Rank: ${profile?.profile?.ranking || 'Unknown'}

SELF-ASSESSMENT (User's confidence in each topic):
${Object.entries(quizAnswers).map(([topic, level]) => `- ${topic}: ${level}`).join('\n')}

AVAILABLE PROBLEMS (from Blind 75, excluding already solved):
${availableProblems.map(p => `ID:${p.id} "${p.title}" [${p.category}] [${p.difficulty}]`).join('\n')}

YOUR TASK:
Select exactly 30 problems from the available list that would be most beneficial for this user. Consider:
1. Focus MORE on topics where user rated themselves as "weak"
2. For "weak" topics, start with easier problems to build confidence
3. For "okay" topics, include a mix of medium problems
4. For "strong" topics, only include the most important/frequently asked problems
5. Ensure good coverage across different categories
6. Prioritize classic interview problems

RESPONSE FORMAT:
Return ONLY a JSON array of problem IDs, nothing else. Example: [1, 121, 217, 238, ...]`;
}

function parseGeminiResponse(text: string, solvedProblemIds: number[]): number[] {
    try {
        // Try to extract JSON array from response
        const jsonMatch = text.match(/\[[\d,\s]+\]/);
        if (jsonMatch) {
            const ids = JSON.parse(jsonMatch[0]) as number[];
            // Filter to only valid Blind 75 IDs that aren't solved
            const validIds = ids.filter(id =>
                BLIND_75_PROBLEMS.some(p => p.id === id) &&
                !solvedProblemIds.includes(id)
            );
            return validIds.slice(0, 30);
        }
    } catch (e) {
        console.error("Failed to parse Gemini response:", e);
    }

    // Fallback: return empty (will use local algorithm)
    return [];
}

function getLocalRecommendations(
    quizAnswers: Record<string, string>,
    profile: any,
    solvedProblemIds: number[]
): number[] {
    const available = BLIND_75_PROBLEMS.filter(p => !solvedProblemIds.includes(p.id));

    // Score each problem
    const scored = available.map(problem => {
        let score = 50; // Base score

        // Map category names
        const categoryMap: Record<string, string> = {
            "Array": "Array",
            "Binary": "Binary",
            "Dynamic Programming": "Dynamic Programming",
            "Graph": "Graph",
            "Interval": "Interval",
            "Linked List": "Linked List",
            "Matrix": "Matrix",
            "String": "String",
            "Tree": "Tree",
            "Heap": "Heap"
        };

        const answer = quizAnswers[problem.category] || quizAnswers[categoryMap[problem.category]];

        if (answer === "weak") {
            score += 30;
            if (problem.difficulty === "Easy") score += 20;
            else if (problem.difficulty === "Medium") score += 10;
        } else if (answer === "okay") {
            score += 15;
            if (problem.difficulty === "Medium") score += 15;
        } else if (answer === "strong") {
            score -= 10;
            if (problem.difficulty === "Hard") score += 10;
        }

        // Slight randomization
        score += Math.random() * 10;

        return { id: problem.id, score };
    });

    return scored
        .sort((a, b) => b.score - a.score)
        .slice(0, 30)
        .map(p => p.id);
}
