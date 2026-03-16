export interface Progress {
    roadmap_id: string;
    total_courses: number;
    completed_courses: number;
    progress_percent: number;
    trust_score: number;
    proficiency_level: number;
}

import BACKEND_URL, { getClerkToken } from "./api";

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
