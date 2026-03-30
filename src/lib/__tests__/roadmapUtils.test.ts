import { describe, it, expect } from 'vitest';
import { sortDynamicCourses } from '../roadmapUtils';
import type { DynamicCourseNode } from '../../services/dynamicRoadmapApi';

function node(
  skill_id: string,
  difficulty_level: number,
  status: DynamicCourseNode['status'] = 'locked'
): DynamicCourseNode {
  return {
    skill_id,
    title: skill_id,
    status,
    confidence: 0,
    proficiency: 0,
    difficulty_level,
    can_skip: false,
    can_fast_track: false,
    reason: '',
  };
}

describe('sortDynamicCourses', () => {
  it('returns an empty array unchanged', () => {
    expect(sortDynamicCourses([], null)).toEqual([]);
  });

  it('sorts by difficulty_level ascending', () => {
    const courses = [
      node('advanced', 1400, 'locked'),
      node('intro', 800, 'unlocked'),
      node('mid', 1100, 'locked'),
    ];
    const sorted = sortDynamicCourses(courses, null);
    expect(sorted.map((c) => c.skill_id)).toEqual(['intro', 'mid', 'advanced']);
  });

  it('puts the recommended course first within its difficulty tier', () => {
    const courses = [
      node('other-800', 800, 'unlocked'),
      node('recommended', 800, 'unlocked'),
    ];
    const sorted = sortDynamicCourses(courses, 'recommended');
    expect(sorted[0].skill_id).toBe('recommended');
  });

  it('puts non-locked before locked at the same difficulty', () => {
    const courses = [
      node('locked-a', 1000, 'locked'),
      node('unlocked-b', 1000, 'unlocked'),
    ];
    const sorted = sortDynamicCourses(courses, null);
    expect(sorted[0].skill_id).toBe('unlocked-b');
    expect(sorted[1].skill_id).toBe('locked-a');
  });

  it('applies priority: difficulty → recommended → status', () => {
    // recommended is at difficulty 1000 (mid-tier), others at 800
    const courses = [
      node('locked-800', 800, 'locked'),
      node('unlocked-800', 800, 'unlocked'),
      node('recommended-1000', 1000, 'unlocked'),
      node('locked-1000', 1000, 'locked'),
    ];
    const sorted = sortDynamicCourses(courses, 'recommended-1000');
    const ids = sorted.map((c) => c.skill_id);
    // difficulty 800 tier comes first (unlocked before locked within it),
    // then difficulty 1000 (recommended first, then locked)
    expect(ids).toEqual([
      'unlocked-800',
      'locked-800',
      'recommended-1000',
      'locked-1000',
    ]);
  });

  it('status ordering: completed → fast_tracked → skippable → unlocked → locked', () => {
    const courses = [
      node('locked', 1000, 'locked'),
      node('skippable', 1000, 'skippable'),
      node('fast_tracked', 1000, 'fast_tracked'),
      node('unlocked', 1000, 'unlocked'),
      node('completed', 1000, 'completed'),
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

  it('treats missing/zero difficulty_level as lowest difficulty', () => {
    const zero = node('zero', 0, 'locked');
    const normal = node('normal', 800, 'unlocked');
    const sorted = sortDynamicCourses([normal, zero], null);
    expect(sorted[0].skill_id).toBe('zero');
  });

  it('does not mutate the original array', () => {
    const courses = [node('b', 1000, 'locked'), node('a', 800, 'unlocked')];
    const original = [...courses];
    sortDynamicCourses(courses, null);
    expect(courses[0].skill_id).toBe(original[0].skill_id);
  });

  it('recommended course at a higher difficulty does not jump ahead of lower-difficulty courses', () => {
    const courses = [
      node('intro', 800, 'unlocked'),
      node('recommended-advanced', 1600, 'unlocked'),
    ];
    const sorted = sortDynamicCourses(courses, 'recommended-advanced');
    // recommended is at depth 1600 — should NOT jump to the top
    expect(sorted[0].skill_id).toBe('intro');
    expect(sorted[1].skill_id).toBe('recommended-advanced');
  });

  it('preserves relative order of courses with identical difficulty and status (stability)', () => {
    const courses = [
      node('first', 1000, 'locked'),
      node('second', 1000, 'locked'),
      node('third', 1000, 'locked'),
    ];
    const sorted = sortDynamicCourses(courses, null);
    expect(sorted.map((c) => c.skill_id)).toEqual(['first', 'second', 'third']);
  });
});
