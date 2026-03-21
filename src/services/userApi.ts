import BACKEND_URL, { fetchWithAuth, getClerkToken } from "./api";

export interface UserSkillProfileItem {
    skill_id: string;
    proficiency_level: number;
    confidence: number;
}

const toNumber = (value: unknown): number => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
};

const normalizeSkillProfile = (payload: unknown): UserSkillProfileItem[] => {
    const skillArray = Array.isArray(payload)
        ? payload
        : Array.isArray((payload as { skills?: unknown[] })?.skills)
            ? (payload as { skills: unknown[] }).skills
            : [];

    return skillArray
        .map((item: any) => ({
            skill_id: String(item?.skill_id ?? item?.roadmap_id ?? "").trim(),
            proficiency_level: toNumber(item?.proficiency_level),
            confidence: toNumber(item?.confidence),
        }))
        .filter((item) => item.skill_id.length > 0);
};

export async function getUserProfile() {
    const response = await fetch(`${BACKEND_URL}/users/me/profile`, {
        headers: {
            Authorization: `Bearer ${await getClerkToken()}`,
            "Content-Type": "application/json"
        }
    });

    if (!response.ok) throw new Error("Failed to fetch user profile");
    return response.json();
}

export async function getUserSkills() {
    console.log("Token:", await getClerkToken());

    const response = await fetch(`${BACKEND_URL}/users/me/skills`, {
        headers: {
            Authorization: `Bearer ${await getClerkToken()}`,
            "Content-Type": "application/json"
        }
    });

    console.log("Response status:", response.status);

    const text = await response.text();
    console.log("Response body:", text);

    if (!response.ok) throw new Error(text);

    return JSON.parse(text);
}

export async function getUserSkillProfile(): Promise<UserSkillProfileItem[]> {
    const response = await fetchWithAuth(`${BACKEND_URL}/users/me/skills`, {
        headers: {
            "Content-Type": "application/json"
        }
    });

    if (!response.ok) {
        throw new Error("Failed to fetch user skills");
    }

    const payload = await response.json();
    return normalizeSkillProfile(payload);
}
