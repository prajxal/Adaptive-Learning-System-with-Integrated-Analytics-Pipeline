
export interface Roadmap {
    id: string;
    topic_count: number;
}

import BACKEND_URL, { getClerkToken } from "./api";

export async function getRoadmaps(): Promise<Roadmap[]> {
    try {
        const res = await fetch(`${BACKEND_URL}/roadmaps`, {
            headers: {
                Authorization: `Bearer ${await getClerkToken()}`
            }
        });
        if (!res.ok) throw new Error("Failed to fetch roadmaps");
        return await res.json();
    } catch (err) {
        console.error(err);
        return [];
    }
}
