import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ROUTES } from "../constants/routes";
import AppBreadcrumb from "../components/AppBreadcrumb";
import { RecommendationPanel } from "../components/RecommendationPanel";
import { usePostHog } from "@posthog/react";
import {
  getDynamicRoadmapStatus,
  skipCourse,
  unskipCourse,
  DynamicCourseNode,
  CourseNodeStatus,
} from "../../services/dynamicRoadmapApi";
import BACKEND_URL, { fetchWithAuth } from "../../services/api";
import DataLoadingState from "../components/DataLoadingState";
import RoadmapDetailSkeleton from "../components/skeletons/RoadmapDetailSkeleton";
import { CourseDifficultyBadge } from "../components/CourseDifficultyBadge";
import { eloToLevel, getCourseDifficultyInfo } from "../../lib/xpUtils";
import { sortDynamicCourses } from "../../lib/roadmapUtils";
import { getUserProfile } from "../../services/userApi";

// Minimal shape from /courses?roadmap_id= used only for the recommendation banner
interface RecommendedCourse {
  id: string;
  title: string;
}

// --- Badge config for each status ---
const BADGE_CONFIG: Record<
  CourseNodeStatus,
  { label: string; badgeClass: string; cardExtraClass: string }
> = {
  completed: {
    label: "Mastered",
    badgeClass: "bg-green-500 text-white",
    cardExtraClass: "",
  },
  skippable: {
    label: "Skip Available",
    badgeClass: "bg-amber-400 text-amber-900",
    cardExtraClass: "border-amber-400/60",
  },
  fast_tracked: {
    label: "Fast Track",
    badgeClass: "bg-blue-500 text-white",
    cardExtraClass: "border-blue-400/60",
  },
  unlocked: {
    label: "Unlocked",
    badgeClass: "bg-indigo-500 text-white",
    cardExtraClass: "",
  },
  locked: {
    label: "Locked",
    badgeClass: "bg-[#1e1e2e] text-[#64748b]",
    cardExtraClass: "opacity-50 cursor-not-allowed",
  },
};

// Per-card skip button state
interface SkipState {
  loading: boolean;
  error: string | null;
}

