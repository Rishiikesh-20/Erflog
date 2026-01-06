// LeetCode API Service using Next.js proxy (Vercel API)
const API_PROXY = "/api/leetcode";

// New API response types for leetcode-api-pied.vercel.app
export interface LeetCodeProfile {
    username: string;
    githubUrl: string | null;
    twitterUrl: string | null;
    linkedinUrl: string | null;
    profile: {
        userAvatar: string;
        realName: string;
        websites: string[];
        countryName: string;
        company: string | null;
        jobTitle: string | null;
        skillTags: string[];
        school: string | null;
        aboutMe: string;
        ranking: number;
        reputation: number;
    };
    submitStats: {
        acSubmissionNum: {
            difficulty: string;
            count: number;
            submissions: number;
        }[];
        totalSubmissionNum: {
            difficulty: string;
            count: number;
            submissions: number;
        }[];
    };
    contestBadge: {
        name: string;
    } | null;
}

export interface ContestInfo {
    userContestRanking: {
        attendedContestsCount: number;
        rating: number;
        globalRanking: number;
        totalParticipants: number;
        topPercentage: number;
        badge: { name: string } | null;
    } | null;
    userContestRankingHistory: {
        attended: boolean;
        rating: number;
        ranking: number;
        trendDirection: string;
        problemsSolved: number;
        totalProblems: number;
        finishTimeInSeconds: number;
        contest: {
            title: string;
            startTime: number;
        };
    }[];
}

export interface RecentSubmission {
    id: string;
    title: string;
    titleSlug: string;
    timestamp: string;
    status: number;
    statusDisplay: string;
    lang: string;
    langName: string;
    runtime: string;
    memory: string;
}

// Simple localStorage cache to avoid hitting rate limits
const CACHE_DURATION_MS = 24 * 60 * 60 * 1000; // 24 hours

function getCachedData<T>(key: string): T | null {
    if (typeof window === 'undefined') return null;
    try {
        const cached = localStorage.getItem(`leetcode_${key}`);
        if (cached) {
            const { data, timestamp } = JSON.parse(cached);
            if (Date.now() - timestamp < CACHE_DURATION_MS) {
                return data as T;
            }
            localStorage.removeItem(`leetcode_${key}`);
        }
    } catch {
        // Ignore cache errors
    }
    return null;
}

function setCachedData<T>(key: string, data: T): void {
    if (typeof window === 'undefined') return;
    try {
        localStorage.setItem(`leetcode_${key}`, JSON.stringify({
            data,
            timestamp: Date.now()
        }));
    } catch {
        // Ignore cache errors (storage full, etc.)
    }
}

class LeetCodeAPIService {
    private async fetchWithRetry(endpoint: string, maxRetries = 3): Promise<any> {
        let lastError: Error | null = null;

        for (let attempt = 0; attempt < maxRetries; attempt++) {
            try {
                if (attempt > 0) {
                    const backoffMs = Math.pow(2, attempt) * 1000;
                    await new Promise(resolve => setTimeout(resolve, backoffMs));
                }

                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 20000);

                const url = `${API_PROXY}?endpoint=${encodeURIComponent(endpoint)}`;
                const response = await fetch(url, { signal: controller.signal });
                clearTimeout(timeoutId);

                if (response.status === 429) {
                    lastError = new Error('Rate limited');
                    continue;
                }

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                if (error instanceof Error && error.name === 'AbortError') {
                    lastError = new Error('Request timeout. The LeetCode API might be slow.');
                } else {
                    lastError = error instanceof Error ? error : new Error('Unknown error');
                }
            }
        }

        throw lastError || new Error('Failed after retries');
    }

    async getUserProfile(username: string): Promise<LeetCodeProfile> {
        const cacheKey = `profile_${username}`;
        const cached = getCachedData<LeetCodeProfile>(cacheKey);
        if (cached) return cached;

        const data = await this.fetchWithRetry(`/user/${username}`);
        setCachedData(cacheKey, data);
        return data;
    }

    async getContestInfo(username: string): Promise<ContestInfo> {
        const cacheKey = `contest_${username}`;
        const cached = getCachedData<ContestInfo>(cacheKey);
        if (cached) return cached;

        const data = await this.fetchWithRetry(`/user/${username}/contests`);
        setCachedData(cacheKey, data);
        return data;
    }

    async getRecentSubmissions(username: string): Promise<RecentSubmission[]> {
        const cacheKey = `submissions_${username}`;
        const cached = getCachedData<RecentSubmission[]>(cacheKey);
        if (cached) return cached;

        const data = await this.fetchWithRetry(`/user/${username}/submissions`);
        setCachedData(cacheKey, data);
        return data;
    }
}

export const leetcodeAPI = new LeetCodeAPIService();
