import { describe, it, expect } from 'vitest';
import { sortDynamicCourses } from '../roadmapUtils';
import type { DynamicCourseNode } from '../../services/dynamicRoadmapApi';

function node(
  skill_id: string,
  required_level: number,
  status: DynamicCourseNode['status'] = 'locked'
): DynamicCourseNode {
  return {
    skill_id,
    title: skill_id,
    status,
    confidence: 0,
    proficiency: 0,
    required_level,
    can_skip: false,
    can_fast_track: false,
    reason: '',
  };
}

describe('sortDynamicCourses', () => {
  it('returns an empty array unchanged', () => {
    expect(sortDynamicCourses([], null)).toEqual([]);
  });

  it('sorts by required_level ascending', () => {
    const courses = [
      node('advanced', 5, 'locked'),
      node('intro', 1, 'unlocked'),
      node('mid', 3, 'locked'),
    ];
    const sorted = sortDynamicCourses(courses, null);
    expect(sorted.map((c) => c.skill_id)).toEqual(['intro', 'mid', 'advanced']);
  });

  it('puts the recommended course first within its required_level tier', () => {
    const courses = [
      node('other-1', 1, 'unlocked'),
      node('recommended', 1, 'unlocked'),
    ];
    const sorted = sortDynamicCourses(courses, 'recommended');
    expect(sorted[0].skill_id).toBe('recommended');
  });

  it('puts non-locked before locked at the same required_level', () => {
    const courses = [
      node('locked-a', 2, 'locked'),
      node('unlocked-b', 2, 'unlocked'),
    ];
    const sorted = sortDynamicCourses(courses, null);
    expect(sorted[0].skill_id).toBe('unlocked-b');
    expect(sorted[1].skill_id).toBe('locked-a');
  });

  it('applies priority: required_level → recommended → status', () => {
    // recommended is at level 3 (mid-tier), others at level 1
    const courses = [
      node('locked-1', 1, 'locked'),
      node('unlocked-1', 1, 'unlocked'),
      node('recommended-3', 3, 'unlocked'),
      node('locked-3', 3, 'locked'),
    ];
    const sorted = sortDynamicCourses(courses, 'recommended-3');
    const ids = sorted.map((c) => c.skill_id);
    // level 1 tier comes first (unlocked before locked within it),
    // then level 3 (recommended first, then locked)
    expect(ids).toEqual([
      'unlocked-1',
      'locked-1',
      'recommended-3',
      'locked-3',
    ]);
  });

  it('status ordering: completed → fast_tracked → skippable → unlocked → locked', () => {
    const courses = [
      node('locked', 2, 'locked'),
      node('skippable', 2, 'skippable'),
      node('fast_tracked', 2, 'fast_tracked'),
      node('unlocked', 2, 'unlocked'),
      node('completed', 2, 'completed'),
    ];
    const sorted = sortDynamicCourses(courses, null);
    expect(sorted.map((c) => c.status)).toEqual([
      'completed',
      'fast_tracked',
      'skippable',
      'unlocked',
      'locked',
    ]);
  });

  it('treats missing/zero required_level as lowest level', () => {
    const zero = node('zero', 0, 'locked');
    const normal = node('normal', 2, 'unlocked');
    const sorted = sortDynamicCourses([normal, zero], null);
    expect(sorted[0].skill_id).toBe('zero');
  });

  it('does not mutate the original array', () => {
    const courses = [node('b', 3, 'locked'), node('a', 1, 'unlocked')];
    const original = [...courses];
    sortDynamicCourses(courses, null);
    expect(courses[0].skill_id).toBe(original[0].skill_id);
  });

  it('recommended course at a higher level does not jump ahead of lower-level courses', () => {
    const courses = [
      node('intro', 1, 'unlocked'),
      node('recommended-advanced', 5, 'unlocked'),
    ];
    const sorted = sortDynamicCourses(courses, 'recommended-advanced');
    // recommended is at level 5 — should NOT jump to the top
    expect(sorted[0].skill_id).toBe('intro');
    expect(sorted[1].skill_id).toBe('recommended-advanced');
  });

  it('preserves relative order of courses with identical required_level and status (stability)', () => {
    const courses = [
      node('first', 3, 'locked'),
      node('second', 3, 'locked'),
      node('third', 3, 'locked'),
    ];
    const sorted = sortDynamicCourses(courses, null);
    expect(sorted.map((c) => c.skill_id)).toEqual(['first', 'second', 'third']);
  });
});
