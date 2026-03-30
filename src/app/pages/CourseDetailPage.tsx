import { useParams, useNavigate } from "react-router-dom";
import { ROUTES } from "../constants/routes";
import { useEffect, useState } from "react";
import AppBreadcrumb from "../components/AppBreadcrumb";
import DataLoadingState from "../components/DataLoadingState";
import CourseDetailSkeleton from "../components/skeletons/CourseDetailSkeleton";

import { getClerkToken } from "../../services/api";
import { useProgress } from "../hooks/useProgress";
import { getSkillProfile, SkillProfile } from "../services/quizApi";
import BACKEND_URL from "../../services/api";
import { getDynamicRoadmapStatus } from "../../services/dynamicRoadmapApi";
import { PlayCircle, FileText, BookOpen } from "lucide-react";
import { usePostHog } from "@posthog/react";

type Course = {
  id: string;
  title: string;
  roadmap_id: string;
  difficulty_level: number | null;
  description?: string | null;
};

export default function CourseDetailPage() {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const posthog = usePostHog();
  const [course, setCourse] = useState<Course | null>(null);
  const [courseLoading, setCourseLoading] = useState(true);
  const [learningPath, setLearningPath] = useState<any[]>([]);
  const [pathLoading, setPathLoading] = useState(true);
  const [resources, setResources] = useState<{ primary: any, additional: any[] }>({ primary: null, additional: [] });
  const [resourcesLoading, setResourcesLoading] = useState(true);
  const [skillProfile, setSkillProfile] = useState<SkillProfile | null>(null);
  const [skillStatus, setSkillStatus] = useState<string>("locked");

  const { getResourceProgress, getCourseProgress } = useProgress();

  useEffect(() => {
    if (!courseId) return;

    getClerkToken().then(token => {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      fetch(`${BACKEND_URL}/courses/${courseId}`, { headers })
        .then((res) => res.json())
        .then((data) => { setCourse(data); setCourseLoading(false); })
        .catch(() => { setCourse(null); setCourseLoading(false); });

      fetch(`${BACKEND_URL}/learning-path/${courseId}`, { headers })
        .then((res) => res.json())
        .then((data) => {
          setLearningPath(data.path || []);
          setPathLoading(false);
        })
        .catch(() => setPathLoading(false));

      const roadmapId = courseId.split(":")[0];

      // Fetch Skill Graph Status
      getDynamicRoadmapStatus(roadmapId)
        .then((data) => {
          const currentSkill = data.courses.find((c) => c.skill_id === courseId);
          if (currentSkill) {
            const rawStatus = currentSkill.status;
            const mapped =
              rawStatus === "completed"
                ? "completed"
                : rawStatus === "locked"
                ? "locked"
                : "unlocked"; // covers unlocked, skippable, fast_tracked
            setSkillStatus(mapped);
          }
        })
        .catch(() => setSkillStatus("locked"));

      // Fetch Adaptive Skill Profile
      getSkillProfile(courseId).then(setSkillProfile);

      fetch(`${BACKEND_URL}/courses/${courseId}/resources`, { headers })
        .then((res) => res.json())
        .then((data) => {
          setResources(data || { primary: null, additional: [] });
          setResourcesLoading(false);
        })
        .catch(() => setResourcesLoading(false));
    });
  }, [courseId]);

  const getResourceIcon = (type: string) => {
    if (type === 'video') return <PlayCircle className="w-5 h-5" style={{ color: 'var(--accent-primary)' }} />;
    if (type === 'article') return <FileText className="w-5 h-5" style={{ color: 'var(--accent-primary)' }} />;
    return <BookOpen className="w-5 h-5" style={{ color: 'var(--accent-primary)' }} />;
  };

  if (courseLoading) {
    return (
      <div className="course-detail-root" style={{ backgroundColor: "#0a0a0f", minHeight: "100vh", position: "relative" }}>
        <DataLoadingState>
          <CourseDetailSkeleton />
        </DataLoadingState>
      </div>
    );
  }

  if (!course && !courseLoading) {
    return (
      <div
        className="flex items-center justify-center min-h-[50vh]"
        style={{ backgroundColor: "#0a0a0f", color: "#64748b" }}
      >
        Course not found.
      </div>
    );
  }

  const totalRes = (resources.primary ? 1 : 0) + (resources.additional?.length || 0);

  return (
    <div className="course-detail-root">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Sora:wght@400;500;600;700;800&display=swap');
        
        .course-detail-root {
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

        .course-detail-bg {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(ellipse at 20% 0%, rgba(99,102,241,0.06) 0%, transparent 60%);
            pointer-events: none;
            z-index: 0;
        }

        .course-detail-content {
            position: relative;
            z-index: 1;
            max-width: 1000px;
            margin: 0 auto;
            padding: 3rem 1.5rem;
        }

        .title-font {
            font-family: 'Sora', sans-serif;
        }

        .back-btn {
            color: var(--text-muted);
            transition: color 0.2s ease;
        }
        
        .back-btn:hover {
            color: var(--text-primary);
        }

        .dark-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 0.75rem;
        }

        .resource-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            transition: all 0.2s ease;
            border-radius: 0.75rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 1.25rem;
            cursor: pointer;
            text-decoration: none;
        }

        .resource-card:hover {
            border-color: var(--accent-primary);
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.375rem;
            padding: 0.25rem 0.625rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .pill-complete {
            background-color: rgba(34, 197, 94, 0.1);
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.2);
        }
        .pill-in-progress {
            background-color: rgba(99, 102, 241, 0.1);
            color: var(--accent-primary);
            border: 1px solid rgba(99, 102, 241, 0.2);
        }
        .pill-not-started {
            background-color: transparent;
            color: var(--text-muted);
            border: 1px solid var(--border);
        }
      `}</style>

      <div className="course-detail-bg"></div>

      <div className="course-detail-content space-y-10">
        <AppBreadcrumb segments={[
          { label: "Home", href: "/dashboard" },
          { label: "Learning Paths", href: "/roadmaps" },
          { label: course.roadmap_id.replace(/-/g, " "), href: ROUTES.ROADMAP(course.roadmap_id) },
          { label: course.title },
        ]} />

        {/* Page Header */}
        <div>
          <h1 className="title-font text-4xl md:text-5xl font-bold tracking-tight mb-3" style={{ color: 'var(--text-primary)' }}>
            {course.title}
          </h1>
          <p className="text-lg" style={{ color: 'var(--text-muted)' }}>
            {totalRes} resources in this course
          </p>
        </div>

        {/* Skill Status Banner */}
        {(() => {
          const progress = getCourseProgress(course.id, totalRes);
          const resourcesFinished = totalRes > 0 && progress.percentage === 100;
          const isUnlocked = skillStatus === "unlocked" || skillStatus === "completed" || resourcesFinished;

          if (skillStatus === "completed") {
            return (
              <div className="dark-card p-6 flex flex-col sm:flex-row justify-between items-center gap-4" style={{ borderLeft: '3px solid #22c55e' }}>
                <div className="font-semibold text-lg" style={{ color: '#22c55e' }}>✓ Skill Mastered</div>
                <button
                  onClick={() => { posthog?.capture('quiz_started', { course_id: courseId, course_title: course?.title, retake: true }); navigate(`/course/${courseId}/quiz`); }}
                  className="px-6 py-2.5 rounded-lg text-sm font-bold border transition-colors"
                  style={{ borderColor: 'var(--border)', color: 'var(--text-muted)', backgroundColor: 'transparent' }}
                  onMouseOver={(e) => { e.currentTarget.style.color = 'var(--text-primary)'; e.currentTarget.style.borderColor = 'var(--text-muted)' }}
                  onMouseOut={(e) => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.borderColor = 'var(--border)' }}
                >
                  Retake Quiz
                </button>
              </div>
            );
          }

          const isLocked = !isUnlocked && skillStatus === "locked";

          return (
            <div className="dark-card p-6 flex flex-col sm:flex-row justify-between items-center gap-4" style={{ borderLeft: `3px solid ${isLocked ? 'var(--border)' : 'var(--accent-primary)'}` }}>
              <div className="font-semibold text-lg" style={{ color: isLocked ? 'var(--text-muted)' : 'var(--text-primary)' }}>
                {isLocked ? '🔒 Complete prerequisites to unlock this topic' : 'Ready to test your knowledge?'}
              </div>
              <button
                onClick={() => {
                  if (!isLocked) {
                    posthog?.capture('quiz_started', { course_id: courseId, course_title: course?.title, retake: false });
                    navigate(`/course/${courseId}/quiz`);
                  }
                }}
                disabled={isLocked}
                title={isLocked ? "Complete prerequisites first" : ""}
                className={`px-8 py-2.5 rounded-lg text-sm font-bold transition-colors shadow-sm ${isLocked ? 'cursor-not-allowed opacity-50' : ''}`}
                style={{
                  backgroundColor: isLocked ? 'var(--bg-card-hover)' : 'var(--accent-primary)',
                  color: isLocked ? 'var(--text-muted)' : 'white',
                  border: isLocked ? '1px solid var(--border)' : 'none'
                }}
                onMouseOver={(e) => { if (!isLocked) e.currentTarget.style.backgroundColor = '#4f46e5'; }}
                onMouseOut={(e) => { if (!isLocked) e.currentTarget.style.backgroundColor = 'var(--accent-primary)'; }}
              >
                Take Quiz
              </button>
            </div>
          );
        })()}

        {/* Skill Metrics Row */}
        {skillProfile && (
          <div className="flex gap-4">
            <div className="dark-card p-4 sm:p-5 flex-1 max-w-[200px]">
              <div className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--accent-primary)' }}>Mastery</div>
              <div className="title-font text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
                {Math.min(100, Math.round(skillProfile.proficiency_level * (skillProfile.proficiency_level <= 1 ? 100 : 1)))}%
              </div>
            </div>
            <div className="dark-card p-4 sm:p-5 flex-1 max-w-[200px]">
              <div className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>Confidence</div>
              <div className="title-font text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
                {Math.min(100, Math.round(skillProfile.confidence * 100)) || 0}%
              </div>
            </div>
          </div>
        )}

        {/* Resources Section */}
        <div>
          <h2 className="title-font text-2xl font-semibold mb-6 mt-10">Learning Resources</h2>
          {resourcesLoading ? (
            <p style={{ color: 'var(--text-muted)' }}>Loading resources...</p>
          ) : (
            <div className="space-y-4">
              {totalRes === 0 ? (
                <div className="py-12 flex flex-col items-center justify-center text-center">
                  <BookOpen className="w-10 h-10 mb-4 opacity-50" style={{ color: 'var(--text-muted)' }} />
                  <p style={{ color: 'var(--text-muted)' }}>No resources available for this course yet</p>
                </div>
              ) : (
                (() => {
                  const allResources = [];
                  if (resources.primary) allResources.push(resources.primary);
                  if (resources.additional) allResources.push(...resources.additional);

                  return allResources.map((res: any) => {
                    const status = getResourceProgress(courseId as string, res.id);

                    let typeLabel = res.resource_type || 'article';

                    return (
                      <div
                        key={res.id}
                        className="resource-card group"
                        onClick={() => navigate(ROUTES.RESOURCE(courseId as string, res.id))}
                      >
                        <div className="flex items-center gap-4">
                          <div className="shrink-0">
                            {getResourceIcon(typeLabel)}
                          </div>
                          <div className="flex flex-col">
                            <span className="font-bold line-clamp-1" style={{ color: 'var(--text-primary)' }}>{res.title}</span>
                            <span className="text-[10px] uppercase font-bold tracking-wider mt-1" style={{ color: 'var(--text-muted)' }}>{typeLabel}</span>
                          </div>
                        </div>

                        <div className="shrink-0 ml-4 hidden sm:block">
                          {status === 'completed' && <span className="status-pill pill-complete">✓ Complete</span>}
                          {status === 'in_progress' && <span className="status-pill pill-in-progress">▶ In Progress</span>}
                          {status === 'not_started' && <span className="status-pill pill-not-started">○ Not Started</span>}
                        </div>
                      </div>
                    );
                  });
                })()
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
