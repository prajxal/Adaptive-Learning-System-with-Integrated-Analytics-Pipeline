import BACKEND_URL, { getClerkToken } from "../../services/api";

// --- Types ---
export interface SkillProfile {
    skill_id: string;
    proficiency_level: number;
    confidence: number;
    github_proficiency: number;
    resume_proficiency: number;
    quiz_proficiency: number;
}

export interface QuizQuestion {
    id?: string;
    question: string;
    options: string[];
    explanation?: string;
    correct_answer?: string;
}

export interface Quiz {
    id: string;
    skill_id: string;
    title?: string;
    questions: QuizQuestion[];
    passing_score: number;
}

export interface QuizSubmissionResponse {
    attempt_id: string;
    skill_id: string;
    score: number;
    passed: boolean;
    message: string;
}

// --- Helper for Authorized Requests ---
async function getAuthHeaders(): Promise<HeadersInit> {
    const token = await getClerkToken();
    return {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
}

// --- API Methods ---

export async function getSkillProfile(skillId: string): Promise<SkillProfile | null> {
    try {
        const response = await fetch(`${BACKEND_URL}/skill-profile/${encodeURIComponent(skillId)}`, {
            headers: await getAuthHeaders(),
        });
        if (!response.ok) throw new Error(`Failed to fetch profile: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error("Error fetching skill profile:", error);
        return null;
    }
}

export async function getQuiz(skillId: string): Promise<Quiz | null> {
    try {
        const response = await fetch(`${BACKEND_URL}/quiz/${encodeURIComponent(skillId)}`, {
            headers: await getAuthHeaders(),
        });
        // Can also 503 if Gemini fails
        if (!response.ok) throw new Error(`Failed to fetch/generate quiz: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error("Error fetching quiz:", error);
        return null;
    }
}

export async function submitQuizAttempt(skillId: string, answers: Record<string, string>): Promise<QuizSubmissionResponse | null> {
    try {
        const response = await fetch(`${BACKEND_URL}/quiz/${encodeURIComponent(skillId)}/submit`, {
            method: "POST",
            headers: await getAuthHeaders(),
            body: JSON.stringify({ answers }),
        });
        if (!response.ok) throw new Error(`Failed to submit quiz: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error("Error submitting quiz:", error);
        return null;
    }
}
