import BACKEND_URL, { getClerkToken } from "../../services/api";

export type RoadmapNode = {
  id: string;
  title: string;
  difficulty: number;
  roadmap_id: string;
};

export type RecommendationResponse = {
  user_xp: number;
  user_level: number;
  next_in_current_roadmap: RoadmapNode[];
  suggested_new_roadmaps: string[];
};

export type UserResponse = {
  id: string;
  email: string;
  total_xp: number;
  current_level: number;
  resume_status: string | null;
  github_status: string | null;
};

export type EventPayload = {
  user_id: string;
  event_type: string;
  course_id?: string;
};

type EventResponse = {
  status: string;
};

async function requestJson<T>(url: string, options: RequestInit = {}): Promise<T | null> {
  try {
    const token = await getClerkToken();
    const headers = {
      ...options.headers,
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    const response = await fetch(url, { ...options, headers });

    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    return (await response.json()) as T;
  } catch (error) {
    console.error("API error:", error);
    return null;
  }
}

export async function getRecommendation(currentRoadmapId: string): Promise<RecommendationResponse | null> {
  return requestJson<RecommendationResponse>(
    `${BACKEND_URL}/recommend/recommend?current_roadmap_id=${encodeURIComponent(currentRoadmapId)}`
  );
}

export async function getUser(): Promise<UserResponse | null> {
  return requestJson<UserResponse>(`${BACKEND_URL}/users/me`);
}

export async function sendEvent(event: EventPayload): Promise<EventResponse | null> {
  return requestJson<EventResponse>(`${BACKEND_URL}/events`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(event),
  });
}
