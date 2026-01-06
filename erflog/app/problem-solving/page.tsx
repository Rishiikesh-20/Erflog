"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Search,
    Trophy,
    Target,
    TrendingUp,
    Award,
    Loader2,
    AlertCircle,
    Clock,
    Flame,
    ExternalLink,
    CheckCircle2,
    Circle,
    Layers,
    Link,
    TreeDeciduous,
    Network,
    Sparkles,
    ChevronDown,
    ChevronUp,
    Binary,
    Calendar,
    Grid3X3,
    Type,
    ArrowUpDown,
    ListChecks,
    BarChart3,
    Lightbulb,
    ThumbsUp,
    ThumbsDown,
    Meh,
    ArrowRight,
    Zap,
    Bot,
} from "lucide-react";
import { leetcodeAPI } from "@/lib/leetcode-api";
import type {
    LeetCodeProfile,
    ContestInfo,
    RecentSubmission,
} from "@/lib/leetcode-api";
import {
    getLeetCodeProblems,
    getLeetCodeRecommendations,
    getLeetCodeProgress,
    saveLeetCodeProgress,
    type LeetCodeCategory,
    type LeetCodeProblem,
} from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";

// Icon mapping for categories
const categoryIcons: Record<string, any> = {
    Layers, Binary, Sparkles, Network, Calendar, Link, Grid3X3, Type, TreeDeciduous, ArrowUpDown
};

// Quiz skill levels
type SkillLevel = "weak" | "okay" | "strong" | null;

interface QuizAnswers {
    [category: string]: SkillLevel;
}

