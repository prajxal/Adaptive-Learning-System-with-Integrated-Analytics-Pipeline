import BACKEND_URL, { fetchWithAuth } from "./api";

export type CourseNodeStatus = 'completed' | 'skippable' | 'fast_tracked' | 'unlocked' | 'locked';

export interface CoursePrerequisiteRef {
  id: string;
  title: string;
  completed: boolean;
}

export interface DynamicCourseNode {
  skill_id: string;
  title: string;
  status: CourseNodeStatus;
  confidence: number;
  proficiency: number;
  required_level: number;
  can_skip: boolean;
  can_fast_track: boolean;
  reason: string;
  prerequisites: CoursePrerequisiteRef[];
}

export interface DynamicRoadmapStatus {
  roadmap_id: string;
  courses: DynamicCourseNode[];
  summary: {
    total: number;
    completed: number;
    skippable: number;
    fast_tracked: number;
    unlocked: number;
    locked: number;
  };
  thresholds: {
    skip: number;
    fast_track: number;
  };
  computed_in_ms: number;
}

export async function getDynamicRoadmapStatus(roadmapId: string): Promise<DynamicRoadmapStatus> {
  const res = await fetchWithAuth(`${BACKEND_URL}/skill-graph/${roadmapId}/dynamic-status`);
  if (!res.ok) {
    throw new Error(`Failed to fetch dynamic roadmap status: ${res.status}`);
  }
  return res.json();
}

export async function skipCourse(courseId: string): Promise<void> {
  const res = await fetchWithAuth(`${BACKEND_URL}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_type: "course_skipped", course_id: courseId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Skip failed: ${res.status}`);
  }
}

export async function unskipCourse(courseId: string): Promise<void> {
  const res = await fetchWithAuth(`${BACKEND_URL}/events/skip/${encodeURIComponent(courseId)}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Un-skip failed: ${res.status}`);
  }
}
