// Curated DSA Roadmap - Essential LeetCode Problems
// Covering: Arrays, Strings, Linked Lists, Trees, Graphs, DP, Stacks, Queues, etc.

export interface RoadmapProblem {
    id: number;
    title: string;
    slug: string;
    difficulty: "Easy" | "Medium" | "Hard";
    topic: string;
    url: string;
}

export interface RoadmapCategory {
    name: string;
    icon: string; // Lucide icon name
    color: string;
    description: string;
    problems: RoadmapProblem[];
}

export const dsaRoadmap: RoadmapCategory[] = [
    {
        name: "Arrays & Hashing",
        icon: "Layers",
        color: "#3B82F6",
        description: "Foundation of DSA - array manipulation and hash-based solutions",
        problems: [
            { id: 1, title: "Two Sum", slug: "two-sum", difficulty: "Easy", topic: "Arrays", url: "https://leetcode.com/problems/two-sum/" },
            { id: 49, title: "Group Anagrams", slug: "group-anagrams", difficulty: "Medium", topic: "Hashing", url: "https://leetcode.com/problems/group-anagrams/" },
        ]
    },
    {
        name: "Two Pointers",
        icon: "ArrowLeftRight",
        color: "#8B5CF6",
        description: "Efficient traversal techniques for sorted arrays",
        problems: [
            { id: 15, title: "3Sum", slug: "3sum", difficulty: "Medium", topic: "Two Pointers", url: "https://leetcode.com/problems/3sum/" },
        ]
    },
    {
        name: "Stack & Queue",
        icon: "Layers3",
        color: "#EC4899",
        description: "LIFO and FIFO data structures",
        problems: [
            { id: 20, title: "Valid Parentheses", slug: "valid-parentheses", difficulty: "Easy", topic: "Stack", url: "https://leetcode.com/problems/valid-parentheses/" },
            { id: 155, title: "Min Stack", slug: "min-stack", difficulty: "Medium", topic: "Stack", url: "https://leetcode.com/problems/min-stack/" },
        ]
    },
    {
        name: "Linked List",
        icon: "Link",
        color: "#14B8A6",
        description: "Pointer manipulation and list operations",
        problems: [
            { id: 206, title: "Reverse Linked List", slug: "reverse-linked-list", difficulty: "Easy", topic: "Linked List", url: "https://leetcode.com/problems/reverse-linked-list/" },
            { id: 141, title: "Linked List Cycle", slug: "linked-list-cycle", difficulty: "Easy", topic: "Linked List", url: "https://leetcode.com/problems/linked-list-cycle/" },
        ]
    },
    {
        name: "Binary Tree",
        icon: "TreeDeciduous",
        color: "#22C55E",
        description: "Tree traversals, DFS, and BFS concepts",
        problems: [
            { id: 104, title: "Maximum Depth of Binary Tree", slug: "maximum-depth-of-binary-tree", difficulty: "Easy", topic: "Binary Tree", url: "https://leetcode.com/problems/maximum-depth-of-binary-tree/" },
            { id: 102, title: "Binary Tree Level Order Traversal", slug: "binary-tree-level-order-traversal", difficulty: "Medium", topic: "Binary Tree", url: "https://leetcode.com/problems/binary-tree-level-order-traversal/" },
        ]
    },
    {
        name: "Binary Search Tree",
        icon: "GitBranch",
        color: "#10B981",
        description: "Ordered tree operations and search",
        problems: [
            { id: 98, title: "Validate Binary Search Tree", slug: "validate-binary-search-tree", difficulty: "Medium", topic: "BST", url: "https://leetcode.com/problems/validate-binary-search-tree/" },
            { id: 230, title: "Kth Smallest Element in a BST", slug: "kth-smallest-element-in-a-bst", difficulty: "Medium", topic: "BST", url: "https://leetcode.com/problems/kth-smallest-element-in-a-bst/" },
        ]
    },
    {
        name: "Graphs",
        icon: "Network",
        color: "#F59E0B",
        description: "Graph traversal, connected components, shortest paths",
        problems: [
            { id: 200, title: "Number of Islands", slug: "number-of-islands", difficulty: "Medium", topic: "Graph", url: "https://leetcode.com/problems/number-of-islands/" },
            { id: 133, title: "Clone Graph", slug: "clone-graph", difficulty: "Medium", topic: "Graph", url: "https://leetcode.com/problems/clone-graph/" },
        ]
    },
    {
        name: "Dynamic Programming",
        icon: "Sparkles",
        color: "#EF4444",
        description: "Memoization and tabulation techniques",
        problems: [
            { id: 70, title: "Climbing Stairs", slug: "climbing-stairs", difficulty: "Easy", topic: "DP", url: "https://leetcode.com/problems/climbing-stairs/" },
            { id: 322, title: "Coin Change", slug: "coin-change", difficulty: "Medium", topic: "DP", url: "https://leetcode.com/problems/coin-change/" },
            { id: 300, title: "Longest Increasing Subsequence", slug: "longest-increasing-subsequence", difficulty: "Medium", topic: "DP", url: "https://leetcode.com/problems/longest-increasing-subsequence/" },
        ]
    },
    {
        name: "Binary Search",
        icon: "Search",
        color: "#6366F1",
        description: "Divide and conquer search algorithms",
        problems: [
            { id: 33, title: "Search in Rotated Sorted Array", slug: "search-in-rotated-sorted-array", difficulty: "Medium", topic: "Binary Search", url: "https://leetcode.com/problems/search-in-rotated-sorted-array/" },
        ]
    },
    {
        name: "Backtracking",
        icon: "Undo2",
        color: "#D946EF",
        description: "Recursive exploration with pruning",
        problems: [
            { id: 78, title: "Subsets", slug: "subsets", difficulty: "Medium", topic: "Backtracking", url: "https://leetcode.com/problems/subsets/" },
            { id: 39, title: "Combination Sum", slug: "combination-sum", difficulty: "Medium", topic: "Backtracking", url: "https://leetcode.com/problems/combination-sum/" },
        ]
    },
];

// Flatten all problems for easy access
export const allRoadmapProblems: RoadmapProblem[] = dsaRoadmap.flatMap(cat => cat.problems);

// Get total count
export const totalProblemsCount = allRoadmapProblems.length;
