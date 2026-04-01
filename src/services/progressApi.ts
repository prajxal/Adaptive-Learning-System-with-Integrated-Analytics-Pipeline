export interface Progress {
    roadmap_id: string;
    total_courses: number;
    completed_courses: number;
    progress_percent: number;
    xp: number;
    level: number;
    proficiency_level: number;
}

import BACKEND_URL, { fetchWithAuth, getClerkToken } from "./api";

export async function getProgress(roadmapId: string): Promise<Progress | null> {
    try {
        const res = await fetch(`${BACKEND_URL}/progress/${roadmapId}`, {
            headers: {
                Authorization: `Bearer ${await getClerkToken()}`
            }
        });
        if (!res.ok) return null;

        return await res.json();
    } catch {
        return null;
    }
}

export async function getAllProgress(): Promise<Progress[]> {
    try {
        const res = await fetchWithAuth(`${BACKEND_URL}/progress/all`);
        if (!res.ok) return [];
        const data = await res.json();
        return data?.roadmaps ?? [];
    } catch {
        return [];
    }
}

export async function getRoadmapProgress(roadmapId: string): Promise<Record<string, number>> {
    try {
        const res = await fetchWithAuth(`${BACKEND_URL}/progress/roadmap/${roadmapId}`);
        if (!res.ok) return {};
        const data = await res.json();
        return data?.course_progress ?? {};
    } catch {
        return {};
    }
}
