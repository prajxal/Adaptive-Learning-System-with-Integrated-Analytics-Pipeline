import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { ROUTES } from "../constants/routes";
import { useProgress } from "../hooks/useProgress";

interface Course {
    id: string;
    title: string;
    difficulty_level: number;
}

import BACKEND_URL from "../../services/api";

export default function RoadmapDetailPage() {
    const { roadmapId } = useParams();
    const userId = localStorage.getItem("user_id") || "1";
    const navigate = useNavigate();

    const { getRoadmapProgress, getCourseProgress } = useProgress();

    const [courses, setCourses] = useState<Course[]>([]);
    const [skillStatuses, setSkillStatuses] = useState<Record<string, string>>({});
    const [coursesLoading, setCoursesLoading] = useState(true);

    useEffect(() => {
        async function loadCoursesAndStatus() {
            try {
                const tokenStr = localStorage.getItem("access_token");
                const headers: Record<string, string> = { "Content-Type": "application/json" };
                if (tokenStr) headers["Authorization"] = `Bearer ${tokenStr}`;

                // Fetch Course List
                const res = await fetch(`${BACKEND_URL}/courses?roadmap_id=${roadmapId}`, { headers });
                if (!res.ok) throw new Error("Failed to fetch courses");
                const data = await res.json();
                setCourses(data);

                // Fetch Skill Graph Status mappings
                const statusRes = await fetch(`${BACKEND_URL}/skill-graph/${roadmapId}/status`, {
                    headers
                });

                if (statusRes.ok) {
                    const statusData = await statusRes.json();
                    const statusMap: Record<string, string> = {};
                    if (statusData.skills && Array.isArray(statusData.skills)) {
                        statusData.skills.forEach((s: any) => {
                            statusMap[s.skill_id] = s.status;
                        });
                    }
                    setSkillStatuses(statusMap);
                }
            } catch (err) {
                console.error(err);
            } finally {
                setCoursesLoading(false);
            }
        }

        if (roadmapId) {
            loadCoursesAndStatus();
        }
    }, [roadmapId]);

    if (coursesLoading) {
        return (
            <div className="roadmap-detail-root flex items-center justify-center min-h-[50vh]">
                <style>{`
                    .roadmap-detail-root {
                        --bg-primary: #0a0a0f;
                        --text-muted: #64748b;
                        background-color: var(--bg-primary);
                    }
                `}</style>
                <div style={{ color: 'var(--text-muted)' }}>Loading roadmap tracks...</div>
            </div>
        );
    }

    const courseMetaForProgress = courses.map(c => ({ id: c.id, total_resources: 5 }));
    const progress = getRoadmapProgress(roadmapId || "", courseMetaForProgress);

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

                .roadmap-detail-content {
                    position: relative;
                    z-index: 1;
                    max-width: 1000px;
                    margin: 0 auto;
                    padding: 3rem 1.5rem;
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

                .back-btn {
                    color: var(--text-muted);
                    transition: color 0.2s ease;
                }
                
                .back-btn:hover {
                    color: var(--text-primary);
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
                .status-completed {
                    background-color: #22c55e;
                    color: white;
                }
                .status-unlocked {
                    background-color: #6366f1;
                    color: white;
                }
                .status-locked {
                    background-color: #1e1e2e;
                    color: var(--text-muted);
                }
            `}</style>

            <div className="roadmap-detail-bg"></div>

            <div className="roadmap-detail-content space-y-10">
                <Link to={ROUTES.DASHBOARD} className="back-btn inline-flex items-center gap-2 font-medium text-sm mb-2">
                    <span>←</span> Back
                </Link>

                <div>
                    <h1 className="title-font text-4xl md:text-5xl font-bold capitalize mb-3 tracking-tight">
                        {roadmapId?.replace(/-/g, ' ')}
                    </h1>
                    <p className="text-lg" style={{ color: 'var(--text-muted)' }}>
                        {courses.length} topics in this track
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {courses.length === 0 ? (
                        <div className="col-span-1 md:col-span-2 py-12 text-center" style={{ color: 'var(--text-muted)' }}>
                            No topics found for this roadmap
                        </div>
                    ) : (
                        courses.map((course) => {
                            const status = skillStatuses[course.id] || "locked";
                            const cProg = getCourseProgress(course.id, 5);

                            const isCompleted = status === "completed";
                            const isUnlocked = status === "unlocked";
                            const isLocked = status === "locked";

                            return (
                                <div
                                    key={course.id}
                                    className={`course-card ${isLocked ? 'locked' : 'interactive cursor-pointer'}`}
                                    onClick={(e) => {
                                        if (isLocked) {
                                            e.preventDefault();
                                            return;
                                        }
                                        navigate(ROUTES.COURSE(course.id));
                                    }}
                                >
                                    <div className="flex justify-between items-start mb-6">
                                        <h3 className="title-font text-xl font-bold leading-tight pr-4" style={{ color: 'var(--text-primary)' }}>
                                            {course.title}
                                        </h3>
                                        <div className="shrink-0">
                                            {isCompleted ? (
                                                <div className="status-badge status-completed">✓ Mastered</div>
                                            ) : isUnlocked ? (
                                                <div className="status-badge status-unlocked"><span style={{ fontSize: '8px' }}>●</span> Unlocked</div>
                                            ) : (
                                                <div className="status-badge status-locked">🔒 Locked</div>
                                            )}
                                        </div>
                                    </div>

                                    <div className="mb-8" style={{ color: 'var(--text-muted)' }}>
                                        <span className="text-sm font-medium">Difficulty Level {course.difficulty_level}</span>
                                    </div>

                                    <div className="mt-auto flex flex-col gap-3">
                                        <div className="flex items-center justify-between text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
                                            <span>Progress</span>
                                            <span>{!isLocked ? `${cProg.percentage}%` : '0%'}</span>
                                        </div>
                                        <div className="w-full h-[3px] rounded-full overflow-hidden" style={{ backgroundColor: 'var(--border)' }}>
                                            <div
                                                className="h-full rounded-full transition-all duration-500"
                                                style={{
                                                    backgroundColor: 'var(--accent-primary)',
                                                    width: !isLocked ? `${cProg.percentage}%` : '0%'
                                                }}
                                            />
                                        </div>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        </div>
    );
}
