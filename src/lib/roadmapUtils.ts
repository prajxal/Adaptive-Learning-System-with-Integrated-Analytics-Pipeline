import { DynamicCourseNode } from '../services/dynamicRoadmapApi';

/**
 * Sort order for course status — lower = appears first.
 * Completed/active statuses surface before locked courses.
 */
const STATUS_ORDER: Record<string, number> = {
  completed:   0,
  fast_tracked: 1,
  skippable:   2,
  unlocked:    3,
  locked:      4,
};

/**
 * Sort a flat list of DynamicCourseNode for display.
 *
 * Priority:
 *   1. required_level ascending (lower = earlier in the learning path)
 *   2. recommended course first within its required_level tier
 *   3. non-locked before locked within the same required_level tier
 *   4. original array order preserved otherwise (stable)
 */
export function sortDynamicCourses(
  courses: DynamicCourseNode[],
  recommendedId: string | null
): DynamicCourseNode[] {
  return courses.slice().sort((a, b) => {
    // 1. required_level ascending (treat missing/0 as lowest level)
    const diffA = a.required_level || 0;
    const diffB = b.required_level || 0;
    if (diffA !== diffB) return diffA - diffB;

    // 2. recommended course first within the same difficulty tier
    const recA = a.skill_id === recommendedId ? 0 : 1;
    const recB = b.skill_id === recommendedId ? 0 : 1;
    if (recA !== recB) return recA - recB;

    // 3. status order (non-locked before locked)
    const statusA = STATUS_ORDER[a.status] ?? 4;
    const statusB = STATUS_ORDER[b.status] ?? 4;
    return statusA - statusB;

    // original index is preserved by Array.prototype.sort stability (ES2019+)
  });
}
