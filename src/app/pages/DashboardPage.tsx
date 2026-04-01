import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getGithubStatus } from "../../services/githubApi";
import { getUserSkills } from "../../services/userApi";
import { getRoadmaps, Roadmap } from "../../services/roadmapApi";
import BACKEND_URL, { fetchWithAuth } from "../../services/api";
import { getDynamicRoadmapStatus, DynamicCourseNode } from "../../services/dynamicRoadmapApi";
import { useProgress } from "../hooks/useProgress";
import { BookOpen, Compass, ArrowRight, Map, Zap } from "lucide-react";
import { usePostHog } from "@posthog/react";
import LearningInsightsCard from "../../components/dashboard/LearningInsightsCard";
import SkillRadarChart from "../../components/dashboard/SkillRadarChart";
import { OnboardingWizard } from "../components/OnboardingWizard";
import { getCurrentUser, completeOnboarding } from "../../services/userApi";


interface RecommendedCourse {
  id: string;
  title: string;
  difficulty: number;
  roadmap_id: string;
}

const CARD_STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Sora:wght@400;500;600;700;800&display=swap');

  .dashboard-root {
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
  .dashboard-bg {
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(ellipse at 20% 0%, rgba(99,102,241,0.06) 0%, transparent 60%);
    pointer-events: none; z-index: 0;
  }
  .dashboard-content {
    position: relative; z-index: 1;
    max-width: 1000px; margin: 0 auto; padding: 3rem 1.5rem;
  }
  .title-font { font-family: 'Sora', sans-serif; }
  .dark-card {
    background-color: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 0.75rem;
  }
  .upload-zone {
    border: 1px dashed var(--border);
    transition: border-color 0.2s ease;
  }
  .upload-zone:hover { border-color: var(--accent-primary); cursor: pointer; }
  .upload-btn {
    background-color: #16161f;
    border: 1px solid var(--border);
    color: var(--text-primary);
    transition: border-color 0.2s ease;
  }
  .upload-btn:hover { border-color: var(--accent-primary); }
  .path-card {
    background-color: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 0.75rem;
    transition: all 0.2s ease;
    display: flex; flex-direction: column;
    text-decoration: none;
  }
  .path-card:hover {
    background-color: var(--bg-card-hover);
    border-color: var(--accent-primary);
    box-shadow: 0 0 24px rgba(99,102,241,0.12);
  }
  .section-label {
    display: flex; align-items: center; gap: 0.5rem;
    margin-bottom: 1rem;
  }
  .hero-card {
    border-radius: 1rem;
    background: linear-gradient(135deg, #3730a3 0%, #4f46e5 40%, #6366f1 100%);
    position: relative;
    overflow: hidden;
  }
  .hero-card::before {
    content: '';
    position: absolute;
    top: -40%;
    right: -10%;
    width: 400px;
    height: 400px;
    border-radius: 50%;
    background: rgba(255,255,255,0.04);
    pointer-events: none;
  }
  .hero-card::after {
    content: '';
    position: absolute;
    bottom: -30%;
    left: -5%;
    width: 300px;
    height: 300px;
    border-radius: 50%;
    background: rgba(255,255,255,0.03);
    pointer-events: none;
  }
`;

const getAccentColor = (title: string) => {
  const t = title.toLowerCase();
  if (t.includes("ai") || t.includes("machine learning")) return "#6366f1";
  if (t.includes("backend") || t.includes("back-end")) return "#3b82f6";
  if (t.includes("frontend") || t.includes("front-end")) return "#ec4899";
  if (t.includes("devops") || t.includes("cloud")) return "#10b981";
  if (t.includes("data")) return "#f59e0b";
  if (t.includes("mobile")) return "#06b6d4";
  return "#6366f1";
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const posthog = usePostHog();

  const [skills, setSkills] = useState<any[]>([]);
  const [roadmaps, setRoadmaps] = useState<Roadmap[]>([]);
  const [recommendation, setRecommendation] = useState<{
    user_xp: number;
    user_level: number;
    next_in_current_roadmap: RecommendedCourse[];
    suggested_new_roadmaps: string[];
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [githubConnected, setGithubConnected] = useState(false);
  const [recommendedCourseStatus, setRecommendedCourseStatus] = useState<DynamicCourseNode | null>(null);
  const [onboardingCompleted, setOnboardingCompleted] = useState(true); // default true to avoid flash
  const hasFetchedInitialDataRef = React.useRef(false);

  const { getLastAccessed } = useProgress();
  const lastAccessed = getLastAccessed();

  const fetchGithubStatus = async () => {
    try {
      const data = await getGithubStatus();
      setGithubConnected(data.connected);
    } catch {
      // non-critical
    }
  };

  const fetchSkills = async () => {
    try {
      const data = await getUserSkills();
      setSkills(data.skills || []);
      return data.skills || [];
    } catch {
      setSkills([]);
      return [];
    }
  };

  const fetchRecommendation = async (skillsList: any[]) => {
    try {
      const inProgress = skillsList
        .filter((s) => (s.progress_percent || 0) > 0 && (s.progress_percent || 0) < 100)
        .sort((a, b) => (b.progress_percent || 0) - (a.progress_percent || 0));
      const roadmapId = inProgress[0]?.roadmap_id || skillsList[0]?.roadmap_id;
      if (!roadmapId) return;
      const res = await fetchWithAuth(
        `${BACKEND_URL}/recommend/recommend?current_roadmap_id=${encodeURIComponent(roadmapId)}`
      );
      if (res.ok) {
        const data = await res.json();
        setRecommendation(data);

        // Fetch dynamic status for the recommended course to show contextual messaging
        const topCourse = data?.next_in_current_roadmap?.[0];
        if (topCourse?.id && topCourse?.roadmap_id) {
          try {
            const dynamicStatus = await getDynamicRoadmapStatus(topCourse.roadmap_id);
            const match = dynamicStatus.courses.find((c) => c.skill_id === topCourse.id);
            setRecommendedCourseStatus(match ?? null);
          } catch {
            // non-critical; dynamic status is best-effort
          }
        }
      }
    } catch {
      // non-critical; silently fail
    }
  };

  useEffect(() => {
    if (hasFetchedInitialDataRef.current) return;
    hasFetchedInitialDataRef.current = true;
    const fetchDashboardData = async () => {
      try {
        const [skillsResult, roadmapsResult, , userMe] = await Promise.all([
          fetchSkills(),
          getRoadmaps().catch(() => [] as Roadmap[]),
          fetchGithubStatus(),
          getCurrentUser().catch(() => ({ onboarding_completed: true })),
        ]);
        setRoadmaps(roadmapsResult);
        setOnboardingCompleted(Boolean((userMe as any).onboarding_completed));
        await fetchRecommendation(skillsResult);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboardData();
  }, []);

  const handleDismissOnboarding = async () => {
    setOnboardingCompleted(true);
    try {
      await completeOnboarding();
    } catch {
      // non-critical; UI already updated
    }
  };

  // ── Derived data ──────────────────────────────────────────────────
  const isNewUser = !loading && !onboardingCompleted && skills.length === 0 && !githubConnected;
  const startedSkillIds = new Set(skills.map((s) => s.roadmap_id));
  const continueLearning = skills.filter(
    (s) => (s.progress_percent || 0) > 0 && (s.progress_percent || 0) < 100
  );
  const completedPaths = skills.filter((s) => (s.progress_percent || 0) >= 100);
  const explorePaths = roadmaps.filter((r) => !startedSkillIds.has(r.id));
  const recommendedCourse = recommendation?.next_in_current_roadmap?.[0] ?? null;
  const suggestedNewRoadmaps = recommendation?.suggested_new_roadmaps ?? [];
  const explorePathIds = new Set(explorePaths.map((r) => r.id));
  const extraSuggested = suggestedNewRoadmaps.filter(
    (id) => !explorePathIds.has(id) && !startedSkillIds.has(id)
  );

  // Hero: derive progress for the last-accessed roadmap
  const heroRoadmapId = lastAccessed?.courseId?.split(":")?.[0] ?? null;
  const heroSkill = heroRoadmapId ? skills.find((s) => s.roadmap_id === heroRoadmapId) : null;
  const heroProgress = heroSkill?.progress_percent ?? 0;
  const heroHasSession = !!(lastAccessed?.courseId && lastAccessed?.resourceId);

  return (
    <div className="dashboard-root">
      <style>{CARD_STYLES}</style>
      <div className="dashboard-bg" />

      <div className="dashboard-content">

        {/* ── Page Header ── */}
        <div className="mb-8">
          <h1 className="title-font text-4xl md:text-5xl font-bold tracking-tight mb-2">
            Dashboard
          </h1>
          <p className="text-lg" style={{ color: "var(--text-muted)" }}>
            Your learning command center.
          </p>
        </div>

        {/* ── ONBOARDING WIZARD (new users only) ── */}
        {isNewUser && (
          <OnboardingWizard
            githubConnected={githubConnected}
            hasSkills={skills.length > 0}
            onDismiss={handleDismissOnboarding}
          />
        )}

        {/* ── 1. CONTINUE LEARNING HERO ── */}
        <div className="mb-10">
          {loading ? (
            <div className="hero-card p-8 h-[160px] animate-pulse opacity-50" />
          ) : heroHasSession ? (
            /* Active session hero */
            <div className="hero-card p-7 sm:p-8">
              <div className="relative z-10 flex flex-col sm:flex-row gap-6 justify-between">
                <div className="flex-1 min-w-0">
                  <p
                    className="text-[11px] font-bold tracking-[0.1em] uppercase mb-3"
                    style={{ color: "rgba(255,255,255,0.5)" }}
                  >
                    Continue Learning
                  </p>
                  <h2 className="title-font text-2xl sm:text-3xl font-bold text-white tracking-tight mb-1 truncate">
                    {lastAccessed!.courseTitle || heroRoadmapId?.replace(/-/g, " ")}
                  </h2>
                  {lastAccessed!.resourceTitle && (
                    <p className="text-sm mb-5 truncate" style={{ color: "rgba(255,255,255,0.55)" }}>
                      Last visited: {lastAccessed!.resourceTitle}
                    </p>
                  )}

                  {/* Progress bar */}
                  <div className="flex items-center gap-3 max-w-xs">
                    <div
                      className="flex-1 h-[5px] rounded-full overflow-hidden"
                      style={{ backgroundColor: "rgba(255,255,255,0.15)" }}
                    >
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${heroProgress}%`,
                          backgroundColor: "rgba(255,255,255,0.85)",
                          transition: "width 0.6s ease",
                        }}
                      />
                    </div>
                    <span
                      className="text-xs font-bold shrink-0"
                      style={{ color: "rgba(255,255,255,0.7)" }}
                    >
                      {Math.round(heroProgress)}%
                    </span>
                  </div>
                </div>

                <div className="flex sm:flex-col items-start sm:items-end justify-between sm:justify-center gap-3 shrink-0">
                  <button
                    onClick={() => {
                      posthog?.capture("continue_learning_clicked", {
                        course_title: lastAccessed!.courseTitle,
                        course_id: lastAccessed!.courseId,
                      });
                      navigate(`/course/${lastAccessed!.courseId}/resource/${lastAccessed!.resourceId}`);
                    }}
                    className="bg-white font-bold py-2.5 px-6 rounded-xl text-sm transition-all shadow-md whitespace-nowrap"
                    style={{ color: "#4f46e5" }}
                    onMouseOver={(e) => {
                      e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.9)";
                      e.currentTarget.style.transform = "translateY(-1px)";
                    }}
                    onMouseOut={(e) => {
                      e.currentTarget.style.backgroundColor = "white";
                      e.currentTarget.style.transform = "translateY(0)";
                    }}
                  >
                    Resume Learning →
                  </button>
                  {heroSkill && (
                    <span
                      className="text-xs font-medium"
                      style={{ color: "rgba(255,255,255,0.45)" }}
                    >
                      {heroSkill.completed_courses || 0} / {heroSkill.total_courses || 0} topics done
                    </span>
                  )}
                </div>
              </div>
            </div>
          ) : (
            /* No active session — Start Your Journey hero */
            <div
              className="hero-card p-7 sm:p-8 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6"
              style={{ background: "linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #3730a3 100%)" }}
            >
              <div className="relative z-10">
                <p
                  className="text-[11px] font-bold tracking-[0.1em] uppercase mb-3"
                  style={{ color: "rgba(255,255,255,0.45)" }}
                >
                  Get Started
                </p>
                <h2 className="title-font text-2xl sm:text-3xl font-bold text-white tracking-tight mb-1">
                  Start your learning journey
                </h2>
                <p className="text-sm" style={{ color: "rgba(255,255,255,0.5)" }}>
                  Pick a roadmap and we'll guide you step by step.
                </p>
              </div>
              <button
                onClick={() => {
                  posthog?.capture("start_journey_clicked");
                  navigate("/roadmaps");
                }}
                className="relative z-10 bg-white font-bold py-2.5 px-6 rounded-xl text-sm transition-all shadow-md whitespace-nowrap shrink-0"
                style={{ color: "#3730a3" }}
                onMouseOver={(e) => {
                  e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.9)";
                  e.currentTarget.style.transform = "translateY(-1px)";
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.backgroundColor = "white";
                  e.currentTarget.style.transform = "translateY(0)";
                }}
              >
                Browse Learning Paths →
              </button>
            </div>
          )}
        </div>

        {/* ── 2. RECOMMENDED NEXT STEP ── */}
        <div className="mb-10">
          <div className="section-label">
            <TrendingUpIcon className="w-4 h-4" color="#10b981" />
            <h3 className="title-font text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
              Recommended Next Step
            </h3>
          </div>

          {loading ? (
            <div className="dark-card h-[96px] animate-pulse" />
          ) : recommendedCourse ? (
            <div className="space-y-3">
              <Link
                to={`/course/${recommendedCourse.id}`}
                className="path-card p-5 flex items-center justify-between group"
                onClick={() =>
                  posthog?.capture("recommended_course_clicked", { course_id: recommendedCourse.id })
                }
              >
                <div>
                  <p
                    className="text-xs font-semibold mb-1 uppercase tracking-widest"
                    style={{ color: "#10b981" }}
                  >
                    Next Up · {recommendedCourse.roadmap_id.replace(/-/g, " ")}
                  </p>
                  <h4 className="title-font font-bold" style={{ color: "var(--text-primary)" }}>
                    {recommendedCourse.title}
                  </h4>
                  {recommendedCourseStatus?.status === "skippable" && (
                    <p className="flex items-center gap-1 mt-1.5 text-xs font-medium" style={{ color: "#f59e0b" }}>
                      <Zap className="w-3 h-3 shrink-0" />
                      You might already know this — skip it or verify with a quiz.
                    </p>
                  )}
                  {recommendedCourseStatus?.status === "fast_tracked" && (
                    <p className="flex items-center gap-1 mt-1.5 text-xs font-medium" style={{ color: "#60a5fa" }}>
                      <Zap className="w-3 h-3 shrink-0" />
                      Your profile suggests some familiarity — jump straight to the quiz.
                    </p>
                  )}
                </div>
                <span
                  className="shrink-0 ml-4 text-xs font-semibold px-3 py-1.5 rounded-full border whitespace-nowrap"
                  style={{
                    backgroundColor: "rgba(16,185,129,0.1)",
                    color: "#10b981",
                    borderColor: "rgba(16,185,129,0.25)",
                  }}
                >
                  Start →
                </span>
              </Link>

              {(recommendation?.next_in_current_roadmap?.slice(1, 3) ?? []).map((alt) => (
                <Link
                  key={alt.id}
                  to={`/course/${alt.id}`}
                  className="path-card p-4 flex items-center justify-between group"
                  onClick={() =>
                    posthog?.capture("alternative_course_clicked", { course_id: alt.id })
                  }
                >
                  <div>
                    <p className="text-xs mb-0.5" style={{ color: "var(--text-muted)" }}>
                      Alternative · {alt.roadmap_id.replace(/-/g, " ")}
                    </p>
                    <h4 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                      {alt.title}
                    </h4>
                  </div>
                  <ArrowRight
                    className="w-4 h-4 shrink-0 ml-3 opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ color: "var(--text-muted)" }}
                  />
                </Link>
              ))}
            </div>
          ) : (
            <div className="dark-card p-6 flex flex-col sm:flex-row items-center justify-between gap-4" style={{ borderStyle: "dashed" }}>
              <div>
                <p className="text-sm font-medium mb-1" style={{ color: "var(--text-primary)" }}>
                  No recommendations yet
                </p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {skills.length === 0 && !githubConnected
                    ? "Connect GitHub or upload your resume, then pick a roadmap to get personalised suggestions."
                    : "Start a learning path and your next recommended course will appear here."}
                </p>
              </div>
              <button
                onClick={() => navigate(skills.length === 0 && !githubConnected ? "/profile" : "/roadmaps")}
                className="shrink-0 text-xs font-semibold px-4 py-2 rounded-lg transition-all whitespace-nowrap"
                style={{ background: "rgba(99,102,241,0.12)", color: "#818cf8", border: "1px solid rgba(99,102,241,0.2)" }}
                onMouseOver={(e) => { e.currentTarget.style.background = "rgba(99,102,241,0.2)"; }}
                onMouseOut={(e) => { e.currentTarget.style.background = "rgba(99,102,241,0.12)"; }}
              >
                {skills.length === 0 && !githubConnected ? "Import Skills →" : "Browse Paths →"}
              </button>
            </div>
          )}
        </div>

        {/* ── 3. LEARNING PATHS ── */}
        <div className="mb-10">
          <h2 className="title-font text-2xl font-semibold mb-1">Learning Paths</h2>
          <p className="text-sm mb-7" style={{ color: "var(--text-muted)" }}>
            Pick up where you left off or discover something new.
          </p>

          {/* In Progress sub-section */}
          {(loading || continueLearning.length > 0) && (
            <div className="mb-8">
              <div className="section-label">
                <BookOpen className="w-4 h-4" style={{ color: "#6366f1" }} />
                <h3
                  className="title-font text-base font-semibold"
                  style={{ color: "var(--text-primary)" }}
                >
                  In Progress
                </h3>
                {completedPaths.length > 0 && (
                  <span
                    className="text-xs font-medium px-2 py-0.5 rounded-full ml-1"
                    style={{ backgroundColor: "rgba(16,185,129,0.1)", color: "#10b981" }}
                  >
                    {completedPaths.length} completed
                  </span>
                )}
              </div>

              {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[1, 2].map((i) => (
                    <div key={i} className="dark-card h-[130px] animate-pulse" />
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {continueLearning.map((skill) => (
                    <Link
                      key={skill.roadmap_id}
                      to={`/roadmap/${skill.roadmap_id}`}
                      className="path-card p-5 group cursor-pointer"
                    >
                      <div className="flex items-center gap-2.5 mb-1">
                        <div
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: getAccentColor(skill.roadmap_id) }}
                        />
                        <h4
                          className="title-font font-bold capitalize"
                          style={{ color: "var(--text-primary)" }}
                        >
                          {skill.roadmap_id.replace(/-/g, " ")}
                        </h4>
                      </div>
                      <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
                        {skill.completed_courses || 0} / {skill.total_courses || 0} topics
                      </p>
                      <div className="mt-auto">
                        <div className="flex justify-between items-center mb-1.5">
                          <span
                            className="text-xs font-semibold"
                            style={{ color: "var(--accent-primary)" }}
                          >
                            {Math.round(skill.progress_percent || 0)}%
                          </span>
                          <ArrowRight
                            className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity"
                            style={{ color: "var(--text-muted)" }}
                          />
                        </div>
                        <div
                          className="w-full h-[3px] rounded-full overflow-hidden"
                          style={{ backgroundColor: "var(--border)" }}
                        >
                          <div
                            className="h-full rounded-full"
                            style={{
                              backgroundColor: "var(--accent-primary)",
                              width: `${skill.progress_percent || 0}%`,
                              transition: "width 0.5s ease",
                            }}
                          />
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Explore sub-section */}
          <div>
            <div className="section-label">
              <Compass className="w-4 h-4" style={{ color: "#f59e0b" }} />
              <h3
                className="title-font text-base font-semibold"
                style={{ color: "var(--text-primary)" }}
              >
                Explore
              </h3>
            </div>

            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="dark-card h-[100px] animate-pulse" />
                ))}
              </div>
            ) : explorePaths.length === 0 && extraSuggested.length === 0 ? (
              <div className="dark-card p-5 flex items-center gap-4" style={{ borderStyle: "dashed" }}>
                <span className="text-xl shrink-0">🎉</span>
                <div>
                  <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                    You've explored all available roadmaps!
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                    Check back soon — new learning paths are added regularly.
                  </p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {explorePaths.slice(0, 6).map((roadmap) => (
                  <Link
                    key={roadmap.id}
                    to={`/roadmap/${roadmap.id}`}
                    className="path-card p-5 group"
                    onClick={() =>
                      posthog?.capture("explore_path_clicked", { roadmap_id: roadmap.id })
                    }
                  >
                    <div className="flex items-center gap-2.5 mb-1">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: getAccentColor(roadmap.id) }}
                      />
                      <h4
                        className="title-font font-bold capitalize"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {roadmap.id.replace(/-/g, " ")}
                      </h4>
                    </div>
                    <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
                      {roadmap.topic_count} topics
                    </p>
                    <div
                      className="text-xs font-medium px-2.5 py-1 rounded-full inline-block"
                      style={{ backgroundColor: "rgba(245,158,11,0.1)", color: "#f59e0b" }}
                    >
                      Not Started
                    </div>
                  </Link>
                ))}
                {extraSuggested.slice(0, 3).map((id) => (
                  <Link
                    key={id}
                    to={`/roadmap/${id}`}
                    className="path-card p-5 group"
                    onClick={() =>
                      posthog?.capture("suggested_path_clicked", { roadmap_id: id })
                    }
                  >
                    <div className="flex items-center gap-2.5 mb-1">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: getAccentColor(id) }}
                      />
                      <h4
                        className="title-font font-bold capitalize"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {id.replace(/-/g, " ")}
                      </h4>
                    </div>
                    <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
                      AI suggested
                    </p>
                    <div
                      className="text-xs font-medium px-2.5 py-1 rounded-full inline-block"
                      style={{ backgroundColor: "rgba(99,102,241,0.1)", color: "#6366f1" }}
                    >
                      Suggested
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── 4. LEARNING INSIGHTS ── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <LearningInsightsCard
            skills={skills}
            githubConnected={githubConnected}
            recommendedCourse={recommendedCourse}
            loading={loading}
          />
          <SkillRadarChart skills={skills} loading={loading} />
        </div>


      </div>
    </div>
  );
}

function TrendingUpIcon({ className, color }: { className?: string; color?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke={color || "currentColor"}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
      <polyline points="16 7 22 7 22 13" />
    </svg>
  );
}
