import BACKEND_URL, { getClerkToken } from "../../services/api";

export type RecommendationResponse = {
  user_id: string;
  recommended_course: string;
  difficulty: string;
};

export type UserResponse = {
  user_id: string;
  skill_level: string;
  engagement_score: number;
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

export async function getRecommendation(userId: string): Promise<RecommendationResponse | null> {
  return requestJson<RecommendationResponse>(`${BACKEND_URL}/recommend/${userId}`);
}

export async function getUser(userId: string): Promise<UserResponse | null> {
  return requestJson<UserResponse>(`${BACKEND_URL}/users/${userId}`);
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