export default function ProblemSolvingPage() {
    const { isAuthenticated, isLoading: authLoading } = useAuth();
    
    const [username, setUsername] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Flow states: "search" → "quiz" → "results"
    const [currentStep, setCurrentStep] = useState<"search" | "quiz" | "results">("search");

    // Data states
    const [profile, setProfile] = useState<LeetCodeProfile | null>(null);
    const [contestInfo, setContestInfo] = useState<ContestInfo | null>(null);
    const [recentSubmissions, setRecentSubmissions] = useState<RecentSubmission[]>([]);

    // Quiz state
    const [quizAnswers, setQuizAnswers] = useState<QuizAnswers>({});
    const [currentCardIndex, setCurrentCardIndex] = useState(0);

    // AI Recommendations
    const [aiRecommendedIds, setAiRecommendedIds] = useState<number[]>([]);
    const [recommendationSource, setRecommendationSource] = useState<string>("");

    // Blind 75 Progress States
    const [solvedProblems, setSolvedProblems] = useState<Set<number>>(new Set());
    const [showFullList, setShowFullList] = useState(false);
    const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
    
    // Backend data
    const [categories, setCategories] = useState<LeetCodeCategory[]>([]);
    const [allProblems, setAllProblems] = useState<LeetCodeProblem[]>([]);
    const [isSavingProgress, setIsSavingProgress] = useState(false);
    
    // Track if user has existing progress (to skip quiz)
    const [hasExistingProgress, setHasExistingProgress] = useState<boolean | null>(null);
    const [isLoadingProgress, setIsLoadingProgress] = useState(true);

    // Load problems from backend on mount
    useEffect(() => {
        const loadProblems = async () => {
            try {
                const data = await getLeetCodeProblems();
                setCategories(data.categories);
                const allProbs: LeetCodeProblem[] = [];
                data.categories.forEach(cat => allProbs.push(...cat.problems));
                setAllProblems(allProbs);
            } catch (error) {
                console.error("Failed to load problems:", error);
            }
        };
        loadProblems();
    }, []);

    // Load progress from backend when authenticated
    useEffect(() => {
        const loadProgress = async () => {
            setIsLoadingProgress(true);
            if (isAuthenticated) {
                try {
                    const data = await getLeetCodeProgress();
                    const hasSolvedProblems = data.solved_problem_ids && data.solved_problem_ids.length > 0;
                    const hasQuizAnswers = data.quiz_answers && Object.keys(data.quiz_answers).length > 0;
                    
                    setSolvedProblems(new Set(data.solved_problem_ids || []));
                    if (hasQuizAnswers) {
                        setQuizAnswers(data.quiz_answers as QuizAnswers);
                    }
                    
                    // If user has any progress, skip quiz and go directly to results
                    if (hasSolvedProblems || hasQuizAnswers) {
                        setHasExistingProgress(true);
                        setCurrentStep("results");
                    } else {
                        setHasExistingProgress(false);
                    }
                } catch (error) {
                    console.error("Failed to load progress:", error);
                    setHasExistingProgress(false);
                }
            } else {
                setHasExistingProgress(false);
            }
            setIsLoadingProgress(false);
        };
        if (!authLoading) {
            loadProgress();
        }
    }, [isAuthenticated, authLoading]);

    // Save progress to backend (debounced)
    const saveProgressToBackend = useCallback(async (solved: number[], quiz?: QuizAnswers) => {
        if (!isAuthenticated) return;
        setIsSavingProgress(true);
        try {
            await saveLeetCodeProgress(solved, quiz as Record<string, string>);
        } catch (error) {
            console.error("Failed to save progress:", error);
        } finally {
            setIsSavingProgress(false);
        }
    }, [isAuthenticated]);

    // Toggle solved and save to backend
    const toggleSolved = (problemId: number) => {
        setSolvedProblems(prev => {
            const newSet = new Set(prev);
            if (newSet.has(problemId)) {
                newSet.delete(problemId);
            } else {
                newSet.add(problemId);
            }
            // Save to backend
            saveProgressToBackend([...newSet]);
            return newSet;
        });
    };

    // Handle quiz answer and auto-advance
    const setQuizAnswer = (category: string, level: SkillLevel) => {
        setQuizAnswers(prev => {
            const newAnswers = { ...prev, [category]: level };
            // Save to backend with quiz answers
            saveProgressToBackend([...solvedProblems], newAnswers);
            return newAnswers;
        });

        // Auto advance to next card after a short delay
        setTimeout(() => {
            if (currentCardIndex < categories.length - 1) {
                setCurrentCardIndex(prev => prev + 1);
            }
        }, 300);
    };

    const handleSearch = async () => {
        if (!username.trim()) {
            setError("Please enter a valid LeetCode username");
            return;
        }

        setIsLoading(true);
        setError(null);

        const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

        try {
            const profileData = await leetcodeAPI.getUserProfile(username);
            setProfile(profileData);

            await delay(300);
            try {
                const contestData = await leetcodeAPI.getContestInfo(username);
                setContestInfo(contestData);
            } catch {
                setContestInfo(null);
            }

            await delay(300);
            try {
                const submissionsData = await leetcodeAPI.getRecentSubmissions(username);
                setRecentSubmissions(submissionsData || []);
            } catch {
                setRecentSubmissions([]);
            }

            // Move to quiz step
            setCurrentStep("quiz");
            setCurrentCardIndex(0);
        } catch (err) {
            console.error("Error fetching LeetCode data:", err);
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to fetch data. Please check the username and try again."
            );
        } finally {
            setIsLoading(false);
        }
    };

    // Get AI recommendations from backend
    const getAIRecommendations = async () => {
        setIsGenerating(true);

        try {
            const response = await getLeetCodeRecommendations({
                quiz_answers: quizAnswers as Record<string, string>,
                leetcode_profile: profile ? {
                    total_solved: getTotalSolved(),
                    easy_solved: getEasySolved(),
                    medium_solved: getMediumSolved(),
                    hard_solved: getHardSolved(),
                } : undefined,
                solved_problem_ids: [...solvedProblems]
            });

            setAiRecommendedIds(response.recommended_ids || []);
            setRecommendationSource(response.source || "local");
            setCurrentStep("results");
        } catch (error) {
            console.error("Failed to get AI recommendations:", error);
            // Fallback to local recommendations
            const localIds = getLocalRecommendations();
            setAiRecommendedIds(localIds);
            setRecommendationSource("local");
            setCurrentStep("results");
        } finally {
            setIsGenerating(false);
        }
    };

    // Local fallback recommendation algorithm
    const getLocalRecommendations = (): number[] => {
        const unsolved = allProblems.filter(p => !solvedProblems.has(p.id));

        const scored = unsolved.map(problem => {
            let score = 50;
            const answer = quizAnswers[problem.category];

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

            score += Math.random() * 10;
            return { id: problem.id, score };
        });

        return scored.sort((a, b) => b.score - a.score).slice(0, 30).map(p => p.id);
    };

    // Stats helpers
    const getTotalSolved = () => {
        if (!profile?.submitStats?.acSubmissionNum) return 0;
        return profile.submitStats.acSubmissionNum.find(s => s.difficulty === "All")?.count || 0;
    };

    const getEasySolved = () => {
        if (!profile?.submitStats?.acSubmissionNum) return 0;
        return profile.submitStats.acSubmissionNum.find(s => s.difficulty === "Easy")?.count || 0;
    };

    const getMediumSolved = () => {
        if (!profile?.submitStats?.acSubmissionNum) return 0;
        return profile.submitStats.acSubmissionNum.find(s => s.difficulty === "Medium")?.count || 0;
    };

    const getHardSolved = () => {
        if (!profile?.submitStats?.acSubmissionNum) return 0;
        return profile.submitStats.acSubmissionNum.find(s => s.difficulty === "Hard")?.count || 0;
    };

    // Get recommended problems
    const recommendedProblems = useMemo(() => {
        if (showFullList) return allProblems;
        if (aiRecommendedIds.length > 0) {
            return allProblems.filter(p => aiRecommendedIds.includes(p.id));
        }
        return allProblems.slice(0, 30);
    }, [aiRecommendedIds, showFullList, allProblems]);

    // Group problems by category
    const groupedProblems = useMemo(() => {
        const groups = new Map<string, LeetCodeProblem[]>();
        recommendedProblems.forEach(problem => {
            const category = categories.find(c => c.problems.some(p => p.id === problem.id));
            if (category) {
                const existing = groups.get(category.name) || [];
                existing.push(problem);
                groups.set(category.name, existing);
            }
        });
        return groups;
    }, [recommendedProblems, categories]);

    // Blind 75 Progress
    const totalProblemsCount = allProblems.length;
    const blind75Progress = solvedProblems.size;
    const blind75Percentage = totalProblemsCount > 0 ? Math.round((blind75Progress / totalProblemsCount) * 100) : 0;

    // Toggle category expansion
    const toggleCategory = (categoryName: string) => {
        setExpandedCategories(prev => {
            const newSet = new Set(prev);
            newSet.has(categoryName) ? newSet.delete(categoryName) : newSet.add(categoryName);
            return newSet;
        });
    };

    // Check if quiz is complete
    const quizAnsweredCount = Object.values(quizAnswers).filter(v => v !== null).length;
    const canProceed = quizAnsweredCount >= 5;

    // Current quiz card
    const currentCategory = categories[currentCardIndex];

    // Animation variants for cards
    const cardVariants = {
        enter: (direction: number) => ({
            x: direction > 0 ? 300 : -300,
            opacity: 0,
            scale: 0.8,
            rotateY: direction > 0 ? 45 : -45,
        }),
        center: {
            x: 0,
            opacity: 1,
            scale: 1,
            rotateY: 0,
            transition: { type: "spring" as const, stiffness: 300, damping: 30 }
        },
        exit: (direction: number) => ({
            x: direction < 0 ? 300 : -300,
            opacity: 0,
            scale: 0.8,
            rotateY: direction < 0 ? 45 : -45,
        })
    };

    return (
        <div className="min-h-screen p-8" style={{ backgroundColor: "#F0EFE9" }}>
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center mb-8"
                >
                    <h1 className="font-serif-bold text-4xl md:text-5xl mb-4" style={{ color: "#D95D39" }}>
                        Problem Solving 
                    </h1>
                    <p className="text-lg text-secondary max-w-2xl mx-auto">
                        {currentStep === "search" && "Get AI-powered Blind 75 recommendations"}
                        {currentStep === "quiz" && "Swipe through topics and rate your confidence"}
                        {currentStep === "results" && "Your personalized Blind 75 roadmap"}
                    </p>
                </motion.div>

                {/* Loading State */}
                {isLoadingProgress && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="flex flex-col items-center justify-center py-20"
                    >
                        <Loader2 className="w-8 h-8 animate-spin mb-4" style={{ color: "#D95D39" }} />
                        <p className="text-secondary">Loading your progress...</p>
                    </motion.div>
                )}

                {/* Step 1: Search - Only show if no existing progress */}
                {!isLoadingProgress && currentStep === "search" && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-white rounded-2xl p-8 shadow-sm"
                        style={{ borderColor: "#E5E0D8", borderWidth: "1px" }}
                    >
                        <div className="flex flex-col md:flex-row gap-4">
                            <div className="flex-1 relative">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "#888" }} />
                                <input
                                    type="text"
                                    placeholder="Enter your LeetCode username..."
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                                    className="w-full pl-12 pr-4 py-3 rounded-lg border text-ink focus:outline-none focus:ring-2 transition-all"
                                    style={{ borderColor: "#E5E0D8" }}
                                />
                            </div>
                            <button
                                onClick={handleSearch}
                                disabled={isLoading}
                                className="px-8 py-3 rounded-lg font-medium text-white transition-all hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-2"
                                style={{ backgroundColor: "#D95D39" }}
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                        Analyzing...
                                    </>
                                ) : (
                                    <>
                                        <Zap className="w-5 h-5" />
                                        Start Quiz
                                    </>
                                )}
                            </button>
                        </div>
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="mt-4 p-4 rounded-lg flex items-center gap-3"
                                style={{ backgroundColor: "#FEE2E2", color: "#DC2626" }}
                            >
                                <AlertCircle className="w-5 h-5" />
                                {error}
                            </motion.div>
                        )}
                    </motion.div>
                )}

                {/* Step 2: Animated Quiz Cards */}
                {currentStep === "quiz" && profile && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="space-y-6"
                    >
                        {/* Profile Summary */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-white rounded-2xl p-6 shadow-sm flex items-center gap-4"
                            style={{ borderColor: "#E5E0D8", borderWidth: "1px" }}
                        >
                            <div className="w-16 h-16 rounded-full overflow-hidden" style={{ borderColor: "#D95D39", borderWidth: "2px" }}>
                                <img
                                    src={profile.profile?.userAvatar || "/default-avatar.png"}
                                    alt={profile.username}
                                    className="w-full h-full object-cover"
                                />
                            </div>
                            <div className="flex-1">
                                <h2 className="font-serif-bold text-xl text-ink">
                                    {profile.profile?.realName || profile.username}
                                </h2>
                                <p className="text-secondary text-sm">
                                    {getTotalSolved()} problems solved
                                </p>
                            </div>
                            <div className="text-right">
                                <p className="text-2xl font-bold" style={{ color: "#D95D39" }}>
                                    {currentCardIndex + 1}/{categories.length}
                                </p>
                            </div>
                        </motion.div>

                        {/* Progress Dots */}
                        <div className="flex justify-center gap-2">
                            {categories.map((_: LeetCodeCategory, idx: number) => (
                                <button
                                    key={idx}
                                    onClick={() => setCurrentCardIndex(idx)}
                                    className={`w-3 h-3 rounded-full transition-all ${idx === currentCardIndex ? 'scale-125' : 'opacity-50 hover:opacity-75'
                                        }`}
                                    style={{
                                        backgroundColor: quizAnswers[categories[idx].name]
                                            ? (quizAnswers[categories[idx].name] === 'weak' ? '#DC2626'
                                                : quizAnswers[categories[idx].name] === 'okay' ? '#D97706'
                                                    : '#16A34A')
                                            : idx === currentCardIndex ? '#D95D39' : '#E5E0D8'
                                    }}
                                />
                            ))}
                        </div>

                        {/* Animated Card Stack */}
                        <div className="relative h-[400px] flex items-center justify-center perspective-1000">
                            <AnimatePresence mode="wait" custom={1}>
                                <motion.div
                                    key={currentCardIndex}
                                    custom={1}
                                    variants={cardVariants}
                                    initial="enter"
                                    animate="center"
                                    exit="exit"
                                    className="absolute w-full max-w-md"
                                >
                                    <div
                                        className="bg-white rounded-3xl p-8 shadow-xl"
                                        style={{ borderColor: currentCategory.color, borderWidth: "3px" }}
                                    >
                                        {/* Card Header */}
                                        <div className="flex items-center gap-4 mb-6">
                                            <div
                                                className="w-16 h-16 rounded-2xl flex items-center justify-center"
                                                style={{ backgroundColor: `${currentCategory.color}20` }}
                                            >
                                                {(() => {
                                                    const IconComponent = categoryIcons[currentCategory.icon] || Layers;
                                                    return <IconComponent className="w-8 h-8" style={{ color: currentCategory.color }} />;
                                                })()}
                                            </div>
                                            <div>
                                                <h3 className="font-serif-bold text-2xl text-ink">{currentCategory.name}</h3>
                                                <p className="text-secondary">{currentCategory.problems.length} problems</p>
                                            </div>
                                        </div>

                                        {/* Question */}
                                        <p className="text-lg text-ink mb-8 text-center">
                                            How confident are you with <span className="font-bold" style={{ color: currentCategory.color }}>{currentCategory.name}</span> problems?
                                        </p>

                                        {/* Answer Buttons */}
                                        <div className="space-y-3">
                                            <motion.button
                                                whileHover={{ scale: 1.02 }}
                                                whileTap={{ scale: 0.98 }}
                                                onClick={() => setQuizAnswer(currentCategory.name, "weak")}
                                                className={`w-full flex items-center justify-center gap-3 py-4 rounded-xl transition-all ${quizAnswers[currentCategory.name] === "weak" ? "ring-2 ring-offset-2" : ""
                                                    }`}
                                                style={{
                                                    backgroundColor: quizAnswers[currentCategory.name] === "weak" ? "#FEE2E2" : "#FEF2F2",
                                                    color: "#DC2626",
                                                    ...(quizAnswers[currentCategory.name] === "weak" && { ringColor: "#DC2626" })
                                                }}
                                            >
                                                <ThumbsDown className="w-5 h-5" />
                                                <span className="font-medium">Weak - Need more practice</span>
                                            </motion.button>

                                            <motion.button
                                                whileHover={{ scale: 1.02 }}
                                                whileTap={{ scale: 0.98 }}
                                                onClick={() => setQuizAnswer(currentCategory.name, "okay")}
                                                className={`w-full flex items-center justify-center gap-3 py-4 rounded-xl transition-all ${quizAnswers[currentCategory.name] === "okay" ? "ring-2 ring-offset-2" : ""
                                                    }`}
                                                style={{
                                                    backgroundColor: quizAnswers[currentCategory.name] === "okay" ? "#FEF3C7" : "#FFFBEB",
                                                    color: "#D97706",
                                                    ...(quizAnswers[currentCategory.name] === "okay" && { ringColor: "#D97706" })
                                                }}
                                            >
                                                <Meh className="w-5 h-5" />
                                                <span className="font-medium">Okay - Can solve most</span>
                                            </motion.button>

                                            <motion.button
                                                whileHover={{ scale: 1.02 }}
                                                whileTap={{ scale: 0.98 }}
                                                onClick={() => setQuizAnswer(currentCategory.name, "strong")}
                                                className={`w-full flex items-center justify-center gap-3 py-4 rounded-xl transition-all ${quizAnswers[currentCategory.name] === "strong" ? "ring-2 ring-offset-2" : ""
                                                    }`}
                                                style={{
                                                    backgroundColor: quizAnswers[currentCategory.name] === "strong" ? "#DCFCE7" : "#F0FDF4",
                                                    color: "#16A34A",
                                                    ...(quizAnswers[currentCategory.name] === "strong" && { ringColor: "#16A34A" })
                                                }}
                                            >
                                                <ThumbsUp className="w-5 h-5" />
                                                <span className="font-medium">Strong - Very confident</span>
                                            </motion.button>
                                        </div>
                                    </div>
                                </motion.div>
                            </AnimatePresence>
                        </div>

                        {/* Navigation */}
                        <div className="flex justify-center gap-4">
                            <button
                                onClick={() => setCurrentCardIndex(prev => Math.max(0, prev - 1))}
                                disabled={currentCardIndex === 0}
                                className="px-6 py-2 rounded-lg font-medium transition-all disabled:opacity-30"
                                style={{ backgroundColor: "#E5E0D8" }}
                            >
                                Previous
                            </button>

                            {currentCardIndex < categories.length - 1 ? (
                                <button
                                    onClick={() => setCurrentCardIndex(prev => prev + 1)}
                                    className="px-6 py-2 rounded-lg font-medium text-white transition-all hover:opacity-90"
                                    style={{ backgroundColor: "#D95D39" }}
                                >
                                    Next
                                </button>
                            ) : (
                                <button
                                    onClick={getAIRecommendations}
                                    disabled={!canProceed || isGenerating}
                                    className="px-6 py-2 rounded-lg font-medium text-white transition-all hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
                                    style={{ backgroundColor: canProceed ? "#D95D39" : "#9CA3AF" }}
                                >
                                    {isGenerating ? (
                                        <>
                                            <Loader2 className="w-5 h-5 animate-spin" />
                                            AI Analyzing...
                                        </>
                                    ) : (
                                        <>
                                            <Bot className="w-5 h-5" />
                                            Get AI Recommendations
                                        </>
                                    )}
                                </button>
                            )}
                        </div>

                        {!canProceed && (
                            <p className="text-center text-secondary text-sm">
                                Answer at least 5 topics to continue ({quizAnsweredCount}/5)
                            </p>
                        )}
                    </motion.div>
                )}

                {/* Step 3: Results - Works with or without profile */}
                {!isLoadingProgress && currentStep === "results" && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="space-y-8"
                    >
                        {/* Profile Header - Only show if profile was fetched */}
                        {profile && (
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="bg-white rounded-2xl p-8 shadow-sm"
                                style={{ borderColor: "#E5E0D8", borderWidth: "1px" }}
                            >
                                <div className="flex flex-col md:flex-row items-center gap-6">
                                    <div className="w-24 h-24 rounded-full overflow-hidden" style={{ borderColor: "#D95D39", borderWidth: "3px" }}>
                                        <img
                                            src={profile.profile?.userAvatar || "/default-avatar.png"}
                                            alt={profile.username}
                                            className="w-full h-full object-cover"
                                        />
                                    </div>
                                    <div className="text-center md:text-left flex-1">
                                        <h2 className="font-serif-bold text-3xl text-ink">
                                            {profile.profile?.realName || profile.username}
                                        </h2>
                                        <p className="text-secondary">@{profile.username}</p>
                                        <div className="flex items-center gap-4 mt-2 justify-center md:justify-start">
                                            <div className="flex items-center gap-1">
                                                <Trophy className="w-4 h-4" style={{ color: "#D95D39" }} />
                                                <span className="text-sm text-ink">Rank #{profile.profile?.ranking?.toLocaleString() || "N/A"}</span>
                                            </div>
                                            <div className="flex items-center gap-1">
                                                <Target className="w-4 h-4" style={{ color: "#D95D39" }} />
                                                <span className="text-sm text-ink">{getTotalSolved()} Solved</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        {/* Stats */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-xl p-6 shadow-sm" style={{ borderColor: "#E5E0D8", borderWidth: "1px" }}>
                                <div className="flex items-center gap-3 mb-3">
                                    <div className="p-2 rounded-lg" style={{ backgroundColor: "#22C55E15" }}><Flame className="w-5 h-5" style={{ color: "#22C55E" }} /></div>
                                    <span className="text-sm text-secondary">Easy</span>
                                </div>
                                <p className="text-2xl font-serif-bold text-ink">{getEasySolved()}</p>
                            </motion.div>
                            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-white rounded-xl p-6 shadow-sm" style={{ borderColor: "#E5E0D8", borderWidth: "1px" }}>
                                <div className="flex items-center gap-3 mb-3">
                                    <div className="p-2 rounded-lg" style={{ backgroundColor: "#F59E0B15" }}><Flame className="w-5 h-5" style={{ color: "#F59E0B" }} /></div>
                                    <span className="text-sm text-secondary">Medium</span>
                                </div>
                                <p className="text-2xl font-serif-bold text-ink">{getMediumSolved()}</p>
                            </motion.div>
                            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-white rounded-xl p-6 shadow-sm" style={{ borderColor: "#E5E0D8", borderWidth: "1px" }}>
                                <div className="flex items-center gap-3 mb-3">
                                    <div className="p-2 rounded-lg" style={{ backgroundColor: "#EF444415" }}><Flame className="w-5 h-5" style={{ color: "#EF4444" }} /></div>
                                    <span className="text-sm text-secondary">Hard</span>
                                </div>
                                <p className="text-2xl font-serif-bold text-ink">{getHardSolved()}</p>
                            </motion.div>
                        </div>

                        {/* Blind 75 Progress Tracker */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-white rounded-2xl p-8 shadow-sm"
                            style={{ borderColor: "#E5E0D8", borderWidth: "1px" }}
                        >
                            {/* Header */}
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-3">
                                    <ListChecks className="w-6 h-6" style={{ color: "#D95D39" }} />
                                    <div>
                                        <h2 className="font-serif-bold text-2xl text-ink">
                                            {showFullList ? "Blind 75 Complete" : "AI Recommended For You"}
                                        </h2>
                                        {!showFullList && (
                                            <div className="flex items-center gap-2 mt-1">
                                                <span className="flex items-center gap-1 text-xs px-2 py-1 rounded-full" style={{ backgroundColor: "#DBEAFE", color: "#2563EB" }}>
                                                    <Bot className="w-3 h-3" />
                                                    {recommendationSource === "gemini" ? "Optimized roadmap" : "AI-optimized selection"}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className="text-3xl font-serif-bold" style={{ color: "#D95D39" }}>
                                        {blind75Progress}/{totalProblemsCount}
                                    </p>
                                    <p className="text-sm text-secondary">{blind75Percentage}% Complete</p>
                                </div>
                            </div>

                            {/* Progress Bar */}
                            <div className="w-full h-4 rounded-full mb-6" style={{ backgroundColor: "#E5E0D8" }}>
                                <motion.div
                                    className="h-full rounded-full"
                                    style={{ backgroundColor: "#D95D39" }}
                                    initial={{ width: 0 }}
                                    animate={{ width: `${blind75Percentage}%` }}
                                    transition={{ duration: 0.5 }}
                                />
                            </div>

                            {/* Stats Row */}
                            <div className="grid grid-cols-3 gap-4 mb-6">
                                <div className="text-center p-3 rounded-lg" style={{ backgroundColor: "#DCFCE7" }}>
                                    <p className="text-lg font-bold" style={{ color: "#16A34A" }}>
                                        {allProblems.filter((p: LeetCodeProblem) => p.difficulty === "Easy" && solvedProblems.has(p.id)).length}/
                                        {allProblems.filter((p: LeetCodeProblem) => p.difficulty === "Easy").length}
                                    </p>
                                    <p className="text-xs" style={{ color: "#16A34A" }}>Easy</p>
                                </div>
                                <div className="text-center p-3 rounded-lg" style={{ backgroundColor: "#FEF3C7" }}>
                                    <p className="text-lg font-bold" style={{ color: "#D97706" }}>
                                        {allProblems.filter((p: LeetCodeProblem) => p.difficulty === "Medium" && solvedProblems.has(p.id)).length}/
                                        {allProblems.filter((p: LeetCodeProblem) => p.difficulty === "Medium").length}
                                    </p>
                                    <p className="text-xs" style={{ color: "#D97706" }}>Medium</p>
                                </div>
                                <div className="text-center p-3 rounded-lg" style={{ backgroundColor: "#FEE2E2" }}>
                                    <p className="text-lg font-bold" style={{ color: "#DC2626" }}>
                                        {allProblems.filter((p: LeetCodeProblem) => p.difficulty === "Hard" && solvedProblems.has(p.id)).length}/
                                        {allProblems.filter((p: LeetCodeProblem) => p.difficulty === "Hard").length}
                                    </p>
                                    <p className="text-xs" style={{ color: "#DC2626" }}>Hard</p>
                                </div>
                            </div>

                            {/* Toggle */}
                            <div className="flex justify-center mb-6">
                                <button
                                    onClick={() => setShowFullList(!showFullList)}
                                    className="flex items-center gap-2 px-4 py-2 rounded-lg transition-all hover:bg-opacity-80"
                                    style={{ backgroundColor: showFullList ? "#D95D39" : "#F0EFE9", color: showFullList ? "#fff" : "#1A1A1A" }}
                                >
                                    <BarChart3 className="w-4 h-4" />
                                    {showFullList ? "Show AI Picks (30)" : "Show Full List (75)"}
                                </button>
                            </div>

                            {/* Problem Categories */}
                            <div className="space-y-4">
                                {categories.map((category: LeetCodeCategory) => {
                                    const IconComponent = categoryIcons[category.icon] || Layers;
                                    const categoryProblems = showFullList
                                        ? category.problems
                                        : (groupedProblems.get(category.name) || []);
                                    const solvedInCategory = category.problems.filter((p: LeetCodeProblem) => solvedProblems.has(p.id)).length;
                                    const isExpanded = expandedCategories.has(category.name);
                                    const quizAnswer = quizAnswers[category.name];

                                    if (categoryProblems.length === 0) return null;

                                    return (
                                        <motion.div
                                            key={category.name}
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            className="rounded-xl overflow-hidden"
                                            style={{ backgroundColor: "#F9F8F5" }}
                                        >
                                            <button
                                                onClick={() => toggleCategory(category.name)}
                                                className="w-full flex items-center justify-between p-4 hover:bg-opacity-50 transition-all"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className="p-2 rounded-lg" style={{ backgroundColor: `${category.color}15` }}>
                                                        <IconComponent className="w-5 h-5" style={{ color: category.color }} />
                                                    </div>
                                                    <div className="text-left">
                                                        <div className="flex items-center gap-2">
                                                            <h3 className="font-medium text-ink">{category.name}</h3>
                                                            {quizAnswer && (
                                                                <span className={`text-xs px-2 py-0.5 rounded-full ${quizAnswer === 'weak' ? 'bg-red-100 text-red-600' :
                                                                    quizAnswer === 'okay' ? 'bg-yellow-100 text-yellow-600' :
                                                                        'bg-green-100 text-green-600'
                                                                    }`}>
                                                                    {quizAnswer}
                                                                </span>
                                                            )}
                                                        </div>
                                                        <p className="text-xs text-secondary">
                                                            {categoryProblems.length} problems • {solvedInCategory}/{category.problems.length} solved
                                                        </p>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <div className="w-24 h-2 rounded-full" style={{ backgroundColor: "#E5E0D8" }}>
                                                        <div
                                                            className="h-full rounded-full transition-all"
                                                            style={{ backgroundColor: category.color, width: `${(solvedInCategory / category.problems.length) * 100}%` }}
                                                        />
                                                    </div>
                                                    {isExpanded ? <ChevronUp className="w-5 h-5 text-secondary" /> : <ChevronDown className="w-5 h-5 text-secondary" />}
                                                </div>
                                            </button>

                                            <AnimatePresence>
                                                {isExpanded && (
                                                    <motion.div
                                                        initial={{ height: 0, opacity: 0 }}
                                                        animate={{ height: "auto", opacity: 1 }}
                                                        exit={{ height: 0, opacity: 0 }}
                                                        className="px-4 pb-4"
                                                    >
                                                        <div className="space-y-2">
                                                            {categoryProblems.map((problem) => {
                                                                const isSolved = solvedProblems.has(problem.id);
                                                                return (
                                                                    <div
                                                                        key={problem.id}
                                                                        className={`flex items-center justify-between p-3 rounded-lg bg-white transition-all ${isSolved ? 'opacity-60' : ''}`}
                                                                        style={{ borderColor: "#E5E0D8", borderWidth: "1px" }}
                                                                    >
                                                                        <div className="flex items-center gap-3">
                                                                            <button onClick={() => toggleSolved(problem.id)} className="transition-all hover:scale-110">
                                                                                {isSolved ? (
                                                                                    <CheckCircle2 className="w-5 h-5" style={{ color: "#16A34A" }} />
                                                                                ) : (
                                                                                    <Circle className="w-5 h-5 text-secondary" />
                                                                                )}
                                                                            </button>
                                                                            <span className={`text-sm font-medium ${isSolved ? 'line-through text-secondary' : 'text-ink'}`}>
                                                                                {problem.id}. {problem.title}
                                                                            </span>
                                                                        </div>
                                                                        <div className="flex items-center gap-2">
                                                                            <span
                                                                                className="px-2 py-0.5 rounded text-xs font-medium"
                                                                                style={{
                                                                                    backgroundColor: problem.difficulty === "Easy" ? "#DCFCE7" : problem.difficulty === "Medium" ? "#FEF3C7" : "#FEE2E2",
                                                                                    color: problem.difficulty === "Easy" ? "#16A34A" : problem.difficulty === "Medium" ? "#D97706" : "#DC2626",
                                                                                }}
                                                                            >
                                                                                {problem.difficulty}
                                                                            </span>
                                                                            <a href={problem.leetcode_url} target="_blank" rel="noopener noreferrer" className="p-1 rounded hover:bg-gray-100 transition-all">
                                                                                <ExternalLink className="w-4 h-4 text-secondary" />
                                                                            </a>
                                                                        </div>
                                                                    </div>
                                                                );
                                                            })}
                                                        </div>
                                                    </motion.div>
                                                )}
                                            </AnimatePresence>
                                        </motion.div>
                                    );
                                })}
                            </div>
                        </motion.div>

                        {/* Contest Info */}
                        {contestInfo?.userContestRanking && (
                            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-2xl p-8 shadow-sm" style={{ borderColor: "#E5E0D8", borderWidth: "1px" }}>
                                <div className="flex items-center gap-3 mb-6">
                                    <TrendingUp className="w-6 h-6" style={{ color: "#D95D39" }} />
                                    <h2 className="font-serif-bold text-2xl text-ink">Contest Performance</h2>
                                </div>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                                    <div><p className="text-sm text-secondary mb-1">Contests</p><p className="text-2xl font-serif-bold text-ink">{contestInfo.userContestRanking.attendedContestsCount}</p></div>
                                    <div><p className="text-sm text-secondary mb-1">Rating</p><p className="text-2xl font-serif-bold text-ink">{Math.round(contestInfo.userContestRanking.rating)}</p></div>
                                    <div><p className="text-sm text-secondary mb-1">Global Rank</p><p className="text-2xl font-serif-bold text-ink">#{contestInfo.userContestRanking.globalRanking?.toLocaleString()}</p></div>
                                    <div><p className="text-sm text-secondary mb-1">Top %</p><p className="text-2xl font-serif-bold text-ink">{contestInfo.userContestRanking.topPercentage?.toFixed(2)}%</p></div>
                                </div>
                            </motion.div>
                        )}

                        {/* Recent Submissions */}
                        {recentSubmissions.length > 0 && (
                            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-2xl p-8 shadow-sm" style={{ borderColor: "#E5E0D8", borderWidth: "1px" }}>
                                <div className="flex items-center gap-3 mb-6">
                                    <Clock className="w-6 h-6" style={{ color: "#D95D39" }} />
                                    <h2 className="font-serif-bold text-2xl text-ink">Recent Submissions</h2>
                                </div>
                                <div className="space-y-3">
                                    {recentSubmissions.slice(0, 5).map((sub, idx) => (
                                        <div key={sub.id || idx} className="flex items-center justify-between p-4 rounded-lg" style={{ backgroundColor: "#F9F8F5" }}>
                                            <div className="flex-1">
                                                <p className="font-medium text-ink">{sub.title}</p>
                                                <div className="flex items-center gap-3 mt-1">
                                                    <span className="text-xs text-secondary">{sub.langName || sub.lang}</span>
                                                    <span className="text-xs text-secondary">{new Date(parseInt(sub.timestamp) * 1000).toLocaleDateString()}</span>
                                                </div>
                                            </div>
                                            <span className="px-3 py-1 rounded-full text-xs font-medium" style={{ backgroundColor: sub.statusDisplay === "Accepted" ? "#DCFCE7" : "#FEE2E2", color: sub.statusDisplay === "Accepted" ? "#16A34A" : "#DC2626" }}>
                                                {sub.statusDisplay}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </motion.div>
                        )}
                    </motion.div>
                )}
            </div>
        </div>
    );
}