export default function RoadmapDetailPage() {
  const { roadmapId } = useParams<{ roadmapId: string }>();
  const navigate = useNavigate();
  const posthog = usePostHog();

  const [dynamicCourses, setDynamicCourses] = useState<DynamicCourseNode[]>([]);
  const [coursesLoading, setCoursesLoading] = useState(true);
  const [recommendedStart, setRecommendedStart] = useState<RecommendedCourse | null>(null);
  const [alternativeStarts, setAlternativeStarts] = useState<RecommendedCourse[]>([]);
  const [skipStates, setSkipStates] = useState<Record<string, SkipState>>({});
  const [unskipLoading, setUnskipLoading] = useState<Record<string, boolean>>({});
  const [userLevel, setUserLevel] = useState<number | undefined>(undefined);

  const sortedCourses = useMemo(
    () => sortDynamicCourses(dynamicCourses, recommendedStart?.id ?? null),
    [dynamicCourses, recommendedStart]
  );

  const loadDynamicStatus = useCallback(async () => {
    if (!roadmapId) return;
    try {
      const status = await getDynamicRoadmapStatus(roadmapId);
      setDynamicCourses(status.courses);
    } catch (err) {
      console.error("Failed to load dynamic roadmap status:", err);
    }
  }, [roadmapId]);

  useEffect(() => {
    async function load() {
      if (!roadmapId) return;
      setCoursesLoading(true);
      try {
        // Fetch dynamic status (primary data source — single request)
        const [, coursesRes, profileData] = await Promise.all([
          loadDynamicStatus(),
          // Keep the /courses call only for recommendation panel data (recommended_start / alternative_starts)
          fetchWithAuth(`${BACKEND_URL}/courses?roadmap_id=${roadmapId}`),
          getUserProfile().catch(() => null),
        ]);

        if (profileData?.global_elo_rating != null) {
          setUserLevel(eloToLevel(profileData.global_elo_rating).level);
        }

        if (coursesRes && coursesRes.ok) {
          const data = await coursesRes.json();
          setRecommendedStart(data.recommended_start ?? null);
          setAlternativeStarts(data.alternative_starts ?? []);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setCoursesLoading(false);
      }
    }
    load();
  }, [roadmapId, loadDynamicStatus]);

  const handleSkip = useCallback(
    async (courseId: string, courseTitle: string) => {
      posthog?.capture("course_skip_clicked", {
        course_id: courseId,
        roadmap_id: roadmapId,
        course_title: courseTitle,
      });

      setSkipStates((prev) => ({
        ...prev,
        [courseId]: { loading: true, error: null },
      }));

      try {
        await skipCourse(courseId);
        posthog?.capture("course_skip_success", {
          course_id: courseId,
          roadmap_id: roadmapId,
          course_title: courseTitle,
        });
        setSkipStates((prev) => ({
          ...prev,
          [courseId]: { loading: false, error: null },
        }));
        // Refetch dynamic status so the UI reflects the skip
        await loadDynamicStatus();
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to skip course";
        setSkipStates((prev) => ({
          ...prev,
          [courseId]: { loading: false, error: message },
        }));
        posthog?.capture("course_skip_failed", {
          course_id: courseId,
          error: (err as Error).message,
        });
      }
    },
    [roadmapId, posthog, loadDynamicStatus]
  );

  const handleUnskip = useCallback(
    async (courseId: string) => {
      setUnskipLoading((prev) => ({ ...prev, [courseId]: true }));
      try {
        await unskipCourse(courseId);
        posthog?.capture("course_unskipped", {
          course_id: courseId,
          roadmap_id: roadmapId,
        });
        await loadDynamicStatus();
      } catch (err) {
        // Silently swallow 404 — course was completed normally, not skipped
        const message = err instanceof Error ? err.message : "";
        if (!message.includes("404") && !message.includes("Un-skip failed: 404")) {
          setSkipStates((prev) => ({
            ...prev,
            [courseId]: { loading: false, error: message || "Failed to undo skip" },
          }));
        }
      } finally {
        setUnskipLoading((prev) => ({ ...prev, [courseId]: false }));
      }
    },
    [roadmapId, posthog, loadDynamicStatus]
  );

  const handleFastTrack = useCallback(
    (courseId: string, courseTitle: string) => {
      posthog?.capture("course_fast_track_clicked", {
        course_id: courseId,
        roadmap_id: roadmapId,
        course_title: courseTitle,
      });
      navigate(ROUTES.QUIZ(courseId));
    },
    [roadmapId, posthog, navigate]
  );

  const handleLearnAnyway = useCallback(
    (courseId: string) => {
      navigate(ROUTES.COURSE(courseId));
    },
    [navigate]
  );

  const handleCourseClick = useCallback(
    (course: DynamicCourseNode) => {
      if (course.status === "locked") return;
      posthog?.capture("course_selected", {
        course_id: course.skill_id,
        roadmap_id: roadmapId,
        course_title: course.title,
        difficulty_level: course.difficulty_level,
        difficulty_label: getCourseDifficultyInfo(course.difficulty_level).label,
        status: course.status,
      });
      navigate(ROUTES.COURSE(course.skill_id));
    },
    [roadmapId, posthog, navigate]
  );

  if (coursesLoading) {
    return (
      <div className="roadmap-detail-root" style={{ backgroundColor: "#0a0a0f", minHeight: "100vh" }}>
        <DataLoadingState>
          <RoadmapDetailSkeleton />
        </DataLoadingState>
      </div>
    );
  }

  return (
    <div className="roadmap-detail-root">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Sora:wght@400;500;600;700;800&display=swap');

        .roadmap-detail-root {
          --bg-primary: #0a0a0f;
          --bg-card: #111118;
          --bg-card-hover: #16161f;
          --accent-primary: #6366f1;
          --accent-secondary: #818cf8;
          --text-primary: #f1f5f9;
          --text-muted: #64748b;
          --border: #1e1e2e;

          background-color: var(--bg-primary);
          color: var(--text-primary);
          font-family: 'DM Sans', sans-serif;

          min-height: 100vh;
          position: relative;
        }

        .roadmap-detail-bg {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: radial-gradient(ellipse at 20% 0%, rgba(99,102,241,0.06) 0%, transparent 60%);
          pointer-events: none;
          z-index: 0;
        }

        .title-font {
          font-family: 'Sora', sans-serif;
        }

        .course-card {
          background-color: var(--bg-card);
          border: 1px solid var(--border);
          transition: all 0.2s ease;
          display: flex;
          flex-direction: column;
          text-decoration: none;
          border-radius: 0.75rem;
          padding: 1.5rem;
        }

        .course-card.interactive:hover {
          box-shadow: 0 0 24px rgba(99,102,241,0.15);
          border-color: var(--accent-primary);
        }

        .course-card.locked {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .status-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.375rem;
          padding: 0.25rem 0.625rem;
          border-radius: 9999px;
          font-size: 0.75rem;
          font-weight: 600;
        }

        .confidence-indicator {
          font-size: 0.7rem;
          font-weight: 600;
          opacity: 0.8;
          margin-top: 0.25rem;
        }

        .action-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 0.375rem;
          padding: 0.5rem 1rem;
          border-radius: 0.5rem;
          font-size: 0.8rem;
          font-weight: 600;
          cursor: pointer;
          border: none;
          transition: opacity 0.15s ease, background-color 0.15s ease;
        }

        .action-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .btn-skip {
          background-color: #f59e0b;
          color: #1c1917;
        }
        .btn-skip:hover:not(:disabled) {
          background-color: #d97706;
        }

        .btn-learn-anyway {
          background-color: transparent;
          color: var(--text-muted);
          border: 1px solid var(--border);
        }
        .btn-learn-anyway:hover:not(:disabled) {
          color: var(--text-primary);
          border-color: #64748b;
        }

        .btn-fast-track {
          background-color: #3b82f6;
          color: white;
        }
        .btn-fast-track:hover:not(:disabled) {
          background-color: #2563eb;
        }

        .btn-start {
          background-color: #6366f1;
          color: white;
        }
        .btn-start:hover:not(:disabled) {
          background-color: #4f46e5;
        }

        .skip-error {
          font-size: 0.7rem;
          color: #f87171;
          margin-top: 0.25rem;
          text-align: center;
        }
      `}</style>

      <div className="roadmap-detail-bg"></div>

      <div className="flex h-full min-h-0 w-full overflow-hidden relative z-10 px-4 sm:px-6 lg:px-8 py-8 max-w-[1400px] mx-auto">
        {/* Left — Roadmap Grid */}
        <div className="flex-1 overflow-auto pr-0 lg:pr-8 space-y-10">
          <AppBreadcrumb
            segments={[
              { label: "Home", href: "/dashboard" },
              { label: "Learning Paths", href: "/roadmaps" },
              { label: roadmapId?.replace(/-/g, " ") || "Roadmap" },
            ]}
          />

          <div>
            <h1 className="title-font text-4xl md:text-5xl font-bold capitalize mb-3 tracking-tight">
              {roadmapId?.replace(/-/g, " ")}
            </h1>
            <p className="text-lg" style={{ color: "var(--text-muted)" }}>
              {sortedCourses.length} topics in this track
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sortedCourses.length === 0 ? (
              <div
                className="col-span-1 md:col-span-2 py-12 text-center"
                style={{ color: "var(--text-muted)" }}
              >
                No topics found for this roadmap
              </div>
            ) : (
              sortedCourses.map((course) => {
                const badgeCfg = BADGE_CONFIG[course.status];
                const isLocked = course.status === "locked";
                const isSkippable = course.status === "skippable";
                const isFastTracked = course.status === "fast_tracked";
                const isUnlocked = course.status === "unlocked";
                const isCompleted = course.status === "completed";
                const isRecommended =
                  recommendedStart?.id === course.skill_id && isUnlocked;
                const skipState = skipStates[course.skill_id];
                const skipLoading = skipState?.loading ?? false;
                const skipError = skipState?.error ?? null;
                const isUnskipLoading = unskipLoading[course.skill_id] ?? false;
                const showConfidence = isSkippable || isFastTracked;
                const confidencePercent = Math.round(Math.min(1, Math.max(0, course.confidence)) * 100);

                return (
                  <div
                    key={course.skill_id}
                    className={`course-card ${badgeCfg.cardExtraClass} ${
                      isLocked ? "locked" : "interactive cursor-pointer"
                    }`}
                    onClick={() => {
                      if (!isLocked) handleCourseClick(course);
                    }}
                  >
                    {/* Header */}
                    <div className="flex justify-between items-start mb-4">
                      <h3
                        className="title-font text-xl font-bold leading-tight pr-4"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {course.title}
                      </h3>
                      <div className="shrink-0 flex flex-col items-end gap-1">
                        <div className={`status-badge ${badgeCfg.badgeClass}`}>
                          {isCompleted && "✓ "}
                          {isFastTracked && "⚡ "}
                          {badgeCfg.label}
                        </div>
                        {isRecommended && (
                          <div className="status-badge bg-indigo-900/60 text-indigo-300 text-[10px]">
                            ★ Start Here
                          </div>
                        )}
                        {showConfidence && (
                          <span
                            className="confidence-indicator"
                            style={{
                              color: isFastTracked ? "#60a5fa" : "#fbbf24",
                            }}
                          >
                            {confidencePercent}% confidence
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Lock reason block — prominent amber callout for locked courses */}
                    {isLocked && course.reason && (
                      <div
                        className="flex items-start gap-2 rounded-md px-3 py-2 mt-1 mb-3 text-xs font-medium"
                        style={{
                          backgroundColor: 'rgba(245,158,11,0.08)',
                          border: '1px solid rgba(245,158,11,0.25)',
                          color: '#d97706',
                        }}
                      >
                        <span style={{ flexShrink: 0, marginTop: '1px' }}>⏳</span>
                        <span>{course.reason}</span>
                      </div>
                    )}

                    {/* Reason caption for non-locked statuses */}
                    {!isLocked && course.reason && (
                      <p className="text-xs italic text-muted-foreground mt-1">{course.reason}</p>
                    )}

                    {/* Prerequisite list — shown on locked cards when prereqs exist */}
                    {isLocked && course.prerequisites?.length > 0 && (
                      <div className="mb-4">
                        <p
                          className="text-xs font-semibold uppercase tracking-wide mb-2"
                          style={{ color: 'rgba(255,255,255,0.35)' }}
                        >
                          Prerequisites
                        </p>
                        <ul className="flex flex-col gap-1.5">
                          {course.prerequisites.map((prereq) => (
                            <li
                              key={prereq.id}
                              className="flex items-center justify-between gap-3 text-sm"
                            >
                              {prereq.completed ? (
                                <span
                                  className="flex items-center gap-1.5"
                                  style={{ color: 'rgba(255,255,255,0.35)' }}
                                >
                                  <span style={{ color: '#4ade80' }}>✓</span>
                                  <span className="line-through">{prereq.title}</span>
                                </span>
                              ) : (
                                <>
                                  <span style={{ color: 'rgba(255,255,255,0.7)' }}>
                                    {prereq.title}
                                  </span>
                                  <button
                                    className="shrink-0 text-xs font-semibold"
                                    style={{ color: '#818cf8' }}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      navigate(ROUTES.COURSE(prereq.id));
                                    }}
                                  >
                                    Start Learning →
                                  </button>
                                </>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Difficulty */}
                    <div className="mb-6">
                      <CourseDifficultyBadge
                        difficultyLevel={course.difficulty_level}
                        isLocked={isLocked}
                        userLevel={userLevel}
                      />
                    </div>

                    {/* Undo skip for completed cards */}
                    {isCompleted && (
                      <div
                        className="mt-auto pt-2"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          disabled={isUnskipLoading}
                          onClick={() => handleUnskip(course.skill_id)}
                          className="text-xs text-gray-400 underline disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isUnskipLoading ? "Undoing..." : "Undo skip"}
                        </button>
                      </div>
                    )}

                    {/* Action buttons */}
                    {!isLocked && !isCompleted && (
                      <div
                        className="mt-auto flex flex-col gap-2"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {isSkippable && (
                          <>
                            <div className="flex gap-2">
                              <button
                                className="action-btn btn-skip flex-1"
                                disabled={skipLoading}
                                onClick={() =>
                                  handleSkip(course.skill_id, course.title)
                                }
                              >
                                {skipLoading ? (
                                  <span className="inline-block w-3 h-3 border-2 border-amber-900 border-t-transparent rounded-full animate-spin" />
                                ) : null}
                                {skipLoading ? "Skipping..." : "Skip"}
                              </button>
                              <button
                                className="action-btn btn-learn-anyway flex-1"
                                onClick={() =>
                                  handleLearnAnyway(course.skill_id)
                                }
                              >
                                Learn Anyway
                              </button>
                            </div>
                            {skipError && (
                              <p className="skip-error">{skipError}</p>
                            )}
                          </>
                        )}

                        {isFastTracked && (
                          <button
                            className="action-btn btn-fast-track w-full"
                            onClick={() =>
                              handleFastTrack(course.skill_id, course.title)
                            }
                          >
                            Jump to Quiz →
                          </button>
                        )}

                        {isUnlocked && (
                          <button
                            className="action-btn btn-start w-full"
                            onClick={() =>
                              handleLearnAnyway(course.skill_id)
                            }
                          >
                            Start Learning
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right — Recommendation Sidebar */}
        <div className="hidden lg:block w-80 shrink-0 h-full overflow-y-auto border-l border-white/10 pl-8">
          {roadmapId && (
            <RecommendationPanel
              currentRoadmapId={roadmapId}
              recommendedStart={recommendedStart}
              alternativeStarts={alternativeStarts}
            />
          )}
        </div>
      </div>
    </div>
  );
}
