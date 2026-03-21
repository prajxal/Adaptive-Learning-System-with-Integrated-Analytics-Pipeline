import BACKEND_URL, { fetchWithAuth, getClerkToken } from "./api";

export interface GithubLanguageInsight {
    skill: string;
    weight: number;
    confidence: number;
}

export interface GithubAnalysisResponse {
    connected: boolean;
    username: string;
    languages: GithubLanguageInsight[];
}

const toNumber = (value: unknown): number => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
};

const normalizeLanguages = (payload: unknown): GithubLanguageInsight[] => {
    if (!Array.isArray(payload)) {
        return [];
    }

    return payload
        .map((item: any) => ({
            skill: String(item?.skill ?? "").trim(),
            weight: toNumber(item?.weight),
            confidence: toNumber(item?.confidence),
        }))
        .filter((item) => item.skill.length > 0);
};

export async function getGithubStatus() {
    const res = await fetch(`${BACKEND_URL}/github/status`, {
        headers: {
            Authorization: `Bearer ${await getClerkToken()}`,
        },
    });

    if (!res.ok) throw new Error("Failed to fetch GitHub status");

    return res.json();
}

export async function redirectToGithubConnect() {
    const res = await fetch(`${BACKEND_URL}/github/connect`, {
        headers: {
            Authorization: `Bearer ${await getClerkToken()}`,
        },
    });

    if (!res.ok) {
        throw new Error("Failed to initialize GitHub OAuth flow");
    }

    const data = await res.json();
    window.location.href = data.url;
}

export async function getGithubAnalysis(): Promise<GithubAnalysisResponse> {
    const res = await fetchWithAuth(`${BACKEND_URL}/users/me/github-analysis`);
    if (!res.ok) {
        throw new Error("Failed to fetch GitHub analysis");
    }

    const payload = await res.json();

    return {
        connected: Boolean(payload?.connected),
        username: String(payload?.username ?? ""),
        languages: normalizeLanguages(payload?.languages),
    };
}
