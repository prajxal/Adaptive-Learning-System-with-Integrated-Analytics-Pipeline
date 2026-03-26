import React from "react";
import { BookOpen, AlertTriangle, TrendingUp, Zap } from "lucide-react";
import { Link } from "react-router-dom";

interface Skill {
  roadmap_id: string;
  progress_percent?: number;
  completed_courses?: number;
  total_courses?: number;
  trust_score?: number;
}

interface RecommendedCourse {
  id: string;
  title: string;
  roadmap_id: string;
}

interface LearningInsightsCardProps {
  skills: Skill[];
  githubConnected: boolean;
  recommendedCourse?: RecommendedCourse | null;
  loading?: boolean;
}

const formatRoadmapName = (id: string) =>
  id.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export default function LearningInsightsCard({
  skills,
  githubConnected,
  recommendedCourse,
  loading = false,
}: LearningInsightsCardProps) {
  // Descriptive: what the user has completed
  const totalCompleted = skills.reduce((sum, s) => sum + (s.completed_courses || 0), 0);
  const totalCourses = skills.reduce((sum, s) => sum + (s.total_courses || 0), 0);
  const activeRoadmaps = skills.filter((s) => (s.progress_percent || 0) > 0).length;

  // Diagnostic: struggle areas — skills with lowest trust_score that are above baseline
  const engagedSkills = skills.filter((s) => (s.trust_score || 800) !== 800);
  const sortedByScore = [...skills].sort(
    (a, b) => (a.trust_score || 800) - (b.trust_score || 800)
  );
  const struggleAreas = sortedByScore
    .filter((s) => (s.trust_score || 800) < 950)
    .slice(0, 3);

  // Prescriptive: conditional action nudges
  const prescriptiveActions: string[] = [];
  if (!githubConnected)
    prescriptiveActions.push("Connect GitHub to improve skill detection accuracy.");
  if (skills.length === 0)
    prescriptiveActions.push("Upload your resume to auto-detect your skills.");
  const inProgressCount = skills.filter(
    (s) => (s.progress_percent || 0) > 0 && (s.progress_percent || 0) < 100
  ).length;
  if (inProgressCount > 0)
    prescriptiveActions.push("Take a quiz on an active course to update your Elo rating.");
  if (prescriptiveActions.length === 0)
    prescriptiveActions.push("Keep learning — you're making great progress!");

  const panels = [
    {
      icon: BookOpen,
      color: "#6366f1",
      bg: "rgba(99,102,241,0.08)",
      borderColor: "rgba(99,102,241,0.2)",
      label: "What You've Done",
      tag: "Descriptive",
      content:
        loading ? (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>Loading...</p>
        ) : skills.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            No activity yet. Start a roadmap.
          </p>
        ) : (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span style={{ color: "var(--text-muted)" }}>Courses completed</span>
              <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
                {totalCompleted} / {totalCourses}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span style={{ color: "var(--text-muted)" }}>Active roadmaps</span>
              <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
                {activeRoadmaps}
              </span>
            </div>
          </div>
        ),
    },
    {
      icon: AlertTriangle,
      color: "#f59e0b",
      bg: "rgba(245,158,11,0.08)",
      borderColor: "rgba(245,158,11,0.2)",
      label: "Struggle Areas",
      tag: "Diagnostic",
      content:
        loading ? (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>Loading...</p>
        ) : struggleAreas.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            {engagedSkills.length === 0
              ? "Take quizzes to identify struggle areas."
              : "No struggle areas detected — great work!"}
          </p>
        ) : (
          <div className="space-y-1.5">
            {struggleAreas.map((s) => (
              <div key={s.roadmap_id} className="flex justify-between text-sm">
                <span style={{ color: "var(--text-muted)" }}>
                  {formatRoadmapName(s.roadmap_id)}
                </span>
                <span className="font-medium" style={{ color: "#f59e0b" }}>
                  Elo {Math.round(s.trust_score || 800)}
                </span>
              </div>
            ))}
          </div>
        ),
    },
    {
      icon: TrendingUp,
      color: "#10b981",
      bg: "rgba(16,185,129,0.08)",
      borderColor: "rgba(16,185,129,0.2)",
      label: "Likely Next",
      tag: "Predictive",
      content:
        loading ? (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>Loading...</p>
        ) : recommendedCourse ? (
          <div>
            <p className="text-sm font-medium mb-1" style={{ color: "var(--text-primary)" }}>
              {recommendedCourse.title}
            </p>
            <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>
              in {formatRoadmapName(recommendedCourse.roadmap_id)}
            </p>
            <Link
              to={`/course/${recommendedCourse.id}`}
              className="inline-block text-xs font-semibold px-3 py-1 rounded-full transition-colors"
              style={{ backgroundColor: "rgba(16,185,129,0.15)", color: "#10b981" }}
            >
              Start →
            </Link>
          </div>
        ) : (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Start a roadmap to get course predictions.
          </p>
        ),
    },
    {
      icon: Zap,
      color: "#ec4899",
      bg: "rgba(236,72,153,0.08)",
      borderColor: "rgba(236,72,153,0.2)",
      label: "Next Best Actions",
      tag: "Prescriptive",
      content: (
        <ul className="space-y-1.5">
          {prescriptiveActions.map((action, i) => (
            <li key={i} className="text-sm" style={{ color: "var(--text-muted)" }}>
              <span className="font-bold mr-1" style={{ color: "#ec4899" }}>›</span>
              {action}
            </li>
          ))}
        </ul>
      ),
    },
  ];

  return (
    <div className="dark-card p-6">
      <h2 className="title-font text-xl font-semibold mb-6">Learning Insights</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {panels.map(({ icon: Icon, color, bg, borderColor, label, tag, content }) => (
          <div
            key={tag}
            className="rounded-lg p-4"
            style={{ backgroundColor: bg, border: `1px solid ${borderColor}` }}
          >
            <div className="flex items-center gap-2 mb-2">
              <Icon className="w-3.5 h-3.5" style={{ color }} />
              <span
                className="text-[10px] font-bold tracking-widest uppercase"
                style={{ color }}
              >
                {tag}
              </span>
            </div>
            <p
              className="text-sm font-semibold mb-2.5"
              style={{ color: "var(--text-primary)" }}
            >
              {label}
            </p>
            {content}
          </div>
        ))}
      </div>
    </div>
  );
}
